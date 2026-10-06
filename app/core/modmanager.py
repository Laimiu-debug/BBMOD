"""游戏 data 目录的 mod 管理：安装/卸载/启用/禁用/快照恢复/profile。

安全红线：
- 只操作记录在案的文件（mod zip 与本软件自建目录），官方 data_*.dat 永不触碰；
- 每次文件操作写入审计日志 %APPDATA%/BBMOD/operations.log；
- 禁用 = 移出 data 目录到 bbmod_disabled/（游戏只挂载 data 内的 zip）。
"""
from __future__ import annotations

import copy
from contextlib import contextmanager
import datetime
import json
import tempfile
import threading
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from .modinfo import ModInfo, analyze_zip
from .local_mod_archive import staged_packages, validate_name
from .mod_transactions import ModTransaction, atomic_json

DISABLED_DIR = "bbmod_disabled"      # 用户手动禁用的 mod
STASH_DIR = "bbmod_seedgen_stash"    # 刷种子期间临时移出的 mod（自动管理）
PAYLOAD_MARK = "bbmod_payload.json"  # 注入 payload 的清单标记


def _now() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@dataclass
class InstalledMod:
    path: Path
    enabled: bool  # True=data 目录内；False=禁用目录
    info: ModInfo


@dataclass
class Snapshot:
    """data 目录 mod 状态快照（刷种子编排用）。"""
    moved: list[tuple[Path, Path]] = field(default_factory=list)  # (原位置, 临时位置)

    @property
    def empty(self) -> bool:
        return not self.moved


class ModManager:
    def __init__(self, game_root: Path) -> None:
        self.root = Path(game_root)
        self.data = self.root / "data"
        self.disabled_dir = self.root / DISABLED_DIR
        self.stash_dir = self.root / STASH_DIR
        self.audit_path = self.root.parent / "BBMOD_operations.log"
        self.transaction = ModTransaction(self.root)
        self._infos: dict[Path, tuple[tuple, ModInfo]] = {}
        self._infos_lock = threading.Lock()
        self._file_lock = threading.RLock()

    # ---------------- 基础 ----------------

    @contextmanager
    def file_access(self):
        """Serialize installed-file readers and writers; nested validation is allowed."""
        with self._file_lock:
            yield

    def analyze(self, path: Path) -> ModInfo:
        with self.file_access():
            return self._analyze(path)

    def _analyze(self, path: Path) -> ModInfo:
        """按 (路径, mtime, 大小, inode) 复用 zip 分析结果；返回副本，调用方可修改其字段。"""
        try:
            stat = path.stat()
        except OSError:
            return analyze_zip(path)
        signature = (stat.st_mtime_ns, stat.st_size, stat.st_ino)
        with self._infos_lock:
            cached = self._infos.get(path)
        if cached is None or cached[0] != signature:
            cached = (signature, analyze_zip(path))
            with self._infos_lock:
                self._infos[path] = cached
        return copy.copy(cached[1])

    def _prune_infos(self, keep: set[Path]) -> None:
        with self._infos_lock:
            for path in [p for p in self._infos if p not in keep]:
                del self._infos[path]

    def _audit(self, action: str, src: Path, dst: Path | None = None) -> None:
        line = f"[{_now()}] {action}: {src}" + (f" -> {dst}" if dst else "")
        try:
            self.audit_path.parent.mkdir(parents=True, exist_ok=True)
            with self.audit_path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
        except OSError:
            pass

    def scan(self, analyze: bool = True) -> list[InstalledMod]:
        """扫描 data 与禁用目录中的 mod。"""
        with self.file_access():
            return self._scan(analyze)

    def _scan(self, analyze: bool) -> list[InstalledMod]:
        mods: list[InstalledMod] = []
        from .preload_merge import FILENAME
        for f in sorted(self.data.glob("*.zip")):
            if f.name == FILENAME:
                continue
            mods.append(InstalledMod(path=f, enabled=True, info=self.analyze(f) if analyze else _stub_info(f)))
        for f in sorted(self.data.glob("*.rar")):
            mods.append(InstalledMod(path=f, enabled=True, info=_stub_info(f)))
        if self.disabled_dir.exists():
            for f in sorted(self.disabled_dir.glob("*.zip")) + sorted(self.disabled_dir.glob("*.rar")):
                mods.append(InstalledMod(path=f, enabled=False, info=self.analyze(f) if analyze else _stub_info(f)))
        if analyze:
            self._prune_infos({m.path for m in mods})
        return mods

    def installed_zip_names(self) -> set[str]:
        from .preload_merge import FILENAME
        return ({f.name for f in self.data.glob("*.zip")} | {f.name for f in self.data.glob("*.rar")}) - {FILENAME}

    def _apply(self, changes, *, validate=False, keep_backups=False):
        with self.file_access():
            return self._apply_locked(changes, validate=validate, keep_backups=keep_backups)

    def _apply_locked(self, changes, *, validate=False, keep_backups=False):
        from .diagnostics import diagnose_mods
        from .preload_merge import plan
        if validate:
            current = {m.path: m.info for m in self.scan() if m.enabled}
            previous = {(i.source, i.title) for i in diagnose_mods(list(current.values())).issues if i.severity == 'error'}
            incoming = set()
            for destination, source in changes.items():
                if destination.parent != self.data:
                    continue
                if source is None:
                    current.pop(destination, None)
                else:
                    info = self.analyze(source)
                    info.file_name = destination.name
                    current[destination] = info
                    incoming.add(destination.name)
            errors = [i for i in diagnose_mods(list(current.values())).issues
                      if i.severity == 'error' and ((i.source, i.title) not in previous or i.source in incoming)]
            if errors:
                raise ValueError('MOD 组合未通过兼容检查，未更改文件：\n' + '\n'.join(
                    f'{i.source}：{i.title}。{i.fix or ""}' for i in errors))
        with tempfile.TemporaryDirectory(prefix='bbmod-preload-') as temporary:
            plan(self.data, changes, Path(temporary))
            return self.transaction.apply(changes, keep_backups=keep_backups)

    # ---------------- 安装 / 卸载 / 启用 / 禁用 ----------------

    def install(self, src: Path, overwrite: bool = False) -> list[Path]:
        """安装 mod zip 到 data 目录；自动解出内嵌 zip（如 EIMO 内的 zbigmap007）。

        返回实际写入 data 的文件列表。
        """
        return self.install_many([src], overwrite=overwrite)

    def install_many(self, sources: list[Path], overwrite: bool = False) -> list[Path]:
        """Validate the entire selection before committing any package."""
        with tempfile.TemporaryDirectory(prefix='bbmod-install-') as temporary:
            packages = []
            for index, source in enumerate(sources):
                staging = Path(temporary) / str(index)
                staging.mkdir()
                packages.extend(staged_packages(source, staging))
            changes = {}
            seen = set()
            for package in packages:
                if package.name.casefold() in seen:
                    raise ValueError(f'所选 MOD 安装文件重名：{package.name}')
                seen.add(package.name.casefold())
                destination = self.data / package.name
                if (self.disabled_dir / package.name).exists():
                    raise FileExistsError(f'{package.name} 已安装但已禁用，请先启用或卸载。')
                if destination.exists() and not overwrite:
                    raise FileExistsError(f'{package.name} 已安装，已取消本次安装。')
                changes[destination] = package
            destinations = list(changes)
            self._apply(changes, validate=True)
        for destination in destinations:
            self._audit('install', destination)
        return destinations

    def _move(self, src: Path, dst_dir: Path) -> Path:
        dst_dir.mkdir(parents=True, exist_ok=True)
        dst = dst_dir / src.name
        if dst.exists():  # 重名防覆盖
            stem, suffix = src.stem, src.suffix
            dst = dst_dir / f"{stem}_{datetime.datetime.now():%H%M%S}{suffix}"
        src.rename(dst)
        self._audit("move", src, dst)
        return dst

    def disable(self, name: str) -> Path:
        """禁用：data/x.zip → bbmod_disabled/。"""
        return self.set_enabled_many([name], False)[0]

    def enable(self, name: str) -> Path:
        """启用：bbmod_disabled/x.zip → data/。"""
        return self.set_enabled_many([name], True)[0]

    def set_enabled_many(self, names: list[str], enabled: bool) -> list[Path]:
        changes, destinations = {}, []
        for name in dict.fromkeys(names):
            validate_name(name)
            src = (self.disabled_dir if enabled else self.data) / name
            destination = (self.data if enabled else self.disabled_dir) / name
            if not src.is_file():
                raise FileNotFoundError(name)
            if destination.exists():
                raise FileExistsError(f'目标目录已有同名文件：{name}，请先处理重复文件。')
            changes.update({destination: src, src: None})
            destinations.append(destination)
        self._apply(changes, validate=True)
        for destination in destinations:
            self._audit('enable' if enabled else 'disable', destination)
        return destinations

    def uninstall(self, name: str, *, from_disabled: bool = False) -> Path:
        """删除所选文件及关联在线/汉化记录；保留仓库原包和存档。"""
        validate_name(name)
        target = (self.disabled_dir if from_disabled else self.data) / name
        if not target.is_file():
            raise FileNotFoundError(f'{name} 已不存在，请刷新。')
        changes = {target: None}
        from .online_catalog import OnlineInstaller
        installer = OnlineInstaller(self)
        state = installer.state()
        other = (self.data if from_disabled else self.disabled_dir) / name
        keys = [key for key in state['mods'] if key.casefold() == name.casefold()]
        with tempfile.TemporaryDirectory(prefix='bbmod-uninstall-') as temporary:
            from .localization_profiles import LocalizationProfiles
            localizations = LocalizationProfiles(self.root)
            record = localizations.stage_uninstall(target, Path(temporary))
            if record is not None:
                changes[localizations.registry] = record
            if keys and not other.exists():
                for key in keys:
                    del state['mods'][key]
                receipt = Path(temporary) / 'record.json'
                atomic_json(receipt, state)
                changes[installer.state_path] = receipt
            self._apply(changes, validate=True)
        self._audit('uninstall', target)
        return target

    def delete_permanently(self, name: str, from_disabled: bool = False) -> None:
        p = (self.disabled_dir if from_disabled else self.data) / validate_name(name)
        if p.exists():
            self.uninstall(name, from_disabled=from_disabled)

    # ---------------- 快照（刷种子编排） ----------------

    def stash_all_mods(self) -> Snapshot:
        """把 data 内全部 mod zip 移到刷种子暂存目录，返回快照以便恢复。"""
        snap = Snapshot()
        for f in sorted(self.data.glob("*.zip")) + sorted(self.data.glob("*.rar")):
            snap.moved.append((f, self._move(f, self.stash_dir)))
        self._audit("stash-all", self.data, self.stash_dir)
        return snap

    def restore_snapshot(self, snap: Snapshot) -> int:
        """恢复快照：把暂存的 mod 移回 data。返回恢复数量。"""
        count = 0
        for original, stashed in snap.moved:
            if not stashed.exists():
                continue
            target = self.data / original.name
            if not target.exists():
                stashed.rename(target)
                self._audit("restore", stashed, target)
                count += 1
        return count

    def cleanup_stash(self) -> int:
        """孤儿暂存清理（快照丢失时）：全部移回 data。"""
        count = 0
        if self.stash_dir.exists():
            for f in list(self.stash_dir.iterdir()):
                if f.is_file():
                    target = self.data / f.name
                    if not target.exists():
                        f.rename(target)
                        count += 1
            try:
                self.stash_dir.rmdir()
            except OSError:
                pass
        self._audit("stash-cleanup", self.stash_dir, self.data)
        return count

    def has_orphan_stash(self) -> bool:
        return self.stash_dir.exists() and any(self.stash_dir.iterdir())

    # ---------------- profile（mod 集合方案） ----------------

    def _profiles_path(self) -> Path:
        return self.disabled_dir / "profiles.json"

    def save_profile(self, name: str) -> dict:
        """把当前 data 目录的 mod 集合保存为命名方案。"""
        name = self._profile_name(name)
        self._check_profile_write()
        profiles = self.load_profiles()
        profiles[name] = {
            "enabled": sorted(self.installed_zip_names()),
            "saved_at": datetime.datetime.now().isoformat(timespec="seconds"),
        }
        self._profiles_path().parent.mkdir(parents=True, exist_ok=True)
        atomic_json(self._profiles_path(), profiles)
        self._audit("profile-save", self._profiles_path(), None)
        return profiles[name]

    @staticmethod
    def _profile_name(name: str) -> str:
        from .profile_protocol import text
        return text(name, 100, required=True)

    def _check_profile_write(self):
        if self.transaction.journal.exists():
            raise ValueError('请先恢复上次 MOD 操作。')

    def rename_profile(self, name: str, new_name: str) -> None:
        self._check_profile_write()
        new_name = self._profile_name(new_name)
        profiles = self.load_profiles()
        if name not in profiles:
            raise ValueError('方案已不存在，请刷新列表。')
        if name == new_name:
            return
        if new_name in profiles:
            raise ValueError('已有同名方案，请换一个名称。')
        profiles = {new_name if key == name else key: value for key, value in profiles.items()}
        atomic_json(self._profiles_path(), profiles)
        self._audit('profile-rename', self._profiles_path(), None)

    def delete_profile(self, name: str) -> None:
        """Remove only the saved configuration, never installed files or hosted data."""
        self._check_profile_write()
        profiles = self.load_profiles()
        if name not in profiles:
            raise ValueError('方案已不存在，请刷新列表。')
        del profiles[name]
        atomic_json(self._profiles_path(), profiles)
        self._audit('profile-delete', self._profiles_path(), None)

    def record_profile_share(self, name: str, origin: str, identity: str) -> None:
        from .online_catalog import site_origin
        from .shared_profiles import profile_identity
        self._check_profile_write()
        profiles = self.load_profiles()
        if name not in profiles:
            raise ValueError('本地方案已不存在。')
        profiles[name].update(published_id=profile_identity(identity, origin), published_origin=site_origin(origin))
        atomic_json(self._profiles_path(), profiles)

    def load_profiles(self) -> dict:
        try:
            return json.loads(self._profiles_path().read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    def preview_profile(self, name: str) -> dict:
        profiles = self.load_profiles()
        if name not in profiles:
            raise KeyError(f"方案 {name} 不存在")
        want: set[str] = set(profiles[name]["enabled"])
        for item in want:
            validate_name(item)
        mods = self.scan(analyze=False)
        from .preload_merge import FILENAME
        enabled = {m.path.name for m in mods if m.enabled and m.path.name != FILENAME}
        disabled = {m.path.name for m in mods if not m.enabled}
        missing = want - enabled - disabled
        if missing:
            raise FileNotFoundError('方案中的 MOD 已卸载或缺失：' + '、'.join(sorted(missing)))
        if enabled & disabled:
            raise ValueError('启用与禁用目录存在同名文件，请先处理：' + '、'.join(sorted(enabled & disabled)))
        return {'enable': sorted(want - enabled), 'disable': sorted(enabled - want)}

    def apply_profile(self, name: str, *, expected: dict | None = None) -> tuple[int, int]:
        """预检后切换，失败回滚；中断时可从持久化记录恢复。"""
        plan = self.preview_profile(name)
        if expected is not None and plan != expected:
            raise ValueError('MOD 状态已改变，请重新预览方案。')
        changes = {}
        for item in plan['enable']:
            changes[self.data / item] = self.disabled_dir / item
            changes[self.disabled_dir / item] = None
        for item in plan['disable']:
            changes[self.disabled_dir / item] = self.data / item
            changes[self.data / item] = None
        self._apply(changes, validate=True)
        self._audit("profile-apply", self._profiles_path(), self.data)
        return len(plan['enable']), len(plan['disable'])

    def installation_states(self, mods: list[InstalledMod] | None = None) -> dict[str, str]:
        states = {}
        for mod in self.scan(analyze=False) if mods is None else mods:
            key = mod.path.name.casefold()
            value = '已启用' if mod.enabled else '已禁用'
            states[key] = '同名重复安装' if key in states else value
        return states


def _stub_info(f: Path) -> ModInfo:
    return ModInfo(path=f, file_name=f.name, size=f.stat().st_size if f.exists() else 0)

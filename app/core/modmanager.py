"""游戏 data 目录的 mod 管理：安装/卸载/启用/禁用/快照恢复/profile。

安全红线：
- 只操作记录在案的文件（mod zip 与本软件自建目录），官方 data_*.dat 永不触碰；
- 每次文件操作写入审计日志 %APPDATA%/BBMOD/operations.log；
- 禁用 = 移出 data 目录到 bbmod_disabled/（游戏只挂载 data 内的 zip）。
"""
from __future__ import annotations

import datetime
import json
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from .modinfo import ModInfo, analyze_zip

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

    # ---------------- 基础 ----------------

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
        mods: list[InstalledMod] = []
        for f in sorted(self.data.glob("*.zip")):
            mods.append(InstalledMod(path=f, enabled=True, info=analyze_zip(f) if analyze else _stub_info(f)))
        for f in sorted(self.data.glob("*.rar")):
            mods.append(InstalledMod(path=f, enabled=True, info=_stub_info(f)))
        if self.disabled_dir.exists():
            for f in sorted(self.disabled_dir.glob("*.zip")) + sorted(self.disabled_dir.glob("*.rar")):
                mods.append(InstalledMod(path=f, enabled=False, info=analyze_zip(f) if analyze else _stub_info(f)))
        return mods

    def installed_zip_names(self) -> set[str]:
        return {f.name for f in self.data.glob("*.zip")} | {f.name for f in self.data.glob("*.rar")}

    # ---------------- 安装 / 卸载 / 启用 / 禁用 ----------------

    def install(self, src: Path, overwrite: bool = False) -> list[Path]:
        """安装 mod zip 到 data 目录；自动解出内嵌 zip（如 EIMO 内的 zbigmap007）。

        返回实际写入 data 的文件列表。
        """
        src = Path(src)
        written: list[Path] = []
        dst = self.data / src.name
        if dst.exists() and not overwrite:
            raise FileExistsError(f"{src.name} 已存在于 data 目录")
        self.data.mkdir(exist_ok=True)
        dst.write_bytes(src.read_bytes())
        self._audit("install", src, dst)
        written.append(dst)

        if src.suffix.lower() == ".zip":
            with zipfile.ZipFile(src) as zf:
                for entry in zf.namelist():
                    if entry.lower().endswith(".zip"):
                        inner_name = Path(entry).name
                        inner_dst = self.data / inner_name
                        if not inner_dst.exists() or overwrite:
                            inner_dst.write_bytes(zf.read(entry))
                            self._audit("install-nested", src / entry, inner_dst)
                            written.append(inner_dst)
        return written

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
        src = self.data / name
        if not src.exists():
            raise FileNotFoundError(name)
        return self._move(src, self.disabled_dir)

    def enable(self, name: str) -> Path:
        """启用：bbmod_disabled/x.zip → data/。"""
        src = self.disabled_dir / name
        if not src.exists():
            raise FileNotFoundError(name)
        return self._move(src, self.data)

    def uninstall(self, name: str) -> Path:
        """卸载：从 data 移到禁用目录（可随时删档或再启用，不做永久删除）。"""
        return self.disable(name)

    def delete_permanently(self, name: str, from_disabled: bool = False) -> None:
        p = (self.disabled_dir if from_disabled else self.data) / name
        if p.exists():
            p.unlink()
            self._audit("delete", p)

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
        profiles = self.load_profiles()
        profiles[name] = {
            "enabled": sorted(self.installed_zip_names()),
            "saved_at": datetime.datetime.now().isoformat(timespec="seconds"),
        }
        self._profiles_path().parent.mkdir(parents=True, exist_ok=True)
        self._profiles_path().write_text(json.dumps(profiles, ensure_ascii=False, indent=2), encoding="utf-8")
        self._audit("profile-save", self._profiles_path(), None)
        return profiles[name]

    def load_profiles(self) -> dict:
        try:
            return json.loads(self._profiles_path().read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    def apply_profile(self, name: str) -> tuple[int, int]:
        """应用方案：启用清单内的 mod、禁用其余。返回 (启用数, 禁用数)。"""
        profiles = self.load_profiles()
        if name not in profiles:
            raise KeyError(f"方案 {name} 不存在")
        want: set[str] = set(profiles[name]["enabled"])
        enabled = 0
        disabled = 0
        # 先禁用不在清单中的
        for f in list(self.data.glob("*.zip")) + list(self.data.glob("*.rar")):
            if f.name not in want:
                self.disable(f.name)
                disabled += 1
        # 再启用清单中的（从禁用目录找回来）
        for name_want in want:
            if not (self.data / name_want).exists():
                if (self.disabled_dir / name_want).exists():
                    self.enable(name_want)
                    enabled += 1
        self._audit("profile-apply", self._profiles_path(), self.data)
        return enabled, disabled


def _stub_info(f: Path) -> ModInfo:
    return ModInfo(path=f, file_name=f.name, size=f.stat().st_size if f.exists() else 0)

"""Manage opaque localization ZIPs and launch the selected game directory.

Third-party prose/scripts are never imported into our translation catalog.
Switches keep byte-verified backups and a durable rollback journal.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import uuid
import zipfile

from . import game as game_mod, l10n
from .modmanager import DISABLED_DIR

CURRENT = 'current'
NONE = 'none'
BUILTIN = 'bbmod'
STORAGE = 'bbmod_localizations'
GUARD = 'mod_zz_bbmod_preview_guard.zip'
NAME_HINT = re.compile(r'汉化|中文|chinese|localization|translation|l10n|zh[-_]?cn', re.I)


def digest(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_suffix('.tmp')
    pending.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    pending.replace(path)


def _zip_name(name: str) -> str:
    if not name or name != Path(name).name or '/' in name or '\\' in name or ':' in name or not name.lower().endswith('.zip'):
        raise ValueError('汉化文件必须是单个 ZIP 文件名')
    return name


def archive_paths(path: Path) -> set[str]:
    """Read the directory, not the contents of third-party translation scripts."""
    with zipfile.ZipFile(path) as archive:
        names = {name.replace('\\', '/').lower() for name in archive.namelist() if not name.endswith('/')}
    if not names:
        raise ValueError(f'空的汉化包：{path.name}')
    for name in names:
        if PurePosixPath(name).is_absolute() or '..' in PurePosixPath(name).parts or ':' in name:
            raise ValueError(f'汉化包包含越界路径：{path.name}')
    return names


def _overrides(names: set[str]) -> set[str]:
    return {re.sub(r'\.(?:c?nut)$', '.squirrel', name) for name in names
            if name.startswith(('ui/', 'scripts/', 'gfx/fonts/'))}


@dataclass
class SwitchPlan:
    profile_id: str
    title: str
    fingerprint: dict[str, str]
    sources: dict[str, tuple[Path, str]]
    disable: list[str]
    install: list[str]
    conflicts: list[str]

    @property
    def changed(self) -> bool:
        return bool(self.disable or self.install)


class LocalizationProfiles:
    def __init__(self, game_root: Path):
        self.root = Path(game_root).resolve()
        self.data = self.root / 'data'
        self.store = self.root / STORAGE
        self.registry = self.store / 'profiles.json'
        self.journal = self.store / 'pending-switch.json'
        for folder in (self.data, self.store, self.root / DISABLED_DIR):
            if not folder.resolve().is_relative_to(self.root):
                raise ValueError('汉化目录不能指向游戏目录以外')

    def _stored(self, relative: str) -> Path:
        rel = PurePosixPath(relative)
        if rel.is_absolute() or '..' in rel.parts or ':' in relative or '\\' in relative:
            raise ValueError('汉化库路径无效')
        path = self.store.joinpath(*rel.parts)
        if not path.resolve().is_relative_to(self.store.resolve()):
            raise ValueError('汉化库路径越界')
        return path

    def _game_file(self, relative: str) -> Path:
        parts = PurePosixPath(relative).parts
        if len(parts) != 2 or parts[0] not in {'data', DISABLED_DIR}:
            raise ValueError('切换记录不能操作游戏本体文件')
        _zip_name(parts[1])
        path = self.root.joinpath(*parts)
        if path.is_symlink() or not path.resolve().is_relative_to(self.root):
            raise ValueError('切换路径越界')
        return path

    def profiles(self) -> dict:
        if not self.registry.exists():
            return {}
        raw = json.loads(self.registry.read_text(encoding='utf-8'))
        if raw.get('schema') != 1 or not isinstance(raw.get('profiles'), dict):
            raise ValueError('汉化方案记录损坏，请保留文件并检查')
        for key, profile in raw['profiles'].items():
            if key in {CURRENT, NONE} or not profile.get('files'):
                raise ValueError('汉化方案记录无效')
            for item in profile['files']:
                _zip_name(item['name'])
                self._stored(item['stored'])
        return raw['profiles']

    def inventory(self) -> list[dict]:
        profiles = self.profiles()
        managed = {item['name'].casefold() for profile in profiles.values() for item in profile['files']}
        result = []
        for folder, enabled in ((self.data, True), (self.root / DISABLED_DIR, False)):
            for path in sorted(folder.glob('*.zip')):
                if path.name == GUARD:
                    continue
                own = l10n.is_bbmod_l10n(path)
                result.append({'path': path, 'name': path.name, 'enabled': enabled, 'own': own,
                               'managed': path.name.casefold() in managed,
                               'candidate': own or bool(NAME_HINT.search(path.name))})
        return result

    def _ensure_idle(self, *, changing: bool = False) -> None:
        if game_mod.is_game_running():
            raise RuntimeError('游戏正在运行，无需再次启动；切换汉化请先退出游戏。')
        if (self.root / 'bbmod_seedgen_session/session.json').exists():
            raise RuntimeError('种子远征尚未恢复，请先停止并恢复该会话。')
        if changing and (self.data / GUARD).exists():
            raise RuntimeError('这是禁止存档的开发测试副本。请选用常用游戏目录管理汉化，测试保护文件需由开发工具更新。')

    def register(self, title: str, paths: list[Path], *, builtin: bool = False) -> str:
        self._ensure_idle()
        if not title.strip() or not paths:
            raise ValueError('请填写方案名称并选择至少一个汉化 ZIP')
        if len({p.name.casefold() for p in paths}) != len(paths):
            raise ValueError('同一方案不能包含同名文件')
        validated = []
        for path in map(Path, paths):
            _zip_name(path.name)
            if path.name.casefold() == GUARD.casefold():
                raise ValueError('开发存档保护文件不能作为汉化包导入')
            names = archive_paths(path)
            if any(name.endswith('.zip') for name in names):
                raise ValueError(f'{path.name} 是合集压缩包，请先解压并选择其中实际的汉化 ZIP。')
            if 'bbmod_preview_guard.json' in names:
                raise ValueError('开发存档保护文件不能作为汉化包导入')
            if builtin and not l10n.is_bbmod_l10n(path):
                raise ValueError('内置方案只接受 BBMOD 独立汉化包')
            validated.append((path, digest(path)))
        profiles = self.profiles()
        key = BUILTIN if builtin else uuid.uuid4().hex
        revision = uuid.uuid4().hex
        files = []
        for source, expected in validated:
            relative = f'packages/{revision}/{source.name}'
            target = self._stored(relative)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            if digest(target) != expected:
                raise OSError(f'复制过程中汉化文件发生变化：{source.name}')
            files.append({'name': source.name, 'stored': relative, 'sha256': expected})
        profiles[key] = {'name': title.strip(), 'files': files}
        _write_json(self.registry, {'schema': 1, 'profiles': profiles})
        return key

    def _fingerprint(self) -> dict[str, str]:
        return {path.name: digest(path) for path in sorted(self.data.glob('*.zip'))}

    def plan(self, profile_id: str) -> SwitchPlan:
        if self.journal.exists():
            raise RuntimeError('上次切换未完成，请先点击“恢复上次切换”。')
        profiles = self.profiles()
        title = '沿用当前配置' if profile_id == CURRENT else '停用已管理及已识别汉化'
        fingerprint = self._fingerprint()
        existing_names = {name.casefold(): name for name in fingerprint}
        sources = {}
        if profile_id not in {CURRENT, NONE}:
            profile = profiles[profile_id]
            title = profile['name']
            for item in profile['files']:
                source = self._stored(item['stored'])
                if digest(source) != item['sha256']:
                    raise ValueError(f'汉化库文件已改变，请重新导入：{item["name"]}')
                # Windows treats these names as the same target; journal it once.
                name = existing_names.get(item['name'].casefold(), item['name'])
                sources[name] = (source, item['sha256'])
        disable, conflicts = [], []
        if profile_id != CURRENT:
            owned = {item['name'] for item in self.inventory() if item['managed'] or item['candidate']}
            targets = set().union(*(_overrides(archive_paths(path)) for path, _ in sources.values())) if sources else set()
            for name, current in fingerprint.items():
                if name in sources and sources[name][1] == current:
                    continue
                overlap = bool(targets & _overrides(archive_paths(self.data / name))) if targets else False
                if name in owned or name in sources or overlap:
                    disable.append(name)
                    if overlap and name not in owned:
                        conflicts.append(name)
        install = [name for name, (_, expected) in sources.items() if fingerprint.get(name) != expected]
        return SwitchPlan(profile_id, title, fingerprint, sources, disable, install, conflicts)

    @staticmethod
    def _copy_verified(source: Path, target: Path, expected: str) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        # Stage outside the game's mounted ZIP namespace.
        pending = target.with_suffix('.bbmod-pending')
        if pending.exists():
            raise FileExistsError(f'存在未处理的临时文件：{pending.name}')
        try:
            shutil.copy2(source, pending)
            if digest(pending) != expected:
                raise OSError(f'文件校验失败：{source.name}')
            pending.replace(target)
        finally:
            if pending.exists():
                pending.unlink()

    def apply(self, plan: SwitchPlan) -> None:
        self._ensure_idle(changing=plan.changed)
        if self.journal.exists():
            raise RuntimeError('请先恢复上次未完成的切换')
        fresh = self.plan(plan.profile_id)
        if fresh != plan:
            raise RuntimeError('文件或方案已改变，请刷新切换预览后重试。')
        if not plan.changed:
            return
        # Compute every target, including disabled copies, before any game write.
        after = {}
        contents = {}
        for name in plan.disable:
            expected = plan.fingerprint[name]
            relative = f'{DISABLED_DIR}/{name}'
            target = self._game_file(relative)
            if target.exists() and digest(target) != expected:
                relative = f'{DISABLED_DIR}/{Path(name).stem}-{uuid.uuid4().hex[:12]}.zip'
            after[relative] = expected
            contents[relative] = self.data / name
            after[f'data/{name}'] = None
        for name in plan.install:
            after[f'data/{name}'] = plan.sources[name][1]
            contents[f'data/{name}'] = plan.sources[name][0]
        transaction = uuid.uuid4().hex
        before = {}
        staged = {}
        for index, (relative, expected) in enumerate(after.items()):
            target = self._game_file(relative)
            old = digest(target) if target.exists() else None
            backup = f'transactions/{transaction}/before/{index}.zip'
            if old:
                self._copy_verified(target, self._stored(backup), old)
            before[relative] = {'sha256': old, 'backup': backup}
            if expected:
                stage = f'transactions/{transaction}/after/{index}.zip'
                self._copy_verified(contents[relative], self._stored(stage), expected)
                staged[relative] = stage
        _write_json(self.journal, {'schema': 1, 'before': before, 'after': after, 'profile': plan.title})
        try:
            # Recheck after backups, then make a reversible switch.
            self._ensure_idle(changing=True)
            if self._fingerprint() != plan.fingerprint:
                raise RuntimeError('游戏文件在备份期间改变，切换已取消。')
            for relative, expected in after.items():
                target = self._game_file(relative)
                observed = digest(target) if target.exists() else None
                if observed != before[relative]['sha256']:
                    raise RuntimeError(f'文件在切换期间改变，未覆盖：{relative}')
                if expected:
                    self._copy_verified(self._stored(staged[relative]), target, expected)
                elif target.exists():
                    target.unlink()
            for relative, expected in after.items():
                target = self._game_file(relative)
                assert (digest(target) if target.exists() else None) == expected
            self.journal.unlink()
        except Exception:
            self.recover()
            raise

    def recover(self) -> None:
        self._ensure_idle(changing=True)
        if not self.journal.exists():
            return
        state = json.loads(self.journal.read_text(encoding='utf-8'))
        if state.get('schema') != 1 or state['before'].keys() != state['after'].keys():
            raise ValueError('恢复记录无效，请保留备份并检查')
        # Preflight all records before restoring any, including crash/foreign edits.
        for relative, original in state['before'].items():
            target = self._game_file(relative)
            current = digest(target) if target.exists() else None
            if current not in {original['sha256'], state['after'][relative]}:
                raise RuntimeError(f'切换期间文件被外部修改，已保留文件及备份：{relative}')
            if original['sha256'] and digest(self._stored(original['backup'])) != original['sha256']:
                raise OSError(f'恢复备份校验失败：{relative}')
        for relative, original in state['before'].items():
            target = self._game_file(relative)
            pending = target.with_suffix('.bbmod-pending')
            if pending.exists():
                if pending.is_symlink() or not pending.is_file() or not pending.resolve().is_relative_to(self.root):
                    raise ValueError('恢复临时文件路径无效')
                saved = self._stored(f'transactions/interrupted-{uuid.uuid4().hex}/{target.name}')
                self._copy_verified(pending, saved, digest(pending))
                pending.unlink()
            if original['sha256']:
                self._copy_verified(self._stored(original['backup']), target, original['sha256'])
            elif target.exists():
                target.unlink()
        self.journal.unlink()

    def launch(self, game, runtime: Path) -> dict:
        self._ensure_idle()
        if self.journal.exists():
            raise RuntimeError('汉化切换尚未恢复，暂不能启动游戏。')
        if game.root.resolve() != self.root or game.exe.resolve() != (self.root / 'win32/BattleBrothers.exe').resolve():
            raise ValueError('启动目标与当前游戏目录不一致')
        active = [item for item in self.inventory() if item['enabled']]
        own = [item for item in active if item['own']]
        if len(own) > 1 or (own and any(not item['own'] and (item['managed'] or item['candidate']) for item in active)):
            raise RuntimeError('当前同时启用了多套汉化，请先选择方案并应用。')
        if own:
            overlaps = l10n.conflicting_ui_mods(self.data, own[0]['path'])
            overlaps = [path for path in overlaps if path.name != GUARD]
            if overlaps:
                raise RuntimeError('以下文件与独立汉化冲突，请先在切换预览中处理：\n' + '\n'.join(p.name for p in overlaps))
            guard_path = self.data / GUARD
            if guard_path.exists():
                with zipfile.ZipFile(guard_path) as archive:
                    guard = json.loads(archive.read('BBMOD_PREVIEW_GUARD.json'))
                if (guard.get('package_sha256') != digest(own[0]['path'])
                        or guard.get('automatic_campaign_start') is not False
                        or set(guard.get('disabled_functions', [])) != {'autosave', 'saveCampaign'}):
                    raise RuntimeError('开发测试副本的保护文件与汉化包不一致')
            manifest = l10n.package_manifest(own[0]['path']) or {}
            if manifest.get('place_name_display') == 'mod_ui':
                from .place_display import read_packaged_display
                read_packaged_display(own[0]['path'])
            if manifest.get('requires_bbmod_launcher') or manifest.get('uses_bbmod_map_font'):
                raise RuntimeError('当前安装的是依赖旧中文启动组件的汉化包。请在汉化管理中导入新版包，或进入“译文编辑与制作”制作新版包，确认应用后再启动游戏。新版通过普通 MOD 显示中文地名，无需旧启动器。')
        # Never use a Steam URL here: it may launch a different installation.
        return game_mod.launch_executable(game)

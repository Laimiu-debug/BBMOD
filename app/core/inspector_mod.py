"""Install/remove the small tooltip reader, preserving existing mod frameworks."""
import hashlib
import json
from pathlib import Path
import shutil
import time
import uuid
import zipfile

from . import game
from .l10n_compat import hooks_assets, HOOKS_CREDIT
from .paths import resource_path

FILENAME = 'mod_bbmod_item_inspector.zip'
VERSION = 3
SCRIPT = 'scripts/!mods_preload/bbmod_item_inspector.nut'
MANIFEST = 'BBMOD_ITEM_INSPECTOR.json'
UI_MODULE = 'ui/screens/tooltip/modules/tooltip_module.js'


def hover_ui(data):
    """Append to this installation's original UI, without replacing main.html.

    This also works without a localization/UI-loader mod. Refuse to overwrite a
    third-party replacement of the same module; ordinary prototype hooks work.
    """
    original = None
    for path in sorted(data.iterdir()):
        if path.suffix.lower() not in ('.zip', '.dat') or path.name == FILENAME:
            continue
        try:
            with zipfile.ZipFile(path) as archive:
                if UI_MODULE not in archive.namelist(): continue
                if path.name not in game.OFFICIAL_ARCHIVES:
                    raise ValueError('读取 MOD 与 ' + path.name + ' 同时替换装备提示界面，请先停用其中一个。原文件未改动。')
                original = archive.read(UI_MODULE)
        except zipfile.BadZipFile:
            continue
    if original is None or b'TooltipModule.prototype.notifyBackendQueryTooltipData' not in original:
        raise ValueError('未找到受支持的游戏装备提示界面，请先校验游戏文件。')
    return original + b'\n;\n' + resource_path('data/item_inspector/hover.js').read_bytes()


def installed_version(path):
    if not owned(path): return 0
    with zipfile.ZipFile(path) as archive:
        return json.loads(archive.read(MANIFEST)).get('version', 0)


def owned(path):
    if not path.exists(): return False
    try:
        with zipfile.ZipFile(path) as archive:
            manifest = json.loads(archive.read(MANIFEST))
            files = manifest['files']
            return (manifest.get('id') == 'bbmod_item_inspector' and SCRIPT in files
                and set(archive.namelist()) == set(files) | {MANIFEST}
                and all(archive.getinfo(name).file_size < 4 * 1024 * 1024
                    and hashlib.sha256(archive.read(name)).hexdigest() == digest for name, digest in files.items()))
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile):
        return False


def framework_provider(data):
    for path in sorted(data.iterdir()):
        if path.name == FILENAME or path.suffix.lower() not in ('.zip', '.dat') or path.name.startswith('data_'):
            continue
        try:
            with zipfile.ZipFile(path) as archive:
                names = {n.lower().replace('\\', '/') for n in archive.namelist()}
                if 'scripts/!mods_preload/!!redirect.nut' in names or any('modern_hooks' in n for n in names):
                    return path.name
        except (OSError, zipfile.BadZipFile):
            continue
    return ''


def change(game_info, *, remove=False):
    if game.is_game_running():
        raise ValueError('请先退出游戏，再调整装备读取 MOD。')
    data = game_info.data_dir.resolve()
    target = data / FILENAME
    if target.is_symlink() or (target.exists() and not owned(target)):
        raise ValueError('同名 MOD 文件被修改或来源不明，已保留原文件。请先在 MOD 军械库中处理。')
    if remove and not target.exists():
        return '读取 MOD 已移除。'
    ui = None if remove else hover_ui(data)
    backup = None
    if target.exists():
        backup_folder = data.parent / 'BBMOD-backups' / 'item-inspector'
        backup_folder.mkdir(parents=True, exist_ok=True)
        backup = backup_folder / (str(time.time_ns()) + '-' + FILENAME)
        shutil.copy2(target, backup)
        if hashlib.sha256(backup.read_bytes()).digest() != hashlib.sha256(target.read_bytes()).digest():
            raise OSError('原 MOD 备份校验失败，未修改游戏文件')
    if remove:
        target.unlink()
        return '读取 MOD 已移除；备份已保留。'
    provider = framework_provider(data)
    files = {SCRIPT: resource_path('data/item_inspector/bridge.nut').read_bytes(), UI_MODULE: ui}
    if not provider:
        files.update(hooks_assets())
        files['BBMOD_HOOKS_CREDIT.txt'] = HOOKS_CREDIT.encode('utf-8')
    manifest = {'id': 'bbmod_item_inspector', 'schema': 1, 'version': VERSION, 'game_version': '1.5.2.3',
                'external_framework': provider, 'files': {k: hashlib.sha256(v).hexdigest() for k, v in files.items()}}
    temporary = data / ('.bbmod-inspector-' + uuid.uuid4().hex + '.tmp')
    try:
        with zipfile.ZipFile(temporary, 'x', zipfile.ZIP_DEFLATED) as archive:
            for name, raw in files.items(): archive.writestr(name, raw)
            archive.writestr(MANIFEST, json.dumps(manifest, ensure_ascii=False))
        if not owned(temporary): raise OSError('读取 MOD 校验失败')
        if game.is_game_running(): raise ValueError('游戏已启动，安装已取消，请退出游戏后重试。')
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
    return '读取 MOD 已安装，下次启动游戏生效。' + ('沿用现有脚本框架：' + provider if provider else '已附带脚本框架。')

"""Independent catalog, verified original text patches, and Chinese UI font."""
from __future__ import annotations

import datetime
import hashlib
import json
import re
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path

from .game import OFFICIAL_ARCHIVES
from .modmanager import ModManager
from .paths import resource_path
from .full_l10n import CATEGORIES, load_full_catalog, write_full_patches
from .l10n_tokens import validate_translation
from .place_names import load_policy, original_names, preserve_inline_names
from .l10n_compat import override_keys, write_hooks

BRAND_META = 'BBMOD_L10N.json'
PACKAGE_ID = 'bbmod.independent.zh-CN'
PACKAGE_NAME = 'mod_bbmod_zhcn.zip'
VERSION = '0.3.0-rc.2'
CATALOG_FILE = resource_path('localization/catalog.json')
UI_ROOT = 'ui/mods/bbmod_l10n/'
FONT_ENTRY = UI_ROOT + 'NotoSansSC-Regular.ttf'


@dataclass(frozen=True)
class StringEntry:
    source: str
    value: str
    category: str
    status: str = 'reviewed'

    @property
    def id(self) -> str:
        return self.source


def load_catalog(path: Path | None = None) -> tuple[dict, list[StringEntry]]:
    meta = json.loads((path or CATALOG_FILE).read_text(encoding='utf-8-sig'))
    if meta.get('schema_version') != 1 or not isinstance(meta.get('groups'), dict):
        raise ValueError('不支持的独立译文目录格式')
    entries = []
    seen = set()
    for category, group in meta['groups'].items():
        for source, value in group.items():
            if not isinstance(source, str) or not source.strip() or source in seen:
                raise ValueError(f'重复或无效的英文条目：{source}')
            if re.search(r'[\u4e00-\u9fff]', source):
                raise ValueError(f'独立词库需要英文来源：{source}')
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f'缺少译文：{source}')
            entries.append(StringEntry(source, value, category))
            seen.add(source)
    # Explicit test/custom catalogs remain self-contained.
    full = load_full_catalog() if path is None else None
    if full:
        from .place_display import reviewed_places
        place_terms = reviewed_places(full, load_policy(full))
        positions = {entry.source: i for i, entry in enumerate(entries)}
        for entry in full['entries'].values():
            if entry['source'] in place_terms:
                entry = {**entry, 'translation': place_terms[entry['source']], 'status': 'reviewed'}
            if entry['source'] in seen:
                # The assembled catalog includes the latest independent review.
                # An older menu entry must not undo that review while packaging.
                index = positions[entry['source']]
                previous = entries[index]
                entries[index] = StringEntry(entry['source'], entry['translation'], previous.category,
                                             entry.get('status', 'machine_draft'))
                meta['groups'][previous.category][entry['source']] = entry['translation']
                continue
            category = CATEGORIES.get(entry['category'], '其他游戏文本')
            entries.append(StringEntry(entry['source'], entry['translation'], category, entry.get('status', 'machine_draft')))
            meta['groups'].setdefault(category, {})
            seen.add(entry['source'])
        meta['scope'] = full.get('scope_description', '本体与官方 DLC 文本初稿；待完成逐条校对和游戏内验收')
        if place_terms:
            meta['scope'] = meta['scope'].replace('地名保留原版英文', '地名译文已校对，原始数据保留英文')
        meta['translation_stage'] = full.get('translation_stage', 'draft')
    return meta, entries


def translated_catalog(overrides: dict[str, str] | None = None) -> dict[str, str]:
    _, entries = load_catalog()
    result = {entry.source: entry.value for entry in entries}
    for source, value in (overrides or {}).items():
        if source not in result:
            raise ValueError(f'覆盖表包含未知条目：{source}')
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f'译文不能为空：{source}')
        issues = validate_translation(source, value)
        if issues:
            raise ValueError('；'.join(issues) + '：' + source[:80])
        result[source] = value
    return result


def read_base_html(data_dir: Path) -> tuple[bytes, str]:
    found = None
    for archive_name in sorted(OFFICIAL_ARCHIVES):
        archive = Path(data_dir) / archive_name
        if not archive.is_file():
            continue
        with zipfile.ZipFile(archive) as zf:
            if 'ui/main.html' in zf.namelist():
                found = (zf.read('ui/main.html'), archive_name)
    if found is None:
        raise FileNotFoundError('游戏 data_*.dat 内未找到 ui/main.html')
    raw, archive_name = found
    html = raw.decode('utf-8-sig')
    if not re.search(r'</head\s*>', html, re.I):
        raise ValueError('游戏界面入口格式不受支持')
    if re.search(r'mod_hooks|bbmod_l10n|modern_hooks', html, re.I):
        raise ValueError('游戏档案内的界面入口含第三方注入，请先用 Steam 校验还原，再构建独立汉化。')
    return raw, archive_name


def build_localization(game_root: Path, overrides: dict[str, str], out_path: Path) -> dict:
    game_root, out_path = Path(game_root), Path(out_path)
    if out_path.suffix.lower() != '.zip' or out_path.resolve().is_relative_to((game_root / 'data').resolve()):
        raise ValueError('请将汉化包导出为游戏 data 目录以外的 ZIP，再通过安装操作启用。')
    meta, entries = load_catalog()
    dictionary = translated_catalog(overrides)
    full = load_full_catalog()
    policy = load_policy(full)
    if full:
        from .native_font import check_executable
        check_executable(game_root / 'win32/BattleBrothers.exe')
    ui_keys = {source for group in json.loads(CATALOG_FILE.read_text(encoding='utf-8-sig'))['groups'].values() for source in group}
    ui_dictionary = {source: dictionary[source] for source in ui_keys}
    if full:
        # Shared code/display constants stay unchanged in native bytecode.
        # Translate their rendered text using the same published catalog.
        ui_dictionary = dict(full.get('display_fallbacks', {}))
        ui_dictionary.update({source.strip(): value.strip() for source, value in dictionary.items()
                              if source.strip() and value.strip()})
        inline = preserve_inline_names({key: {**entry, 'translation': dictionary.get(entry['source'], entry['translation'])}
                                       for key, entry in full['entries'].items()}, policy)
        ui_dictionary.update({entry['source'].strip(): entry['translation'].strip()
                              for key, entry in inline.items() if policy and key in policy.get('inline_mentions', {})})
        # A separately rendered town name must not be translated again by the
        # UI fallback. Names embedded in narrative come from the same entity.
        ui_dictionary.update({name.strip(): name.strip() for name in original_names(full, policy)})
    raw, archive_name = read_base_html(game_root / 'data')
    html = raw.decode('utf-8-sig')
    injection = ('\n<!-- BBMOD independent localization -->\n'
        '<link rel="stylesheet" href="mods/bbmod_l10n/fonts.css"/>\n'
        '<script src="mods/bbmod_l10n/dictionary.js"></script>\n'
        '<script src="mods/bbmod_l10n/runtime.js"></script>\n')
    if full:
        injection = '<script src="mod_hooks.js"></script>\n' + injection
    if policy:
        injection = injection.replace('<script src="mods/bbmod_l10n/runtime.js">',
                                      '<script src="mods/bbmod_l10n/place_names.js"></script>\n<script src="mods/bbmod_l10n/runtime.js">')
    html = re.sub(r'</head\s*>', lambda match: injection + match.group(0), html, count=1, flags=re.I)
    source_dir = resource_path('localization')
    assets = ['runtime.js', 'fonts.css', 'NotoSansSC-Regular.ttf', 'FONT-LICENSE.txt']
    for asset in assets:
        if not (source_dir / asset).is_file():
            raise FileNotFoundError(f'缺少独立汉化资源：{asset}')
    manifest = {
        'package_id': PACKAGE_ID, 'brand': 'BBMOD 独立汉化', 'version': VERSION,
        'target_game_version': '1.5.2.3', 'language': 'zh-CN',
        'scope': meta['scope'] + ('；地名存档保留英文，从 BBMOD 启动时地图及对话统一显示中文，直接启动显示英文' if policy else ''), 'provenance': meta['provenance'],
        'entry_count': len(entries), 'overrides_applied': len(overrides),
        'base_archive': archive_name, 'base_ui_sha256': hashlib.sha256(raw).hexdigest(),
        'catalog_sha256': hashlib.sha256(CATALOG_FILE.read_bytes()).hexdigest(),
        'built_at': datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'),
        'requires_hooks': False, 'game_acceptance': 'pending',
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # A failed build cannot truncate the last usable output.
    with tempfile.NamedTemporaryFile(prefix='.bbmod-l10n-', suffix='.zip', dir=out_path.parent, delete=False) as tmp:
        pending = Path(tmp.name)
    try:
        with zipfile.ZipFile(pending, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
            if full:
                manifest.update(write_hooks(zf))
            if policy:
                from .place_display import write_display_assets
                manifest.update(write_display_assets(zf, full, policy, dictionary))
            zf.writestr('ui/main.html', html.encode('utf-8'))
            zf.writestr(UI_ROOT + 'dictionary.js', 'window.BBMOD_DICTIONARY = ' + json.dumps(ui_dictionary, ensure_ascii=True) + ';\n')
            for asset in assets:
                zf.write(source_dir / asset, UI_ROOT + asset)
            from .input_ime import ENTRY, patch_input
            with zipfile.ZipFile(game_root / 'data' / archive_name) as original:
                if ENTRY in original.namelist():
                    zf.writestr(ENTRY, patch_input(original.read(ENTRY)))
                    manifest['chinese_input_support'] = True
            if full:
                from .full_l10n import FULL_CATALOG_FILE
                manifest.update(write_full_patches(zf, game_root, full, dictionary, catalog_sha256=hashlib.sha256(FULL_CATALOG_FILE.read_bytes()).hexdigest()))
                manifest['requires_bbmod_launcher'] = not bool(policy)
                manifest['uses_bbmod_map_font'] = True
                manifest['supports_direct_launch'] = bool(policy)
                review_note = ('本体与官方 DLC 的正文和 2,196 条地名译文均已独立精修；当前版本仅完成离线检查，游戏内验收尚未进行。'
                               if full.get('editorial_review', {}).get('status') == 'complete'
                               else '长篇剧情为独立翻译初稿，可在汉化工坊中继续校对。')
                zf.writestr('BBMOD中文启动说明.txt', '本包覆盖本体及官方 DLC 文本。\n从新版 BBMOD 启动时，地图、任务和对话中的地名统一显示中文；直接从 Steam 或游戏 EXE 启动时，地名显示英文，正文仍为中文。\n地名的英文原值和存档保持不变，中文显示标记仅存在于此次游戏进程；退出软件不会影响已启动的游戏，下次直接启动仍为英文。\n旧汉化存档中已经保存的中文名称不会自动恢复；不会迁移或重写存档。\n' + review_note + '\n')
            zf.writestr(BRAND_META, json.dumps(manifest, ensure_ascii=False, indent=2))
        with zipfile.ZipFile(pending) as zf:
            broken = zf.testzip()
            if broken:
                raise ValueError(f'汉化包校验失败：{broken}')
        pending.replace(out_path)
    finally:
        if pending.exists():
            pending.unlink()
    return {**manifest, 'out': str(out_path), 'entries': len(entries), 'applied': len(overrides), 'missing': []}


def package_manifest(path: Path) -> dict | None:
    try:
        with zipfile.ZipFile(path) as zf:
            result = json.loads(zf.read(BRAND_META))
            return result if isinstance(result, dict) else None
    except (KeyError, ValueError, OSError, zipfile.BadZipFile):
        return None


def is_bbmod_l10n(path: Path) -> bool:
    meta = package_manifest(path)
    return bool(meta and meta.get('package_id') == PACKAGE_ID)


def find_localization_zips(data_dir: Path) -> list[Path]:
    return [p for p in sorted(Path(data_dir).glob('*.zip')) if is_bbmod_l10n(p)]


def conflicting_ui_mods(data_dir: Path, package: Path | None = None) -> list[Path]:
    conflicts = []
    targets = {'ui/main.html'}
    if package:
        with zipfile.ZipFile(package) as zf:
            targets.update(override_keys(zf.namelist()))
    for path in sorted(Path(data_dir).glob('*.zip')):
        if is_bbmod_l10n(path):
            continue
        try:
            with zipfile.ZipFile(path) as zf:
                names = override_keys(zf.namelist())
                if names & targets:
                    conflicts.append(path)
        except (OSError, zipfile.BadZipFile):
            continue
    return conflicts


def install_localization(manager: ModManager, package: Path) -> list[Path]:
    from .game import is_game_running
    if is_game_running():
        raise RuntimeError('请先关闭游戏，再安装汉化。')
    if not is_bbmod_l10n(package):
        raise ValueError('这不是 BBMOD 独立汉化包')
    conflicts = conflicting_ui_mods(manager.data, package)
    if conflicts:
        raise RuntimeError('以下模组与本汉化修改了相同的游戏文件，请先在 MOD 军械库中停用冲突项：\n' + '\n'.join(p.name for p in conflicts))
    installed = manager.data / package.name
    if installed.exists() and not is_bbmod_l10n(installed):
        raise FileExistsError(f'同名文件不是本软件的独立汉化包：{installed.name}')
    # Atomic update with rollback of the previous independent package.
    old = installed.read_bytes() if installed.exists() else None
    try:
        return manager.install(package, overwrite=True)
    except Exception:
        if old is not None:
            installed.write_bytes(old)
        elif installed.exists():
            installed.unlink()
        raise

"""Build full-text patches from the user's exact official archives.

The distributed data consists of independent translations and source positions,
not a copy of somebody else's translated or decompiled game scripts.
"""
from __future__ import annotations

from contextlib import ExitStack
import hashlib
import json
from pathlib import Path, PurePosixPath
import zipfile

from .cnut import Cnut, patch_literals
from .cnut_semantics import protected_literals
from .game import OFFICIAL_ARCHIVES
from .l10n_tokens import validate_translation
from .paths import resource_path
from .place_names import load_policy, geographic_spans, owner_pool_patches, preserve_inline_names, POOL_ENTRY, POOL_FILE
from .l10n_compat import DISPLAY_ONLY_FILES

FULL_CATALOG_FILE = resource_path('localization/full_catalog.json')
CATEGORIES = {'ambitions': '志向与誓言', 'config': '名称与游戏术语', 'contracts': '委托与谈判', 'entity': '人物、城镇与世界', 'events': '事件与剧情', 'items': '武器、护甲与物品', 'retinue': '随从', 'scenarios': '起源与战斗场景', 'skills': '技能、特长与状态', 'states': '战役与战斗提示', 'ui': '游戏界面', 'ai': '地图行军状态', 'factions': '势力', 'dlc': '扩展内容', 'mapgen': '世界生成'}


def load_full_catalog() -> dict | None:
    if not FULL_CATALOG_FILE.exists():
        return None
    result = json.loads(FULL_CATALOG_FILE.read_text(encoding='utf-8'))
    if result.get('schema_version') != 1 or not isinstance(result.get('entries'), dict) or not isinstance(result.get('files'), dict):
        raise ValueError('完整汉化目录格式无效')
    for key, entry in result['entries'].items():
        source, value = entry.get('source'), entry.get('translation')
        if not isinstance(source, str) or not isinstance(value, str):
            raise ValueError(f'原文或译文格式无效：{key}')
        if hashlib.sha256(source.encode('utf-8')).hexdigest()[:20] != key:
            raise ValueError(f'原文标识校验失败：{key}')
        if not value.strip() and not entry.get('omit_grammar'):
            raise ValueError(f'尚未翻译：{key}')
        problems = validate_translation(source, value)
        if problems:
            raise ValueError(f'{key}：' + '；'.join(problems))
    return result


def patch_js(raw: bytes, patches: list, entries: dict) -> bytes:
    chunks = []
    cursor = 0
    for start, end, key in sorted(patches):
        if start < cursor or end > len(raw) or end <= start:
            raise ValueError('界面译文位置重叠或越界')
        # File hashes validate the full original, including the quote style.
        value = json.dumps(entries[key]['translation'], ensure_ascii=True).encode('ascii')
        chunks.extend([raw[cursor:start], value])
        cursor = end
    chunks.append(raw[cursor:])
    return b''.join(chunks)


def write_full_patches(zf: zipfile.ZipFile, game_root: Path, catalog: dict, overrides: dict[str, str], *, catalog_sha256: str | None = None) -> dict:
    policy = load_policy(catalog)
    entries = {key: {**entry, 'translation': overrides.get(entry['source'], entry['translation'])} for key, entry in catalog['entries'].items()}
    entries = preserve_inline_names(entries, policy)
    for key, entry in entries.items():
        problems = validate_translation(entry['source'], entry['translation'])
        if problems:
            raise ValueError(f'自定义译文 {key}：' + '；'.join(problems))
    count = 0
    retained_names = pool_changes = 0
    sources = []
    with ExitStack() as stack:
        archives = {}
        for name, spec in catalog['files'].items():
            path = PurePosixPath(name)
            if path.is_absolute() or '..' in path.parts or '\\' in name or ':' in name or path.suffix not in {'.cnut', '.js'}:
                raise ValueError('不安全或不支持的汉化目标路径')
            archive_name = spec['archive']
            if archive_name not in OFFICIAL_ARCHIVES:
                raise ValueError('完整汉化只能读取本体和官方 DLC')
            if archive_name not in archives:
                file = game_root / 'data' / archive_name
                if not file.is_file():
                    # Optional DLC archives absent from this user's game stay absent.
                    if archive_name != 'data_001.dat':
                        continue
                    raise FileNotFoundError('缺少游戏本体档案 data_001.dat')
                archives[archive_name] = stack.enter_context(zipfile.ZipFile(file))
            try:
                raw = archives[archive_name].read(name)
            except KeyError as error:
                raise ValueError(f'原版档案缺少 {name}，请核对游戏版本') from error
            if hashlib.sha256(raw).hexdigest() != spec['sha256']:
                raise ValueError(f'{name} 与支持的原版不一致，请校验游戏文件后再构建。')
            if name in DISPLAY_ONLY_FILES:
                # Keep the vanilla/MOD implementation, translate its DOM labels.
                continue
            if spec.get('kind') == 'js':
                result = patch_js(raw, spec['patches'], entries)
                replacement_count = len(spec['patches'])
            else:
                parsed = Cnut(raw, encrypted=True)
                protected = {f['path']: protected_literals(f) for f in parsed.functions}
                spans = {lit.start: lit for lit in parsed.literals}
                for start, end, key in spec['patches']:
                    lit = spans.get(start)
                    if lit is None or lit.end != end:
                        raise ValueError(f'{name}：文本位置不是字符串常量')
                    if lit.index in protected[lit.function] and entries[key]['translation'] != lit.text:
                        raise ValueError(f'{name}：不能翻译游戏内部标识 {lit.text}')
                geography = geographic_spans(policy, name)
                patches = [p for p in spec['patches'] if tuple(p) not in geography]
                extras, extra_entries = owner_pool_patches(name, parsed) if policy else ([], {})
                result = patch_literals(raw, patches + extras, {**entries, **extra_entries})
                retained_names += len(geography)
                pool_changes += len(extras)
                replacement_count = len(patches)
            zf.writestr(name, result)
            count += replacement_count
            sources.append({'file': name, 'archive': archive_name, 'source_sha256': spec['sha256'], 'output_sha256': hashlib.sha256(result).hexdigest(), 'text_replacements': replacement_count})
    policy_meta = {}
    if policy:
        if pool_changes != 2:
            raise ValueError('未能完整应用地名原文规则')
        zf.write(POOL_FILE, POOL_ENTRY)
        policy_meta = {'place_name_policy': 'original_english', 'place_name_entries': len(policy['name_keys']),
                       'place_name_literals_preserved': retained_names, 'place_owner_pool_redirects': pool_changes,
                       'existing_save_names': 'retained_as_saved',
                       'place_name_policy_sha256': hashlib.sha256(resource_path('localization/place_names.json').read_bytes()).hexdigest()}
    zf.writestr('BBMOD_TEXT_SOURCES.json', json.dumps(sources, ensure_ascii=False))
    if catalog_sha256 is None:
        catalog_sha256 = hashlib.sha256(json.dumps(catalog,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')).hexdigest()
    return {'full_text_files': len(sources), 'text_replacements': count, 'full_text_entries': len(entries), 'translation_stage': catalog.get('translation_stage', 'draft'), 'editorial_review': catalog.get('editorial_review', {}), 'native_map_font': catalog.get('native_map_font', 'pending'), 'full_catalog_sha256': catalog_sha256, **policy_meta}

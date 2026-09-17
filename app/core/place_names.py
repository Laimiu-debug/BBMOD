"""Keep canonical geographic names English in maps, contracts and dialogue.

This is a persistent package policy, independent of launcher state. Character
names stay localized; location templates alone use the original owner pools.
"""
from __future__ import annotations

import hashlib
import json

from .cnut import Cnut
from .l10n_tokens import validate_translation
from .paths import resource_path

POLICY_FILE = resource_path('localization/place_names.json')
POOL_FILE = resource_path('localization/place_name_pools.cnut')
POOL_ENTRY = 'scripts/config/z_bbmod_place_name_pools.cnut'
MANAGER_FILE = 'scripts/entity/world/entity_manager.cnut'
POOL_KEYS = {'CharacterNames': 'BBMODPlaceCharacterNames', 'KnightNames': 'BBMODPlaceKnightNames'}


def load_policy(catalog: dict | None) -> dict | None:
    # Small UI-only catalogs and test fixtures do not have geography.
    if not catalog or 'scripts/config/world_location_names.cnut' not in catalog['files']:
        return None
    policy = json.loads(POLICY_FILE.read_text(encoding='utf-8'))
    if policy.get('schema_version') != 1 or policy.get('policy') != 'original_english':
        raise ValueError('地名原文配置无效')
    for file, expected in policy['source_files'].items():
        if catalog['files'].get(file, {}).get('sha256') != expected:
            raise ValueError(f'地名配置与游戏文本不匹配：{file}')
    for site in policy['sites']:
        if [site['start'], site['end'], site['key']] not in catalog['files'][site['file']]['patches']:
            raise ValueError('地名文本位置失效，请更新地名配置')
    if set(policy['name_keys']) != {s['key'] for s in policy['sites']}:
        raise ValueError('地名配置条目不完整')
    if any(k not in catalog['entries'] for k in policy['name_keys']):
        raise ValueError('地名原文条目缺失')
    raw = POOL_FILE.read_bytes()
    if hashlib.sha256(raw).hexdigest() != policy['owner_script_sha256']:
        raise ValueError('地名所用原版姓名库校验失败')
    return policy


def original_names(catalog: dict, policy: dict | None) -> set[str]:
    return {catalog['entries'][key]['source'] for key in policy['name_keys']} if policy else set()


def geographic_spans(policy: dict | None, file: str) -> set[tuple[int, int, str]]:
    return {(s['start'], s['end'], s['key']) for s in policy['sites'] if s['file'] == file} if policy else set()


def owner_pool_patches(file: str, parsed: Cnut) -> tuple[list, dict]:
    """Redirect exactly two data lookups; no instruction or RNG call changes."""
    if file != MANAGER_FILE:
        return [], {}
    functions = [f for f in parsed.functions if f['name'] == 'getUniqueLocationName']
    if len(functions) != 1:
        raise ValueError('地名生成函数与支持的游戏版本不符')
    literals = [lit for lit in parsed.literals if lit.function == functions[0]['path'] and lit.text in POOL_KEYS]
    if len(literals) != 2 or {lit.text for lit in literals} != set(POOL_KEYS):
        raise ValueError('地名中的姓名引用与支持的游戏版本不符')
    entries = {'bbmod_owner_' + lit.text: {'source': lit.text, 'translation': POOL_KEYS[lit.text]} for lit in literals}
    return [[lit.start, lit.end, 'bbmod_owner_' + lit.text] for lit in literals], entries


def allowed_pool_change(file: str, function: str, source, target) -> bool:
    return (file == MANAGER_FILE and function == 'getUniqueLocationName'
            and isinstance(source, str) and source in POOL_KEYS and POOL_KEYS[source] == target)


def preserve_inline_names(entries: dict, policy: dict | None) -> dict:
    if not policy:
        return entries
    result = dict(entries)
    for key, replacements in policy.get('inline_mentions', {}).items():
        entry = entries[key]
        value = entry['translation']
        for chinese, english in replacements.items():
            if english not in entry['source']:
                raise ValueError('正文地名校对缺少对应原文')
            value = value.replace(chinese, english)
        problems = validate_translation(entry['source'], value)
        if problems:
            raise ValueError('正文地名保留规则损坏了文本标记：' + '；'.join(problems))
        result[key] = {**entry, 'translation': value}
    return result

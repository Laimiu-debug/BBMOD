"""Portable, version-pinned MOD collection manifests shared by hub and desktop."""
import hashlib
import json
import re

MAX_MANIFEST_BYTES = 512 * 1024
MAX_MOD_BYTES = 100 * 1024 * 1024
MAX_TOTAL_BYTES = 2 * 1024 * 1024 * 1024
MAX_MODS = 200
HASH = re.compile(r'[0-9a-f]{64}\Z')


def text(value, limit, *, required=False):
    if (not isinstance(value, str) or len(value) > limit
            or any(ord(c) < 32 and c not in '\n\t' for c in value)
            or (required and not value.strip())):
        raise ValueError('方案文字为空、过长或包含无效字符。')
    return value.strip()


def file_name(value):
    value = text(value, 100, required=True)
    if (any(c in value for c in '<>:"/\\|?*\n\t') or value.endswith((' ', '.'))
            or not value.lower().endswith('.zip') or value.startswith('.')
            or value.split('.')[0].upper() in {'CON', 'PRN', 'AUX', 'NUL',
                *{f'COM{i}' for i in range(10)}, *{f'LPT{i}' for i in range(10)}}
            or value.casefold() == 'zzzz_bbmod_preload.zip'):
        raise ValueError('共享方案需要可直接安装的 MOD ZIP 文件名。')
    return value


def validate_manifest(value):
    if not isinstance(value, dict) or type(value.get('schema_version')) is not int or value['schema_version'] != 1:
        raise ValueError('不支持的共享方案格式，请更新 BBMOD。')
    mods = value.get('mods')
    if not isinstance(mods, list) or not 1 <= len(mods) <= MAX_MODS:
        raise ValueError(f'共享方案需包含 1–{MAX_MODS} 个 MOD。')
    result = {'schema_version': 1, 'name': text(value.get('name'), 100, required=True),
              'note': text(value.get('note', ''), 2000),
              'game_version': text(value.get('game_version', ''), 40), 'mods': []}
    names, total = set(), 0
    for item in mods:
        if not isinstance(item, dict):
            raise ValueError('方案 MOD 条目无效。')
        name = file_name(item.get('file_name'))
        sha = item.get('sha256')
        size = item.get('size')
        if not isinstance(sha, str) or not HASH.fullmatch(sha):
            raise ValueError('MOD 缺少有效 SHA-256。')
        if type(size) is not int or not 0 < size <= MAX_MOD_BYTES:
            raise ValueError('共享 MOD 单文件最大 100 MB。')
        if name.casefold() in names:
            raise ValueError('方案含有重复安装文件名。')
        names.add(name.casefold())
        total += size
        result['mods'].append({'file_name': name, 'sha256': sha, 'size': size,
            'title': text(item.get('title', name), 200), 'version': text(item.get('version', ''), 100)})
    if total > MAX_TOTAL_BYTES:
        raise ValueError('方案总大小超过 2 GB。')
    result['mods'].sort(key=lambda m: m['file_name'].casefold())
    return result


def manifest_key(manifest):
    return hashlib.sha256(json.dumps(validate_manifest(manifest), ensure_ascii=False,
                                    sort_keys=True, separators=(',', ':')).encode('utf-8')).hexdigest()

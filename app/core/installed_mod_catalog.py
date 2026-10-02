"""Read-only installed MOD names and release status, with conservative matching.

Squirrel registration versions are shown as local script versions. They are not
assumed to use the same numbering as website releases (for example 63 versus
0.28.14). A verified install receipt or an exact release hash supplies that link.
"""
from __future__ import annotations

import hashlib
import os
import re
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from functools import lru_cache

from .modinfo import ModInfo
from .modstore import load_index
from .online_catalog import site_origin
from .site_config import SITE_ORIGIN, same_site


@dataclass(frozen=True)
class InstalledModDisplay:
    display_name: str
    installed_version: str
    latest_version: str = ""
    update_available: bool = False
    page_path: str = ""
    update_url: str = ""
    status: str = "未匹配官网"
    tooltip: str = ""
    search_text: str = ""
    matched_by: str = ""
    version_source: str = ""
    catalog_item: Mapping | None = None


@lru_cache(maxsize=1)
def _bundled_index():
    index = load_index()
    return index if isinstance(index, dict) else {}


def _text(value):
    return value.strip() if isinstance(value, str) else ""


def _ids(value):
    if not isinstance(value, (list, tuple)):
        return frozenset()
    return frozenset(v for v in value if isinstance(v, str) and v)


def _identity_registrations(info):
    registrations = info.registrations
    if any(reg.mod_id == 'mod_modern_hooks' for reg in registrations):
        # Modern Hooks registers game/DLC placeholders and the analyzer can also
        # find its display-name alias in the register implementation. Those are
        # not separate bundled MODs. Keep every unrelated MOD identity intact.
        registrations = [reg for reg in registrations
                         if reg.mod_id not in {'vanilla', 'dlc', 'Modern Hooks'}]
    return registrations


def _local_ids(info):
    # A package owns its identity independently of its bundled script libraries.
    if info.package_id:
        return frozenset({info.package_id})
    return frozenset(r.mod_id for r in _identity_registrations(info) if r.mod_id)


def _receipt(info, receipts, origin):
    if not isinstance(receipts, Mapping):
        return None
    matches = [v for k, v in receipts.items()
               if isinstance(k, str) and k.casefold() == info.file_name.casefold()
               and isinstance(v, Mapping)]
    if len(matches) != 1:
        return None
    result = matches[0]
    if not same_site(result.get('origin'), origin) or not _text(result.get('id')):
        return None
    digest = _text(result.get('sha256')).lower()
    return result if re.fullmatch('[0-9a-f]{64}', digest) else None


def receipt_needs_hash(info: ModInfo, receipts=None, origin=SITE_ORIGIN) -> bool:
    """Only hash files with a usable install receipt; run file I/O in a worker."""
    try:
        origin = site_origin(origin)
    except (ValueError, TypeError, AttributeError):
        return False
    return _receipt(info, receipts, origin) is not None


def read_local_sha256(info: ModInfo) -> str:
    """Read the archive without modifying it; inaccessible files stay unknown."""
    try:
        with info.path.open('rb') as source:
            before = os.fstat(source.fileno())
            digest = hashlib.file_digest(source, 'sha256').hexdigest()
            after = os.fstat(source.fileno())
            current = info.path.stat()
        def signature(stat):
            return stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns
        return digest if signature(before) == signature(after) == signature(current) else ''
    except OSError:
        return ""


def _match(info, items, receipt):
    if receipt:
        matches = [item for item in items if item.get('id') == receipt.get('id')]
        if len(matches) == 1:
            return matches[0], 'receipt'
        if matches:
            return None, ''
    own_ids = _local_ids(info)
    matches = [item for item in items
               if _text(item.get('file_name')).casefold() == info.file_name.casefold()]
    if matches:
        if len(matches) != 1:
            return None, ''
        item = matches[0]
        declared = _ids(item['metadata'].get('mod_ids'))
        # Do not label a stand-alone dependency as the bundle containing it.
        if own_ids and declared and own_ids != declared:
            if not info.package_id or info.package_id not in declared:
                return None, ''
        return item, 'file_name'
    if not own_ids:
        return None, ''
    if info.package_id:
        matches = [item for item in items
                   if info.package_id in _ids(item['metadata'].get('mod_ids'))]
        kind = 'package_id'
    else:
        matches = [item for item in items
                   if _ids(item['metadata'].get('mod_ids')) == own_ids]
        kind = 'mod_ids'
    return (matches[0], kind) if len(matches) == 1 else (None, '')


def _offline_name(info, index):
    if not isinstance(index, Mapping):
        return ''
    entries = [(name, meta) for name, meta in index.items()
               if isinstance(name, str) and isinstance(meta, Mapping)]
    exact = [meta for name, meta in entries
             if name.casefold() == info.file_name.casefold()]
    if len(exact) == 1:
        return _text(exact[0].get('name_cn'))
    own_ids = _local_ids(info)
    matches = [meta for _, meta in entries
               if own_ids and _ids(meta.get('mod_ids')) == own_ids]
    return _text(matches[0].get('name_cn')) if len(matches) == 1 else ''


def _chinese(text):
    return bool(re.search('[\u3400-\u9fff]', text))


def _name(info, item, index):
    title = _text(item['metadata'].get('title')) if item else ''
    names = [_text(r.name) for r in _identity_registrations(info) if _text(r.name)]
    preferred = [title if _chinese(title) else '',
                 info.package_name if _chinese(info.package_name) else '',
                 _offline_name(info, index)]
    preferred.extend(name for name in names if _chinese(name))
    preferred.extend([title, info.package_name, *names, info.primary_id])
    return next((value for value in preferred if value), info.file_name)


_VERSION = re.compile(
    r'^v?(\d+(?:\.\d+)*)(?:[-._]?(dev|alpha|a|beta|b|pre|rc)'
    r'(?:[.-]?(\d+))?)?(?:\+[a-z0-9.-]+)?$', re.I)
_STAGE = {'dev': 0, 'alpha': 1, 'a': 1, 'beta': 2, 'b': 2, 'pre': 3, 'rc': 4}


def _version(value):
    value = _text(value)
    if len(value) > 128:
        return None
    match = _VERSION.fullmatch(value)
    if not match:
        return None
    core = tuple(int(part) for part in match[1].split('.'))
    stage = (_STAGE[match[2].lower()], int(match[3] or 0)) if match[2] else (5, 0)
    return core, stage


def _compare(left, right, source):
    if _text(left) and _text(left) == _text(right):
        return 0
    a, b = _version(left), _version(right)
    if a is None or b is None:
        return None
    # Integer script revisions and dotted release versions are different domains.
    # For registration-derived versions, even missing patch fields are uncertain.
    if source == 'registration' and len(a[0]) != len(b[0]):
        return None
    depth = max(len(a[0]), len(b[0]))
    ka = (a[0] + (0,) * (depth - len(a[0])), a[1])
    kb = (b[0] + (0,) * (depth - len(b[0])), b[1])
    return (ka > kb) - (ka < kb)


def _local_version(info, receipt, item, digest, release_versions):
    if item and digest and digest == _text(item.get('sha256')).lower():
        return _text(item.get('version')), 'catalog_hash'
    if item and digest and isinstance(release_versions, Mapping):
        known = release_versions.get(item.get('id'), {})
        if isinstance(known, Mapping) and _text(known.get(digest)):
            return _text(known[digest]), 'catalog_hash'
    if receipt and _text(receipt.get('version')):
        return _text(receipt['version']), 'receipt'
    if info.package_version:
        return info.package_version, 'package'
    registrations = _identity_registrations(info)
    if len(registrations) == 1 and registrations[0].version:
        return registrations[0].version, 'registration'
    return ('多版本' if registrations else '未识别'), ''


def _page(item, origin):
    if not item or not origin:
        return ''
    try:
        ident = str(uuid.UUID(item.get('id', '')))
    except (ValueError, TypeError, AttributeError):
        return ''
    expected = f'/mods/{ident}/'
    return expected if item.get('page_path') == expected else ''


def resolve_installed_mod(
    info: ModInfo,
    catalog_items: Sequence[Mapping] = (),
    *,
    receipts: Mapping | None = None,
    local_index: Mapping | None = None,
    origin: str = SITE_ORIGIN,
    local_sha256: str | None = None,
    release_versions: Mapping | None = None,
) -> InstalledModDisplay:
    """Resolve one MOD without network or file writes.

    catalog_items should come from parse_catalog. receipts is the install state's
    ``mods`` mapping. local_sha256 is required before a receipt can supply identity
    or version. Optional release_versions maps work ID -> SHA-256 -> release label.
    """
    try:
        origin = site_origin(origin)
    except (ValueError, TypeError, AttributeError):
        origin = ''
    digest = _text(local_sha256).lower()
    if not re.fullmatch('[0-9a-f]{64}', digest):
        digest = ''
    recorded = _receipt(info, receipts, origin) if origin else None
    receipt = recorded if recorded and digest == _text(recorded.get('sha256')).lower() else None
    items = [item for item in catalog_items if isinstance(item, Mapping)
             and isinstance(item.get('metadata'), Mapping)]
    item, matched_by = _match(info, items, receipt)
    index = _bundled_index() if local_index is None else local_index
    name = _name(info, item, index)
    installed, source = _local_version(info, receipt, item, digest, release_versions)
    latest = _text(item.get('version')) if item else ''
    comparison = _compare(installed, latest, source) if item and source else None
    status = ('未匹配官网' if not item else '版本待确认' if comparison is None
              else '有更新' if comparison < 0 else '已是最新' if comparison == 0
              else '本地版本较新')
    page_path = _page(item, origin)
    registrations = '\n'.join(
        f'{reg.mod_id}：{reg.name or "未命名"}（脚本版本 {reg.version or "未识别"}）'
        for reg in info.registrations)
    details = [name, f'文件：{info.file_name}', f'本地版本：{installed}']
    if info.package_id:
        details.append(f'包 ID：{info.package_id}')
        if info.package_version:
            details.append(f'包版本：{info.package_version}')
    if latest:
        details.append(f'官网版本：{latest} · {status}')
    if registrations:
        details.extend(['注册信息：', registrations])
    if item and source == 'registration' and comparison is None:
        details.append('脚本版本与官网发布版本无法直接比较。')
    tooltip = '\n'.join(details)
    return InstalledModDisplay(
        display_name=name, installed_version=installed, latest_version=latest,
        update_available=status == '有更新' and bool(page_path),
        page_path=page_path, update_url=origin + page_path if page_path else '',
        status=status, tooltip=tooltip,
        search_text=' '.join([info.file_name, name, tooltip]),
        matched_by=matched_by, version_source=source, catalog_item=item,
    )

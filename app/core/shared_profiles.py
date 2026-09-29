"""Share immutable collection manifests and install all files in one transaction."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import time
import uuid
from urllib.error import HTTPError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, build_opener

from .archive_safety import inspect_archive
from .diagnostics import diagnose_mods
from .mod_transactions import atomic_json, digest
from .modinfo import analyze_zip
from .online_catalog import NoRedirect, site_origin, OnlineInstaller
from .profile_protocol import (MAX_MANIFEST_BYTES, MAX_MOD_BYTES, MAX_MODS, MAX_TOTAL_BYTES,
                               validate_manifest, manifest_key, text)


def _open(request):
    try:
        return build_opener(NoRedirect()).open(request, timeout=60)
    except HTTPError as error:
        try:
            message = json.loads(error.read(MAX_MANIFEST_BYTES)).get('error')
        except (ValueError, AttributeError):
            message = None
        raise ValueError(message or f'网站请求失败（{error.code}），请检查网站是否已支持方案分享。') from error


def _json(origin, path, value=None):
    data = None if value is None else json.dumps(value, ensure_ascii=False).encode('utf-8')
    if data and len(data) > MAX_MANIFEST_BYTES:
        raise ValueError('方案清单过大。')
    request = Request(site_origin(origin) + path, data=data, headers={
        'Content-Type': 'application/json', 'X-BBMOD-Profile-Share': '1', 'User-Agent': 'BBMOD-Profiles/1'})
    with _open(request) as response:
        raw = response.read(MAX_MANIFEST_BYTES + 1)
    if len(raw) > MAX_MANIFEST_BYTES:
        raise ValueError('网站返回的方案数据过大。')
    result = json.loads(raw)
    if not isinstance(result, dict):
        raise ValueError('网站返回的方案数据无效。')
    return result


def profile_identity(value, origin):
    """Only IDs or links to the selected site; links cannot change the source."""
    if not isinstance(value, str):
        raise ValueError('方案编号无效。')
    value = value.strip()
    if '://' in value:
        parts = urlsplit(value)
        if parts.query or parts.fragment:
            raise ValueError('共享方案链接不能包含额外参数。')
        if parts.scheme == 'bbmod' and parts.netloc == 'profiles':
            value = parts.path.removeprefix('/')
        elif (parts.scheme + '://' + parts.netloc) == site_origin(origin):
            segments = parts.path.strip('/').split('/')
            if len(segments) != 2 or segments[0] != 'profiles':
                raise ValueError('请粘贴方案广场中的方案链接。')
            value = segments[1]
        else:
            raise ValueError('方案链接与当前军械库网站不一致。')
    try:
        if str(uuid.UUID(value)) != value:
            raise ValueError
    except (ValueError, AttributeError):
        raise ValueError('方案编号无效。') from None
    return value


def _check_combination(infos):
    issues = diagnose_mods(infos).issues
    errors = [f'{i.source}：{i.title}。{i.fix or ""}' for i in issues if i.severity == 'error']
    if errors:
        raise ValueError('方案未通过 MOD 兼容检查：\n' + '\n'.join(errors))
    return [f'{i.source}：{i.title}' for i in issues if i.severity == 'warning']


def prepare_share(manager, name, note='', game_version='', progress=lambda _: None):
    if manager.transaction.journal.exists():
        raise ValueError('请先恢复上次 MOD 操作。')
    manager.preview_profile(name)
    profiles = manager.load_profiles()
    sources, items, infos = {}, [], []
    locations = {m.path.name: m.path for m in manager.scan(analyze=False)}
    for filename in profiles[name]['enabled']:
        progress('正在核对本机文件：' + filename)
        path = locations[filename]
        if path.is_symlink():
            raise ValueError('方案文件不能是符号链接。')
        info = analyze_zip(path)
        infos.append(info)
        sha = digest(path)
        sources[sha] = path
        items.append({'file_name': filename, 'sha256': sha, 'size': path.stat().st_size,
            'title': (info.package_name or ' / '.join(r.name or r.mod_id for r in info.registrations) or filename)[:200],
            'version': (info.package_version if info.package_id else ' / '.join(r.version for r in info.registrations))[:100]})
    manifest = validate_manifest({'schema_version': 1, 'name': name, 'note': note,
                                  'game_version': game_version, 'mods': items})
    warnings = _check_combination(infos)
    return {'manifest': manifest, 'sources': sources, 'warnings': warnings}


def negotiate(origin, prepared):
    manifest = prepared['manifest']
    result = _json(origin, '/api/v1/profiles/plan/', manifest)
    if result.get('fingerprint') != manifest_key(manifest) or not isinstance(result.get('files'), list):
        raise ValueError('网站返回的上传计划与方案不一致。')
    rows = result['files']
    expected = {(m['file_name'], m['sha256']) for m in manifest['mods']}
    if len(rows) != len(expected):
        raise ValueError('网站返回的上传清单不完整。')
    actual = set()
    for row in rows:
        if not isinstance(row, dict) or row.get('status') not in {'available', 'missing', 'blocked'}:
            raise ValueError('网站返回的文件状态无效。')
        actual.add((row.get('file_name'), row.get('sha256')))
        if row['status'] == 'missing' and (not isinstance(row.get('ticket'), str) or len(row['ticket']) > 4096):
            raise ValueError('网站未提供有效的上传凭据。')
    if actual != expected:
        raise ValueError('网站返回的上传清单与方案不一致。')
    blocked = [row['file_name'] for row in rows if row['status'] == 'blocked']
    if blocked:
        raise ValueError('以下文件已下架或未公开，不能分享：\n' + '\n'.join(blocked))
    return rows


def _upload(origin, item, ticket, path):
    if digest(path) != item['sha256']:
        raise ValueError(f"{item['file_name']} 已改变，请重新分享方案。")
    with path.open('rb') as source:
        inspect_archive(source, max_bytes=MAX_MOD_BYTES)
    boundary = 'bbmod-' + uuid.uuid4().hex
    prefix = (f'--{boundary}\r\nContent-Disposition: form-data; name="ticket"\r\n\r\n{ticket}\r\n'
              f'--{boundary}\r\nContent-Disposition: form-data; name="archive"; filename="mod.zip"\r\n'
              'Content-Type: application/zip\r\n\r\n').encode('utf-8')
    suffix = f'\r\n--{boundary}--\r\n'.encode('ascii')

    def chunks():
        yield prefix
        started, count = time.monotonic(), 0
        with path.open('rb') as source:
            while block := source.read(128 * 1024):
                count += len(block)
                if count > item['size'] or time.monotonic() - started > 600:
                    raise ValueError('文件已改变或上传超时，请重试。')
                yield block
        if count != item['size']:
            raise ValueError('文件大小已改变，请重新分享。')
        yield suffix

    request = Request(site_origin(origin) + '/api/v1/profiles/files/' + item['sha256'] + '/', data=chunks(),
        headers={'Content-Type': 'multipart/form-data; boundary=' + boundary,
                 'Content-Length': str(len(prefix) + item['size'] + len(suffix)),
                 'X-BBMOD-Profile-Share': '1', 'User-Agent': 'BBMOD-Profiles/1'})
    with _open(request) as response:
        result = json.loads(response.read(MAX_MANIFEST_BYTES + 1))
    if not isinstance(result, dict) or result.get('sha256') != item['sha256']:
        raise ValueError('网站未确认文件上传成功，请重试。')


def publish_share(origin, prepared, progress=lambda _: None):
    # Renegotiate immediately before sending bytes: another user may have filled
    # a miss while the confirmation dialog was open. Also makes retries resumable.
    rows = negotiate(origin, prepared)
    uploaded = set()
    items = {m['sha256']: m for m in prepared['manifest']['mods']}
    for row in rows:
        sha = row['sha256']
        if row['status'] != 'missing' or sha in uploaded:
            continue
        progress('正在补传网站缺失的 MOD：' + row['file_name'])
        _upload(origin, items[sha], row['ticket'], prepared['sources'][sha])
        uploaded.add(sha)
    progress('文件已齐备，正在发布方案…')
    result = _json(origin, '/api/v1/profiles/', prepared['manifest'])
    identity = profile_identity(result.get('id', ''), origin)
    if result.get('page_path') != f'/profiles/{identity}/':
        raise ValueError('网站返回的分享链接无效。')
    return site_origin(origin) + result['page_path']


def fetch_profile(origin, identity):
    identity = profile_identity(identity, origin)
    result = _json(origin, f'/api/v1/profiles/{identity}/')
    if result.get('id') != identity:
        raise ValueError('网站返回的方案编号不一致。')
    return validate_manifest(result.get('manifest'))


def fetch_profiles(origin, query='', page=1):
    """Read and validate one page without trusting server-supplied URLs."""
    query = text(query, 100)
    if type(page) is not int or page < 1:
        raise ValueError('方案页码无效。')
    result = _json(origin, '/api/v1/profiles/?' + urlencode({'q': query, 'page': page}))
    if type(result.get('schema_version')) is not int or result['schema_version'] != 1:
        raise ValueError('网站尚未支持方案列表，请更新网站或使用链接导入。')
    items = result.get('items')
    if (not isinstance(items, list) or len(items) > 12
            or any(type(result.get(key)) is not int for key in ('page', 'pages', 'total'))
            or not 1 <= result['page'] <= result['pages']
            or result['total'] < len(items)):
        raise ValueError('网站返回的方案列表无效。')
    rows, seen = [], set()
    for item in items:
        if not isinstance(item, dict):
            raise ValueError('网站返回的方案条目无效。')
        identity = profile_identity(item.get('id', ''), origin)
        path = f'/profiles/{identity}/'
        if identity in seen or item.get('page_path') != path:
            raise ValueError('网站返回的方案链接无效。')
        seen.add(identity)
        if (type(item.get('mod_count')) is not int or not 1 <= item['mod_count'] <= MAX_MODS
                or type(item.get('total_size')) is not int or not 0 < item['total_size'] <= MAX_TOTAL_BYTES):
            raise ValueError('网站返回的方案大小无效。')
        rows.append({'id': identity, 'page_path': path, 'name': text(item.get('name'), 100, required=True),
            'note': text(item.get('note', ''), 2000), 'game_version': text(item.get('game_version', ''), 40),
            'created_at': text(item.get('created_at', ''), 64),
            'mod_count': item['mod_count'], 'total_size': item['total_size']})
    return {**result, 'items': rows}


def _local_state(manager):
    state, names = {}, set()
    for mod in manager.scan(analyze=False):
        name = mod.path.name.casefold()
        if name in names:
            raise ValueError('启用与禁用目录存在同名文件，请先处理：' + mod.path.name)
        if mod.path.is_symlink() or mod.path.resolve().parent != mod.path.parent.resolve():
            raise ValueError('MOD 路径无效。')
        names.add(name)
        state[str(mod.path.relative_to(manager.root))] = digest(mod.path)
    for path in (manager._profiles_path(), OnlineInstaller(manager).state_path):
        state[str(path.relative_to(manager.root))] = digest(path)
    return state


def preview_apply(manager, manifest):
    manifest = validate_manifest(manifest)
    if manager.transaction.journal.exists():
        raise ValueError('请先恢复上次 MOD 操作。')
    state = _local_state(manager)
    active = {m.path.name.casefold(): m for m in manager.scan(analyze=False) if m.enabled}
    hashes = {sha for path, sha in state.items() if Path(path).suffix.lower() in {'.zip', '.rar'}}
    desired = {m['file_name'].casefold() for m in manifest['mods']}
    download = [m['file_name'] for m in manifest['mods'] if m['sha256'] not in hashes]
    change = [m['file_name'] for m in manifest['mods'] if m['file_name'].casefold() not in active
              or state[str(active[m['file_name'].casefold()].path.relative_to(manager.root))] != m['sha256']]
    return {'state': state, 'fingerprint': manifest_key(manifest), 'download': download, 'change': change,
            'disable': sorted(m.path.name for key, m in active.items() if key not in desired)}


def _download(origin, identity, item, destination):
    from .downloads import download_verified
    download_verified(site_origin(origin) + f"/api/v1/profiles/{identity}/files/{item['sha256']}/",
                      destination, size=item['size'], sha256=item['sha256'])


def apply_shared(manager, origin, identity, manifest, *, expected, progress=lambda _: None):
    identity = profile_identity(identity, origin)
    manifest = validate_manifest(manifest)
    if preview_apply(manager, manifest) != expected:
        raise ValueError('本机 MOD 或方案已改变，请重新预览。')
    if fetch_profile(origin, identity) != manifest:
        raise ValueError('共享方案已改变，请重新预览。')
    with tempfile.TemporaryDirectory(prefix='bbmod-profile-') as temporary:
        staging, packages, infos = Path(temporary), {}, []
        local = {sha: manager.root / name for name, sha in expected['state'].items()
                 if Path(name).suffix.lower() in {'.zip', '.rar'}}
        for index, item in enumerate(manifest['mods']):
            sha = item['sha256']
            if sha not in packages:
                destination = staging / f'{index}.zip'
                if sha in local:
                    progress('复用本机 MOD：' + item['file_name'])
                    shutil.copyfile(local[sha], destination)
                else:
                    progress('下载缺失 MOD：' + item['file_name'])
                    _download(origin, identity, item, destination)
                with destination.open('rb') as source:
                    checked = inspect_archive(source, max_bytes=MAX_MOD_BYTES)
                if checked['sha256'] != sha or checked['size'] != item['size']:
                    raise ValueError('MOD 文件已改变或下载校验失败，请重新预览。')
                packages[sha] = destination
            info = analyze_zip(packages[sha])
            info.file_name = item['file_name']
            infos.append(info)
        warnings = _check_combination(infos)
        if preview_apply(manager, manifest) != expected:
            raise ValueError('下载期间本机文件已改变，尚未应用，请重新预览。')
        # Recheck delisting after downloads, including when all files were local.
        fetch_profile(origin, identity)
        from .game import is_game_running
        if is_game_running():
            raise ValueError('游戏已启动，请关闭游戏后重新应用方案。')
        mods = manager.scan(analyze=False)
        wanted = {m['file_name'].casefold(): m for m in manifest['mods']}
        changes = {}
        for mod in mods:
            name = mod.path.name.casefold()
            if mod.enabled and name not in wanted:
                changes[manager.disabled_dir / mod.path.name] = mod.path
                changes[mod.path] = None
            elif not mod.enabled and name in wanted:
                changes[mod.path] = None
        for item in manifest['mods']:
            existing = next((m for m in mods if m.enabled and m.path.name.casefold() == item['file_name'].casefold()), None)
            target = existing.path if existing else manager.data / item['file_name']
            changes[target] = packages[item['sha256']]
        profiles = manager.load_profiles()
        name = next((name for name, profile in profiles.items()
                     if profile.get('shared_id') == identity and profile.get('shared_origin') == site_origin(origin)),
                    manifest['name'])
        serial = 2
        while name in profiles and (profiles[name].get('shared_id') != identity
                or profiles[name].get('shared_origin') != site_origin(origin)):
            name = f"{manifest['name']}（共享 {serial}）"
            serial += 1
        from datetime import datetime
        profiles[name] = {**profiles.get(name, {}), 'enabled': sorted(path.name for path, source in changes.items()
                                          if path.parent == manager.data and source is not None),
                          'saved_at': datetime.now().isoformat(timespec='seconds'), 'shared_id': identity,
                          'shared_origin': site_origin(origin)}
        profile_file = staging / 'profiles.json'
        atomic_json(profile_file, profiles)
        changes[manager._profiles_path()] = profile_file
        installer = OnlineInstaller(manager)
        receipt = installer.state()
        for filename in list(receipt['mods']):
            item = wanted.get(filename.casefold())
            if item and receipt['mods'][filename].get('sha256') != item['sha256']:
                del receipt['mods'][filename]
        if installer.state_path.exists():
            receipt_file = staging / 'online-catalog.json'
            atomic_json(receipt_file, receipt)
            changes[installer.state_path] = receipt_file
        progress('所有文件已校验，正在应用整套方案…')
        backup = manager._apply(changes, validate=True, keep_backups=True)
        manager._audit('shared-profile-apply', manager._profiles_path(), manager.data)
    return {'name': name, 'count': len(manifest['mods']), 'downloaded': len(expected['download']),
            'disabled': len(expected['disable']), 'backup': str(backup), 'warnings': warnings}

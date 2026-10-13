"""Share closed-game campaigns and restore their pinned MODs in one transaction."""
from pathlib import Path
import hashlib
import json
import tempfile
import uuid
from urllib.parse import urlencode, urlsplit
from urllib.request import Request

from . import game, shared_profiles as profiles
from .archive_safety import inspect_archive
from .mod_transactions import ModTransaction, digest
from .online_catalog import site_origin
from .profile_protocol import MAX_MANIFEST_BYTES, MAX_MOD_BYTES, MAX_MODS, MAX_TOTAL_BYTES, text
from .save_protocol import DLCS, MAX_SAVE_BYTES, inspect_save, manifest_key, profile_manifest, save_name, validate_manifest
from .site_config import same_site


def save_directory(preferred=None):
    if preferred:
        return Path(preferred).resolve()
    candidates = [folder / 'savegames' for folder in game.find_log_write_paths()]
    return next((p for p in candidates if p.is_dir()),
                (game.documents_path() or Path.home() / 'Documents') / game.GAME_DIRNAME / 'savegames')


def list_saves(directory):
    rows = []
    for path in Path(directory).glob('*.sav'):
        if path.is_symlink():
            continue
        with path.open('rb') as source:
            header = source.read(7)
        if len(header) != 7 or header[:3] != b'\xbb\x00\x02' or not int.from_bytes(header[3:7], 'little'):
            continue
        stat = path.stat()
        rows.append({'path': path, 'name': path.stem.strip() or '未命名战役', 'size': stat.st_size, 'mtime': stat.st_mtime})
    return sorted(rows, key=lambda row: row['mtime'], reverse=True)


def _idle(manager):
    if game.is_game_running():
        raise ValueError('请先退出游戏，再分享或恢复存档。')
    if manager.transaction.journal.exists() or (manager.root / 'bbmod_localizations/pending-switch.json').exists():
        raise ValueError('请先恢复上次未完成的文件操作。')
    if (manager.root / 'bbmod_seedgen_session/session.json').exists():
        raise ValueError('请先停止并恢复种子远征。')
    if (manager.data / 'mod_zz_bbmod_preview_guard.zip').exists():
        raise ValueError('开发测试目录不能用于分享或恢复战役存档。')


def _json(origin, path, value=None):
    data = None if value is None else json.dumps(value, ensure_ascii=False).encode('utf-8')
    if data and len(data) > MAX_MANIFEST_BYTES:
        raise ValueError('存档清单过大。')
    request = Request(site_origin(origin) + path, data=data, headers={'Content-Type': 'application/json',
        'X-BBMOD-Save-Share': '1', 'User-Agent': 'BBMOD-Saves/1'})
    with profiles._open(request) as response:
        raw = response.read(MAX_MANIFEST_BYTES + 1)
    if len(raw) > MAX_MANIFEST_BYTES:
        raise ValueError('网站返回的存档数据过大。')
    result = json.loads(raw)
    if not isinstance(result, dict):
        raise ValueError('网站返回的存档数据无效。')
    return result


def save_identity(value, origin):
    if not isinstance(value, str):
        raise ValueError('存档分享编号无效。')
    value = value.strip()
    if '://' in value:
        parts = urlsplit(value)
        if parts.query or parts.fragment:
            raise ValueError('存档链接不能包含额外参数。')
        if parts.scheme == 'bbmod' and parts.netloc == 'saves':
            value = parts.path.removeprefix('/')
        elif same_site(parts.scheme + '://' + parts.netloc, site_origin(origin)):
            segments = parts.path.strip('/').split('/')
            if len(segments) != 2 or segments[0] != 'saves':
                raise ValueError('请使用存档广场的分享链接。')
            value = segments[1]
        else:
            raise ValueError('存档链接与当前网站来源不一致。')
    try:
        if str(uuid.UUID(value)) != value:
            raise ValueError
    except (ValueError, AttributeError):
        raise ValueError('存档分享编号无效。') from None
    return value


def prepare_share(manager, path, name, note='', game_version='', progress=lambda _: None):
    _idle(manager)
    path = Path(path)
    if path.is_symlink() or path.suffix.lower() != '.sav':
        raise ValueError('请选择普通战役存档 .sav 文件。')
    with path.open('rb') as source:
        save = inspect_save(source)
    save['file_name'] = 'BBMOD-' + save['sha256'][:12] + '.sav'
    items, sources, infos = [], {}, []
    with manager.file_access():
        for mod in manager.scan(analyze=False):
            if not mod.enabled:
                continue
            if mod.path.is_symlink() or mod.path.suffix.lower() != '.zip':
                raise ValueError('分享存档需要所有启用的 MOD 均为可直接安装的 ZIP。')
            progress('核对配套 MOD：' + mod.path.name)
            with mod.path.open('rb') as source:
                checked = inspect_archive(source, max_bytes=MAX_MOD_BYTES)
            info = manager.analyze(mod.path)
            infos.append(info)
            items.append({**checked, 'file_name': mod.path.name,
                'title': (info.package_name or ' / '.join(r.name or r.mod_id for r in info.registrations) or mod.path.name)[:200],
                'version': (info.package_version or ' / '.join(r.version for r in info.registrations))[:100]})
            sources[checked['sha256']] = mod.path
    manifest = validate_manifest({'schema_version': 1, 'name': name, 'note': note,
        'game_version': game_version, 'mods': items, 'save': save,
        'dlcs': [dlc for dlc, enabled in game.installed_dlcs(manager.data).items() if enabled]})
    prepared = {'manifest': manifest, 'sources': sources, 'save_path': path, 'manager': manager,
                'warnings': profiles._check_combination(infos)}
    _check_sources(prepared)
    return prepared


def _check_sources(prepared):
    manager, manifest = prepared['manager'], prepared['manifest']
    _idle(manager)
    active = {m.path.name for m in manager.scan(analyze=False) if m.enabled}
    if active != {m['file_name'] for m in manifest['mods']}:
        raise ValueError('启用的 MOD 已改变，请重新核对存档分享。')
    if sorted(d for d, present in game.installed_dlcs(manager.data).items() if present) != manifest['dlcs']:
        raise ValueError('游戏 DLC 已改变，请重新分享。')
    if digest(prepared['save_path']) != manifest['save']['sha256']:
        raise ValueError('存档已改变，请重新分享。')
    for item in manifest['mods']:
        if digest(prepared['sources'][item['sha256']]) != item['sha256']:
            raise ValueError('配套 MOD 已改变，请重新分享。')


def negotiate(origin, prepared):
    manifest = validate_manifest(prepared['manifest'])
    result = _json(origin, '/api/v1/saves/plan/', manifest)
    if result.get('schema_version') != 1 or result.get('fingerprint') != manifest_key(manifest):
        raise ValueError('网站返回的存档计划与清单不一致。')
    rows, save = result.get('files'), result.get('save')
    if not isinstance(rows, list) or len(rows) != len(manifest['mods']) or not isinstance(save, dict):
        raise ValueError('存档上传计划不完整。')
    expected = {(m['file_name'], m['sha256']) for m in manifest['mods']}
    actual = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError('MOD 上传计划无效。')
        actual.add((row.get('file_name'), row.get('sha256')))
    if actual != expected or save.get('sha256') != manifest['save']['sha256']:
        raise ValueError('存档上传计划文件不匹配。')
    for row in [*rows, save]:
        if row.get('status') not in {'available', 'missing'}:
            raise ValueError('存档或配套 MOD 已下架，无法分享。')
        if row['status'] == 'missing' and (not isinstance(row.get('ticket'), str) or not 0 < len(row['ticket']) <= 4096):
            raise ValueError('网站没有返回有效上传凭据。')
    return result


def _upload_save(origin, item, ticket, path):
    boundary = 'bbmod-' + uuid.uuid4().hex
    prefix = (f'--{boundary}\r\nContent-Disposition: form-data; name="ticket"\r\n\r\n{ticket}\r\n'
              f'--{boundary}\r\nContent-Disposition: form-data; name="save"; filename="campaign.sav"\r\n'
              'Content-Type: application/octet-stream\r\n\r\n').encode('utf-8')
    suffix = f'\r\n--{boundary}--\r\n'.encode('ascii')
    def chunks():
        yield prefix
        size, sha = 0, hashlib.sha256()
        with Path(path).open('rb') as source:
            while block := source.read(128 * 1024):
                size += len(block)
                if size > item['size']:
                    raise ValueError('上传期间存档大小已改变。')
                sha.update(block)
                yield block
        if size != item['size'] or sha.hexdigest() != item['sha256']:
            raise ValueError('上传期间存档已改变。')
        yield suffix
    request = Request(site_origin(origin) + f"/api/v1/saves/files/{item['sha256']}/", data=chunks(), headers={
        'Content-Type': 'multipart/form-data; boundary=' + boundary, 'X-BBMOD-Save-Share': '1',
        'Content-Length': str(len(prefix) + item['size'] + len(suffix)), 'User-Agent': 'BBMOD-Saves/1'})
    with profiles._open(request) as response:
        raw = response.read(MAX_MANIFEST_BYTES + 1)
    if len(raw) > MAX_MANIFEST_BYTES or json.loads(raw).get('sha256') != item['sha256']:
        raise ValueError('网站未确认存档上传成功。')


def publish_share(origin, prepared, progress=lambda _: None):
    _check_sources(prepared)
    plan, uploaded = negotiate(origin, prepared), set()
    items = {m['sha256']: m for m in prepared['manifest']['mods']}
    for row in plan['files']:
        sha = row['sha256']
        if row['status'] == 'missing' and sha not in uploaded:
            progress('上传配套 MOD：' + row['file_name'])
            profiles._upload(origin, items[sha], row['ticket'], prepared['sources'][sha])
            uploaded.add(sha)
    if plan['save']['status'] == 'missing':
        progress('上传战役存档…')
        _upload_save(origin, prepared['manifest']['save'], plan['save']['ticket'], prepared['save_path'])
    _check_sources(prepared)
    progress('存档与 MOD 已齐备，正在发布…')
    result = _json(origin, '/api/v1/saves/', prepared['manifest'])
    identity = save_identity(result.get('id'), origin)
    if result.get('page_path') != f'/saves/{identity}/':
        raise ValueError('网站返回的存档分享链接无效。')
    return site_origin(origin) + result['page_path']


def fetch_save(origin, identity):
    identity = save_identity(identity, origin)
    result = _json(origin, f'/api/v1/saves/{identity}/')
    if result.get('id') != identity:
        raise ValueError('网站返回的存档编号不一致。')
    return validate_manifest(result.get('manifest'))


def fetch_saves(origin, query='', page=1):
    if type(page) is not int or page < 1:
        raise ValueError('存档页码无效。')
    result = _json(origin, '/api/v1/saves/?' + urlencode({'q': text(query, 100), 'page': page}))
    if (type(result.get('schema_version')) is not int or result['schema_version'] != 1
            or not isinstance(result.get('items'), list) or len(result['items']) > 12
            or any(type(result.get(k)) is not int for k in ('page', 'pages', 'total'))
            or not 1 <= result['page'] <= result['pages'] or result['total'] < len(result['items'])):
        raise ValueError('网站返回的存档列表无效。')
    rows, seen = [], set()
    for row in result['items']:
        if not isinstance(row, dict):
            raise ValueError('存档条目无效。')
        identity = save_identity(row.get('id'), origin)
        if identity in seen or row.get('page_path') != f'/saves/{identity}/':
            raise ValueError('存档详情链接无效。')
        seen.add(identity)
        if (type(row.get('mod_count')) is not int or not 0 <= row['mod_count'] <= MAX_MODS
                or type(row.get('total_size')) is not int or not 256 <= row['total_size'] <= MAX_TOTAL_BYTES + MAX_SAVE_BYTES
                or not isinstance(row.get('dlcs'), list) or len(row['dlcs']) > len(DLCS)
                or any(not isinstance(d, str) or d not in DLCS for d in row['dlcs'])):
            raise ValueError('存档条目信息无效。')
        rows.append({**row, 'id': identity, 'name': text(row.get('name'), 100, required=True),
                     'note': text(row.get('note', ''), 2000), 'game_version': text(row.get('game_version'), 40, required=True),
                     'created_at': text(row.get('created_at'), 64)})
    return {**result, 'items': rows}


class SaveTransaction(ModTransaction):
    """Same durable MOD journal; only one explicitly selected save folder is added."""
    def __init__(self, root, directory):
        super().__init__(root)
        self.save_dir = Path(directory).resolve()
        self.prefix = '@savegames-' + hashlib.sha256(str(self.save_dir).casefold().encode('utf-8')).hexdigest()[:16]

    def relative(self, destination):
        path = Path(destination)
        if path.parent == self.save_dir:
            return self.prefix + '/' + save_name(path.name)
        return super().relative(destination)

    def target(self, relative):
        parts = Path(relative).parts
        if parts and parts[0].startswith('@savegames-'):
            if len(parts) != 2 or parts[0] != self.prefix:
                raise ValueError('恢复记录的存档目录与当前选择不一致，请选择原导入目录。')
            path = self.save_dir / save_name(parts[1])
            if path.is_symlink() or path.resolve().parent != self.save_dir:
                raise ValueError('存档路径越界。')
            return path
        return super().target(relative)

    def before_commit(self, entries):
        if game.is_game_running():
            raise ValueError('游戏已启动，已取消存档导入。')
        for entry in entries:
            if entry['path'].startswith(self.prefix) and entry['before'] is not None:
                raise ValueError('目标存档已存在，已取消导入并保留原存档。')


def preview_restore(manager, manifest, directory, game_version):
    _idle(manager)
    manifest = validate_manifest(manifest)
    if game_version != manifest['game_version']:
        raise ValueError(f"存档使用游戏 {manifest['game_version']}，本机为 {game_version or '未知'}，请先使用相同游戏版本。")
    missing = set(manifest['dlcs']) - {d for d, present in game.installed_dlcs(manager.data).items() if present}
    if missing:
        raise ValueError('本机缺少配套 DLC：' + '、'.join(sorted(missing)))
    directory = Path(directory).resolve()
    if directory.is_relative_to(manager.root.resolve()):
        raise ValueError('存档目录应为文档下的 savegames，不能放入游戏安装目录。')
    target = directory / ('BBMOD-' + manifest['save']['sha256'][:12] + '-' + uuid.uuid4().hex[:8] + '.sav')
    return {'mods': profiles.preview_apply(manager, profile_manifest(manifest), allow_empty=True),
            'fingerprint': manifest_key(manifest), 'target': str(target), 'directory': str(directory)}


def restore(manager, origin, identity, manifest, *, expected, game_version, progress=lambda _: None):
    identity, manifest = save_identity(identity, origin), validate_manifest(manifest)
    directory, target = Path(expected['directory']), Path(expected['target'])
    fresh = preview_restore(manager, manifest, directory, game_version)
    if (fresh['mods'] != expected['mods'] or fresh['fingerprint'] != expected['fingerprint']
            or target.parent != directory or save_name(target.name) != target.name or target.exists()):
        raise ValueError('本机文件、存档目录或清单已改变，请重新预览。')
    if fetch_save(origin, identity) != manifest:
        raise ValueError('存档分享已改变，请重新预览。')
    from .downloads import download_verified
    def download(item, destination):
        download_verified(site_origin(origin) + f"/api/v1/saves/{identity}/files/{item['sha256']}/",
                          destination, size=item['size'], sha256=item['sha256'])
    def verify():
        if fetch_save(origin, identity) != manifest:
            raise ValueError('存档分享已改变，请重新预览。')
        _idle(manager)
        if set(manifest['dlcs']) - {d for d, present in game.installed_dlcs(manager.data).items() if present}:
            raise ValueError('下载期间本机 DLC 已改变，请重新预览。')
        return profile_manifest(manifest)
    with tempfile.TemporaryDirectory(prefix='bbmod-save-') as temporary:
        staged = Path(temporary) / 'campaign.sav'
        progress('下载战役存档…')
        download(manifest['save'], staged)
        with staged.open('rb') as source:
            if inspect_save(source) != {k: manifest['save'][k] for k in ('sha256', 'size')}:
                raise ValueError('存档下载校验失败。')
        with manager.file_access():
            original = manager.transaction
            manager.transaction = SaveTransaction(manager.root, directory)
            try:
                result = profiles.apply_shared(manager, origin, identity, profile_manifest(manifest),
                    expected=expected['mods'], progress=progress, allow_empty=True, save_share=True,
                    download=download, verify=verify,
                    extra_changes={target: staged})
            finally:
                manager.transaction = original
    return {**result, 'save_path': str(target)}


def recover(manager, directory):
    if game.is_game_running() or (manager.root / 'bbmod_seedgen_session/session.json').exists():
        raise ValueError('请先退出游戏并停止种子远征，再恢复。')
    with manager.file_access():
        SaveTransaction(manager.root, directory).recover()

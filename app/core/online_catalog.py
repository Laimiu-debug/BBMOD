"""Self-hosted catalog client and reversible installation; never starts the game."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
import time
import uuid
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, HTTPRedirectHandler, build_opener

from .archive_safety import inspect_archive, valid_install_name
from .modinfo import analyze_zip
from .downloads import download_verified
from .site_config import canonical_site_origin, same_site

MAX_DOWNLOAD = 100 * 1024 * 1024


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('军械库地址发生重定向，请填写网站最终地址后重试。')


def site_origin(value):
    value = value.strip().rstrip('/')
    parts = urlsplit(value)
    if (parts.scheme not in {'http', 'https'} or not parts.hostname
            or parts.username is not None or parts.password is not None
            or parts.path or parts.query or parts.fragment or any(c.isspace() for c in value)):
        raise ValueError('请输入网站根地址，例如 http://服务器IP:8080 或 https://域名。')
    _ = parts.port
    return canonical_site_origin(f'{parts.scheme}://{parts.netloc.lower()}')


def _request(url):
    return build_opener(NoRedirect()).open(Request(url, headers={'User-Agent': 'BBMOD-Catalog/1', 'Accept-Encoding': 'identity'}), timeout=12)


def parse_catalog(payload):
    if not isinstance(payload, dict) or payload.get('schema_version') != 1 or not isinstance(payload.get('mods'), list):
        raise ValueError('网站返回了不支持的军械库格式。')
    if len(payload['mods']) > 5000:
        raise ValueError('军械库条目过多。')
    seen = set()
    names = set()
    result = []
    for item in payload['mods']:
        if not isinstance(item, dict):
            raise ValueError('军械库条目无效。')
        try:
            uuid.UUID(item['id']); uuid.UUID(item['release_id'])
            if not valid_install_name(item['file_name']):
                raise ValueError('无效的安装文件名。')
            if item['id'] in seen or item['file_name'].casefold() in names:
                raise ValueError('军械库包含重复作品或安装文件。')
            if not isinstance(item['size'], int) or not 0 < item['size'] <= MAX_DOWNLOAD:
                raise ValueError('MOD 文件大小超过限制。')
            if not isinstance(item['sha256'], str) or not re.fullmatch('[0-9a-f]{64}', item['sha256']):
                raise ValueError('缺少有效 SHA-256 校验值。')
            if not isinstance(item['version'], str) or len(item['version']) > 40:
                raise ValueError('版本信息无效。')
            if item['download_path'] != f"/files/{item['release_id']}/download/" or item['page_path'] != f"/mods/{item['id']}/":
                raise ValueError('下载路径必须来自本站。')
            meta = item['metadata']
            for key in ['title', 'summary', 'description', 'category', 'author', 'game_version', 'license']:
                if not isinstance(meta.get(key), str) or len(meta[key]) > 20000:
                    raise ValueError('作品说明无效。')
            for key in ['mod_ids', 'requires', 'conflicts']:
                if not isinstance(meta.get(key), list) or len(meta[key]) > 30 or any(not isinstance(v, str) or not re.fullmatch('[A-Za-z0-9_.-]{1,100}', v) for v in meta[key]):
                    raise ValueError('MOD 依赖信息无效。')
            seen.add(item['id']); names.add(item['file_name'].casefold())
            result.append(item)
        except (KeyError, TypeError, AttributeError) as exc:
            raise ValueError('军械库条目字段不完整。') from exc
    return result


def fetch_catalog(origin):
    return _fetch_catalog(site_origin(origin) + '/api/v1/catalog/')


def _fetch_catalog(url):
    parts = []; total = 0; started = time.monotonic()
    with _request(url) as response:
        while block := response.read1(128 * 1024):
            total += len(block)
            if total > 4 * 1024 * 1024 or time.monotonic() - started > 30:
                raise ValueError('目录数据过大或读取超时。')
            parts.append(block)
    return parse_catalog(json.loads(b''.join(parts)))


def download_release(origin, item, cache, *, cancelled=lambda: False, progress=lambda _: None):
    # Validate one item again, including callers outside the UI.
    parse_catalog({'schema_version': 1, 'mods': [item]})
    origin = site_origin(origin)
    cache = Path(cache)
    cache.mkdir(parents=True, exist_ok=True)
    handle, name = tempfile.mkstemp(prefix='mod-', suffix='.zip', dir=cache)
    os.close(handle)
    target = Path(name)
    try:
        download_verified(origin + item['download_path'], target, size=item['size'], sha256=item['sha256'],
                          cancelled=cancelled, progress=progress)
        with target.open('rb') as src:
            inspect_archive(src)
        return target
    except Exception:
        target.unlink(missing_ok=True)
        raise


def _atomic_json(path, data):
    handle, temp = tempfile.mkstemp(dir=path.parent, prefix='.online-', suffix='.tmp')
    try:
        with os.fdopen(handle, 'w', encoding='utf-8') as out:
            json.dump(data, out, ensure_ascii=False, indent=2)
            out.flush(); os.fsync(out.fileno())
        os.replace(temp, path)
    finally:
        Path(temp).unlink(missing_ok=True)


def _hash(path):
    with path.open('rb') as src:
        return hashlib.file_digest(src, 'sha256').hexdigest()


class OnlineInstaller:
    def __init__(self, manager):
        self.mm = manager
        self.data = manager.data
        self.disabled = manager.disabled_dir
        self.state_path = self.disabled / 'online-catalog.json'
        self.backups = self.disabled / 'online-backups'

    def state(self):
        if not self.state_path.exists():
            return {'mods': {}}
        data = json.loads(self.state_path.read_text(encoding='utf-8'))
        if not isinstance(data, dict) or not isinstance(data.get('mods'), dict):
            raise ValueError('在线 MOD 安装记录损坏，请先恢复记录。')
        return data

    def _locations(self, name):
        if not valid_install_name(name):
            raise ValueError('无效安装文件名。')
        candidates = [self.data / name, self.disabled / name]
        if any(p.is_symlink() or p.resolve().parent != p.parent.resolve() for p in candidates):
            raise ValueError('安装路径不能是符号链接。')
        found = [p for p in candidates if p.exists()]
        if len(found) > 1:
            raise ValueError('启用和禁用目录中均有同名文件，请先处理重复文件。')
        return found[0] if found else None

    def check_compatibility(self, item, archive, *, local_file_name=None):
        info = analyze_zip(archive)
        installed = self.mm.scan()
        target_name = local_file_name or item['file_name']
        enabled = [m.info for m in installed if m.enabled and m.path.name.casefold() != target_name.casefold()]
        ids = {r.mod_id for m in enabled for r in m.registrations}
        own = set(item['metadata']['mod_ids']) | {r.mod_id for r in info.registrations}
        missing = set(item['metadata']['requires']) - ids - own
        clashes = set(item['metadata']['conflicts']) & ids
        duplicate = own & ids
        for other in enabled:
            clashes.update(set(other.declared_conflicts) & own)
        if missing or clashes or duplicate:
            details = []
            if missing: details.append('缺少或未启用前置：' + '、'.join(sorted(missing)))
            if clashes: details.append('存在已声明冲突：' + '、'.join(sorted(clashes)))
            if duplicate: details.append('其他已启用文件已注册同一 MOD：' + '、'.join(sorted(duplicate)))
            raise ValueError('\n'.join(details))

    def install(self, origin, item, archive, *, local_file_name=None,
                expected_current_sha256=None, installed_version=None):
        """Install a catalog release, or update one explicitly selected local file.

        Local updates use all three keyword arguments from the pre-download
        selection. The digest prevents replacing a file changed while downloading;
        the selected filename preserves profiles, load order and enabled state.
        Normal catalog installs continue to refuse untracked local files.
        """
        if self.mm.transaction.journal.exists():
            raise ValueError('请先恢复上次未完成的 MOD 操作。')
        parse_catalog({'schema_version': 1, 'mods': [item]})
        origin = site_origin(origin)
        local_update = any(v is not None for v in
                           (local_file_name, expected_current_sha256, installed_version))
        if local_update and (not valid_install_name(local_file_name)
                             or not isinstance(expected_current_sha256, str)
                             or not re.fullmatch('[0-9a-f]{64}', expected_current_sha256)
                             or not isinstance(installed_version, str)
                             or not installed_version.strip() or len(installed_version) > 128
                             or any(ord(c) < 32 for c in installed_version)):
            raise ValueError('本地更新须提供所选文件名、当前 SHA-256 和已安装版本，请刷新后重试。')
        archive = Path(archive)
        with archive.open('rb') as src:
            check = inspect_archive(src)
        if check['sha256'] != item['sha256'] or check['size'] != item['size']:
            raise ValueError('安装文件校验失败。')
        state = self.state()
        name = local_file_name if local_update else item['file_name']
        receipt_keys = [key for key in state['mods'] if key.casefold() == name.casefold()]
        if len(receipt_keys) > 1:
            raise ValueError('所选文件存在重复在线安装记录，请先处理重复记录。')
        receipt_key = receipt_keys[0] if receipt_keys else name
        previous = state['mods'].get(receipt_key)
        if previous and (not same_site(previous['origin'], origin) or previous['id'] != item['id']):
            raise ValueError('同名文件属于另一网站或作品，不能自动覆盖。')
        current = self._locations(name)
        current_hash = _hash(current) if current else None
        if local_update and (not current or current_hash != expected_current_sha256):
            raise ValueError('所选 MOD 文件已改变或已不存在，请刷新后重新更新。')
        if current and ((not previous and not local_update)
                        or (previous and current_hash != previous['sha256'])):
            raise ValueError('同名文件未由在线军械库管理或已被修改，已停止覆盖。请先手动备份处理。')
        if local_update:
            if previous and previous['version'] != installed_version:
                raise ValueError('在线安装记录版本已改变，请刷新后重新更新。')
            self._check_local_update_identity(current, archive, item, trusted=bool(previous))
            for key, other in state['mods'].items():
                if (key.casefold() != name.casefold() and same_site(other['origin'], origin)
                        and other['id'] == item['id'] and self._locations(key)):
                    raise ValueError('同一作品已安装在另一文件中，请先处理重复安装。')
            if name.casefold() != item['file_name'].casefold() and self._locations(item['file_name']):
                raise ValueError('网站新版文件名已存在本地，请先处理重复安装。')
        if current and current_hash == item['sha256']:
            return f"{item['metadata']['title']} 已是所选版本，保留现有备份。"
        if ((previous and previous['version'] == item['version'])
                or (local_update and installed_version == item['version'])):
            raise ValueError('网站上同一版本的文件校验值发生变化，请联系作者发布新版本后再更新。')
        self.check_compatibility(item, archive, local_file_name=name)
        target = current or self.data / name
        self.disabled.mkdir(parents=True, exist_ok=True)
        self.backups.mkdir(parents=True, exist_ok=True)
        backup = None
        installed = False
        try:
            with tempfile.TemporaryDirectory(prefix='bbmod-online-') as staging:
                changes = {target: archive}
                entry = {'origin': origin, 'id': item['id'], 'version': item['version'], 'sha256': item['sha256']}
                if current:
                    backup = self.backups / f'{uuid.uuid4().hex}.zip'
                    shutil.copy2(current, backup)
                    if _hash(backup) != current_hash:
                        raise ValueError('更新前备份校验失败。')
                    old_entry = previous or {'origin': origin, 'id': item['id'],
                                            'version': installed_version, 'sha256': current_hash,
                                            'adopted_from_local': True}
                    entry['previous'] = {k: v for k, v in old_entry.items() if k != 'previous'}
                    entry['backup'] = backup.name
                if receipt_key != name:
                    del state['mods'][receipt_key]
                state['mods'][name] = entry
                receipt = Path(staging) / 'online-catalog.json'
                _atomic_json(receipt, state)
                changes[self.state_path] = receipt
                if current and (self._locations(name) != current or _hash(current) != current_hash):
                    raise ValueError('更新前 MOD 文件已改变，请刷新后重试。')
                if _hash(archive) != item['sha256']:
                    raise ValueError('安装文件校验失败。')
                self.mm._apply(changes, validate=True)
                installed = True
        finally:
            # Keep backups needed by an interrupted transaction; otherwise a
            # failed update must not leave an unreferenced catalog backup.
            if backup and not installed and not self.mm.transaction.journal.exists():
                try:
                    referenced = self.state()['mods'].get(name, {}).get('backup') == backup.name
                except (OSError, ValueError):
                    referenced = True
                if not referenced:
                    backup.unlink(missing_ok=True)
        return f"已安装 {item['metadata']['title']} v{item['version']}" + ('（保持禁用）' if target.parent == self.disabled else '')

    def _check_local_update_identity(self, current, archive, item, *, trusted):
        old = analyze_zip(current)
        new = analyze_zip(archive)
        if old.analysis_errors or new.analysis_errors:
            raise ValueError('无法确认新旧 MOD 文件身份，已停止自动更新。')
        if old.package_id or new.package_id:
            if not old.package_id or old.package_id != new.package_id:
                raise ValueError('新旧 MOD 的包身份不一致，已停止自动更新。')
            return
        if trusted:
            # A verified receipt binds releases to the same catalog work even
            # when its author adds or replaces script registrations.
            return
        old_ids = {reg.mod_id for reg in old.registrations}
        new_ids = {reg.mod_id for reg in new.registrations}
        if old_ids or new_ids:
            if not old_ids or not old_ids <= new_ids:
                raise ValueError('新旧 MOD 注册身份不一致，不能用另一作品或部分组件覆盖。')
        elif current.name.casefold() != item['file_name'].casefold():
            raise ValueError('此 MOD 没有可核实的注册身份，不能用不同文件名自动更新。')

    def rollback(self, name):
        if self.mm.transaction.journal.exists():
            raise ValueError('请先恢复上次未完成的 MOD 操作。')
        state = self.state()
        entry = state['mods'].get(name, {})
        previous = entry.get('previous')
        if not previous or not re.fullmatch('[0-9a-f]{32}\\.zip', entry.get('backup', '')):
            raise ValueError('此 MOD 没有可恢复的上一版。')
        backup = self.backups / entry['backup']
        current = self._locations(name)
        if not current or _hash(current) != entry['sha256'] or not backup.is_file() or _hash(backup) != previous['sha256']:
            raise ValueError('当前文件或备份已被更改，已停止恢复。')
        with tempfile.TemporaryDirectory(prefix='bbmod-online-rollback-') as staging:
            state['mods'][name] = previous
            receipt = Path(staging) / 'online-catalog.json'
            _atomic_json(receipt, state)
            self.mm._apply({current: backup, self.state_path: receipt}, validate=True)
        return f"已恢复 {name} v{previous['version']}"

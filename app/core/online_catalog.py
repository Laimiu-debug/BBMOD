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

MAX_DOWNLOAD = 100 * 1024 * 1024


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('军械库地址发生重定向，请填写网站最终地址后重试。')


def site_origin(value):
    value = value.strip().rstrip('/')
    parts = urlsplit(value)
    if (parts.scheme not in {'http', 'https'} or not parts.hostname or parts.username or parts.password
            or parts.path or parts.query or parts.fragment or any(c.isspace() for c in value)):
        raise ValueError('请输入网站根地址，例如 http://服务器IP:8080 或 https://域名。')
    _ = parts.port
    return f'{parts.scheme}://{parts.netloc.lower()}'


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
    parts = []; total = 0; started = time.monotonic()
    with _request(site_origin(origin) + '/api/v1/catalog/') as response:
        while block := response.read1(128 * 1024):
            total += len(block)
            if total > 4 * 1024 * 1024 or time.monotonic() - started > 30:
                raise ValueError('目录数据过大或读取超时。')
            parts.append(block)
    return parse_catalog(json.loads(b''.join(parts)))


def download_release(origin, item, cache, *, cancelled=lambda: False):
    # Validate one item again, including callers outside the UI.
    parse_catalog({'schema_version': 1, 'mods': [item]})
    origin = site_origin(origin)
    cache = Path(cache)
    cache.mkdir(parents=True, exist_ok=True)
    handle, name = tempfile.mkstemp(prefix='mod-', suffix='.zip', dir=cache)
    target = Path(name)
    started = time.monotonic()
    try:
        count = 0
        sha = hashlib.sha256()
        with os.fdopen(handle, 'wb') as out, _request(origin + item['download_path']) as response:
            while block := response.read1(128 * 1024):
                if cancelled() or time.monotonic() - started > 180:
                    raise ValueError('下载已取消或超时。')
                count += len(block)
                if count > item['size']:
                    raise ValueError('下载大小与目录不一致。')
                out.write(block); sha.update(block)
        if count != item['size'] or sha.hexdigest() != item['sha256']:
            raise ValueError('下载校验失败，文件已丢弃。请刷新目录后重试。')
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
        if not isinstance(data.get('mods'), dict):
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

    def check_compatibility(self, item, archive):
        info = analyze_zip(archive)
        installed = self.mm.scan()
        enabled = [m.info for m in installed if m.enabled and m.path.name.casefold() != item['file_name'].casefold()]
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

    def install(self, origin, item, archive):
        parse_catalog({'schema_version': 1, 'mods': [item]})
        origin = site_origin(origin)
        archive = Path(archive)
        with archive.open('rb') as src:
            check = inspect_archive(src)
        if check['sha256'] != item['sha256'] or check['size'] != item['size']:
            raise ValueError('安装文件校验失败。')
        state = self.state()
        name = item['file_name']
        previous = state['mods'].get(name)
        if previous and (previous['origin'] != origin or previous['id'] != item['id']):
            raise ValueError('同名文件属于另一网站或作品，不能自动覆盖。')
        current = self._locations(name)
        if current and (not previous or _hash(current) != previous['sha256']):
            raise ValueError('同名文件未由在线军械库管理或已被修改，已停止覆盖。请先手动备份处理。')
        if current and previous['sha256'] == item['sha256']:
            return f"{item['metadata']['title']} 已是所选版本，保留现有备份。"
        if previous and previous['version'] == item['version'] and previous['sha256'] != item['sha256']:
            raise ValueError('网站上同一版本的文件校验值发生变化，请联系作者发布新版本后再更新。')
        self.check_compatibility(item, archive)
        target = current or self.data / name
        self.disabled.mkdir(parents=True, exist_ok=True)
        self.backups.mkdir(parents=True, exist_ok=True)
        backup = None
        if current:
            backup = self.backups / f'{uuid.uuid4().hex}.zip'
            shutil.copy2(current, backup)
        handle, stage = tempfile.mkstemp(prefix='.bbmod-download-', suffix='.tmp', dir=target.parent)
        os.close(handle)
        replaced = False
        try:
            shutil.copyfile(archive, stage)
            if _hash(Path(stage)) != item['sha256']:
                raise ValueError('暂存文件校验失败。')
            os.replace(stage, target); replaced = True
            entry = {'origin': origin, 'id': item['id'], 'version': item['version'], 'sha256': item['sha256']}
            if backup:
                entry['previous'] = {k: v for k, v in previous.items() if k != 'previous'}
                entry['backup'] = backup.name
            state['mods'][name] = entry
            _atomic_json(self.state_path, state)
        except Exception:
            if replaced:
                if backup: shutil.copy2(backup, target)
                else: target.unlink(missing_ok=True)
            raise
        finally:
            Path(stage).unlink(missing_ok=True)
        return f"已安装 {item['metadata']['title']} v{item['version']}" + ('（保持禁用）' if target.parent == self.disabled else '')

    def rollback(self, name):
        state = self.state()
        entry = state['mods'].get(name, {})
        previous = entry.get('previous')
        if not previous or not re.fullmatch('[0-9a-f]{32}\\.zip', entry.get('backup', '')):
            raise ValueError('此 MOD 没有可恢复的上一版。')
        backup = self.backups / entry['backup']
        current = self._locations(name)
        if not current or _hash(current) != entry['sha256'] or not backup.is_file() or _hash(backup) != previous['sha256']:
            raise ValueError('当前文件或备份已被更改，已停止恢复。')
        handle, saved = tempfile.mkstemp(dir=current.parent, prefix='.online-restore-', suffix='.tmp')
        os.close(handle)
        try:
            shutil.copy2(current, saved)
            shutil.copy2(backup, current)
            state['mods'][name] = previous
            _atomic_json(self.state_path, state)
        except Exception:
            shutil.copy2(saved, current)
            raise
        finally:
            Path(saved).unlink(missing_ok=True)
        return f"已恢复 {name} v{previous['version']}"

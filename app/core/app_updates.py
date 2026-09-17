"""Release metadata and recoverable updates of the portable application only."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from urllib.parse import urlsplit
import uuid

from .version import VERSION

REPOSITORY = 'Laimiu-debug/BBMOD'
RELEASES_URL = f'https://github.com/{REPOSITORY}/releases'
API_URL = f'https://api.github.com/repos/{REPOSITORY}/releases?per_page=100'
MAX_DOWNLOAD = 300 * 1024 * 1024
VERSION_PATTERN = re.compile(r'^v?(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$')


def version_key(value: str) -> tuple:
    match = VERSION_PATTERN.fullmatch(value)
    if not match:
        raise ValueError('无法识别版本号：' + value)
    major, minor, patch, prerelease = match.groups()
    identifiers = []
    for item in (prerelease.split('.') if prerelease else []):
        if item.isdigit() and len(item) > 1 and item.startswith('0'):
            raise ValueError('无效的预发布版本号')
        identifiers.append((0, int(item)) if item.isdigit() else (1, item))
    return int(major), int(minor), int(patch), not bool(prerelease), tuple(identifiers)


@dataclass(frozen=True)
class Release:
    tag: str
    name: str
    notes: str
    published: str
    prerelease: bool
    url: str
    download_url: str = ''
    size: int = 0
    sha256: str = ''

    @property
    def installable(self):
        return bool(self.download_url and self.sha256 and 0 < self.size <= MAX_DOWNLOAD)

    def newer_than(self, current=VERSION):
        return version_key(self.tag) > version_key(current)


def parse_releases(payload: bytes) -> list[Release]:
    try:
        rows = json.loads(payload)
    except (ValueError, UnicodeError) as error:
        raise ValueError('更新服务返回了无效的版本数据，请稍后重试。') from error
    if not isinstance(rows, list):
        raise ValueError('更新服务返回了无效的版本列表')
    releases = {}
    for row in rows:
        if not isinstance(row, dict) or row.get('draft'):
            continue
        tag = row.get('tag_name', '')
        try:
            key = version_key(tag)
        except (TypeError, ValueError):
            continue
        # Only this project's release page and exact versioned/legacy assets
        # are actionable. Older clients still need the BBMOD.exe alias.
        url = RELEASES_URL + '/tag/' + tag
        if row.get('html_url') != url:
            continue
        asset_url, size, digest = '', 0, ''
        assets = row.get('assets', [])
        for filename in (f'BBMOD-{tag.removeprefix("v")}.exe', 'BBMOD.exe'):
            for asset in (assets if isinstance(assets, list) else []):
                if not isinstance(asset, dict):
                    continue
                expected = RELEASES_URL + '/download/' + tag + '/' + filename
                if asset.get('name') != filename or asset.get('state') != 'uploaded' or asset.get('browser_download_url') != expected:
                    continue
                checksum = asset.get('digest') or ''
                if re.fullmatch(r'sha256:[0-9a-fA-F]{64}', checksum) and type(asset.get('size')) is int and 0 < asset['size'] <= MAX_DOWNLOAD:
                    asset_url, size, digest = expected, asset['size'], checksum[7:].lower()
                    break
            if asset_url:
                break
        releases[key] = Release(tag, str(row.get('name') or tag), str(row.get('body') or '此版本没有更新说明。'),
                                str(row.get('published_at') or ''), bool(row.get('prerelease')) or not key[3], url, asset_url, size, digest)
    return [releases[key] for key in sorted(releases, reverse=True)]


def available_releases(releases, include_preview):
    return [item for item in releases if include_preview or not item.prerelease]


def download_host_allowed(url: str) -> bool:
    parsed = urlsplit(url)
    return parsed.scheme == 'https' and parsed.hostname in {'github.com', 'release-assets.githubusercontent.com', 'objects.githubusercontent.com'}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def verify_download(path: Path, release: Release):
    if not release.installable or path.stat().st_size != release.size or sha256_file(path) != release.sha256:
        raise ValueError('下载文件不完整或校验值不符，请重新下载')
    with path.open('rb') as stream:
        if stream.read(2) != b'MZ':
            raise ValueError('下载文件不是 Windows 程序')


def write_json(path: Path, data):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    os.replace(temporary, path)


def prepare_install(source: Path, release: Release, *, target: Path | None = None, parent_pid: int | None = None) -> Path:
    if target is None:
        if not getattr(sys, 'frozen', False) or sys.platform != 'win32':
            raise ValueError('源码运行时请手动使用已下载的 EXE')
        target = Path(sys.executable)
    source, target = source.resolve(strict=True), target.resolve(strict=True)
    verify_download(source, release)
    if source == target or target.suffix.lower() != '.exe':
        raise ValueError('无效的程序更新位置')
    # Check write permission before closing the application.
    probe = target.parent / ('.bbmod-write-' + uuid.uuid4().hex)
    with probe.open('xb'):
        pass
    probe.unlink()
    request = source.parent / 'install.json'
    write_json(request, {'source': str(source), 'target': str(target), 'sha256': release.sha256,
                        'size': release.size, 'current_sha256': sha256_file(target), 'version': release.tag,
                        'parent_pid': os.getpid() if parent_pid is None else parent_pid, 'id': uuid.uuid4().hex})
    return request


def restart_environment():
    environment = dict(os.environ)
    environment['PYINSTALLER_RESET_ENVIRONMENT'] = '1'
    return environment


def launch_helper(request: Path):
    if not getattr(sys, 'frozen', False):
        raise ValueError('自动安装仅支持 Windows 单文件发行版')
    helper = request.parent / 'BBMOD-update-helper.exe'
    shutil.copy2(sys.executable, helper)
    with (request.parent / 'helper.log').open('ab') as log:
        return subprocess.Popen([str(helper), '--apply-update', str(request)], cwd=str(request.parent),
                                env=restart_environment(), stdout=log, stderr=log,
                                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))


def wait_for_exit(pid: int, timeout=120):
    if pid <= 0 or pid == os.getpid():
        raise ValueError('无效的待退出程序')
    import ctypes
    from ctypes import wintypes
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel.WaitForSingleObject.restype = wintypes.DWORD
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.OpenProcess(0x00100000, False, pid)
    if not handle:
        if ctypes.get_last_error() == 87:  # Already exited.
            return
        raise OSError('无法等待旧程序退出')
    try:
        if kernel.WaitForSingleObject(handle, timeout * 1000) != 0:
            raise TimeoutError('旧程序尚未退出，更新已取消')
    finally:
        kernel.CloseHandle(handle)


def _replace_with_retry(source, target):
    for attempt in range(40):
        try:
            os.replace(source, target)
            return
        except PermissionError:
            if attempt == 39:
                raise
            time.sleep(0.25)


def install_request(request: Path, *, wait=wait_for_exit, launch=None, verify_mode=False) -> dict:
    """Run in a separate helper. Back up and replace only the selected app EXE."""
    request = request.resolve(strict=True)
    plan = json.loads(request.read_text(encoding='utf-8'))
    source, target = Path(plan['source']).resolve(), Path(plan['target']).resolve()
    if source.parent != request.parent or source == target or target.suffix.lower() != '.exe' or not re.fullmatch('[a-f0-9]{32}', plan['id']):
        raise ValueError('无效的更新请求')
    backup = target.with_name(f'{target.stem}.previous-{plan["id"][:8]}.exe')
    staged = target.with_name(f'.{target.name}.{plan["id"]}.tmp')
    lock = target.with_name(f'.{target.name}.update.lock')
    result_path = request.parent / 'result.json'
    result = {'version': plan['version'], 'target': str(target), 'backup': str(backup), 'time': datetime.now(timezone.utc).isoformat()}
    locked, moved, staged_owned = False, False, False
    try:
        with lock.open('x') as stream:
            stream.write(plan['id'])
        locked = True
        if source.stat().st_size != plan['size'] or sha256_file(source) != plan['sha256']:
            raise ValueError('安装前校验失败，旧程序未修改')
        if verify_mode and plan['parent_pid'] == 0:
            pass
        else:
            wait(plan['parent_pid'])
        if sha256_file(target) != plan['current_sha256']:
            raise ValueError('程序已被其他操作更新，请重新检查版本')
        if backup.exists() or staged.exists():
            raise ValueError('更新暂存文件已存在，请重新下载')
        staged_owned = True
        shutil.copy2(source, staged)
        if sha256_file(staged) != plan['sha256']:
            raise ValueError('复制校验失败')
        _replace_with_retry(target, backup)
        moved = True
        _replace_with_retry(staged, target)
        if launch:
            launch(target)
        else:
            command = [str(target)] + (['--selftest'] if verify_mode else [])
            with (request.parent / 'restarted.log').open('ab') as log:
                process = subprocess.Popen(command, cwd=str(target.parent), env=restart_environment(), stdout=log, stderr=log,
                                           creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                if verify_mode and process.wait(timeout=60) != 0:
                    raise RuntimeError('新版本自检未通过')
        result['status'] = 'installed'
    except Exception as error:
        result.update(status='failed', error=str(error))
        if moved:
            try:
                _replace_with_retry(backup, target)
                result['rolled_back'] = True
            except OSError as rollback_error:
                result['rollback_error'] = str(rollback_error)
    finally:
        if locked:
            if staged_owned and staged.exists():
                staged.unlink()
            lock.unlink(missing_ok=True)
        write_json(result_path, result)
    return result

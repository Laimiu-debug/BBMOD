"""Official-site first, cancellable updates without modal interruptions."""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import time
import uuid
import sys

from PySide6.QtCore import QObject, QTimer, QUrl, Signal
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest

from core.app_updates import (API_URL, SITE_API_URL, VERSION, Release, available_releases,
    download_host_allowed, parse_releases, parse_site_releases, verify_download, version_key, write_json)
from .workers import Worker


class UpdateService(QObject):
    changed = Signal()
    attention = Signal(str)

    def __init__(self, settings, parent=None, *, automatic=True):
        super().__init__(parent)
        self.settings = settings
        self.folder = settings.path.parent / 'updates'
        saved = settings.get('app_updates', {})
        self.preferences = dict(saved) if isinstance(saved, dict) else {}
        self.preferences.setdefault('automatic', True)
        self.preferences.setdefault('preview', '-' in VERSION)
        self.preferences.setdefault('auto_download', True)
        self.preferences.setdefault('install_on_exit', True)
        self.releases = []
        self.status = '可手动检查更新。'
        self.busy = ''
        self.reply = None
        self.received = self.total = 0
        self.downloaded = None
        self.download_release = None
        self._stream = None
        self._partial = None
        self._failure = ''
        self._closed = False
        self._source = 'site'
        self._verifier = None
        self._api_data = bytearray()
        self.network = QNetworkAccessManager(self)
        try:
            cached = (self.folder / 'releases-cache.json').read_bytes()
            self.releases = parse_site_releases(cached) if cached.lstrip().startswith(b'{') else parse_releases(cached)
        except (OSError, ValueError, TypeError):
            pass
        pending = self.preferences.get('pending')
        if isinstance(pending, str):
            result_path = Path(pending).resolve()
            if result_path.is_relative_to(self.folder.resolve()):
                try:
                    result = json.loads(result_path.read_text(encoding='utf-8'))
                    self.status = ('已更新到 ' + result['version']) if result.get('status') == 'installed' else ('上次更新未完成：' + result.get('error', '请重新下载'))
                except (OSError, ValueError, KeyError):
                    self.status = '上次更新尚未完成，可重新检查并下载。'
        self.timer = QTimer(self)
        self.timer.setInterval(6 * 60 * 60 * 1000)
        self.timer.timeout.connect(self.automatic_check)
        if automatic:
            self.timer.start()
            QTimer.singleShot(3500, self.automatic_check)
        QTimer.singleShot(0, self._restore_download)

    def save_preference(self, key, value):
        previous = dict(self.preferences)
        self.preferences[key] = value
        try:
            self.settings.set('app_updates', dict(self.preferences))
        except OSError as error:
            self.preferences = previous
            self.settings.data['app_updates'] = previous
            self.status = '设置未保存：' + str(error)
            self.changed.emit()
            return False
        if key == 'preview':
            self.status = self.release_status() if self.releases else '当前通道尚无版本记录，请检查更新。'
        self.changed.emit()
        return True

    def automatic_check(self):
        if self._closed or not self.preferences.get('automatic') or self.busy:
            return
        try:
            last = float(self.preferences.get('last_check_epoch', 0))
        except (TypeError, ValueError):
            last = 0
        if 0 <= time.time() - last < 6 * 60 * 60:
            return
        self.check()

    def visible_releases(self):
        return available_releases(self.releases, bool(self.preferences.get('preview')))

    def latest(self):
        items = self.visible_releases()
        return items[0] if items else None

    def release_status(self):
        latest = self.latest()
        if not latest:
            return '当前通道尚无已发布版本。可切换到测试版通道。'
        if latest.newer_than():
            return f'发现新版本 {latest.tag}。可查看说明后下载。'
        if version_key(latest.tag) == version_key(VERSION):
            return '当前已是此通道的最新版本。'
        return '当前版本高于此通道的最新发布，不会自动降级。'

    def _request(self, url):
        request = QNetworkRequest(QUrl(url))
        request.setRawHeader(b'User-Agent', ('BBMOD/' + VERSION).encode())
        request.setRawHeader(b'Accept', b'application/json' if url in (API_URL, SITE_API_URL) else b'application/octet-stream')
        if url == API_URL:
            request.setRawHeader(b'X-GitHub-Api-Version', b'2022-11-28')
        request.setTransferTimeout(20000)
        request.setAttribute(QNetworkRequest.RedirectPolicyAttribute, QNetworkRequest.UserVerifiedRedirectPolicy)
        reply = self.network.get(request)
        reply.setReadBufferSize(1024 * 1024)
        reply.redirected.connect(lambda destination, r=reply: self._redirect(r, destination))
        return reply

    def _redirect(self, reply, destination):
        allowed = (destination.toString() in (API_URL, SITE_API_URL)
                   if self.busy == 'check' else download_host_allowed(destination.toString()))
        if allowed:
            reply.redirectAllowed.emit()
        else:
            self._failure = '更新地址发生了不受信任的跳转'
            reply.abort()

    def check(self):
        if self._closed or self.busy:
            return
        self._source = 'site'
        self.busy, self.status, self._failure = 'check', '正在检查官网发布版本…', ''
        self._start_check()

    def _start_check(self):
        self._api_data = bytearray()
        self.reply = self._request(SITE_API_URL if self._source == 'site' else API_URL)
        self.reply.readyRead.connect(self._read_check)
        self.reply.finished.connect(self._checked)
        self.changed.emit()

    def _read_check(self):
        self._api_data.extend(bytes(self.reply.readAll()))
        if len(self._api_data) > 2 * 1024 * 1024:
            self._failure = '版本列表过大，请通过发布页面查看'
            self.reply.abort()

    def _checked(self):
        reply = self.reply
        self._read_check()
        fallback = False
        completed = False
        try:
            self._check_response(reply)
            parser = parse_site_releases if self._source == 'site' else parse_releases
            releases = parser(bytes(self._api_data))
            if self._source == 'site' and not releases:
                raise ValueError('官网暂时没有可用版本')
            self.folder.mkdir(parents=True, exist_ok=True)
            (self.folder / 'releases-cache.json').write_bytes(bytes(self._api_data))
            self.releases = releases
            self.preferences['last_check_epoch'] = time.time()
            self.preferences['last_check'] = datetime.now(timezone.utc).isoformat()
            self.settings.set('app_updates', self.preferences)
            latest = self.latest()
            self.status = self.release_status()
            completed = True
            if latest and latest.newer_than():
                if latest.tag != self.preferences.get('ignored'):
                    self.attention.emit(latest.tag)
        except (OSError, ValueError, TypeError) as error:
            fallback = self._source == 'site' and not self._closed and self._failure != '已取消。'
            self.status = '官网暂时不可用，正在检查备用源…' if fallback else str(error)
        finally:
            self.reply, self.busy = None, ''
            reply.deleteLater()
            self.changed.emit()
        if fallback:
            self._source, self.busy, self._failure = 'github', 'check', ''
            self._start_check()
        elif completed and not self._closed:
            latest = self.latest()
            if (latest and latest.newer_than() and latest.installable and self.preferences.get('auto_download')
                    and getattr(sys, 'frozen', False) and latest.tag != self.preferences.get('ignored')
                    and not (self.downloaded and self.download_release == latest)):
                self.download(latest)

    def _check_response(self, reply):
        code = reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)
        if self._failure:
            raise ValueError(self._failure)
        if code in (403, 429):
            raise ValueError('更新服务暂时限制了请求次数，请稍后重试。')
        if reply.error() != QNetworkReply.NoError or code != 200:
            raise ValueError('连接更新服务失败，请检查网络后重试。' + (f'（HTTP {code}）' if code else ''))

    def download(self, release):
        if self._closed or self.busy:
            return
        if not release.installable or not download_host_allowed(release.download_url):
            self.status = '此版本没有可校验的 EXE，请在发布页面查看。'
            self.changed.emit()
            return
        folder = self.folder / uuid.uuid4().hex
        try:
            folder.mkdir(parents=True)
            self._partial = folder / 'BBMOD.exe.part'
            self._stream = self._partial.open('xb')
        except OSError as error:
            self.status = '无法保存下载文件：' + str(error)
            self.changed.emit()
            return
        self.busy, self.status, self._failure = 'download', f'正在下载 {release.tag}…', ''
        self.downloaded, self.download_release = None, release
        self.received, self.total = 0, release.size
        self.reply = self._request(release.download_url)
        self.reply.readyRead.connect(self._read_download)
        self.reply.finished.connect(self._downloaded)
        self.changed.emit()

    def _read_download(self):
        chunk = bytes(self.reply.readAll())
        try:
            self.received += len(chunk)
            if self.received > self.total:
                raise ValueError('下载大小与发布记录不符')
            self._stream.write(chunk)
        except (OSError, ValueError) as error:
            self._failure = str(error)
            self.reply.abort()
        self.changed.emit()

    def _downloaded(self):
        reply = self.reply
        try:
            self._read_download()
            self._stream.close()
            self._stream = None
            self._check_response(reply)
            partial, release = self._partial, self.download_release
            self._partial = None
            self._verify_async(partial, release, partial=True)
        except (OSError, ValueError) as error:
            self.status = str(error)
        finally:
            if self._stream:
                self._stream.close()
                self._stream = None
            if self._partial and self._partial.exists():
                self._partial.unlink()
            self.reply = None
            if self.busy != 'verify':
                self.busy = ''
            reply.deleteLater()
            self.changed.emit()

    def _verify_async(self, path, release, *, partial=False):
        self.busy, self.status = 'verify', '正在后台校验程序文件…'
        def verify():
            try:
                verify_download(path, release)
                destination = path.with_name('BBMOD.exe') if partial else path
                if partial:
                    path.replace(destination)
                return destination
            except Exception:
                if partial:
                    path.unlink(missing_ok=True)
                raise
        worker = Worker(verify)
        worker.setParent(self)
        self._verifier = worker
        worker.done.connect(lambda destination: self._verified(destination, release))
        worker.failed.connect(self._verify_failed)
        worker.finished.connect(worker.deleteLater)
        worker.start()

    def _verified(self, destination, release):
        self.busy = ''
        self.downloaded, self.download_release = destination, release
        self.status = '新版已就绪。正常退出软件后静默更新，也可立即重启更新。'
        try:
            from dataclasses import asdict
            write_json(self.folder / 'ready.json', {'path': str(destination), 'release': asdict(release)})
        except OSError:
            self.status += '（下载缓存记录未保存）'
        self.changed.emit()

    def _verify_failed(self, error):
        self.busy, self.status = '', '文件校验未通过：' + error
        self.downloaded = None
        self.changed.emit()

    def _restore_download(self):
        if self._closed or self.busy or self.downloaded:
            return
        try:
            data = json.loads((self.folder / 'ready.json').read_text(encoding='utf-8'))
            path = Path(data['path']).resolve()
            release = Release(**data['release'])
            if (path.is_relative_to(self.folder.resolve()) and path.name == 'BBMOD.exe'
                    and release.newer_than() and download_host_allowed(release.download_url)):
                self._verify_async(path, release)
        except (OSError, ValueError, TypeError, KeyError):
            pass

    def cancel(self):
        if self.reply:
            self._failure = '已取消。'
            self.reply.abort()

    def shutdown(self):
        self._closed = True
        self.timer.stop()
        self.cancel()

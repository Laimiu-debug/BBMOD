"""Crash snapshot lifecycle and a persistent, opt-in report upload queue."""
import base64
import json
import time
from types import SimpleNamespace

from PySide6.QtCore import QObject, QTimer, QUrl, Signal
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkCookie, QNetworkRequest

from core import game as game_mod
from core.site_config import SITE_ORIGIN
from core.crash_reports import AUTO_UPLOAD_KEY, ReportStore, begin_session
from core.version import VERSION
from .workers import Worker


class CrashReports(QObject):
    changed = Signal()

    def __init__(self, ctx, parent=None, *, automatic=True, origin=SITE_ORIGIN):
        super().__init__(parent)
        self.ctx = ctx
        self.store = ReportStore(ctx.settings.path.parent / 'crash-reports')
        self.origin = origin
        self.url = QUrl(origin + '/api/v1/suggestions/')
        self.network = QNetworkAccessManager(self)
        self.reply = None
        self.worker = None
        self.session = None
        self.current = None
        self.closed = False
        self.reviewing = False
        self.status = ''
        self.automatic = automatic
        self.timer = QTimer(self)
        self.timer.setInterval(30_000)
        self.timer.timeout.connect(self.pump)
        if automatic:
            self.timer.start()
            QTimer.singleShot(3000, self.pump)
        ctx.game_session.launch_requested.connect(self.arm)
        ctx.game_session.launch_ended.connect(self.collect)
        ctx.game_session.launch_cancelled.connect(self.cancel_capture)
        ctx.session_changed.connect(lambda active: self.cancel_capture() if active else None)

    def arm(self):
        if self.ctx.seedgen_active or self.closed:
            return
        try:
            self.session = begin_session(game_mod.find_log_write_paths())
            self.context = SimpleNamespace(game=self.ctx.game, mm=self.ctx.mm)
        except OSError as exc:
            self.session = None
            self.status = '本次日志监控未开启：' + str(exc)
            self.changed.emit()

    def cancel_capture(self):
        self.session = None

    def collect(self):
        if self.closed or not self.session or self.ctx.seedgen_active or self.worker:
            return
        session, self.session = self.session, None
        automatic = self.ctx.settings.get(AUTO_UPLOAD_KEY, False) is True
        self.ctx.game_session.begin_collecting()
        self.worker = Worker(lambda: self.store.capture(self.context, session,
                             game_mod.find_log_write_paths(), automatic), self)
        self.worker.done.connect(self._captured)
        self.worker.failed.connect(self._capture_failed)
        self.worker.finished.connect(self._capture_finished)
        self.worker.start()

    def _captured(self, item):
        if item:
            self.status = '检测到疑似异常退出，日志已保存。' + ('正在等待自动上传。' if item['automatic'] else '可预览并提交错误报告。')
            self.changed.emit()

    def _capture_failed(self, error):
        self.status = '日志保存未完成：' + error
        self.changed.emit()

    def _capture_finished(self):
        worker, self.worker = self.worker, None
        worker.deleteLater()
        self.ctx.game_session.finish_collecting()
        self.pump()

    def pump(self):
        if (self.closed or self.reviewing or not self.automatic or self.reply or self.worker
                or self.ctx.settings.get(AUTO_UPLOAD_KEY, False) is not True):
            return
        for item in reversed(self.store.records()):
            if (item['automatic'] and item['state'] in ('pending', 'failed')
                    and item['attempts'] < 3 and item['next_retry'] <= time.time()):
                self.send(item['id'])
                break

    def send(self, identity):
        if self.closed or self.reply or self.worker:
            return False
        try:
            item = self.store.get(identity)
            if item['state'] in ('sent', 'review'):
                return False
            self.current = item
            item['attempts'] += 1
            item['state'] = 'failed'  # A process exit during HTTP leaves a resumable record.
            item['next_retry'] = time.time() + 60 * (2 ** min(item['attempts'], 5))
            self.store.save(item)
            cookies = []
            for value in item.get('cookies', []):
                cookies.extend(QNetworkCookie.parseCookies(base64.b64decode(value)))
            # Each snapshot keeps its own server session and signed receipt.
            from PySide6.QtNetwork import QNetworkCookieJar
            jar = QNetworkCookieJar(self.network)
            jar.setCookiesFromUrl(cookies, self.url)
            self.network.setCookieJar(jar)
            self._request(post=bool(item['ticket']))
            return True
        except (OSError, ValueError, KeyError) as exc:
            self.status = '报告未提交，本地记录已保留：' + str(exc)
            self.changed.emit()
            self.current = None
            return False

    def _request(self, *, post):
        item = self.current
        request = QNetworkRequest(self.url)
        request.setTransferTimeout(20_000)
        request.setAttribute(QNetworkRequest.RedirectPolicyAttribute, QNetworkRequest.ManualRedirectPolicy)
        request.setRawHeader(b'Accept', b'application/json')
        request.setRawHeader(b'User-Agent', ('BBMOD/' + VERSION).encode())
        if post:
            # Persist the exact receipt, payload and cookies before transmission.
            item['posted'] = True
            self.store.save(item)
            request.setHeader(QNetworkRequest.ContentTypeHeader, 'application/json')
            request.setRawHeader(b'Origin', self.origin.encode())
            request.setRawHeader(b'X-CSRFToken', item['ticket']['csrf_token'].encode())
            payload = {**item['payload'], 'submission': item['ticket']['submission']}
            self.reply = self.network.post(request, json.dumps(payload, ensure_ascii=False).encode())
        else:
            self.reply = self.network.get(request)
        self.data = bytearray()
        self.reply.setReadBufferSize(65_536)
        self.reply.readyRead.connect(self._read)
        self.reply.finished.connect(lambda: self._finished(post))
        self.status = '正在上传已保存的错误报告…'
        self.changed.emit()

    def _read(self):
        self.data.extend(bytes(self.reply.readAll()))
        if len(self.data) > 65_536:
            self.reply.abort()

    def _finished(self, post):
        reply = self.reply
        self._read()
        self.reply = None
        item = self.current
        try:
            code = reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)
            data = json.loads(bytes(self.data))
            if not isinstance(data, dict) or data.get('schema_version') != 1:
                raise ValueError('无法识别网站响应。')
            item['cookies'] = [base64.b64encode(bytes(cookie.toRawForm())).decode()
                               for cookie in self.network.cookieJar().cookiesForUrl(self.url)]
            if code not in (200, 201):
                if code == 403 or data.get('code') == 'ticket_expired':
                    if item['posted']:
                        item['state'] = 'review'
                        raise ValueError('提交凭据已过期，之前的请求可能已送达；请在报告列表核对后重新提交。')
                    item['ticket'] = None
                if code == 429:
                    try:
                        delay = min(86400, max(60, int(bytes(reply.rawHeader('Retry-After')).decode())))
                    except ValueError:
                        delay = 3600
                    item['next_retry'] = time.time() + delay
                if code in (400, 413, 415):
                    item['state'] = 'review'
                raise ValueError(str(data.get('error', '网站暂时无法接收报告。')))
            if not post:
                if not all(isinstance(data.get(key), str) and 0 < len(data[key]) <= 500
                           for key in ('submission', 'csrf_token')):
                    raise ValueError('网站返回的提交凭据无效。')
                if data.get('diagnostic_report_max_length', 0) < len(item['payload']['diagnostic_report']):
                    item['state'] = 'review'
                    raise ValueError('网站暂不支持此诊断报告。')
                item['ticket'] = {key: data[key] for key in ('submission', 'csrf_token')}
                self.store.save(item)
                # Turning the option off also cancels automatic GET -> POST.
                if item['automatic'] and self.ctx.settings.get(AUTO_UPLOAD_KEY, False) is not True:
                    raise ValueError('自动上传已关闭。')
                self._request(post=True)
                return
            reference = data.get('reference')
            if not isinstance(reference, str) or not 1 <= len(reference) <= 32:
                raise ValueError('未收到有效回执。')
            item.update(state='sent', reference=reference, message='已送达，回执编号：' + reference)
            item['ticket'] = None
            item['cookies'] = []
            self.store.save(item)
            self.status = item['message']
        except (ValueError, TypeError, KeyError, OSError) as exc:
            item['message'] = str(exc) + '\n报告已保存在本机，可在错误报告列表重试。'
            if item['attempts'] >= 3:
                item['message'] += ' 自动重试已暂停。'
            self.status = item['message']
            try:
                self.store.save(item)
            except OSError as error:
                self.status += '\n状态保存失败：' + str(error)
        finally:
            reply.deleteLater()
            if self.reply is None:
                self.current = None
                self.changed.emit()

    def shutdown(self):
        self.closed = True
        self.timer.stop()
        if self.reply:
            self.reply.abort()
        if self.worker:
            self.worker.wait()

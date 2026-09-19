"""Anonymous desktop feedback; drafts survive failures, receipts prevent duplicates."""
import json

from PySide6.QtCore import QTimer, QUrl, Qt
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest
from PySide6.QtWidgets import (QComboBox, QFormLayout, QGroupBox, QLabel, QLineEdit,
    QPushButton, QTextEdit, QVBoxLayout, QWidget)

from core.app_updates import SITE_ORIGIN
from core.version import VERSION


class FeedbackPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.network = QNetworkAccessManager(self)
        self.endpoint = SITE_ORIGIN + '/api/v1/suggestions/'
        self.origin = SITE_ORIGIN
        self.reply = None
        self.ticket = None
        self.pending_data = None
        self._data = bytearray()
        self._limited = False
        root = QVBoxLayout(self)
        intro = QLabel('遇到问题，或有希望加入的功能，都可以直接告诉我们。无需登录，内容仅管理员可见。')
        intro.setWordWrap(True)
        intro.setObjectName('workspaceHint')
        root.addWidget(intro)
        self.box = QGroupBox('描述问题或建议')
        form = QFormLayout(self.box)
        form.setRowWrapPolicy(QFormLayout.WrapLongRows)
        self.kind = QComboBox()
        for label, value in [('功能建议', 'feature'), ('问题反馈', 'bug'), ('其他想法', 'other')]:
            self.kind.addItem(label, value)
        self.title = QLineEdit(); self.title.setMaxLength(100)
        self.title.setPlaceholderText('用一句话概括（最多 100 字）')
        self.details = QTextEdit(); self.details.setAcceptRichText(False)
        self.details.setMinimumHeight(180)
        self.details.setPlaceholderText('使用场景、操作步骤、实际结果和期望结果，最多 5,000 字。')
        self.nickname = QLineEdit(); self.nickname.setMaxLength(40)
        self.contact = QLineEdit(); self.contact.setMaxLength(150)
        for label, widget in [('类型', self.kind), ('一句话概括', self.title), ('详细说明', self.details),
                              ('称呼（选填）', self.nickname), ('联系方式（选填）', self.contact)]:
            form.addRow(label, widget)
        form.addRow('软件版本', QLabel(VERSION))
        root.addWidget(self.box)
        hint = QLabel('仅发送本页填写的内容和软件版本，不会上传存档、日志或游戏目录。')
        hint.setWordWrap(True); hint.setObjectName('workspaceHint'); root.addWidget(hint)
        self.submit_button = QPushButton('提交反馈'); self.submit_button.setObjectName('feedback_submit')
        self.submit_button.clicked.connect(self.submit); root.addWidget(self.submit_button)
        self.status = QLabel(); self.status.setWordWrap(True); self.status.setTextFormat(Qt.PlainText)
        self.status.setObjectName('workspaceHint')
        self.status.setTextInteractionFlags(Qt.TextSelectableByMouse)
        root.addWidget(self.status); root.addStretch()

    def submit(self):
        if self.reply or self._limited:
            return
        data = {'kind': self.kind.currentData(), 'title': self.title.text().strip(),
                'details': self.details.toPlainText().strip(), 'nickname': self.nickname.text().strip(),
                'contact': self.contact.text().strip(), 'version': 'BBMOD desktop ' + VERSION}
        if not data['title'] or not data['details'] or len(data['details']) > 5000:
            self.status.setText('请填写标题和详细说明，详细说明最多 5,000 字。')
            return
        # A retry of the same text keeps its ticket, even after an ambiguous timeout.
        if self.pending_data != data:
            self.ticket = None
        self.pending_data = data
        self.box.setEnabled(False); self.submit_button.setEnabled(False)
        self.status.setText('正在提交…')
        self._request(post=bool(self.ticket))

    def _request(self, *, post):
        request = QNetworkRequest(QUrl(self.endpoint))
        request.setTransferTimeout(20000)
        request.setAttribute(QNetworkRequest.RedirectPolicyAttribute, QNetworkRequest.ManualRedirectPolicy)
        request.setRawHeader(b'Accept', b'application/json')
        request.setRawHeader(b'User-Agent', ('BBMOD/' + VERSION).encode())
        if post:
            request.setHeader(QNetworkRequest.ContentTypeHeader, 'application/json')
            request.setRawHeader(b'Origin', self.origin.encode())
            request.setRawHeader(b'X-CSRFToken', self.ticket['csrf_token'].encode())
            payload = {**self.pending_data, 'submission': self.ticket['submission']}
            self.reply = self.network.post(request, json.dumps(payload, ensure_ascii=False).encode())
        else:
            self.reply = self.network.get(request)
        self._data = bytearray()
        self.reply.setReadBufferSize(65536)
        self.reply.readyRead.connect(self._read)
        self.reply.finished.connect(lambda: self._finished(post))

    def _read(self):
        self._data.extend(bytes(self.reply.readAll()))
        if len(self._data) > 65536:
            self.reply.abort()

    def _finished(self, post):
        reply = self.reply
        self._read()
        self.reply = None
        code = reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)
        try:
            data = json.loads(bytes(self._data))
            if not isinstance(data, dict) or data.get('schema_version') != 1:
                raise ValueError
            if code not in (200, 201):
                if code == 403 or data.get('code') == 'ticket_expired':
                    self.ticket = None
                details = ' '.join(str(message) for messages in data.get('errors', {}).values() for message in messages)
                self.status.setText(str(data.get('error', '提交失败，请稍后重试。')) + (' ' + details if details else '') + '\n填写内容已保留。')
                if code == 429:
                    self._limited = True
                    try: seconds = min(3600, max(5, int(bytes(reply.rawHeader('Retry-After')).decode())))
                    except (ValueError, TypeError): seconds = 60
                    QTimer.singleShot(seconds * 1000, self._retry_enabled)
                return
            if not post:
                if not all(isinstance(data.get(key), str) and 0 < len(data[key]) <= 500 for key in ('submission', 'csrf_token')):
                    raise ValueError
                self.ticket = data
                self._request(post=True)
                return
            reference = data.get('reference')
            if not isinstance(reference, str) or len(reference) > 32:
                raise ValueError
            self.status.setText('建议已送达，管理员会在后台查看。\n回执编号：' + reference)
            self.title.clear(); self.details.clear()
            self.ticket = None; self.pending_data = None
        except (ValueError, TypeError, KeyError):
            if code == 403:
                self.ticket = None
            self.status.setText('暂时无法提交，请检查网络后重试。填写内容已保留。')
        finally:
            reply.deleteLater()
            if not self.reply:
                self.box.setEnabled(True); self.submit_button.setEnabled(not self._limited)

    def _retry_enabled(self):
        self._limited = False
        self.submit_button.setEnabled(self.reply is None)

    def shutdown(self):
        if self.reply:
            self.reply.abort()

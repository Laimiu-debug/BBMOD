"""Review saved snapshots without replacing an unrelated feedback draft."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QTextEdit, QPushButton, QMessageBox)

from core.support_report import MAX_REPORT_CHARS

STATES = {'manual': '待确认', 'pending': '待上传', 'failed': '待重试', 'sent': '已送达', 'review': '需核对'}


class CrashReportDialog(QDialog):
    def __init__(self, service, parent=None):
        super().__init__(parent)
        self.service = service
        self.identity = None
        self.setWindowTitle('已保存的错误报告')
        self.resize(850, 730)
        layout = QVBoxLayout(self)
        hint = QLabel('疑似异常退出的日志已保存在本机。提交内容仅管理员可见，存档不会上传。\n'
                      '首次提交前可修改报告和补充说明；已尝试发送的报告保持原内容，以便重复请求使用同一回执。')
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.listing = QListWidget()
        self.listing.setMaximumHeight(140)
        self.listing.currentItemChanged.connect(self.select)
        layout.addWidget(self.listing)
        self.message = QLabel()
        self.message.setWordWrap(True)
        self.message.setTextFormat(Qt.PlainText)
        layout.addWidget(self.message)
        self.editor = QTextEdit()
        self.editor.setAcceptRichText(False)
        layout.addWidget(self.editor, 1)
        layout.addWidget(QLabel('复现步骤 / 补充说明（最多 5,000 字）'))
        self.details = QTextEdit()
        self.details.setAcceptRichText(False)
        self.details.setMaximumHeight(90)
        layout.addWidget(self.details)
        actions = QHBoxLayout()
        self.open_button = QPushButton('打开本地日志目录')
        self.open_button.clicked.connect(self.open_folder)
        self.delete_button = QPushButton('删除本地记录')
        self.delete_button.clicked.connect(self.delete)
        self.send_button = QPushButton('提交错误报告')
        self.send_button.clicked.connect(self.send)
        close = QPushButton('关闭')
        close.clicked.connect(self.reject)
        for button in (self.open_button, self.delete_button, self.send_button, close):
            actions.addWidget(button)
        layout.addLayout(actions)
        service.changed.connect(self.update_status)
        self.refresh()

    def refresh(self):
        selected = self.identity
        self.listing.clear()
        for record in self.service.store.records():
            item = QListWidgetItem(f'{record["created"]} · {STATES[record["state"]]} · {record["payload"]["title"]}')
            item.setData(Qt.UserRole, record['id'])
            self.listing.addItem(item)
            if record['id'] == selected:
                self.listing.setCurrentItem(item)
        if self.listing.currentRow() < 0 and self.listing.count():
            self.listing.setCurrentRow(0)
        self.update_status()

    def select(self, item, _previous=None):
        self.identity = item.data(Qt.UserRole) if item else None
        self.editor.clear()
        self.details.clear()
        if self.identity:
            record = self.service.store.get(self.identity)
            self.editor.setPlainText(record['payload']['diagnostic_report'])
            self.details.setPlainText(record['payload']['details'])
        self.update_status()

    def update_status(self):
        try:
            record = self.service.store.get(self.identity) if self.identity else None
        except OSError:
            self.identity = None
            self.refresh()
            return
        busy = self.service.reply is not None or self.service.worker is not None
        self.send_button.setEnabled(bool(record and record['state'] != 'sent') and not busy)
        self.delete_button.setEnabled(bool(record) and not busy)
        self.open_button.setEnabled(bool(record))
        readonly = not record or busy or record['posted'] or record['state'] == 'sent'
        self.editor.setReadOnly(readonly)
        self.details.setReadOnly(readonly)
        self.message.setText(self.service.status if busy else (record['message'] if record else '暂无已保存的错误报告。'))
        self.send_button.setText('核对后重新提交' if record and record['state'] == 'review' else '提交 / 重试')
        for index in range(self.listing.count()):
            item = self.listing.item(index)
            data = self.service.store.get(item.data(Qt.UserRole))
            item.setText(f'{data["created"]} · {STATES[data["state"]]} · {data["payload"]["title"]}')

    def send(self):
        if not self.identity:
            return
        try:
            record = self.service.store.get(self.identity)
            if record['state'] == 'review':
                if QMessageBox.question(self, '核对后重新提交',
                        '之前的请求可能已送达。重新提交可能产生重复报告，仍要继续吗？',
                        QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
                    return
                record.update(ticket=None, cookies=[], posted=False, state='manual')
            if not record['posted']:
                report, details = self.editor.toPlainText().strip(), self.details.toPlainText().strip()
                if not report or len(report) > MAX_REPORT_CHARS or not details or len(details) > 5000:
                    raise ValueError('报告须为 1–60,000 字，补充说明须为 1–5,000 字。')
                record['payload'].update(diagnostic_report=report, details=details)
            record['automatic'] = False
            self.service.store.save(record)
            self.service.send(self.identity)
            self.update_status()
        except (OSError, ValueError) as exc:
            self.message.setText('未提交：' + str(exc))

    def delete(self):
        if self.identity and QMessageBox.question(self, '删除本地报告',
                '删除这份本地日志和报告？已送达官网的报告不受影响。',
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) == QMessageBox.Yes:
            try:
                self.service.store.delete(self.identity)
                self.refresh()
                self.service.changed.emit()
            except OSError as exc:
                self.message.setText('删除失败：' + str(exc))

    def open_folder(self):
        if self.identity:
            from core.game import open_folder
            open_folder(self.service.store.folder(self.identity))

    def showEvent(self, event):
        self.service.reviewing = True
        super().showEvent(event)

    def hideEvent(self, event):
        self.service.reviewing = False
        super().hideEvent(event)

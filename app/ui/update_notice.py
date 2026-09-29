"""Visible, non-modal update prompts that also work with cached release records."""
import sys

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton

from core.version import VERSION
from .theme import style_button


class UpdateNotice(QFrame):
    history_requested = Signal()
    install_requested = Signal()

    def __init__(self, service, context, parent=None):
        super().__init__(parent)
        self.service, self.context = service, context
        self._dismissed = set()
        self._key = None
        self._can_restart = False
        self.setObjectName('updateNotice')
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        self.message = QLabel()
        self.message.setWordWrap(True)
        self.message.setTextFormat(Qt.PlainText)
        layout.addWidget(self.message, 1)
        self.action = QPushButton('查看更新')
        style_button(self.action, 'download', primary=True)
        self.details = QPushButton('版本说明')
        self.later = QPushButton('稍后提醒')
        for button in (self.action, self.details, self.later):
            layout.addWidget(button)
        self.action.clicked.connect(self._activate)
        self.details.clicked.connect(self.history_requested.emit)
        self.later.clicked.connect(self.dismiss)
        self.later.setToolTip('本次运行暂时收起；下载完成、新版本发布或下次启动时会再次提示。')
        service.changed.connect(self.refresh)
        context.management_changed.connect(self.refresh)
        context.session_changed.connect(self.refresh)
        self.refresh()

    def refresh(self, *_):
        service = self.service
        latest = service.latest()
        if not latest or not latest.newer_than() or latest.tag == service.preferences.get('ignored'):
            self._key = None
            self.hide()
            return
        ready = bool(service.downloaded and service.download_release == latest)
        self._key = (latest.tag, 'ready' if ready else 'available')
        self._can_restart = ready and getattr(sys, 'frozen', False) and sys.platform == 'win32'
        if ready:
            hint = ('新版已下载并通过校验，点击重启即可更新。' if self._can_restart
                    else '新版已下载并通过校验，可在版本与更新中打开下载目录。')
        elif service.download_release == latest and service.busy == 'download':
            percent = min(100, int(service.received * 100 / max(service.total, 1)))
            hint = f'正在后台下载：{percent}%，完成后将再次提醒。'
        elif service.download_release == latest and service.busy == 'verify':
            hint = '下载已完成，正在校验程序文件…'
        else:
            hint = '查看更新说明并获取新版；本地方案和设置会保留。'
        self.message.setText(f'发现新版本 {latest.tag} · 当前 {VERSION}\n{hint}')
        self.action.setText('重启并更新' if self._can_restart else '查看更新')
        locked = self.context.management_busy or self.context.seedgen_active or bool(service.busy)
        self.action.setEnabled(not (self._can_restart and locked))
        self.action.setToolTip('请先等待文件操作和种子远征结束。' if self._can_restart and locked else '')
        self.details.setVisible(self._can_restart)
        self.setVisible(self._key not in self._dismissed)

    def dismiss(self):
        if self._key:
            self._dismissed.add(self._key)
        self.hide()

    def _activate(self):
        if self._can_restart:
            self.install_requested.emit()
        else:
            self.history_requested.emit()

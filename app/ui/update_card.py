"""Inline, quiet update controls for the settings workspace."""
import sys
from PySide6.QtCore import QSignalBlocker, Signal
from PySide6.QtWidgets import QCheckBox, QComboBox, QGroupBox, QHBoxLayout, QLabel, QProgressBar, QPushButton, QVBoxLayout
from core.version import VERSION


class UpdateCard(QGroupBox):
    install_requested = Signal()
    history_requested = Signal()

    def __init__(self, service):
        super().__init__('软件更新')
        self.service = service
        root = QVBoxLayout(self)
        root.addWidget(QLabel('当前版本 · ' + VERSION))
        self.status = QLabel(); self.status.setWordWrap(True); root.addWidget(self.status)
        self.progress = QProgressBar(); root.addWidget(self.progress)
        row = QHBoxLayout()
        self.check = QPushButton('检查更新'); self.check.setObjectName('settings_check_update')
        self.check.clicked.connect(service.check); row.addWidget(self.check)
        self.install = QPushButton('立即重启更新'); self.install.clicked.connect(self.install_requested)
        row.addWidget(self.install)
        self.download = QPushButton('下载新版'); self.download.clicked.connect(lambda: service.download(service.latest()))
        row.addWidget(self.download)
        self.cancel = QPushButton('取消下载'); self.cancel.clicked.connect(service.cancel); row.addWidget(self.cancel)
        self.history = QPushButton('版本说明'); self.history.clicked.connect(self.history_requested); row.addWidget(self.history)
        root.addLayout(row)
        self.channel = QComboBox(); self.channel.addItem('正式版', False); self.channel.addItem('正式版和测试版', True)
        self.channel.currentIndexChanged.connect(lambda _: service.save_preference('preview', self.channel.currentData()))
        root.addWidget(self.channel)
        self.preferences = {}
        for key, label in [('automatic', '自动检查更新'), ('auto_download', '发现新版后在后台下载'),
                           ('install_on_exit', '下载就绪后，正常退出软件时静默更新')]:
            checkbox = QCheckBox(label)
            checkbox.toggled.connect(lambda checked, k=key: service.save_preference(k, checked))
            self.preferences[key] = checkbox; root.addWidget(checkbox)
        hint = QLabel('优先从官网获取更新。下载和校验在后台完成；不会强制关闭游戏或打断操作，替换时保留旧程序备份。')
        hint.setWordWrap(True); hint.setObjectName('muted'); root.addWidget(hint)
        service.changed.connect(self.refresh); self.refresh()

    def refresh(self):
        service = self.service
        self.status.setText(service.status)
        self.check.setEnabled(not service.busy)
        ready = bool(service.downloaded and service.download_release and service.download_release.newer_than())
        self.install.setVisible(ready and bool(getattr(sys, 'frozen', False)))
        self.install.setEnabled(not service.busy)
        latest = service.latest()
        self.download.setVisible(bool(latest and latest.newer_than() and latest.installable and not ready))
        self.download.setEnabled(not service.busy)
        self.cancel.setVisible(service.busy == 'download')
        self.progress.setVisible(service.busy in ('download', 'verify'))
        if service.busy == 'verify':
            self.progress.setRange(0, 0)
        else:
            self.progress.setRange(0, 100)
            self.progress.setValue(int(service.received * 100 / max(1, service.total)))
        with QSignalBlocker(self.channel):
            self.channel.setCurrentIndex(1 if service.preferences.get('preview') else 0)
        for key, checkbox in self.preferences.items():
            with QSignalBlocker(checkbox):
                checkbox.setChecked(bool(service.preferences.get(key)))

"""Version history, channel preferences and explicit update installation."""
import sys
from datetime import datetime

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QHBoxLayout,
    QLabel, QListWidget, QListWidgetItem, QProgressBar, QPushButton, QSplitter, QTextBrowser, QVBoxLayout, QWidget)

from core.app_updates import RELEASES_URL
from core.l10n import VERSION as L10N_VERSION
from core.version import VERSION


class UpdateDialog(QDialog):
    install_requested = Signal()

    def __init__(self, service, parent=None):
        super().__init__(parent)
        self.service = service
        self.setWindowTitle('版本与更新')
        self.resize(860, 620)
        self.setMinimumSize(660, 500)
        self._rendered = None
        self._shown_release = object()
        root = QVBoxLayout(self)
        heading = QLabel(f'当前软件  {VERSION}     内置独立汉化  {L10N_VERSION}')
        heading.setWordWrap(True)
        root.addWidget(heading)
        options = QHBoxLayout()
        self.automatic = QCheckBox('启动时自动检查更新')
        self.automatic.setChecked(bool(service.preferences.get('automatic')))
        self.automatic.toggled.connect(lambda value: service.save_preference('automatic', value))
        options.addWidget(self.automatic)
        options.addStretch()
        options.addWidget(QLabel('更新通道'))
        self.channel = QComboBox()
        self.channel.addItem('稳定版', False)
        self.channel.addItem('稳定版 + 测试版', True)
        self.channel.setCurrentIndex(1 if service.preferences.get('preview') else 0)
        self.channel.currentIndexChanged.connect(self._channel_changed)
        options.addWidget(self.channel)
        self.check = QPushButton('立即检查')
        self.check.clicked.connect(service.check)
        options.addWidget(self.check)
        root.addLayout(options)
        self.status = QLabel()
        self.status.setWordWrap(True)
        self.status.setTextFormat(Qt.PlainText)
        root.addWidget(self.status)
        self.checked_at = QLabel()
        self.checked_at.setObjectName('muted')
        root.addWidget(self.checked_at)
        splitter = QSplitter(Qt.Horizontal)
        left = QWidget()
        column = QVBoxLayout(left)
        column.setContentsMargins(0, 0, 0, 0)
        column.addWidget(QLabel('发布历史'))
        self.versions = QListWidget()
        self.versions.setMinimumWidth(170)
        column.addWidget(self.versions)
        splitter.addWidget(left)
        self.notes = QTextBrowser()
        self.notes.setOpenExternalLinks(False)
        self.notes.setOpenLinks(False)
        # Release bodies are displayed as plain text: no remote images or executable links.
        splitter.addWidget(self.notes)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([210, 560])
        root.addWidget(splitter, 1)
        self.progress = QProgressBar()
        root.addWidget(self.progress)
        actions = QHBoxLayout()
        self.page = QPushButton('发布页面')
        self.page.clicked.connect(self._open_release)
        self.download = QPushButton('下载所选版本')
        self.download.clicked.connect(self._download)
        self.cancel_download = QPushButton('取消下载')
        self.cancel_download.clicked.connect(service.cancel)
        self.folder = QPushButton('打开下载目录')
        self.folder.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(service.downloaded.parent))) if service.downloaded else None)
        self.install = QPushButton('重启并更新')
        self.install.clicked.connect(self.install_requested.emit)
        for button in (self.page, self.download, self.cancel_download, self.folder, self.install):
            actions.addWidget(button)
        root.addLayout(actions)
        self.help = QLabel('更新仅替换软件 EXE，保留设置、筛选条件和汉化配置。历史版本可下载留存。')
        self.help.setWordWrap(True)
        root.addWidget(self.help)
        self.close_buttons = QDialogButtonBox(QDialogButtonBox.Close)
        self.close_buttons.button(QDialogButtonBox.Close).setText('关闭')
        self.close_buttons.rejected.connect(self.reject)
        root.addWidget(self.close_buttons)
        self.versions.currentRowChanged.connect(lambda _index: self._selection_changed())
        service.changed.connect(self.refresh)
        self.refresh()

    def selected(self):
        item = self.versions.currentItem()
        return item.data(Qt.UserRole) if item else None

    def _channel_changed(self):
        self.service.save_preference('preview', self.channel.currentData())

    def _selection_changed(self):
        release = self.selected()
        if release != self._shown_release:
            self.notes.setPlainText(release.notes if release else '点击“立即检查”获取版本记录。当前通道没有版本时，可以切换通道。')
            self._shown_release = release
        self.download.setEnabled(bool(release and release.installable and not self.service.busy))

    def _open_release(self):
        release = self.selected()
        QDesktopServices.openUrl(QUrl(release.url if release else RELEASES_URL))

    def _download(self):
        if self.selected():
            self.service.download(self.selected())

    def refresh(self):
        service = self.service
        self.status.setText(service.status)
        checked = service.preferences.get('last_check')
        try:
            stamp = datetime.fromisoformat(checked).astimezone().strftime('%Y-%m-%d %H:%M')
        except (TypeError, ValueError):
            stamp = '尚未成功检查'
        self.checked_at.setText('上次成功检查：' + stamp + '   ·   自动检查间隔 6 小时')
        signature = tuple(service.visible_releases())
        if signature != self._rendered:
            previous = self.selected()
            self.versions.clear()
            for release in signature:
                text = release.tag + ('  当前' if release.tag.lstrip('v') == VERSION else '')
                text += '\n' + ('测试版' if release.prerelease else '稳定版') + '  ' + release.published[:10]
                item = QListWidgetItem(text)
                item.setData(Qt.UserRole, release)
                self.versions.addItem(item)
            self._rendered = signature
            index = next((i for i, item in enumerate(signature) if previous and item.tag == previous.tag), 0)
            self.versions.setCurrentRow(index)
        self._selection_changed()
        self.check.setEnabled(not bool(service.busy))
        self.channel.setEnabled(not bool(service.busy))
        self.progress.setVisible(service.busy == 'download')
        self.progress.setRange(0, max(service.total, 1))
        self.progress.setValue(service.received)
        self.cancel_download.setVisible(bool(service.busy))
        self.cancel_download.setText('取消检查' if service.busy == 'check' else '取消下载')
        self.folder.setVisible(service.downloaded is not None)
        self.install.setVisible(service.downloaded is not None)
        can_install = bool(service.downloaded and service.download_release and service.download_release.newer_than())
        self.install.setEnabled(can_install and getattr(sys, 'frozen', False) and sys.platform == 'win32' and not service.busy)
        self.install.setToolTip('仅较新的 Windows 发行版支持原位置重启更新；历史版本可在下载目录中留存。')

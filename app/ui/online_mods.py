from __future__ import annotations

import threading
from pathlib import Path
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel, QTableWidget, QTableWidgetItem, QTextEdit, QMessageBox, QSplitter
from core.online_catalog import site_origin, fetch_catalog, download_release, OnlineInstaller
from .workers import Worker
from .theme import style_button, style_table


class OnlineModsPage(QWidget):
    def __init__(self, ctx, can_modify, parent=None):
        super().__init__(parent)
        self.ctx, self.can_modify = ctx, can_modify
        self.items = []
        self.rows = []
        self.origin = ''
        self.worker = None
        self.cancelled = threading.Event()
        layout = QVBoxLayout(self)
        bar = QHBoxLayout()
        self.address = QLineEdit(ctx.settings.get('online_catalog_url', ''))
        self.address.setPlaceholderText('军械库网站地址，例如 http://服务器IP:8080')
        self.refresh_btn = QPushButton('连接 / 刷新')
        self.website_btn = QPushButton('打开网站')
        bar.addWidget(self.address, 1); bar.addWidget(self.refresh_btn); bar.addWidget(self.website_btn)
        layout.addLayout(bar)
        self.search = QLineEdit(); self.search.setPlaceholderText('搜索名称、作者或分类…')
        layout.addWidget(self.search)
        splitter = QSplitter(Qt.Vertical)
        self.table = QTableWidget(0, 4)
        style_table(self.table)
        self.table.setHorizontalHeaderLabels(['作品', '版本', '作者 / 分类', '安装记录'])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setColumnWidth(0, 260)
        self.table.setColumnWidth(2, 220)
        self.table.horizontalHeader().setStretchLastSection(True)
        splitter.addWidget(self.table)
        self.details = QTextEdit(); self.details.setReadOnly(True)
        splitter.addWidget(self.details); splitter.setSizes([350, 170])
        layout.addWidget(splitter, 1)
        actions = QHBoxLayout()
        self.install_btn = QPushButton('下载并安装所选版本')
        self.rollback_btn = QPushButton('恢复所选 MOD 上一版')
        self.cancel_btn = QPushButton('取消下载')
        self.cancel_btn.setEnabled(False)
        for button, glyph in [(self.refresh_btn, 'refresh'), (self.website_btn, 'folder'), (self.install_btn, 'download'), (self.rollback_btn, 'restore'), (self.cancel_btn, 'stop')]:
            style_button(button, glyph)
        for button in [self.install_btn, self.rollback_btn, self.cancel_btn]: actions.addWidget(button)
        actions.addStretch(1); layout.addLayout(actions)
        self.status = QLabel('填入你信任的军械库网站地址，连接后查看已公开作品。')
        self.status.setWordWrap(True); self.status.setTextFormat(Qt.PlainText)
        layout.addWidget(self.status)
        self.refresh_btn.clicked.connect(self.refresh)
        self.website_btn.clicked.connect(self.open_website)
        self.search.textChanged.connect(self.render)
        self.table.itemSelectionChanged.connect(self.show_details)
        self.install_btn.clicked.connect(self.install)
        self.rollback_btn.clicked.connect(self.rollback)
        self.cancel_btn.clicked.connect(self.cancelled.set)
        ctx.management_changed.connect(self.update_controls)
        ctx.session_changed.connect(self.update_controls)
        self.update_controls()

    def update_controls(self, *_):
        running = bool(self.worker and self.worker.isRunning())
        blocked = running or self.ctx.management_busy or self.ctx.seedgen_active or not self.ctx.mm
        self.install_btn.setEnabled(not blocked and self.selected() is not None)
        self.rollback_btn.setEnabled(not blocked and self.selected() is not None)
        self.refresh_btn.setEnabled(not running)
        self.address.setEnabled(not running)

    def _run(self, fn, done, *, management=False):
        if self.worker and self.worker.isRunning(): return
        self.cancelled.clear()
        if management: self.ctx.set_management_busy(True)
        self.worker = Worker(fn, self)
        self.worker.done.connect(done)
        self.worker.failed.connect(lambda error: self.status.setText('操作失败：' + error))
        def finish():
            if management: self.ctx.set_management_busy(False)
            self.cancel_btn.setEnabled(False)
            self.update_controls()
        self.worker.finished.connect(finish)
        self.worker.start(); self.update_controls()

    def refresh(self):
        try: origin = site_origin(self.address.text())
        except ValueError as exc:
            self.status.setText(str(exc)); return
        self.status.setText('正在读取在线目录…')
        self.items = []; self.rows = []; self.render()
        def done(items):
            self.items = items; self.origin = origin
            self.ctx.settings.set('online_catalog_url', origin)
            self.render()
            self.status.setText(f'已连接：{origin} · {len(items)} 件公开作品。兼容说明由作者提供。')
        self._run(lambda: fetch_catalog(origin), done)

    def render(self, *_):
        query = self.search.text().casefold()
        self.rows = [r for r in self.items if query in ' '.join(str(r['metadata'].get(k, '')) for k in ['title', 'author', 'category']).casefold()]
        try: installed = OnlineInstaller(self.ctx.mm).state()['mods'] if self.ctx.mm else {}
        except (ValueError, OSError): installed = {}
        self.table.setRowCount(len(self.rows))
        for row, item in enumerate(self.rows):
            meta = item['metadata']; old = installed.get(item['file_name'])
            text = f"本地 v{old['version']}" if old else '未安装'
            for col, value in enumerate([meta['title'], item['version'], meta['author'] + ' / ' + meta['category'], text]):
                self.table.setItem(row, col, QTableWidgetItem(value))
        self.show_details()

    def selected(self):
        row = self.table.currentRow()
        return self.rows[row] if 0 <= row < len(self.rows) else None

    def show_details(self):
        item = self.selected()
        if item:
            m = item['metadata']
            self.details.setPlainText(f"{m['title']} v{item['version']}\n{m['summary']}\n\n{m['description']}\n\n"
                f"游戏版本：{m['game_version']}\nDLC：{m.get('dlc') or '未声明要求'}\n"
                f"前置：{'、'.join(m['requires']) or '未声明'}\n冲突：{'、'.join(m['conflicts']) or '未声明'}\n"
                f"许可：{m['license']}\n{m.get('compatibility_notes', '')}\n\nSHA-256：{item['sha256']}")
        else: self.details.clear()
        self.update_controls()

    def open_website(self):
        try: origin = site_origin(self.address.text())
        except ValueError as exc: self.status.setText(str(exc)); return
        QDesktopServices.openUrl(QUrl(origin))

    def install(self):
        item = self.selected()
        if not item or not self.can_modify(): return
        warning = '\n当前连接使用 HTTP，文件校验不能证明网站身份；请确认地址可信。' if self.origin.startswith('http:') else ''
        if QMessageBox.question(self, '安装在线 MOD', f"安装 {item['metadata']['title']} v{item['version']}？\n"
                '将检查前置和已声明的冲突。更新会备份旧版，已禁用的 MOD 保持禁用。' + warning) != QMessageBox.Yes: return
        origin = self.origin
        manager = self.ctx.mm
        cache = Path(self.ctx.settings.path).parent / 'online-downloads'
        def work():
            archive = download_release(origin, item, cache, cancelled=self.cancelled.is_set)
            try:
                if self.cancelled.is_set(): raise ValueError('下载已取消。')
                from core.game import is_game_running
                if is_game_running(): raise ValueError('游戏已启动，请关闭游戏后再安装。')
                return OnlineInstaller(manager).install(origin, item, archive)
            finally: archive.unlink(missing_ok=True)
        self.status.setText('正在下载、校验并安装…'); self.cancel_btn.setEnabled(True)
        self._run(work, self._installed, management=True)

    def _installed(self, result):
        self.status.setText(result); self.render(); self.ctx.data_changed.emit()

    def rollback(self):
        item = self.selected()
        if not item or not self.can_modify(): return
        if QMessageBox.question(self, '恢复上一版', f"恢复 {item['metadata']['title']} 的上一版安装文件？") != QMessageBox.Yes: return
        manager = self.ctx.mm
        self._run(lambda: OnlineInstaller(manager).rollback(item['file_name']), self._installed, management=True)

from __future__ import annotations

import threading
from pathlib import Path
from PySide6.QtCore import Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel, QTableWidget, QTableWidgetItem, QTextEdit, QMessageBox
from core.online_catalog import site_origin, fetch_catalog, download_release, OnlineInstaller
from core.site_config import SITE_ORIGIN, canonical_site_origin, same_site
from .workers import Worker, track, modify_files
from .theme import style_button, style_table


class OnlineModsPage(QWidget):
    download_progress = Signal(str)
    catalog_changed = Signal(object, str)
    operation_status = Signal(str)

    def __init__(self, ctx, can_modify, parent=None):
        super().__init__(parent)
        self.ctx, self.can_modify = ctx, can_modify
        self.items = []
        self.rows = []
        self._rollback_names = set()
        self._installed_names = {}
        self.pending_mod_id = None
        self.origin = ''
        self.worker = None
        self._local = self._local_mm = None
        self.cancelled = threading.Event()
        layout = QVBoxLayout(self)
        bar = QHBoxLayout()
        self.address = QLineEdit(canonical_site_origin(ctx.settings.get('online_catalog_url', '') or SITE_ORIGIN))
        self.address.setPlaceholderText(SITE_ORIGIN)
        self.address.hide()
        self.source_btn = QPushButton('自定义源（高级）')
        self.source_btn.clicked.connect(lambda: self.address.setVisible(not self.address.isVisible()))
        self.refresh_btn = QPushButton('连接 / 刷新')
        self.website_btn = QPushButton('打开网站')
        bar.addWidget(self.address, 1); bar.addWidget(self.refresh_btn); bar.addWidget(self.website_btn); bar.addWidget(self.source_btn)
        layout.addLayout(bar)
        self.search = QLineEdit(); self.search.setPlaceholderText('搜索名称、作者或分类…')
        layout.addWidget(self.search)
        self.table = QTableWidget(0, 4)
        style_table(self.table)
        self.table.setHorizontalHeaderLabels(['作品', '版本', '作者 / 分类', '安装记录'])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setColumnWidth(0, 260)
        self.table.setColumnWidth(2, 220)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table, 1)
        self.details = QTextEdit(); self.details.setReadOnly(True)
        self.details.setFixedHeight(170)
        layout.addWidget(self.details)
        actions = QHBoxLayout()
        self.install_btn = QPushButton('下载并安装所选版本')
        self.rollback_btn = QPushButton('恢复所选 MOD 上一版')
        self.cancel_btn = QPushButton('取消下载')
        self.cancel_btn.setEnabled(False)
        for button, glyph in [(self.refresh_btn, 'refresh'), (self.website_btn, 'folder'), (self.install_btn, 'download'), (self.rollback_btn, 'restore'), (self.cancel_btn, 'stop')]:
            style_button(button, glyph)
        for button in [self.install_btn, self.rollback_btn, self.cancel_btn]: actions.addWidget(button)
        actions.addStretch(1); layout.addLayout(actions)
        self.status = QLabel('默认连接 BBMOD 官网。点击「连接 / 刷新」查看作品；其他来源可在高级设置中修改。')
        self.status.setWordWrap(True); self.status.setTextFormat(Qt.PlainText)
        self.download_progress.connect(self._report_status)
        layout.addWidget(self.status)
        self.refresh_btn.clicked.connect(self.refresh)
        self.website_btn.clicked.connect(self.open_website)
        self._search_timer = QTimer(self, singleShot=True, interval=200)
        self._search_timer.timeout.connect(self.render)
        self.search.textChanged.connect(lambda *_: self._search_timer.start())
        ctx.data_changed.connect(self.set_local_state)
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
        selected = self.selected()
        self.rollback_btn.setEnabled(not blocked and selected is not None and selected['file_name'] in self._rollback_names)
        self.refresh_btn.setEnabled(not running)
        self.address.setEnabled(not running)

    def _report_status(self, message):
        self.status.setText(message)
        self.operation_status.emit(message)

    def _run(self, fn, done, *, management=False):
        if self.worker and self.worker.isRunning(): return
        self.cancelled.clear()
        if management: self.ctx.set_management_busy(True)
        track(self, 'worker', Worker(fn, self))
        self.worker.done.connect(done)
        self.worker.failed.connect(lambda error: self._report_status('操作失败：' + error))
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
            self.catalog_changed.emit(items, origin)
            self.ctx.settings.set('online_catalog_url', origin)
            self.render()
            self.status.setText(f'已连接：{origin} · {len(items)} 件公开作品。兼容说明由作者提供。')
            if self.pending_mod_id:
                self.focus_mod(self.pending_mod_id)
        self._run(lambda: fetch_catalog(origin), done)

    def set_local_state(self, local=None):
        """(安装记录, 安装状态)；None 表示失效，下次 render 时重新读取。"""
        self._local, self._local_mm = local, self.ctx.mm

    def _local_state(self):
        if self._local is None or self._local_mm is not self.ctx.mm:
            try: installed = OnlineInstaller(self.ctx.mm).state()['mods'] if self.ctx.mm else {}
            except (ValueError, OSError): installed = {}
            self._local = (installed, self.ctx.mm.installation_states() if self.ctx.mm else {})
            self._local_mm = self.ctx.mm
        return self._local

    def render(self, *_):
        self._search_timer.stop()
        query = self.search.text().casefold()
        self.rows = [r for r in self.items if query in (' '.join(str(r['metadata'].get(k, '')) for k in ['title', 'author', 'category']) + ' ' + ' '.join(r['metadata'].get('mod_ids', []))).casefold()]
        installed, actual = self._local_state() if self.rows else ({}, {})
        self._rollback_names = set()
        self._installed_names = {}
        self.table.setRowCount(len(self.rows))
        for row, item in enumerate(self.rows):
            meta = item['metadata']; local_name = item['file_name']
            matching = [(name, receipt) for name, receipt in installed.items()
                        if receipt.get('id') == item['id'] and same_site(receipt.get('origin'), self.origin)
                        and actual.get(name.casefold(), '未安装') != '未安装']
            if len(matching) == 1:
                local_name = matching[0][0]
            old = installed.get(local_name)
            text = actual.get(local_name.casefold(), '未安装')
            if old and text != '未安装' and old.get('id') == item['id'] and same_site(old.get('origin'), self.origin):
                self._installed_names[item['id']] = local_name
                text += f" · v{old['version']}"
                if old.get('previous') and old.get('backup'):
                    self._rollback_names.add(item['file_name'])
            for col, value in enumerate([meta['title'], item['version'], meta['author'] + ' / ' + meta['category'], text]):
                self.table.setItem(row, col, QTableWidgetItem(value))
        self.show_details()

    def focus_mod(self, mod_id):
        self.pending_mod_id = mod_id
        self.search.clear()
        self.render()
        for row, item in enumerate(self.rows):
            if item['id'] == mod_id:
                self.table.selectRow(row)
                self.pending_mod_id = None
                self.status.setText('已定位网页作品。请阅读兼容说明，再点击「下载并安装所选版本」。')
                return
        if self.items:
            self.pending_mod_id = None
            self.status.setText('该作品未公开或已撤回，无法安装。')

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
            archive = download_release(origin, item, cache, cancelled=self.cancelled.is_set,
                                       progress=self.download_progress.emit)
            try:
                if self.cancelled.is_set(): raise ValueError('下载已取消。')
                from core.game import is_game_running
                if is_game_running(): raise ValueError('游戏已启动，请关闭游戏后再安装。')
                return modify_files(manager, lambda: OnlineInstaller(manager).install(origin, item, archive))
            finally: archive.unlink(missing_ok=True)
        self.status.setText('正在下载、校验并安装…'); self.cancel_btn.setEnabled(True)
        self._run(work, self._installed, management=True)

    def update_installed(self, item, *, origin=SITE_ORIGIN, current_file_name=None,
                         current_sha256=None, installed_version=''):
        """The installed-row action updates in place with no second confirmation."""
        if self.worker and self.worker.isRunning():
            return
        if not self.can_modify():
            return
        if not current_file_name or not current_sha256 or not installed_version:
            self._report_status('本地版本尚未确认，请刷新官网版本后重试。')
            return
        origin = site_origin(origin)
        manager = self.ctx.mm
        cache = Path(self.ctx.settings.path).parent / 'online-downloads'

        def work():
            from core.game import is_game_running
            if is_game_running():
                raise ValueError('游戏已启动，请关闭游戏后再更新。')
            archive = download_release(origin, item, cache, cancelled=self.cancelled.is_set,
                                       progress=self.download_progress.emit)
            try:
                if self.cancelled.is_set():
                    raise ValueError('下载已取消。')
                if is_game_running():
                    raise ValueError('游戏已启动，请关闭游戏后再更新。')
                return modify_files(manager, lambda: OnlineInstaller(manager).install(origin, item, archive,
                    local_file_name=current_file_name, expected_current_sha256=current_sha256,
                    installed_version=installed_version))
            finally:
                archive.unlink(missing_ok=True)

        self._report_status(f"正在更新 {item['metadata']['title']}：{installed_version} → {item['version']}…")
        self.cancel_btn.setEnabled(True)
        self._run(work, self._installed, management=True)

    def _installed(self, result):
        self._report_status(result); self.set_local_state(); self.render(); self.ctx.data_changed.emit()

    def rollback(self):
        item = self.selected()
        if not item or not self.can_modify(): return
        if QMessageBox.question(self, '恢复上一版', f"恢复 {item['metadata']['title']} 的上一版安装文件？") != QMessageBox.Yes: return
        manager = self.ctx.mm
        local_name = self._installed_names.get(item['id'], item['file_name'])
        self._run(lambda: modify_files(manager, lambda: OnlineInstaller(manager).rollback(local_name)),
                  self._installed, management=True)

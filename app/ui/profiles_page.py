"""Saved local collections and the website gallery in one desktop workspace."""
from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QInputDialog, QLabel, QLineEdit,
    QMessageBox, QPushButton, QSplitter, QTabWidget, QTableWidget, QTableWidgetItem,
    QTextEdit, QVBoxLayout, QWidget)

from core.online_catalog import site_origin
from core.shared_profiles import fetch_profiles, profile_identity
from .profile_sharing import ProfileSharing, preview_dialog
from .theme import style_button, style_table
from .workers import Worker, track


class ProfilesPage(QWidget):
    choose_game_requested = Signal()

    def __init__(self, ctx, mods):
        super().__init__()
        self.ctx, self.mods = ctx, mods
        self.local_profiles = {}
        self.rows = []
        self.catalog_origin = ''
        self.catalog_page, self.catalog_pages = 1, 1
        self.catalog_loaded = False
        self.catalog_query = ''
        self.worker = None
        self.sharing = ProfileSharing(self)
        root = QVBoxLayout(self)
        self.sections = QTabWidget()
        self.sections.addTab(self._build_local(), '本地方案')
        self.sections.addTab(self._build_online(), '网站方案')
        root.addWidget(self.sections, 1)
        self.status_label = QLabel('保存、整理本地 MOD 组合，或直接从网站选择共享方案。')
        self.status_label.setObjectName('workspaceHint')
        self.status_label.setWordWrap(True)
        self.status_label.setTextFormat(Qt.PlainText)
        root.insertWidget(0, self.status_label)
        self.sections.currentChanged.connect(self._tab_changed)
        ctx.data_changed.connect(self.refresh)
        ctx.management_changed.connect(self.update_controls)
        ctx.session_changed.connect(self.update_controls)
        if hasattr(ctx, 'game_changed'):
            ctx.game_changed.connect(self.refresh)
        mods.online.address.textChanged.connect(self._source_changed)
        self.refresh()

    @staticmethod
    def _table(headers):
        table = QTableWidget(0, len(headers))
        style_table(table)
        table.setHorizontalHeaderLabels(headers)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setSelectionMode(QTableWidget.SingleSelection)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setColumnWidth(0, 260)
        table.horizontalHeader().setStretchLastSection(True)
        return table

    @staticmethod
    def _details():
        details = QTextEdit()
        details.setReadOnly(True)
        return details

    @staticmethod
    def _button(bar, title, glyph, callback):
        button = QPushButton(title)
        style_button(button, glyph)
        button.clicked.connect(lambda: callback())
        bar.addWidget(button)
        return button

    def _build_local(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        bar = QHBoxLayout()
        self.local_search = QLineEdit()
        self.local_search.setPlaceholderText('搜索本地方案名称或 MOD 文件名…')
        bar.addWidget(self.local_search, 1)
        self.save_btn = self._button(bar, '保存当前组合', 'save', self.save_current)
        self._button(bar, '刷新', 'refresh', self.refresh)
        layout.addLayout(bar)
        self.local_hint = QLabel()
        self.local_hint.setWordWrap(True)
        layout.addWidget(self.local_hint)
        splitter = QSplitter(Qt.Vertical)
        self.local_table = self._table(['方案名称', 'MOD 数量', '来源', '保存时间'])
        self.local_details = self._details()
        splitter.addWidget(self.local_table)
        splitter.addWidget(self.local_details)
        splitter.setSizes([310, 180])
        layout.addWidget(splitter, 1)
        actions = QHBoxLayout()
        self.apply_btn = self._button(actions, '预览并应用', 'check', self.apply_local)
        self.rename_btn = self._button(actions, '重命名', 'book', self.rename_local)
        self.delete_btn = self._button(actions, '删除方案', 'close', self.delete_local)
        self.share_btn = self._button(actions, '分享方案', 'save', self.share_local)
        self.copy_local_btn = self._button(actions, '复制分享链接', 'copy', self.copy_local_link)
        actions.addStretch(1)
        layout.addLayout(actions)
        self.local_search.textChanged.connect(self.render_local)
        self.local_table.itemSelectionChanged.connect(self.show_local)
        self.local_table.cellDoubleClicked.connect(lambda *_: self.apply_local())
        return page

    def _build_online(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        bar = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setMaxLength(100)
        self.search.setPlaceholderText('搜索网站方案名称或介绍…')
        bar.addWidget(self.search, 1)
        self.refresh_btn = self._button(bar, '搜索 / 刷新', 'refresh', lambda: self.load_catalog(1))
        self._button(bar, '打开方案广场', 'folder', self.open_gallery)
        layout.addLayout(bar)
        self.source_label = QLabel()
        self.source_label.setWordWrap(True)
        self.source_label.setTextFormat(Qt.PlainText)
        layout.addWidget(self.source_label)
        splitter = QSplitter(Qt.Vertical)
        self.online_table = self._table(['方案名称', 'MOD 数量', '文件总大小', '分享时间'])
        self.online_details = self._details()
        splitter.addWidget(self.online_table)
        splitter.addWidget(self.online_details)
        splitter.setSizes([310, 180])
        layout.addWidget(splitter, 1)
        pager = QHBoxLayout()
        self.prev_btn = self._button(pager, '上一页', 'book', lambda: self.load_catalog(self.catalog_page - 1))
        self.page_label = QLabel('尚未读取网站方案')
        pager.addWidget(self.page_label)
        self.next_btn = self._button(pager, '下一页', 'book', lambda: self.load_catalog(self.catalog_page + 1))
        pager.addStretch(1)
        layout.addLayout(pager)
        actions = QHBoxLayout()
        self.online_apply_btn = self._button(actions, '预览并应用', 'download', self.apply_online)
        self.copy_online_btn = self._button(actions, '复制分享链接', 'copy', self.copy_online_link)
        self.detail_btn = self._button(actions, '查看网页详情', 'folder', self.open_online_detail)
        self.import_link_btn = self._button(actions, '通过链接导入…', 'download', self.sharing.import_link)
        actions.addStretch(1)
        layout.addLayout(actions)
        self.search.returnPressed.connect(lambda: self.load_catalog(1))
        self.online_table.itemSelectionChanged.connect(self.show_online)
        self.online_table.cellDoubleClicked.connect(lambda *_: self.apply_online())
        return page

    def profile_origin(self):
        return self.mods.profile_origin()

    def _can_modify(self):
        return self.mods._can_modify()

    def refresh(self):
        self.local_profiles = self.ctx.mm.load_profiles() if self.ctx.mm else {}
        self.render_local()
        self._show_source()

    def _show_source(self):
        try:
            text = '方案来源：' + self.profile_origin() + '（与在线军械库共用网站设置）'
        except ValueError as error:
            text = '网站地址无效：' + str(error)
        self.source_label.setText(text)

    def selected_local(self):
        row = self.local_table.currentRow()
        item = self.local_table.item(row, 0)
        return item.text() if item and self.local_table.selectionModel().hasSelection() else None

    def render_local(self, *_):
        selected = self.selected_local()
        query = self.local_search.text().strip().casefold()
        names = [name for name, profile in self.local_profiles.items()
                 if query in (name + ' ' + ' '.join(profile.get('enabled', []))).casefold()]
        self.local_table.blockSignals(True)
        self.local_table.clearSelection()
        self.local_table.setRowCount(len(names))
        for row, name in enumerate(names):
            profile = self.local_profiles[name]
            source = '网站导入' if profile.get('shared_id') else '本地保存'
            if profile.get('published_id'):
                source += ' · 已分享'
            values = [name, str(len(profile.get('enabled', []))), source,
                      profile.get('saved_at', '').replace('T', ' ')]
            for col, value in enumerate(values):
                self.local_table.setItem(row, col, QTableWidgetItem(value))
        if names:
            self.local_table.selectRow(names.index(selected) if selected in names else 0)
        self.local_table.blockSignals(False)
        self.local_hint.setText('先选择游戏目录，即可保存和管理本地方案。网站方案无需选择目录即可浏览。'
            if not self.ctx.mm else (f'共 {len(self.local_profiles)} 个本地方案，显示 {len(names)} 个。'
            if self.local_profiles else '还没有本地方案。保存当前启用的 MOD，或从「网站方案」选择并应用。'))
        self.show_local()

    def _local_link(self):
        profile = self.local_profiles.get(self.selected_local(), {})
        prefix = 'published' if profile.get('published_id') else 'shared'
        identity, origin = profile.get(prefix + '_id'), profile.get(prefix + '_origin')
        if not identity or not origin:
            return ''
        try:
            origin = site_origin(origin)
            return origin + '/profiles/' + profile_identity(identity, origin) + '/'
        except ValueError:
            return ''

    def show_local(self):
        name = self.selected_local()
        profile = self.local_profiles.get(name)
        if profile:
            link = self._local_link()
            text = f'{name}\n\n包含 {len(profile.get("enabled", []))} 个 MOD：\n'
            text += '\n'.join(profile.get('enabled', [])) or '空组合（应用后禁用所有 MOD）'
            if link:
                text += '\n\n分享链接：' + link
            if profile.get('shared_id'):
                text += '\n\n应用时按网站分享版本核对并下载缺失文件。'
            else:
                text += '\n\n本地方案按文件名切换，分享时使用本机当前文件内容。'
            self.local_details.setPlainText(text)
        else:
            self.local_details.setPlainText('选择一份方案查看 MOD 清单。')
        if hasattr(self, 'online_apply_btn'):
            self.update_controls()

    def update_controls(self, *_):
        busy = self.ctx.management_busy or self.ctx.seedgen_active
        pending = bool(self.ctx.mm and self.ctx.mm.transaction.journal.exists())
        ready = not busy and not pending
        local = self.selected_local() is not None
        for button in (self.apply_btn, self.rename_btn, self.delete_btn, self.share_btn):
            button.setEnabled(bool(self.ctx.mm) and ready and local)
        self.save_btn.setEnabled(ready)
        self.copy_local_btn.setEnabled(bool(self._local_link()))
        running = bool(self.worker and self.worker.isRunning())
        online = self.selected_online() is not None
        self.refresh_btn.setEnabled(not running)
        self.search.setEnabled(not running)
        self.prev_btn.setEnabled(not running and self.catalog_loaded and self.catalog_page > 1)
        self.next_btn.setEnabled(not running and self.catalog_loaded and self.catalog_page < self.catalog_pages)
        self.online_apply_btn.setEnabled(ready and online and not running)
        self.import_link_btn.setEnabled(ready)
        self.copy_online_btn.setEnabled(online)
        self.detail_btn.setEnabled(online)

    def save_current(self):
        if not self.sharing._ready():
            return
        name, ok = QInputDialog.getText(self, '保存当前组合', '方案名称：')
        if not ok or not name.strip():
            return
        name = name.strip()
        if name in self.ctx.mm.load_profiles() and QMessageBox.question(self, '覆盖方案',
                f'用当前启用的 MOD 覆盖「{name}」？原方案及其分享关联将被替换。',
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            return
        self._edit_local(lambda: self.ctx.mm.save_profile(name), f'已保存方案「{name}」。')

    def _edit_local(self, action, message):
        if not self.sharing._ready():
            return
        try:
            action()
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, '方案操作失败', str(error))
            return
        self.refresh()
        self.ctx.data_changed.emit()
        self.status_label.setText(message)

    def rename_local(self):
        name = self.selected_local()
        if not name or not self.sharing._ready():
            return
        renamed, ok = QInputDialog.getText(self, '重命名本地方案', '新名称（不更改已发布的网站方案）：', text=name)
        if ok and renamed.strip():
            self._edit_local(lambda: self.ctx.mm.rename_profile(name, renamed), f'已重命名为「{renamed.strip()}」。')

    def delete_local(self):
        name = self.selected_local()
        if not name or not self.sharing._ready():
            return
        if QMessageBox.question(self, '删除本地方案', f'删除本地方案「{name}」？\n\n'
                '只删除方案记录，已安装的 MOD 和网站上的共享方案仍然保留。',
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) == QMessageBox.Yes:
            self._edit_local(lambda: self.ctx.mm.delete_profile(name), f'已删除本地方案「{name}」，MOD 文件保留。')

    def apply_local(self):
        name = self.selected_local()
        if not name or not self.sharing._ready():
            return
        profile = self.ctx.mm.load_profiles().get(name)
        if not profile:
            self.refresh()
            return
        if profile.get('shared_id'):
            self.sharing.import_link(profile['shared_id'], origin=profile.get('shared_origin'))
            return
        try:
            plan = self.ctx.mm.preview_profile(name)
            details = '将启用：\n' + ('\n'.join(plan['enable']) or '无')
            details += '\n\n将禁用：\n' + ('\n'.join(plan['disable']) or '无')
            if preview_dialog(self, '预览本地方案', f'应用「{name}」', details, '应用方案'):
                self._edit_local(lambda: self.ctx.mm.apply_profile(name, expected=plan), f'已应用方案「{name}」。')
        except (OSError, ValueError, KeyError) as error:
            QMessageBox.warning(self, '无法应用方案', str(error))

    def share_local(self):
        name = self.selected_local()
        if name:
            self.sharing.share(name)

    def copy_local_link(self):
        link = self._local_link()
        if link:
            QApplication.clipboard().setText(link)
            self.status_label.setText('分享链接已复制：' + link)

    def _tab_changed(self, index):
        if index == 1 and not self.catalog_loaded:
            self.load_catalog(1)

    def open_online(self):
        if self.sections.currentIndex() == 1:
            if not self.catalog_loaded:
                self.load_catalog(1)
        else:
            self.sections.setCurrentIndex(1)

    def _source_changed(self, *_):
        self.catalog_loaded = False
        self.rows = []
        self.render_online()
        self.page_label.setText('来源已更改，请刷新网站方案')
        self._show_source()

    def load_catalog(self, page=1):
        if self.worker and self.worker.isRunning():
            return
        try:
            origin = self.profile_origin()
        except ValueError as error:
            self.status_label.setText(str(error))
            return
        query = self.search.text().strip()
        if query != self.catalog_query:
            page = 1
        self.catalog_loaded = False
        self.rows = []
        self.render_online()
        self.page_label.setText('正在读取…')
        self.status_label.setText('正在读取网站现有方案…')
        worker = track(self, 'worker', Worker(lambda: fetch_profiles(origin, query, page), self))

        def current_source():
            try:
                return self.profile_origin() == origin
            except ValueError:
                return False

        def done(result):
            if not current_source():
                return
            self.catalog_origin = origin
            self.catalog_query = query
            self.catalog_page, self.catalog_pages = result['page'], result['pages']
            self.catalog_loaded = True
            self.rows = result['items']
            self.render_online()
            self.page_label.setText(f'第 {self.catalog_page} / {self.catalog_pages} 页 · 共 {result["total"]} 个方案')
            self.status_label.setText('选择方案即可预览并应用；下载前会重新核对文件是否可用。'
                if self.rows else ('没有找到匹配的方案，请修改关键词重试。' if query else '网站暂时还没有公开方案。'))

        def failed(error):
            if current_source():
                self.page_label.setText('读取失败，可点击「搜索 / 刷新」重试')
                self.status_label.setText('无法读取网站方案：' + error + '；仍可管理本地方案或通过链接导入。')
        worker.done.connect(done)
        worker.failed.connect(failed)
        worker.finished.connect(self.update_controls)
        worker.start()
        self.update_controls()

    def render_online(self):
        self.online_table.blockSignals(True)
        self.online_table.clearSelection()
        self.online_table.setRowCount(len(self.rows))
        for row, item in enumerate(self.rows):
            values = [item['name'], str(item['mod_count']), f'{item["total_size"] / 1024**2:.1f} MB',
                      item['created_at'][:10]]
            for col, value in enumerate(values):
                self.online_table.setItem(row, col, QTableWidgetItem(value))
        if self.rows:
            self.online_table.selectRow(0)
        self.online_table.blockSignals(False)
        self.show_online()

    def selected_online(self):
        row = self.online_table.currentRow()
        return self.rows[row] if 0 <= row < len(self.rows) and self.online_table.selectionModel().hasSelection() else None

    def show_online(self):
        item = self.selected_online()
        self.online_details.setPlainText((f'{item["name"]}\n游戏版本：{item["game_version"] or "未注明"}'
            f'\n{item["mod_count"]} 个 MOD · 文件总大小 {item["total_size"] / 1024**2:.1f} MB'
            f'\n\n{item["note"] or "分享者未填写介绍。"}\n\n应用前会展示完整 MOD 清单与本机变更。')
            if item else '从网站列表选择方案，无需寻找分享链接。')
        self.update_controls()

    def apply_online(self):
        item = self.selected_online()
        if item:
            self.sharing.import_link(item['id'], origin=self.catalog_origin)

    def copy_online_link(self):
        item = self.selected_online()
        if item:
            link = self.catalog_origin + item['page_path']
            QApplication.clipboard().setText(link)
            self.status_label.setText('分享链接已复制：' + link)

    def open_online_detail(self):
        item = self.selected_online()
        if item:
            QDesktopServices.openUrl(QUrl(self.catalog_origin + item['page_path']))

    def open_gallery(self):
        try:
            QDesktopServices.openUrl(QUrl(self.profile_origin() + '/profiles/'))
        except ValueError as error:
            self.status_label.setText(str(error))

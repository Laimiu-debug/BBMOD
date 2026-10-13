"""Campaign sharing with a visible MOD preview and a searchable website gallery."""
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QApplication, QFileDialog, QHBoxLayout, QInputDialog, QLabel,
    QLineEdit, QMessageBox, QPushButton, QSizePolicy, QSplitter, QTabWidget, QTextEdit, QVBoxLayout, QWidget)

from core import shared_saves
from core.online_catalog import site_origin
from .profile_sharing import ProfileSharing, preview_dialog
from .profiles_page import ProfilesPage
from .theme import style_button


class SavesPage(QWidget):
    choose_game_requested = Signal()

    def __init__(self, ctx, mods):
        super().__init__()
        self.ctx, self.mods = ctx, mods
        self.local_rows, self.rows = [], []
        self.catalog_page, self.catalog_pages = 1, 1
        self.catalog_origin = ''
        self.runner = ProfileSharing(self)
        root = QVBoxLayout(self)
        self.status_label = QLabel('选择战役并连同当前启用的整套 MOD 分享，或从存档广场继续兄弟的远征。')
        self.status_label.setWordWrap(True)
        self.status_label.setTextFormat(Qt.PlainText)
        self.status_label.setObjectName('workspaceHint')
        root.addWidget(self.status_label)
        self.sections = QTabWidget()
        self.sections.addTab(self._local(), '本机存档')
        self.sections.addTab(self._online(), '存档广场')
        root.addWidget(self.sections, 1)
        self.sections.currentChanged.connect(lambda index: self.load_catalog(1) if index == 1 and not self.catalog_origin else None)
        ctx.data_changed.connect(self.refresh)
        ctx.game_changed.connect(self.refresh)
        ctx.management_changed.connect(self.update_controls)
        ctx.session_changed.connect(self.update_controls)
        ctx.game_session.changed.connect(self.update_controls)
        mods.online.address.textChanged.connect(self._source_changed)
        self.refresh()

    def _button(self, bar, title, glyph, callback):
        button = QPushButton(title)
        style_button(button, glyph)
        button.clicked.connect(lambda: callback())
        bar.addWidget(button)
        return button

    def _local(self):
        page, layout = QWidget(), QVBoxLayout()
        page.setLayout(layout)
        bar = QHBoxLayout()
        self.directory_label = QLabel()
        self.directory_label.setWordWrap(True)
        self.directory_label.setTextFormat(Qt.PlainText)
        bar.addWidget(self.directory_label, 1)
        self.folder_btn = self._button(bar, '选择存档目录', 'folder', self.choose_directory)
        self.local_refresh_btn = self._button(bar, '刷新', 'refresh', self.refresh)
        layout.addLayout(bar)
        hint = QLabel('先退出游戏，并确认当前启用的 MOD 与所选战役一致。分享会包含整套 MOD；已有存档和 MOD 不会因分享而改动。')
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.local_table = ProfilesPage._table(['战役文件', '大小', '修改时间'])
        layout.addWidget(self.local_table, 1)
        bar = QHBoxLayout()
        self.share_btn = self._button(bar, '分享存档与 MOD', 'save', self.share_selected)
        self.import_btn = self._button(bar, '通过链接恢复…', 'download', self.import_link)
        self.recover_btn = self._button(bar, '恢复上次导入', 'refresh', self.recover)
        bar.addStretch()
        layout.addLayout(bar)
        self.local_table.itemSelectionChanged.connect(self.update_controls)
        return page

    def _online(self):
        page, layout = QWidget(), QVBoxLayout()
        page.setLayout(layout)
        bar = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setMaxLength(100)
        self.search.setPlaceholderText('查找战役名称或介绍…')
        bar.addWidget(self.search, 1)
        self.refresh_btn = self._button(bar, '搜索 / 刷新', 'refresh', lambda: self.load_catalog(1))
        self._button(bar, '打开存档广场', 'folder', self.open_gallery)
        layout.addLayout(bar)
        splitter = QSplitter(Qt.Vertical)
        splitter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Ignored)
        self.online_table = ProfilesPage._table(['战役名称', 'MOD 数量', '整套大小', '游戏版本'])
        self.online_table.setMinimumHeight(96)
        splitter.addWidget(self.online_table)
        self.details = QTextEdit()
        self.details.setReadOnly(True)
        self.details.setMinimumHeight(64)
        splitter.addWidget(self.details)
        splitter.setSizes([290, 120])
        splitter.setChildrenCollapsible(False)
        layout.addWidget(splitter, 1)
        pager = QHBoxLayout()
        self.prev_btn = self._button(pager, '上一页', 'book', lambda: self.load_catalog(self.catalog_page - 1))
        self.page_label = QLabel('尚未读取存档广场')
        pager.addWidget(self.page_label)
        self.next_btn = self._button(pager, '下一页', 'book', lambda: self.load_catalog(self.catalog_page + 1))
        pager.addStretch()
        layout.addLayout(pager)
        bar = QHBoxLayout()
        self.restore_btn = self._button(bar, '预览并恢复存档与 MOD', 'download', self.restore_selected)
        self.copy_btn = self._button(bar, '复制分享链接', 'copy', self.copy_link)
        self.detail_btn = self._button(bar, '网页详情', 'folder', self.open_detail)
        bar.addStretch()
        layout.addLayout(bar)
        self.online_table.itemSelectionChanged.connect(self.show_online)
        self.search.returnPressed.connect(lambda: self.load_catalog(1))
        return page

    def profile_origin(self):
        return site_origin(self.mods.profile_origin())

    def open_gallery(self):
        try:
            QDesktopServices.openUrl(QUrl(self.profile_origin() + '/saves/'))
        except ValueError as error:
            QMessageBox.warning(self, '网站地址无效', str(error))

    def _can_modify(self):
        return self.mods._can_modify()

    def directory(self):
        return shared_saves.save_directory(self.ctx.settings.get('savegames_directory'))

    def choose_directory(self):
        if self.ctx.management_busy:
            return
        directory = QFileDialog.getExistingDirectory(self, '选择 Battle Brothers 的 savegames 目录', str(self.directory()))
        if directory:
            self.ctx.settings.set('savegames_directory', directory)
            self.refresh()

    def refresh(self):
        self.directory_label.setText('存档目录：' + str(self.directory()))
        selected = self.selected_local()
        try:
            self.local_rows = shared_saves.list_saves(self.directory())
        except (OSError, ValueError) as error:
            self.local_rows = []
            self.status_label.setText('无法读取存档目录：' + str(error))
        self.local_table.blockSignals(True)
        self.local_table.setRowCount(len(self.local_rows))
        for row, item in enumerate(self.local_rows):
            for col, value in enumerate((item['path'].name, f"{item['size']/1024**2:.1f} MB",
                    datetime.fromtimestamp(item['mtime']).strftime('%Y-%m-%d %H:%M'))):
                from PySide6.QtWidgets import QTableWidgetItem
                cell = QTableWidgetItem(value)
                cell.setToolTip(str(item['path']))
                self.local_table.setItem(row, col, cell)
        if self.local_rows:
            self.local_table.selectRow(next((i for i, r in enumerate(self.local_rows) if r['path'] == selected), 0))
        self.local_table.blockSignals(False)
        self.update_controls()

    def selected_local(self):
        row = self.local_table.currentRow()
        return self.local_rows[row]['path'] if 0 <= row < len(self.local_rows) else None

    def selected_online(self):
        row = self.online_table.currentRow()
        return self.rows[row] if 0 <= row < len(self.rows) else None

    def update_controls(self, *_):
        if not hasattr(self, 'restore_btn'):
            return
        pending = bool(self.ctx.mm and self.ctx.mm.transaction.journal.exists())
        busy = self.ctx.management_busy or self.ctx.seedgen_active or self.ctx.game_session.occupied
        running = bool(self.runner.worker and self.runner.worker.isRunning())
        ready = bool(self.ctx.mm) and not busy and not pending and not running
        self.share_btn.setEnabled(ready and self.selected_local() is not None)
        self.import_btn.setEnabled(ready)
        self.restore_btn.setEnabled(ready and self.selected_online() is not None)
        self.folder_btn.setEnabled(not self.ctx.management_busy and not running)
        self.local_refresh_btn.setEnabled(not running)
        self.recover_btn.setVisible(pending)
        self.recover_btn.setEnabled(pending and not busy and not running)
        self.refresh_btn.setEnabled(not running and not self.ctx.management_busy)
        self.prev_btn.setEnabled(not running and self.catalog_page > 1)
        self.next_btn.setEnabled(not running and self.catalog_page < self.catalog_pages)
        self.copy_btn.setEnabled(self.selected_online() is not None)
        self.detail_btn.setEnabled(self.selected_online() is not None)

    def _ready(self):
        if not self.ctx.mm:
            self.choose_game_requested.emit()
        if not self.ctx.mm or not self._can_modify():
            return False
        if self.ctx.mm.transaction.journal.exists():
            QMessageBox.warning(self, '请先恢复', '上次文件操作未完成，请先恢复。')
            return False
        return True

    def share_selected(self):
        path = self.selected_local()
        if not path or not self._ready():
            return
        name, ok = QInputDialog.getText(self, '分享战役', '战役名称：', text=path.stem.strip() or '我的战团')
        if not ok or not name.strip():
            return
        note, ok = QInputDialog.getMultiLineText(self, '战役介绍', '介绍战役进度、玩法及使用注意事项（选填）：')
        if not ok:
            return
        try:
            origin = self.profile_origin()
        except ValueError as error:
            QMessageBox.warning(self, '网站地址无效', str(error))
            return
        manager = self.ctx.mm
        version = self.ctx.game.version or ''
        def prepare(progress):
            prepared = shared_saves.prepare_share(manager, path, name, note, version, progress)
            return prepared, shared_saves.negotiate(origin, prepared)
        def confirm(result):
            prepared, plan = result
            manifest = prepared['manifest']
            details = '游戏 ' + manifest['game_version'] + '\nDLC：' + ('、'.join(manifest['dlcs']) or '无') + '\n\n'
            details += '\n'.join(('需要上传：' if row['status'] == 'missing' else '网站已有：') + row['file_name'] for row in plan['files']) or '未启用 MOD'
            details += '\n\n' + '\n'.join(prepared['warnings'])
            missing = {r['sha256'] for r in plan['files'] if r['status'] == 'missing'}
            sizes = {m['sha256']: m['size'] for m in manifest['mods']}
            size = sum(sizes[sha] for sha in missing) + (manifest['save']['size'] if plan['save']['status'] == 'missing' else 0)
            summary = (f"「{manifest['name']}」连同 {len(manifest['mods'])} 个 MOD 将公开分享，需上传 {size/1024**2:.1f} MB。\n"
                       '请确认下面列出的当前 MOD 就是这份战役使用的组合。存档中无法可靠核对后来更换过的 MOD。')
            if preview_dialog(self, '核对存档与 MOD', summary, details, '确认组合，上传并分享') and self._ready() and self.ctx.mm is manager:
                self.runner._run('分享存档', lambda progress: shared_saves.publish_share(origin, prepared, progress), self._shared)
        self.runner._run('核对存档与配套 MOD', prepare, confirm)

    def _shared(self, link):
        QApplication.clipboard().setText(link)
        self.status_label.setText('存档与 MOD 已分享，链接已复制：' + link)
        QMessageBox.information(self, '分享成功', '存档与配套 MOD 已出现在存档广场。\n分享链接已复制：\n' + link)

    def _source_changed(self, *_):
        self.catalog_origin, self.rows = '', []
        self.online_table.setRowCount(0)
        self.page_label.setText('网站来源已改变，请重新读取')
        self.show_online()

    def load_catalog(self, page=1):
        if self.ctx.management_busy:
            return
        try:
            origin = self.profile_origin()
        except ValueError as error:
            QMessageBox.warning(self, '网站地址无效', str(error))
            return
        query = self.search.text()
        def loaded(result):
            if self.profile_origin() != origin:
                return
            self.rows, self.catalog_origin = result['items'], origin
            self.catalog_page, self.catalog_pages = result['page'], result['pages']
            self.online_table.setRowCount(len(self.rows))
            from PySide6.QtWidgets import QTableWidgetItem
            for row, item in enumerate(self.rows):
                for col, value in enumerate((item['name'], str(item['mod_count']), f"{item['total_size']/1024**2:.1f} MB", item['game_version'])):
                    self.online_table.setItem(row, col, QTableWidgetItem(value))
            self.page_label.setText(f"{self.catalog_page} / {self.catalog_pages} 页 · 共 {result['total']} 份战役")
            if self.rows:
                self.online_table.selectRow(0)
            self.show_online()
        self.runner._run('读取存档广场', lambda progress: shared_saves.fetch_saves(origin, query, page), loaded)

    def show_online(self):
        row = self.selected_online()
        self.details.setPlainText((row['name'] + '\n\n' + row['note'] + '\n\nDLC：' + ('、'.join(row['dlcs']) or '无'))
                                  if row else '选择一份战役查看介绍，再预览存档与 MOD 的恢复。')
        self.update_controls()

    def copy_link(self):
        row = self.selected_online()
        if row:
            QApplication.clipboard().setText(self.catalog_origin + row['page_path'])

    def open_detail(self):
        row = self.selected_online()
        if row:
            QDesktopServices.openUrl(QUrl(self.catalog_origin + row['page_path']))

    def restore_selected(self):
        row = self.selected_online()
        if row:
            self.import_link(row['id'], self.catalog_origin)

    def import_link(self, value=None, origin=None):
        if not self._ready():
            return
        if value is None:
            value, ok = QInputDialog.getText(self, '恢复共享存档', '粘贴存档广场链接或分享编号：')
            if not ok or not value.strip():
                return
        try:
            origin = site_origin(origin or self.profile_origin())
            identity = shared_saves.save_identity(value, origin)
        except ValueError as error:
            QMessageBox.warning(self, '存档链接无效', str(error))
            return
        manager, directory, version = self.ctx.mm, self.directory(), self.ctx.game.version
        def read(progress):
            manifest = shared_saves.fetch_save(origin, identity)
            return manifest, shared_saves.preview_restore(manager, manifest, directory, version)
        def confirm(result):
            manifest, expected = result
            plan = expected['mods']
            details = '\n'.join(m['file_name'] + (' · ' + m['version'] if m['version'] else '') for m in manifest['mods']) or '未启用 MOD'
            details += '\n\n将停用并备份：\n' + ('\n'.join(plan['disable']) or '无')
            summary = (f"恢复「{manifest['name']}」及 {len(manifest['mods'])} 个配套 MOD，需下载 {len(plan['download'])} 个 MOD。\n"
                       f"存档另存到：{expected['target']}\n已有存档保留，其他 MOD 停用并备份。游戏版本和 DLC 已核对。")
            if (preview_dialog(self, '恢复存档前核对', summary, details, '下载并恢复存档与 MOD')
                    and self._ready() and self.ctx.mm is manager and self.directory() == directory):
                self.runner._run('恢复存档与 MOD', lambda progress: shared_saves.restore(manager, origin, identity, manifest,
                    expected=expected, game_version=version, progress=progress), self._restored)
        self.runner._run('读取共享存档与核对游戏环境', read, confirm)

    def _restored(self, result):
        self.ctx.data_changed.emit()
        self.refresh()
        self.status_label.setText('存档与整套 MOD 已恢复：' + result['save_path'])
        QMessageBox.information(self, '恢复完成', '可启动游戏，在加载战役中选择这份存档。\n' + result['save_path'] + '\n\n原 MOD 备份：' + result['backup'])

    def recover(self):
        if not self.ctx.mm or self.ctx.management_busy or self.ctx.game_session.occupied:
            return
        self.runner._run('恢复上次存档导入', lambda progress: shared_saves.recover(self.ctx.mm, self.directory()),
                         lambda _: self._recovered())

    def _recovered(self):
        self.ctx.data_changed.emit()
        self.refresh()
        self.status_label.setText('上次未完成的导入已恢复，原有存档和 MOD 已保留。')

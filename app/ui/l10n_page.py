"""Independent localization workshop: bundled translations, local build and install."""
from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFileDialog, QGroupBox, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QMessageBox, QPlainTextEdit, QPushButton, QTabWidget, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)
from core import l10n
from core.l10n_tokens import validate_translation
from core.place_names import load_policy, original_names
from .app_context import AppContext
from .workers import Worker
from .theme import GREEN, MUTED, style_button, style_table
from .localization_manager import LocalizationManager


class WorkshopTabs(QTabWidget):
    """The hidden translation editor must not push management actions offscreen."""

    def __init__(self):
        super().__init__()
        self.currentChanged.connect(self.updateGeometry)

    def minimumSizeHint(self):
        size = super().minimumSizeHint()
        if self.currentWidget() is not None:
            heights = [self.widget(i).minimumSizeHint().height() for i in range(self.count())]
            chrome = max(0, size.height() - max(heights))
            size.setHeight(self.currentWidget().minimumSizeHint().height() + chrome)
        return size

    def heightForWidth(self, width):
        page = self.currentWidget()
        if page is None:
            return super().heightForWidth(width)
        # QTabWidget normally uses the largest height-for-width of every tab.
        # Keep the active controls' font-aware preferred heights; the management
        # table has its own smaller minimum and can scroll independently.
        minimum = self.minimumSizeHint()
        chrome = minimum.height() - page.minimumSizeHint().height()
        page_height = page.layout().totalHeightForWidth(max(0, width - 4))
        return max(minimum.height(), page_height + chrome)


class L10nPage(QWidget):
    def __init__(self, ctx: AppContext) -> None:
        super().__init__()
        self.ctx = ctx
        self.meta, self.entries = l10n.load_catalog()
        full = l10n.load_full_catalog()
        self.geographic_names = original_names(full, load_policy(full)) if full else set()
        self.overrides = self._load_overrides()
        self._loading = False
        self._busy = False
        self._page = 0
        self._page_size = 200
        self._rows = []
        shell = QVBoxLayout(self)
        self.sections = WorkshopTabs()
        self.management = LocalizationManager(ctx, self.open_editor)
        self.ctx.game_session.changed.connect(lambda: self._set_busy(self._busy))
        self.sections.addTab(self.management, '当前汉化与切换')
        editor_page = QWidget()
        self.sections.addTab(editor_page, '译文编辑与制作')
        self.sections.setTabToolTip(1, '高级制作工具；查看当前汉化和日常启动请使用第一个页签')
        shell.addWidget(self.sections)
        root = QVBoxLayout(editor_page)
        info = QGroupBox('汉化制作工具 · 内置译文版本 ' + l10n.VERSION)
        info_layout = QVBoxLayout(info)
        top = QHBoxLayout()
        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        top.addWidget(self.status_label, 1)
        self.export_btn = QPushButton('制作并导出 ZIP')
        style_button(self.export_btn, 'save')
        self.build_btn = QPushButton('制作并预览切换')
        self.build_btn.setToolTip('用此页译文制作新包；完成后仍需到管理页确认应用，当前汉化才会改变')
        style_button(self.build_btn, 'download', primary=True)
        self.uninstall_btn = QPushButton('卸载本汉化')
        style_button(self.uninstall_btn, 'close')
        self.export_btn.clicked.connect(self.export_package)
        self.build_btn.clicked.connect(self.build_and_install)
        self.uninstall_btn.clicked.connect(self.uninstall)
        top.addWidget(self.export_btn)
        top.addWidget(self.build_btn)
        top.addWidget(self.uninstall_btn)
        self.launch_btn = QPushButton('以中文启动')
        style_button(self.launch_btn, 'play')
        self.launch_btn.clicked.connect(self.launch_chinese)
        top.addWidget(self.launch_btn)
        self.uninstall_btn.hide()
        self.launch_btn.hide()
        info_layout.addLayout(top)
        self.scope_label = QLabel('仅在首次制作、修改译文或修复汉化包时使用此页，日常启动无需制作。译文范围：' + self.meta['scope'] + '。新版独立汉化应用后，从 Steam 或本软件启动均显示中文地名。')
        self.scope_label.setObjectName('muted')
        self.scope_label.setWordWrap(True)
        info_layout.addWidget(self.scope_label)
        self.game_path_label = QLabel()
        self.game_path_label.setObjectName('muted')
        self.game_path_label.setWordWrap(True)
        self.game_path_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        info_layout.addWidget(self.game_path_label)
        root.addWidget(info)
        editor = QGroupBox('独立译文目录')
        editor_layout = QVBoxLayout(editor)
        bar = QHBoxLayout()
        self.category = QComboBox()
        self.category.addItems(['全部类别'] + list(self.meta['groups']))
        self.category.currentTextChanged.connect(self._filter)
        bar.addWidget(self.category)
        self.search = QLineEdit()
        self.search.setPlaceholderText('搜索英文原文或中文译文…')
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self._filter)
        bar.addWidget(self.search, 1)
        self.reset_btn = QPushButton('恢复所选默认译文')
        style_button(self.reset_btn, 'refresh')
        self.reset_btn.clicked.connect(self.reset_selected)
        bar.addWidget(self.reset_btn)
        editor_layout.addLayout(bar)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(['类别', '英文原文', '中文译文', '状态'])
        style_table(self.table)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.DoubleClicked | QTableWidget.EditKeyPressed)
        self.table.setColumnWidth(0, 126)
        self.table.setColumnWidth(3, 80)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.itemChanged.connect(self._on_edit)
        self.table.cellDoubleClicked.connect(self._edit_long_text)
        editor_layout.addWidget(self.table, 1)
        self.count_label = QLabel()
        self.count_label.setObjectName('muted')
        pager = QHBoxLayout()
        pager.addWidget(self.count_label, 1)
        self.prev_page = QPushButton('上一页')
        self.next_page = QPushButton('下一页')
        self.prev_page.clicked.connect(lambda: self._turn_page(-1))
        self.next_page.clicked.connect(lambda: self._turn_page(1))
        pager.addWidget(self.prev_page)
        pager.addWidget(self.next_page)
        editor_layout.addLayout(pager)
        root.addWidget(editor, 1)
        self._filter()
        self.refresh_status()

    def _overrides_path(self) -> Path:
        # Keep the old third-party field overrides separate; they cannot be imported here.
        return self.ctx.settings.path.parent / 'l10n_independent_overrides.json'

    def _load_overrides(self) -> dict[str, str]:
        try:
            data = json.loads(self._overrides_path().read_text(encoding='utf-8'))
        except (OSError, ValueError):
            return {}
        known = {entry.source for entry in self.entries}
        return {k: v for k, v in data.items() if k in known and isinstance(v, str) and v.strip()} if isinstance(data, dict) else {}

    def _save_overrides(self) -> None:
        path = self._overrides_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        pending = path.with_suffix('.tmp')
        pending.write_text(json.dumps(self.overrides, ensure_ascii=False, indent=2), encoding='utf-8')
        pending.replace(path)

    def _filter(self) -> None:
        keyword = self.search.text().strip().casefold()
        category = self.category.currentText()
        self._rows = [entry for entry in self.entries
            if (category == '全部类别' or entry.category == category)
            and (not keyword or keyword in entry.source.casefold()
                or keyword in self.overrides.get(entry.source, entry.value).casefold())]
        self._page = 0
        self._render_page()

    def _turn_page(self, delta: int) -> None:
        pages = max(1, (len(self._rows) + self._page_size - 1) // self._page_size)
        self._page = max(0, min(pages - 1, self._page + delta))
        self._render_page()

    @staticmethod
    def _entry_state(entry) -> str:
        return '已校对' if entry.status == 'reviewed' else '待校对'

    def _render_page(self) -> None:
        self._loading = True
        try:
            rows = self._rows[self._page * self._page_size:(self._page + 1) * self._page_size]
            self.table.setRowCount(len(rows))
            for i, entry in enumerate(rows):
                place = entry.source in self.geographic_names
                for col, text in enumerate((entry.category, entry.source,
                        self.overrides.get(entry.source, entry.value),
                        '已自定义' if entry.source in self.overrides else self._entry_state(entry))):
                    item = QTableWidgetItem(text)
                    item.setData(Qt.UserRole, entry.source)
                    item.setToolTip(text)
                    if col != 2 or max(len(entry.source), len(entry.value)) > 150:
                        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                    if col in (1, 2):
                        item.setToolTip('双击展开长文本' if max(len(entry.source), len(entry.value)) > 150 else text)
                    if place and col == 2:
                        item.setToolTip(text + '\n此地名译文仅在从 BBMOD 启动时显示；直接启动仍显示英文。')
                    if col == 3:
                        item.setForeground(QColor(GREEN if entry.source in self.overrides else MUTED))
                    self.table.setItem(i, col, item)
            self._update_count()
        finally:
            self._loading = False

    def _update_count(self) -> None:
        pages = max(1, (len(self._rows) + self._page_size - 1) // self._page_size)
        self.count_label.setText(f'共 {len(self.entries)} 条  ·  筛选 {len(self._rows)} 条  ·  第 {self._page + 1}/{pages} 页  ·  自定义 {len(self.overrides)} 条')
        self.prev_page.setEnabled(self._page > 0)
        self.next_page.setEnabled(self._page + 1 < pages)

    def _edit_long_text(self, row: int, column: int) -> None:
        item = self.table.item(row, 2)
        if item is None:
            return
        source = item.data(Qt.UserRole)
        if max(len(source), len(item.text())) <= 150:
            return
        dialog = QDialog(self)
        dialog.setWindowTitle('编辑剧情译文')
        dialog.resize(960, 680)
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel('英文原文'))
        original = QPlainTextEdit(source)
        original.setReadOnly(True)
        layout.addWidget(original, 1)
        layout.addWidget(QLabel('中文译文 · 请保留变量、数字和排版标记'))
        translated = QPlainTextEdit(item.text())
        layout.addWidget(translated, 1)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Save).setText('保存译文')
        buttons.button(QDialogButtonBox.Cancel).setText('取消')
        def save():
            problems = validate_translation(source, translated.toPlainText())
            if problems:
                QMessageBox.warning(dialog, '请核对译文', '\n'.join(problems))
                return
            item.setText(translated.toPlainText())
            dialog.accept()
        buttons.accepted.connect(save)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        dialog.exec()

    def _on_edit(self, item: QTableWidgetItem) -> None:
        if self._loading or item.column() != 2:
            return
        source = item.data(Qt.UserRole)
        entry = next((entry for entry in self.entries if entry.source == source), None)
        if entry is None:
            return
        value = item.text()
        problems = validate_translation(source, value)
        if problems:
            QMessageBox.warning(self, '请核对译文', '\n'.join(problems))
            self._render_page()
            return
        previous = dict(self.overrides)
        if not value.strip() or value == entry.value:
            self.overrides.pop(source, None)
            value = entry.value
        else:
            self.overrides[source] = value
        try:
            self._save_overrides()
        except OSError as error:
            self.overrides = previous
            QMessageBox.warning(self, '保存失败', str(error))
            self._filter()
            return
        self._loading = True
        item.setText(value)
        state = self.table.item(item.row(), 3)
        state.setText('已自定义' if source in self.overrides else self._entry_state(entry))
        state.setForeground(QColor(GREEN if source in self.overrides else MUTED))
        self._loading = False
        self._update_count()

    def reset_selected(self) -> None:
        for index in {index.row() for index in self.table.selectedIndexes()}:
            item = self.table.item(index, 2)
            source = item.data(Qt.UserRole)
            entry = next(entry for entry in self.entries if entry.source == source)
            item.setText(entry.value)

    def refresh_status(self) -> None:
        game = self.ctx.game
        installed = l10n.find_localization_zips(game.data_dir) if game else []
        manifests = [l10n.package_manifest(path) or {} for path in installed]
        self.game_path_label.setText('当前游戏目录：' + str(game.root) if game else '当前尚未指定游戏目录')
        if not game:
            self.status_label.setText('这里编辑内置译文；查看当前使用的汉化，请先选择游戏目录并返回“当前汉化与切换”。')
        elif installed:
            if any(m.get('translation_stage') == 'partial_preview' for m in manifests):
                state = '独立汉化开发测试版已安装 · 仍有缺译'
            elif any(m.get('full_text_files', 0) for m in manifests):
                reviewed = all(m.get('editorial_review', {}).get('status') == 'complete' for m in manifests)
                state = ('独立汉化已安装 · 非地名译文已全部精修' if reviewed
                         else '独立正文汉化已安装 · 剧情初稿待校对')
            else:
                state = '独立菜单汉化已安装 · 正文汉化尚未安装'
            self.status_label.setText(state + '。日常使用无需重新制作；修改译文后才需生成新包。')
        else:
            fox = any('狐狸' in path.name for path in game.data_dir.glob('*.zip'))
            self.status_label.setText('当前检测到其他汉化文件；可继续使用。此页仅制作 BBMOD 汉化，不会编辑其他汉化。' if fox else
                                      f'内置 {len(self.entries)} 条译文可供制作。只使用已有汉化时，无需操作此页。')
        self._set_busy(self._busy)
        self.uninstall_btn.setEnabled(bool(installed) and not self._busy and not self.ctx.game_session.occupied)
        native = any(m.get('requires_bbmod_launcher') or m.get('uses_bbmod_map_font') for m in manifests)
        self.launch_btn.setEnabled(bool(installed) and not self._busy and not getattr(self.ctx, 'seedgen_active', False)
                                   and not self.ctx.game_session.occupied)
        self.launch_btn.setToolTip('启动当前目录的游戏。新版中文地名由汉化包直接显示。')
        if native:
            self.status_label.setText('当前 BBMOD 汉化依赖旧启动组件，需换用新版包；可导入现成包，或在此制作并确认应用。')
            self.launch_btn.setToolTip('当前包依赖旧启动器，请先换用新版汉化包。')
        if getattr(self.ctx, 'seedgen_active', False):
            self.build_btn.setEnabled(False)
            self.uninstall_btn.setEnabled(False)
        self.management.refresh()

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        locked = busy or getattr(self.ctx, 'management_busy', False) or getattr(self.ctx, 'seedgen_active', False)
        self.export_btn.setEnabled(bool(self.ctx.game) and not locked)
        self.build_btn.setEnabled(bool(self.ctx.game) and not locked and not self.ctx.game_session.occupied)
        self.uninstall_btn.setEnabled(bool(self.ctx.game) and not locked and not self.ctx.game_session.occupied)
        if locked or self.ctx.game_session.occupied:
            self.launch_btn.setEnabled(False)

    def launch_chinese(self) -> None:
        self.sections.setCurrentIndex(0)
        self.management.launch_current()

    def open_editor(self) -> None:
        self.sections.setCurrentIndex(1)

    def _launch_failed(self, error: str) -> None:
        self._set_busy(False)
        self.refresh_status()
        QMessageBox.warning(self, '中文启动未完成', error)

    def export_package(self) -> None:
        if not self.ctx.game:
            return
        path, _ = QFileDialog.getSaveFileName(self, '导出独立汉化包', l10n.PACKAGE_NAME, 'ZIP (*.zip)')
        if path:
            self._build(Path(path), install=False)

    def build_and_install(self) -> None:
        if self.ctx.game:
            output = self.ctx.settings.path.parent / 'packages' / l10n.PACKAGE_NAME
            self._build(output, install=True)

    def _build(self, output: Path, install: bool) -> None:
        if self._busy or getattr(self.ctx, 'management_busy', False) or getattr(self.ctx, 'seedgen_active', False):
            return
        if install and self.ctx.game_session.occupied:
            return
        game_root, manager = self.ctx.game.root, self.ctx.mm
        overrides = dict(self.overrides)
        def build():
            result = l10n.build_localization(game_root, overrides, output)
            if install:
                from core.localization_profiles import LocalizationProfiles
                result['profile_id'] = LocalizationProfiles(game_root).register('BBMOD 独立汉化', [output], builtin=True)
            return result
        self._set_busy(True)
        if hasattr(self.ctx, 'set_management_busy'):
            self.ctx.set_management_busy(True)
        self.status_label.setText('正在构建独立汉化包…')
        self._build_worker = Worker(build, self)
        self._build_worker.done.connect(lambda result: self._after_build(result, install))
        self._build_worker.failed.connect(self._build_failed)
        self._build_worker.start()

    def _after_build(self, result: dict, installed: bool) -> None:
        self._set_busy(False)
        if hasattr(self.ctx, 'set_management_busy'):
            self.ctx.set_management_busy(False)
        self.refresh_status()
        if installed:
            self.sections.setCurrentIndex(0)
            self.management.select_profile(result['profile_id'])
            self.ctx.data_changed.emit()
        pending = bool(installed and self.management.plan and self.management.plan.changed)
        title = ('汉化包已准备，尚未切换' if pending else '汉化包已准备，当前配置无需改变') if installed else '汉化包已导出'
        guidance = '\n当前汉化保持不变；需要换用此包时，再核对切换预览并应用。' if pending else ''
        if installed and self.management.plan is None:
            title = '汉化包已准备，请查看方案提示'
            guidance = '\n当前汉化保持不变，请回到管理页查看提示。'
        QMessageBox.information(self, title,
            f"{result['out']}\n{result['entry_count']} 条独立译文。\n译文范围：{result['scope']}。" + guidance)

    def _build_failed(self, error: str) -> None:
        self._set_busy(False)
        if hasattr(self.ctx, 'set_management_busy'):
            self.ctx.set_management_busy(False)
        self.refresh_status()
        QMessageBox.warning(self, '构建或安装未完成', error)

    def uninstall(self) -> None:
        if not self.ctx.game:
            return
        from core.game import is_game_running
        if is_game_running():
            QMessageBox.information(self, '游戏运行中', '请先关闭游戏，再卸载汉化。')
            return
        for path in l10n.find_localization_zips(self.ctx.game.data_dir):
            try:
                self.ctx.mm.disable(path.name)
            except OSError as error:
                QMessageBox.warning(self, '卸载未完成', str(error))
        self.refresh_status()
        self.ctx.data_changed.emit()

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
        self.sections = QTabWidget()
        self.management = LocalizationManager(ctx, self.build_and_install)
        self.sections.addTab(self.management, '汉化管理与启动')
        editor_page = QWidget()
        self.sections.addTab(editor_page, '独立译文编辑')
        shell.addWidget(self.sections)
        root = QVBoxLayout(editor_page)
        info = QGroupBox('BBMOD 独立汉化  /  ' + l10n.VERSION)
        info_layout = QVBoxLayout(info)
        top = QHBoxLayout()
        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        top.addWidget(self.status_label, 1)
        self.export_btn = QPushButton('导出汉化包')
        style_button(self.export_btn, 'save')
        self.build_btn = QPushButton('生成并选择此汉化')
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
        self.scope_label = QLabel('当前范围：' + self.meta['scope'] + '。从 BBMOD 启动时，地图、任务和对话显示中文地名；直接启动时显示英文。旧存档中已保存的中文名称不会自动恢复。')
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
            self.status_label.setText('译文目录已就绪。指定游戏目录后即可构建汉化包。')
        elif installed:
            if any(m.get('translation_stage') == 'partial_preview' for m in manifests):
                state = '独立汉化开发测试版已安装 · 仍有缺译'
            elif any(m.get('full_text_files', 0) for m in manifests):
                reviewed = all(m.get('editorial_review', {}).get('status') == 'complete' for m in manifests)
                state = ('独立汉化已安装 · 非地名译文已全部精修' if reviewed
                         else '独立正文汉化已安装 · 剧情初稿待校对')
            else:
                state = '独立菜单汉化已安装 · 正文汉化尚未安装'
            self.status_label.setText(state)
        else:
            fox = any('狐狸' in path.name for path in game.data_dir.glob('*.zip'))
            self.status_label.setText('此目录仍装有狐狸汉化 · 尚未安装 BBMOD 独立汉化' if fox else f'独立词库已就绪 · {len(self.entries)} 条译文 · 当前尚未安装')
        self._set_busy(self._busy)
        self.uninstall_btn.setEnabled(bool(installed) and not self._busy)
        native = any(m.get('requires_bbmod_launcher') or m.get('uses_bbmod_map_font') for m in manifests)
        self.launch_btn.setEnabled(native and not self._busy and not getattr(self.ctx, 'seedgen_active', False))
        self.launch_btn.setToolTip('安装完整汉化后，由此启动游戏并加载中文地图字体。')
        if native:
            from core.native_font import missing_components
            missing = missing_components()
            if missing:
                self.status_label.setText(self.status_label.text() + ' · 中文地名启动组件缺失：' + '、'.join(missing))
                self.launch_btn.setToolTip('组件缺失，暂不能以中文地名启动。点击可查看缺失位置和处理说明。')
        if getattr(self.ctx, 'seedgen_active', False):
            self.build_btn.setEnabled(False)
            self.uninstall_btn.setEnabled(False)
        self.management.refresh()

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        locked = busy or getattr(self.ctx, 'management_busy', False) or getattr(self.ctx, 'seedgen_active', False)
        for button in (self.build_btn, self.export_btn):
            button.setEnabled(bool(self.ctx.game) and not locked)
        self.uninstall_btn.setEnabled(bool(self.ctx.game) and not busy)
        if busy:
            self.launch_btn.setEnabled(False)

    def launch_chinese(self) -> None:
        self.sections.setCurrentIndex(0)
        self.management.launch_current()

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
        QMessageBox.information(self, '汉化已生成，请核对切换预览后应用' if installed else '汉化包已导出',
            f"{result['out']}\n{result['entry_count']} 条独立译文。\n当前范围：{result['scope']}。")

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

"""Choose opaque localization packages, review the switch, and start the game."""
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFileDialog, QGroupBox, QHBoxLayout,
    QHeaderView, QInputDialog, QLabel, QListWidget, QListWidgetItem, QMessageBox,
    QPlainTextEdit, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from core.localization_profiles import BUILTIN, CURRENT, NONE, LocalizationProfiles
from core import l10n
from .theme import style_button, style_table
from .workers import Worker


class LocalizationFiles(QTableWidget):
    def sizeHint(self):
        size = super().sizeHint()
        size.setHeight(self.minimumHeight())
        return size


class LocalizationManager(QWidget):
    review_requested = Signal()
    controls_changed = Signal()

    def __init__(self, ctx, open_editor):
        super().__init__()
        self.setObjectName('localizationManager')
        self.ctx, self._busy, self._root = ctx, False, None
        self.backend, self.plan = None, None
        self._active = []
        self._legacy = False
        self._mixed = False
        self.session = ctx.game_session
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)
        box = QGroupBox('当前启用的汉化')
        box.setObjectName('localizationControls')
        controls = QVBoxLayout(box)
        controls.setContentsMargins(8, 8, 8, 8)
        controls.setSpacing(4)
        self.current_name = QLabel()
        self.current_name.setObjectName('localizationCurrentName')
        self.current_name.setTextFormat(Qt.PlainText)
        self.current_name.setWordWrap(True)
        row = QHBoxLayout()
        row.addWidget(self.current_name, 1)
        self.refresh_btn = QPushButton('重新检测')
        style_button(self.refresh_btn, 'refresh')
        self.refresh_btn.clicked.connect(self.refresh)
        row.addWidget(self.refresh_btn)
        controls.addLayout(row)
        self.summary = QLabel()
        self.summary.setTextFormat(Qt.PlainText)
        self.summary.setWordWrap(True)
        controls.addWidget(self.summary)
        layout.addWidget(box)
        row = QHBoxLayout()
        row.addWidget(QLabel('切换方案（可选）'))
        self.choice = QComboBox()
        self.choice.setMinimumWidth(200)
        row.addWidget(self.choice, 1)
        self.keep_current_btn = QPushButton('取消切换，沿用当前')
        style_button(self.keep_current_btn, 'refresh')
        self.keep_current_btn.clicked.connect(lambda: self.choice.setCurrentIndex(self.choice.findData(CURRENT)))
        row.addWidget(self.keep_current_btn)
        layout.addLayout(row)
        self.advanced_toggle = QPushButton('添加方案 / 制作汉化（高级）')
        self.advanced_toggle.setCheckable(True)
        style_button(self.advanced_toggle, 'settings')
        self.advanced_toggle.setToolTip('仅在添加其他汉化或制作自定义汉化包时使用')
        layout.addWidget(self.advanced_toggle, 0, Qt.AlignLeft)
        self.advanced_panel = QWidget()
        advanced = QVBoxLayout(self.advanced_panel)
        advanced.setContentsMargins(0, 0, 0, 0)
        advanced.setSpacing(4)
        row = QHBoxLayout()
        self.import_btn = QPushButton('导入汉化包')
        self.existing_btn = QPushButton('收录已安装汉化')
        self.builtin_btn = QPushButton('打开汉化制作工具')
        for button, glyph in ((self.import_btn, 'folder'), (self.existing_btn, 'book'), (self.builtin_btn, 'download')):
            style_button(button, glyph)
            row.addWidget(button)
        self.import_btn.clicked.connect(self.import_packages)
        self.existing_btn.clicked.connect(self.add_existing)
        self.builtin_btn.clicked.connect(open_editor)
        self.existing_btn.setToolTip('将已有文件保存为可切换的方案；不会重新生成译文或立即切换汉化')
        self.builtin_btn.setToolTip('进入译文编辑页，只有明确点击制作按钮才会生成新包')
        advanced.addLayout(row)
        note = QLabel('已有可用汉化无需重新制作。只有首次制作、修改译文或修复汉化包时，才需使用制作工具。导入或制作不会立即替换当前汉化，需要更换时再确认应用。')
        note.setObjectName('muted')
        note.setWordWrap(True)
        advanced.addWidget(note)
        layout.addWidget(self.advanced_panel)
        self.advanced_panel.hide()
        self.advanced_toggle.toggled.connect(self.advanced_panel.setVisible)
        self.table = LocalizationFiles(0, 3)
        self.table.setHorizontalHeaderLabels(['是否启用', '汉化文件', '来源'])
        style_table(self.table)
        self.table.verticalHeader().setDefaultSectionSize(34)
        self.table.setMinimumHeight(110)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setColumnWidth(0, 80)
        self.table.setColumnWidth(2, 180)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        layout.addWidget(self.table, 1)
        self.preview_title = QLabel('方案说明')
        layout.addWidget(self.preview_title)
        self.preview = QPlainTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setMaximumHeight(80)
        layout.addWidget(self.preview)
        row = QHBoxLayout()
        self.recover_btn = QPushButton('恢复上次切换')
        style_button(self.recover_btn, 'refresh')
        self.recover_btn.clicked.connect(self.recover)
        row.addWidget(self.recover_btn)
        row.addStretch()
        self.apply_btn = QPushButton('应用方案')
        style_button(self.apply_btn, 'check')
        self.apply_btn.clicked.connect(lambda: self.apply(False))
        self.start_btn = QPushButton('应用并启动')
        style_button(self.start_btn, 'play', primary=True)
        self.start_btn.clicked.connect(lambda: self.apply(True))
        row.addWidget(self.apply_btn)
        row.addWidget(self.start_btn)
        layout.addLayout(row)
        self.choice.currentIndexChanged.connect(self._selection_changed)
        self.session.changed.connect(self.update_plan)
        self.refresh()

    def refresh(self):
        game = self.ctx.game
        key = str(game.root.resolve()) if game else None
        selected = self.choice.currentData() if key == self._root else self.ctx.settings.get('localization_choices', {}).get(key, CURRENT)
        self._root = key
        self.plan = None
        self._active = []
        self._legacy = self._mixed = False
        self.choice.blockSignals(True)
        self.choice.clear()
        self.choice.addItem('保持当前汉化（不改动）', CURRENT)
        self.choice.addItem('BBMOD 独立汉化（尚未制作）', BUILTIN)
        self.choice.addItem('停用已识别的汉化', NONE)
        self.table.setRowCount(0)
        try:
            self.backend = LocalizationProfiles(game.root) if game else None
            profiles = self.backend.profiles() if self.backend else {}
            for profile_id, profile in profiles.items():
                if profile_id != BUILTIN:
                    self.choice.addItem(profile['name'], profile_id)
            rows = [item for item in self.backend.inventory() if item['candidate'] or item['managed']] if self.backend else []
            self.table.setRowCount(len(rows))
            for i, item in enumerate(rows):
                labels = ['当前启用' if item['enabled'] else '已停用', item['name'],
                          'BBMOD 独立制作' if item['own'] else ('已加入方案' if item['managed'] else '待归类 · 按文件名识别')]
                for column, label in enumerate(labels):
                    cell = QTableWidgetItem(label)
                    cell.setToolTip(str(item['path']))
                    self.table.setItem(i, column, cell)
            self._active = [item for item in rows if item['enabled']]
            own = [item for item in self._active if item['own']]
            manifests = [l10n.package_manifest(item['path']) or {} for item in own]
            self._legacy = any(m.get('requires_bbmod_launcher') or m.get('uses_bbmod_map_font') for m in manifests)
            self._mixed = bool(own and len(self._active) != 1)
            if len(own) == 1 and not self._mixed:
                version = manifests[0].get('version')
                self.current_name.setText('BBMOD 独立汉化' + (f' {version}' if version else '') + ' · 已启用')
            elif self._active:
                self.current_name.setText('已启用：' + '、'.join(item['name'] for item in self._active))
            else:
                self.current_name.setText('未检测到已启用的汉化包' if game else '尚未选择游戏目录')
            self.current_name.setToolTip('\n'.join(str(item['path']) for item in self._active))
            if BUILTIN in profiles:
                self.choice.setItemText(self.choice.findData(BUILTIN), 'BBMOD 独立汉化（已保存方案）')
            elif own:
                self.choice.setItemText(self.choice.findData(BUILTIN), 'BBMOD 独立汉化（已安装，未存方案）')
            index = self.choice.findData(selected)
            self.choice.setCurrentIndex(max(0, index))
        except Exception as error:
            self.backend = None
            self.current_name.setText('暂时无法读取当前汉化')
            self.summary.setText(str(error))
        finally:
            self.choice.blockSignals(False)
        self.update_plan()

    def _selection_changed(self):
        if self._root:
            choices = dict(self.ctx.settings.get('localization_choices', {}))
            choices[self._root] = self.choice.currentData()
            try:
                self.ctx.settings.set('localization_choices', choices)
            except OSError as error:
                QMessageBox.warning(self, '方案偏好未保存', str(error))
        self.update_plan()

    def select_profile(self, profile_id):
        self.refresh()
        self.choice.setCurrentIndex(self.choice.findData(profile_id))
        self.update_plan()

    def update_plan(self):
        self.plan = None
        self.preview_title.setText('方案说明')
        try:
            if not self.backend:
                self.preview.setPlainText('指定游戏目录后，即可选择汉化和启动游戏。')
            elif self.choice.currentData() == BUILTIN and BUILTIN not in self.backend.profiles():
                if any(item['own'] for item in self._active):
                    self.preview.setPlainText('BBMOD 独立汉化已经启用，只是尚未保存为可切换方案。点击“取消切换，沿用当前”即可继续使用，无需重新生成。')
                else:
                    self.preview.setPlainText('尚无已保存的 BBMOD 汉化方案。继续使用现有汉化请“取消切换，沿用当前”；只有要改用 BBMOD 汉化时，才需导入现成包或进入高级制作工具。')
            else:
                self.plan = self.backend.plan(self.choice.currentData())
                self.preview_title.setText('切换预览 · 尚未应用，当前汉化保持不变' if self.plan.changed else
                                           '当前配置 · 无需重复应用')
                lines = []
                if self.plan.changed:
                    lines.append('准备切换为：' + self.choice.currentText() + '（尚未应用）')
                if self.plan.disable:
                    lines.append('将停用并保留：' + '、'.join(self.plan.disable))
                if self.plan.install:
                    lines.append('将启用：' + '、'.join(self.plan.install))
                if self.plan.conflicts:
                    lines.append('其中以下 MOD 覆盖了相同文件，也将停用：' + '、'.join(self.plan.conflicts))
                if not lines:
                    lines.append('没有待应用的切换，游戏将沿用当前已启用的汉化。' if self._active else
                                 '没有待应用的切换，保持当前游戏文件。')
                if self.plan.profile_id == NONE:
                    lines.append('此操作只停用 ZIP 汉化；直接修改过的游戏本体文件需另行还原。')
                if self.session.message:
                    lines.insert(0, self.session.message)
                self.preview.setPlainText('\n'.join(lines))
        except Exception as error:
            self.preview.setPlainText(str(error))
        if not self.ctx.game:
            self.summary.setText('请先在上方选择游戏目录，再查看该目录已启用的汉化。')
        elif self.backend:
            if self._mixed:
                message = '同时检测到 BBMOD 与其他汉化文件，请先核对并保留所需的一套。无需通过反复生成来处理。'
            elif self._legacy:
                message = '当前包依赖已停用的旧启动组件，需要换用新版汉化包；可导入现成包或在高级制作工具中制作。'
            elif not self._active:
                message = '这里只识别独立汉化包。若游戏原本已有中文，可保持当前配置；无需为了使用 BBMOD 软件而制作汉化。'
            elif self.plan is None or self.plan.changed:
                message = '上方汉化仍然启用，下方选择尚未应用。继续使用当前汉化无需重新生成。'
            else:
                message = '日常游玩直接启动游戏即可；更新 BBMOD 软件也无需重新生成或重新应用汉化。'
            self.summary.setText(message)
        self.update_controls()

    def update_controls(self):
        locked = (self._busy or getattr(self.ctx, 'management_busy', False)
                  or getattr(self.ctx, 'seedgen_active', False) or self.session.occupied)
        available = bool(self.backend) and not locked
        for button in (self.import_btn, self.existing_btn, self.builtin_btn, self.choice, self.refresh_btn):
            button.setEnabled(available)
        self.keep_current_btn.setVisible(self.choice.currentData() != CURRENT and
                                         (self.plan is None or self.plan.changed))
        self.keep_current_btn.setEnabled(available)
        self.recover_btn.setVisible(bool(self.backend and self.backend.journal.exists()))
        self.recover_btn.setEnabled(available)
        self.apply_btn.setEnabled(available and bool(self.plan and self.plan.changed))
        self.start_btn.setEnabled(available and self.plan is not None)
        self.start_btn.setText(self.session.button_text if self.session.occupied else
                              ('应用并启动' if self.plan and self.plan.changed else '启动游戏'))
        self.start_btn.setToolTip(self.session.message if self.session.occupied else
                                 '应用所列汉化变更并启动一次游戏' if self.plan and self.plan.changed else
                                 '启动当前目录的游戏，与上方启动按钮相同')
        self.controls_changed.emit()

    def _run(self, fn, done, *, launch=False):
        if (self._busy or getattr(self.ctx, 'management_busy', False)
                or getattr(self.ctx, 'seedgen_active', False) or self.session.occupied):
            return
        if launch and not self.session.begin_launch():
            return
        self._busy = True
        setter = getattr(self.ctx, 'set_management_busy', None)
        if setter:
            setter(True)
        self.update_controls()
        self.worker = Worker(fn, self)
        def finished(result=None, error=None):
            if launch:
                if error:
                    self.session.launch_failed(error)
                else:
                    self.session.launch_submitted()
            self._busy = False
            if setter:
                setter(False)
            self.refresh()
            self.ctx.data_changed.emit()
            if error:
                QMessageBox.warning(self, '操作未完成', error)
            else:
                done(result)
        self.worker.done.connect(lambda result: finished(result=result))
        self.worker.failed.connect(lambda error: finished(error=error))
        self.worker.start()

    def _register(self, paths):
        if not paths or not self.backend:
            return
        title, ok = QInputDialog.getText(self, '保存汉化方案', '方案名称', text=Path(paths[0]).stem)
        if ok and title.strip():
            backend = self.backend
            self._run(lambda: backend.register(title, [Path(path) for path in paths]), self.select_profile)

    def import_packages(self):
        paths, _ = QFileDialog.getOpenFileNames(self, '选择一个或多个实际汉化 ZIP', '', '汉化包 (*.zip)')
        self._register(paths)

    def add_existing(self):
        if not self.backend:
            return
        dialog = QDialog(self)
        dialog.setWindowTitle('将已有汉化归为一个方案')
        dialog.resize(690, 430)
        layout = QVBoxLayout(dialog)
        note = QLabel('勾选同一套汉化的本体和专用字体。通用框架与其他 MOD 请保留在军械库中管理。')
        note.setWordWrap(True)
        layout.addWidget(note)
        listing = QListWidget()
        for entry in self.backend.inventory():
            item = QListWidgetItem(('启用 · ' if entry['enabled'] else '停用 · ') + entry['name'])
            item.setData(Qt.UserRole, str(entry['path']))
            item.setCheckState(Qt.Unchecked)
            listing.addItem(item)
        layout.addWidget(listing)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText('添加到方案')
        buttons.button(QDialogButtonBox.Cancel).setText('取消')
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        if dialog.exec() == QDialog.Accepted:
            self._register([listing.item(i).data(Qt.UserRole) for i in range(listing.count())
                            if listing.item(i).checkState() == Qt.Checked])

    def apply(self, launch=False):
        if not self.backend or not self.plan:
            return
        backend, plan, game = self.backend, self.plan, self.ctx.game
        runtime = self.ctx.settings.path.parent / 'runtime'
        def work():
            backend.apply(plan)
            return backend.launch(game, runtime) if launch else None
        def done(result):
            if not launch:
                self.preview.setPlainText('汉化方案已应用，可使用上方“启动游戏”。')
        self._run(work, done, launch=launch)

    def launch_current(self):
        if (self._busy or getattr(self.ctx, 'management_busy', False)
                or getattr(self.ctx, 'seedgen_active', False) or self.session.occupied):
            return
        self.update_plan()
        if not self.backend or not self.plan:
            self.review_requested.emit()
            return
        if self.plan.changed:
            self.preview.setPlainText('所选方案还未应用。请核对停用和启用列表后，点击“应用并启动”。\n' + self.preview.toPlainText())
            self.review_requested.emit()
            return
        backend, game = self.backend, self.ctx.game
        runtime = self.ctx.settings.path.parent / 'runtime'
        self._run(lambda: backend.launch(game, runtime), lambda result: None, launch=True)

    def recover(self):
        if self.backend:
            self._run(self.backend.recover, lambda _: self.preview.setPlainText('已恢复切换前的文件，可重新选择方案。'))

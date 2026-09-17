"""Choose opaque localization packages, review the switch, and start the game."""
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFileDialog, QGroupBox, QHBoxLayout,
    QHeaderView, QInputDialog, QLabel, QListWidget, QListWidgetItem, QMessageBox,
    QPlainTextEdit, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from core.localization_profiles import BUILTIN, CURRENT, NONE, LocalizationProfiles
from .theme import style_button, style_table
from .workers import Worker


class LocalizationManager(QWidget):
    def __init__(self, ctx, prepare_builtin):
        super().__init__()
        self.setObjectName('localizationManager')
        self.ctx, self._busy, self._root = ctx, False, None
        self.backend, self.plan = None, None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)
        box = QGroupBox('选择汉化，整备后出发')
        box.setObjectName('localizationControls')
        controls = QVBoxLayout(box)
        controls.setContentsMargins(8, 8, 8, 8)
        controls.setSpacing(4)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        controls.addWidget(self.summary)
        row = QHBoxLayout()
        row.addWidget(QLabel('汉化方案'))
        self.choice = QComboBox()
        self.choice.setMinimumWidth(200)
        row.addWidget(self.choice, 1)
        self.refresh_btn = QPushButton('刷新')
        style_button(self.refresh_btn, 'refresh')
        self.refresh_btn.clicked.connect(self.refresh)
        row.addWidget(self.refresh_btn)
        controls.addLayout(row)
        row = QHBoxLayout()
        self.import_btn = QPushButton('导入汉化 ZIP')
        self.existing_btn = QPushButton('从已安装文件添加')
        self.builtin_btn = QPushButton('生成 / 更新独立汉化')
        for button, glyph in ((self.import_btn, 'folder'), (self.existing_btn, 'book'), (self.builtin_btn, 'download')):
            style_button(button, glyph)
            row.addWidget(button)
        self.import_btn.clicked.connect(self.import_packages)
        self.existing_btn.clicked.connect(self.add_existing)
        self.builtin_btn.clicked.connect(prepare_builtin)
        controls.addLayout(row)
        note = QLabel('新版独立汉化：从本软件启动，地图、任务和对话中的地名显示中文；直接启动游戏时显示英文。正文始终汉化，其他汉化沿用各自规则。')
        note.setObjectName('muted')
        note.setWordWrap(True)
        controls.addWidget(note)
        layout.addWidget(box)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(['状态', '汉化文件', '来源'])
        style_table(self.table)
        self.table.verticalHeader().setDefaultSectionSize(34)
        self.table.setMinimumHeight(110)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setColumnWidth(0, 80)
        self.table.setColumnWidth(2, 180)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        layout.addWidget(self.table, 1)
        layout.addWidget(QLabel('切换预览 · 停用的文件会保留，可切回原方案'))
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
        self.refresh()

    def refresh(self):
        game = self.ctx.game
        key = str(game.root.resolve()) if game else None
        selected = self.choice.currentData() if key == self._root else self.ctx.settings.get('localization_choices', {}).get(key, CURRENT)
        self._root = key
        self.plan = None
        self.choice.blockSignals(True)
        self.choice.clear()
        self.choice.addItem('沿用当前配置', CURRENT)
        self.choice.addItem('BBMOD 独立汉化（内置）', BUILTIN)
        self.choice.addItem('停用已管理及已识别汉化', NONE)
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
                labels = ['已启用' if item['enabled'] else '已停用', item['name'],
                          'BBMOD 独立制作' if item['own'] else ('已加入方案' if item['managed'] else '待归类 · 按文件名识别')]
                for column, label in enumerate(labels):
                    cell = QTableWidgetItem(label)
                    cell.setToolTip(str(item['path']))
                    self.table.setItem(i, column, cell)
            active = [item['name'] for item in rows if item['enabled']]
            self.summary.setText(('当前已启用：' + '、'.join(active)) if active else
                                 ('尚未识别到汉化；可导入或从已安装文件中添加。' if game else '请先在上方指定游戏目录。'))
            index = self.choice.findData(selected)
            self.choice.setCurrentIndex(max(0, index))
        except Exception as error:
            self.backend = None
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
        try:
            if not self.backend:
                self.preview.setPlainText('指定游戏目录后，即可选择汉化和启动游戏。')
            elif self.choice.currentData() == BUILTIN and BUILTIN not in self.backend.profiles():
                self.preview.setPlainText('先点击“生成 / 更新独立汉化”，生成完成后会在这里显示切换预览。')
            else:
                self.plan = self.backend.plan(self.choice.currentData())
                lines = []
                if self.plan.disable:
                    lines.append('将停用并保留：' + '、'.join(self.plan.disable))
                if self.plan.install:
                    lines.append('将启用：' + '、'.join(self.plan.install))
                if self.plan.conflicts:
                    lines.append('其中以下 MOD 覆盖了相同文件，也将停用：' + '、'.join(self.plan.conflicts))
                if not lines:
                    lines.append('当前文件已符合所选方案，可直接启动游戏。')
                if self.plan.profile_id == NONE:
                    lines.append('此操作只停用 ZIP 汉化；直接修改过的游戏本体文件需另行还原。')
                self.preview.setPlainText('\n'.join(lines))
        except Exception as error:
            self.preview.setPlainText(str(error))
        self.update_controls()

    def update_controls(self):
        locked = self._busy or getattr(self.ctx, 'management_busy', False) or getattr(self.ctx, 'seedgen_active', False)
        available = bool(self.backend) and not locked
        for button in (self.import_btn, self.existing_btn, self.builtin_btn, self.choice, self.refresh_btn):
            button.setEnabled(available)
        self.recover_btn.setVisible(bool(self.backend and self.backend.journal.exists()))
        self.recover_btn.setEnabled(available)
        self.apply_btn.setEnabled(available and bool(self.plan and self.plan.changed))
        self.start_btn.setEnabled(available and self.plan is not None)
        self.start_btn.setText('应用并启动' if self.plan and self.plan.changed else '启动游戏')

    def _run(self, fn, done):
        if self._busy or getattr(self.ctx, 'management_busy', False) or getattr(self.ctx, 'seedgen_active', False):
            return
        self._busy = True
        setter = getattr(self.ctx, 'set_management_busy', None)
        if setter:
            setter(True)
        self.update_controls()
        self.worker = Worker(fn, self)
        def finished(result=None, error=None):
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
            self.preview.setPlainText('配置已应用，游戏正在启动，请等待画面载入。' if launch else '汉化方案已应用，可从软件启动游戏。')
        self._run(work, done)

    def launch_current(self):
        if not self.plan:
            return
        if self.plan and self.plan.changed:
            self.preview.setPlainText('所选方案还未应用。请核对停用和启用列表后，点击“应用并启动”。\n' + self.preview.toPlainText())
            return
        if not self.backend:
            return
        backend, game = self.backend, self.ctx.game
        runtime = self.ctx.settings.path.parent / 'runtime'
        self._run(lambda: backend.launch(game, runtime),
                  lambda result: self.preview.setPlainText('游戏正在启动，请等待画面载入。'))

    def recover(self):
        if self.backend:
            self._run(self.backend.recover, lambda _: self.preview.setPlainText('已恢复切换前的文件，可重新选择方案。'))

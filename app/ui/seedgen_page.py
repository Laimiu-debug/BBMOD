"""Seed expedition: readable filters, persistent text notes and click-to-copy sharing."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox,
    QDoubleSpinBox, QFileDialog, QFormLayout, QFrame, QGridLayout, QGroupBox,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMessageBox, QPushButton,
    QSpinBox, QStackedWidget, QTableWidget, QTableWidgetItem, QTabWidget,
    QTextEdit, QVBoxLayout, QWidget,
)

from core import game as game_mod
from core.paths import resource_path
from core.seedgen.config_emitter import (
    ATTRIBUTES, CommonConfig, OriginConfig, ORIGIN_LABELS, ROLE_LABELS,
    SCORE_EXPLANATION, SeedGenConfig, attribute_condition, score_condition,
)
from core.seedgen.log_watcher import SeedResult
from core.seedgen.orchestrator import SeedGenOrchestrator
from core.seedgen.presentation import (
    FORMATS, OPENERS, format_collection, format_seed, highlights, note_key,
)
from .app_context import AppContext
from .theme import style_button, style_table

PAYLOAD_DIR = resource_path("seedgen/payload")
MODE_LABELS = {
    "人物 + 地图": "bro_map", "只找开局兄弟（快）": "bro_only",
    "只找地图": "map_only", "人物 + 红装": "bro_lair", "人物 + 地图 + 红装": "all",
}


def spin(minimum=0, maximum=200, value=0, unlimited=False):
    widget = QSpinBox()
    widget.setRange(minimum, maximum)
    widget.setValue(value)
    if unlimited:
        widget.setSpecialValueText("不限")
    return widget


def labeled_row(layout, label, widget, stretch=1):
    caption = QLabel(label)
    layout.addWidget(caption)
    layout.addWidget(widget, stretch)
    return caption


class SeedGenPage(QWidget):
    def __init__(self, ctx: AppContext) -> None:
        super().__init__()
        self.setObjectName("seedPage")
        self.ctx = ctx
        self.orch: SeedGenOrchestrator | None = None
        self.results: list[SeedResult] = []
        self.extra_attributes: dict[str, int] = {}
        saved_notes = ctx.settings.get("seed_notes", {})
        self.notes = {str(k): v for k, v in saved_notes.items() if isinstance(v, str)} if isinstance(saved_notes, dict) else {}
        self._loading_note = False
        root = QVBoxLayout(self)
        root.setSpacing(8)

        self.cfg_box = QGroupBox("Ⅰ  选择想要的开局")
        self.cfg_box.setObjectName("seedFilters")
        filters = QVBoxLayout(self.cfg_box)
        filters.setSpacing(6)
        top = QHBoxLayout()
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(MODE_LABELS)
        labeled_row(top, "寻找", self.mode_combo, 2)
        self.origin_combo = QComboBox()
        for key, label in ORIGIN_LABELS.items():
            if key != "common":
                self.origin_combo.addItem(label, key)
        self.origin_combo.setCurrentIndex(self.origin_combo.findData("scenario.militia"))
        labeled_row(top, "起源", self.origin_combo, 1)
        help_button = QPushButton("评分说明")
        style_button(help_button, "book")
        help_button.clicked.connect(lambda: QMessageBox.information(self, "评分与属性怎么算", SCORE_EXPLANATION))
        top.addWidget(help_button)
        filters.addLayout(top)
        self.filter_tabs = QTabWidget()
        self.filter_tabs.setObjectName("filterTabs")
        filters.addWidget(self.filter_tabs)

        bro_page = QWidget()
        bro_layout = QVBoxLayout(bro_page)
        bro_layout.setContentsMargins(8, 6, 8, 4)
        bro_layout.setSpacing(5)
        rule_row = QHBoxLayout()
        self.rule_mode = QComboBox()
        for label, key in (("按属性筛选（推荐）", "attributes"), ("沿用起源预设", "preset"), ("高级评分", "score")):
            self.rule_mode.addItem(label, key)
        rule_row.addWidget(self.rule_mode, 2)
        self.bro_count = spin(1, 27, 1)
        self.count_label = labeled_row(rule_row, "至少满足人数", self.bro_count)
        self.more_btn = QPushButton("其他属性…")
        self.more_btn.clicked.connect(self._edit_extra_attributes)
        rule_row.addWidget(self.more_btn)
        bro_layout.addLayout(rule_row)
        self.rule_stack = QStackedWidget()
        bro_layout.addWidget(self.rule_stack)
        attr_page = QWidget()
        attr_layout = QHBoxLayout(attr_page)
        attr_layout.setContentsMargins(0, 0, 0, 0)
        self.attr_spins = {}
        for key, value in (("MeleeSkill", 90), ("MeleeDefense", 25), ("RangedSkill", 0)):
            widget = spin(0, 200, value, True)
            widget.setToolTip("11级预估值；按每级都提升该属性计算。选不限则不检查这一项。")
            self.attr_spins[key] = widget
            labeled_row(attr_layout, ATTRIBUTES[key] + " ≥", widget)
        self.rule_stack.addWidget(attr_page)
        preset_label = QLabel("使用所选起源的原始条件；它可能要求特定特性组合。点击「评分说明」了解评分。")
        preset_label.setWordWrap(True)
        self.rule_stack.addWidget(preset_label)
        score_page = QWidget()
        score_layout = QHBoxLayout(score_page)
        score_layout.setContentsMargins(0, 0, 0, 0)
        self.bro_type_combo = QComboBox()
        for label, key in (("队伍平均分", "TeamScore"), ("指定职业分", "RoleScore"), ("不限职业分", "AnyRoleScore")):
            self.bro_type_combo.addItem(label, key)
        score_layout.addWidget(self.bro_type_combo, 2)
        self.bro_score = QDoubleSpinBox()
        self.bro_score.setRange(-1.0, 2.0)
        self.bro_score.setSingleStep(0.01)
        self.bro_score.setValue(0.80)
        labeled_row(score_layout, "超过", self.bro_score)
        self.bro_role = QComboBox()
        for key, label in ROLE_LABELS.items():
            self.bro_role.addItem(label, key)
        self.role_label = labeled_row(score_layout, "职业", self.bro_role)
        self.rule_stack.addWidget(score_page)
        self.attr_hint = QLabel("同一名兄弟须同时满足以上门槛 · 属性均为11级预估 · 不限项不参与筛选")
        self.attr_hint.setObjectName("muted")
        self.attr_hint.setWordWrap(True)
        bro_layout.addWidget(self.attr_hint)
        self.filter_tabs.addTab(bro_page, "开局兄弟")

        map_page = QWidget()
        map_layout = QVBoxLayout(map_page)
        map_layout.setContentsMargins(8, 8, 8, 4)
        map_row = QHBoxLayout()
        self.port_count = spin(0, 30, 7, True)
        self.city_count = spin(0, 40, 0, True)
        self.armorsmith_count = spin(0, 30, 0, True)
        labeled_row(map_row, "港口 ≥", self.port_count)
        labeled_row(map_row, "城镇 ≥", self.city_count)
        labeled_row(map_row, "甲店 ≥", self.armorsmith_count)
        map_layout.addLayout(map_row)
        map_hint = QLabel("同时满足所有已设门槛才保留；例如港口填7，就找至少7座港口的地图。")
        map_hint.setWordWrap(True)
        map_hint.setObjectName("muted")
        map_layout.addWidget(map_hint)
        self.filter_tabs.addTab(map_page, "地图与港口")

        lair_page = QWidget()
        lair_layout = QVBoxLayout(lair_page)
        lair_layout.setContentsMargins(8, 8, 8, 4)
        lair_row = QHBoxLayout()
        self.named_min = spin(1, 200, 20)
        labeled_row(lair_row, "全地图红装总数至少", self.named_min)
        lair_row.addWidget(QLabel("件"))
        lair_row.addStretch(2)
        lair_layout.addLayout(lair_row)
        lair_hint = QLabel("统计生成时营地中的红装。红装位置可在结果详情的营地记录里核对。")
        lair_hint.setWordWrap(True)
        lair_hint.setObjectName("muted")
        lair_layout.addWidget(lair_hint)
        self.filter_tabs.addTab(lair_page, "营地红装")
        root.addWidget(self.cfg_box)

        run_row = QHBoxLayout()
        self.start_btn = QPushButton("开始远征")
        style_button(self.start_btn, "play", primary=True)
        self.stop_btn = QPushButton("停止并恢复")
        style_button(self.stop_btn, "stop")
        self.stop_btn.setEnabled(False)
        self.options_btn = QPushButton("生成设置…")
        self.options_btn.clicked.connect(self._generation_options)
        self.lower_check = QCheckBox("包含小写种子（大小写必须原样复制）")
        self.real11_check = QCheckBox("逐级模拟11级成长（关闭后使用星级平均成长）")
        self.real11_check.setChecked(True)
        self.progress_label = QLabel("待机 · 开始后，在游戏内选择相同起源并新建战役")
        self.progress_label.setObjectName("runStatus")
        self.progress_label.setWordWrap(True)
        self.start_btn.clicked.connect(self.start)
        self.stop_btn.clicked.connect(self.stop)
        run_row.addWidget(self.start_btn)
        run_row.addWidget(self.stop_btn)
        run_row.addWidget(self.options_btn)
        run_row.addWidget(self.progress_label, 1)
        root.addLayout(run_row)

        self.table = QTableWidget(0, 4)
        style_table(self.table)
        self.table.setMinimumHeight(100)
        self.table.setHorizontalHeaderLabels(["种子码", "发现的亮点", "起源", "轮次"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setWordWrap(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setColumnWidth(0, 146)
        self.table.setColumnWidth(2, 105)
        self.table.setColumnWidth(3, 70)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        root.addWidget(self.table, 1)

        share = QFrame()
        share.setObjectName("sharePanel")
        share_layout = QVBoxLayout(share)
        share_layout.setContentsMargins(9, 7, 9, 7)
        share_layout.setSpacing(5)
        share_row = QHBoxLayout()
        self.format_combo = QComboBox()
        for label, mode in FORMATS.items():
            self.format_combo.addItem(label, mode)
        self.opener_combo = QComboBox()
        self.opener_combo.setEditable(True)
        self.opener_combo.addItems(OPENERS)
        self.opener_combo.lineEdit().setMaxLength(60)
        self.click_copy = QCheckBox("点选即复制")
        self.click_copy.setToolTip("开启后，点击种子行即可复制当前格式；新结果到来不会改动剪贴板。")
        self.copy_btn = QPushButton("复制所选")
        style_button(self.copy_btn, "copy", primary=True)
        self.export_btn = QPushButton("导出全部 TXT")
        style_button(self.export_btn, "save")
        share_row.addWidget(self.format_combo, 2)
        share_row.addWidget(self.opener_combo, 1)
        share_row.addWidget(self.click_copy)
        share_row.addWidget(self.copy_btn)
        share_row.addWidget(self.export_btn)
        share_layout.addLayout(share_row)
        self.detail_label = QTextEdit()
        self.detail_label.setReadOnly(True)
        self.detail_label.setMinimumHeight(42)
        self.detail_label.setMaximumHeight(62)
        self.detail_label.setPlaceholderText("Ⅱ  命中种子后点选一行；在这里预览档案或弹幕，复制后即可粘贴。")
        share_layout.addWidget(self.detail_label)
        self.note_edit = QLineEdit()
        self.note_edit.setMaxLength(1000)
        self.note_edit.setPlaceholderText("补充介绍 / 路线：例如出门金鹅，坐船到北港……（随所选种子保存）")
        self.note_edit.setToolTip("自动文案使用日志中的属性、港口和红装数量；路线由你补充，按种子与起源保存。")
        share_layout.addWidget(self.note_edit)
        root.addWidget(share)

        preferences = ctx.settings.get("seed_share", {})
        if not isinstance(preferences, dict):
            preferences = {}
        selected = self.format_combo.findData(preferences.get("format", "danmaku"))
        self.format_combo.setCurrentIndex(max(0, selected))
        opener = preferences.get("opener", "自动开场白")
        self.opener_combo.setCurrentText(opener if isinstance(opener, str) else "自动开场白")
        self.click_copy.setChecked(bool(preferences.get("click_copy", False)))
        self.copy_btn.clicked.connect(self.copy_selected)
        self.export_btn.clicked.connect(self.export_txt)
        self.format_combo.currentIndexChanged.connect(self._share_changed)
        self.opener_combo.currentTextChanged.connect(self._share_changed)
        self.click_copy.toggled.connect(self._share_changed)
        self.note_edit.textEdited.connect(self._note_changed)
        self.table.itemSelectionChanged.connect(self._show_detail)
        self.table.cellClicked.connect(self._clicked_result)
        self.table.cellDoubleClicked.connect(self._open_record)
        self.copy_shortcut = QShortcut(QKeySequence.Copy, self.table)
        self.copy_shortcut.setContext(Qt.WidgetWithChildrenShortcut)
        self.copy_shortcut.activated.connect(self.copy_selected)
        self.rule_mode.currentIndexChanged.connect(self._rule_changed)
        self.bro_type_combo.currentIndexChanged.connect(self._rule_changed)
        self.mode_combo.currentIndexChanged.connect(self._mode_changed)
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self._poll)
        self._rule_changed()
        self._mode_changed()
        self._share_changed(save=False)
        self._show_detail()

    def _rule_changed(self, *_args) -> None:
        index = self.rule_mode.currentIndex()
        self.rule_stack.setCurrentIndex(index)
        self.more_btn.setVisible(index == 0)
        team = index == 2 and self.bro_type_combo.currentData() == "TeamScore"
        self.bro_count.setVisible(index != 1 and not team)
        self.count_label.setVisible(index != 1 and not team)
        role_visible = self.bro_type_combo.currentData() == "RoleScore"
        self.bro_role.setVisible(role_visible)
        self.role_label.setVisible(role_visible)
        if index == 0:
            extra = f" · 另设{len(self.extra_attributes)}项（其他属性中查看）" if self.extra_attributes else ""
            text = "11级预估 · 同一名兄弟须满足所有门槛 · 不限项不参与筛选" + extra
        elif index == 1:
            text = "原始起源预设可能较严格。想自己选门槛，请切回按属性筛选。"
        else:
            text = "0.8 是综合潜力评分；可能超过1。这里按严格大于筛选，计算方法见「评分说明」。"
        self.attr_hint.setText(text)

    def _mode_changed(self, *_args) -> None:
        mode = MODE_LABELS[self.mode_combo.currentText()]
        enabled = (mode != "map_only", mode in ("map_only", "bro_map", "all"), mode in ("bro_lair", "all"))
        for index, active in enumerate(enabled):
            self.filter_tabs.setTabEnabled(index, active)
        if not enabled[self.filter_tabs.currentIndex()]:
            self.filter_tabs.setCurrentIndex(enabled.index(True))
        self.filter_tabs.setTabText(0, "开局兄弟" if enabled[0] else "本次不筛人物")
        self.filter_tabs.setTabText(1, "地图与港口" if enabled[1] else "本次不筛地图")
        self.filter_tabs.setTabText(2, "营地红装" if enabled[2] else "本次不筛红装")

    def _edit_extra_attributes(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("其他11级预估属性 · 0表示不限")
        layout = QFormLayout(dialog)
        widgets = {}
        for key, label in ATTRIBUTES.items():
            if key not in self.attr_spins:
                widgets[key] = spin(0, 300, self.extra_attributes.get(key, 0), True)
                layout.addRow(label + " ≥", widgets[key])
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)
        if dialog.exec() == QDialog.Accepted:
            self.extra_attributes = {key: widget.value() for key, widget in widgets.items() if widget.value()}
            self._rule_changed()

    def _generation_options(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("种子生成设置")
        layout = QVBoxLayout(dialog)
        lower = QCheckBox(self.lower_check.text())
        lower.setChecked(self.lower_check.isChecked())
        real = QCheckBox(self.real11_check.text())
        real.setChecked(self.real11_check.isChecked())
        layout.addWidget(lower)
        layout.addWidget(real)
        description = QLabel("11级数值假设每级都提升对应属性；慢速起源仍使用星级平均成长。")
        description.setWordWrap(True)
        layout.addWidget(description)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        if dialog.exec() == QDialog.Accepted:
            self.lower_check.setChecked(lower.isChecked())
            self.real11_check.setChecked(real.isChecked())

    def _current_config(self) -> SeedGenConfig:
        mode = MODE_LABELS[self.mode_combo.currentText()]
        cfg = SeedGenConfig(common=CommonConfig.preset(mode))
        cfg.common.EnableLowercaseSeed = self.lower_check.isChecked()
        cfg.common.UseBrotherLevel11RealAttr = self.real11_check.isChecked()
        if mode != "map_only" and self.rule_mode.currentData() != "preset":
            if self.rule_mode.currentData() == "attributes":
                thresholds = {key: widget.value() for key, widget in self.attr_spins.items() if widget.value()}
                thresholds.update(self.extra_attributes)
                condition = attribute_condition(self.bro_count.value(), thresholds)
            else:
                condition = score_condition(self.bro_type_combo.currentData(), round(self.bro_score.value(), 2),
                                            self.bro_count.value(), self.bro_role.currentData())
            cfg.origins = {self.origin_combo.currentData(): OriginConfig(conditions=[condition])}
        if mode in ("map_only", "bro_map", "all"):
            cfg.map_conditions = [["PortNum", self.port_count.value(), "SettlementNum", self.city_count.value(),
                                   "ArmorsmithNum", self.armorsmith_count.value()]]
        if mode in ("bro_lair", "all"):
            cfg.lair_conditions = [["NamedNumber", self.named_min.value()]]
        return cfg

    def start(self) -> None:
        if not self.ctx.game:
            QMessageBox.warning(self, "未找到游戏", "请先指定游戏目录")
            return
        if game_mod.is_game_running():
            QMessageBox.warning(self, "游戏运行中", "请先关闭游戏再开始")
            return
        try:
            cfg = self._current_config()
        except ValueError as error:
            QMessageBox.warning(self, "检查筛选条件", str(error))
            return
        self.orch = SeedGenOrchestrator(self.ctx.game, PAYLOAD_DIR)
        try:
            warnings = self.orch.prepare(cfg)
        except Exception as error:
            QMessageBox.critical(self, "无法开始", str(error))
            self.orch = None
            return
        if warnings:
            QMessageBox.warning(self, "开始前的提示", "\n".join(warnings))
        try:
            if not self.orch.launch():
                raise RuntimeError("未能启动游戏，请检查 Steam 和游戏路径。")
        except Exception as error:
            try:
                self.orch.stop_and_restore()
                self.orch = None
            except Exception as restore_error:
                self.stop_btn.setEnabled(True)
                self.start_btn.setEnabled(False)
                self.ctx.set_seedgen_active(True)
                self.cfg_box.setEnabled(False)
                self.options_btn.setEnabled(False)
                QMessageBox.critical(self, "启动失败，恢复未完成", f"{error}\n{restore_error}")
                return
            QMessageBox.critical(self, "启动失败", str(error))
            return
        self.table.setRowCount(0)
        self.results = self.orch.results
        self.ctx.set_seedgen_active(True)
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.cfg_box.setEnabled(False)
        self.options_btn.setEnabled(False)
        self.progress_label.setText(f"游戏内请选择「{self.origin_combo.currentText()}」并新建战役")
        self.timer.start()
        self.ctx.data_changed.emit()
        self._show_detail()

    def stop(self) -> None:
        if not self.orch:
            return
        self.timer.stop()
        self.progress_label.setText("正在恢复游戏配置…")
        try:
            restored = self.orch.stop_and_restore()
        except Exception as error:
            QMessageBox.warning(self, "恢复未完成", str(error))
            return
        self.results = list(self.orch.results)
        preserved = getattr(getattr(self.orch, "files", None), "preserved", [])
        self.orch = None
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.cfg_box.setEnabled(True)
        self.options_btn.setEnabled(True)
        self.ctx.set_seedgen_active(False)
        self.progress_label.setText(f"已结束 · 命中 {len(self.results)} 个 · 恢复 {restored} 个 MOD")
        self.ctx.data_changed.emit()
        self._show_detail()
        if preserved:
            QMessageBox.information(self, "额外文件已保留", "原配置已恢复，额外变化另存到：\n" + "\n".join(str(p) for p in preserved))

    def _poll(self) -> None:
        if not self.orch:
            self.timer.stop()
            return
        results, _ = self.orch.poll()
        progress = self.orch.progress
        if progress.loop_idx:
            self.progress_label.setText(f"已找 {progress.loop_idx} 个 · 命中 {progress.hits} 个")
        for result in results:
            self._append_result(result)
        if results:
            actual = results[-1].origin
            if actual and actual != self.origin_combo.currentData():
                self.progress_label.setText(f"实际起源为「{ORIGIN_LABELS.get(actual, actual)}」，与所设起源不同；人物使用该起源预设")
        self.export_btn.setEnabled(bool(self.results))

    def _append_result(self, result: SeedResult) -> None:
        row = self.table.rowCount()
        self.table.insertRow(row)
        values = [result.seed, " · ".join(highlights(result)) or "双击查看记录",
                  ORIGIN_LABELS.get(result.origin, result.origin) or "未记录", str(result.loop_idx)]
        for column, value in enumerate(values):
            item = QTableWidgetItem(value)
            item.setToolTip(value)
            if column == 0:
                item.setData(Qt.UserRole, result)
            self.table.setItem(row, column, item)
        self.export_btn.setEnabled(True)
        self.table.scrollToBottom()

    def _selected_result(self) -> SeedResult | None:
        row = self.table.currentRow()
        item = self.table.item(row, 0) if row >= 0 else None
        return item.data(Qt.UserRole) if item else None

    def _show_detail(self) -> None:
        result = self._selected_result()
        self.copy_btn.setEnabled(result is not None)
        self.note_edit.setEnabled(result is not None)
        self.export_btn.setEnabled(bool(self.results))
        self._loading_note = True
        self.note_edit.setText(self.notes.get(note_key(result), "") if result else "")
        self._loading_note = False
        self._update_preview()

    def _update_preview(self) -> None:
        result = self._selected_result()
        self.detail_label.setPlainText(self._formatted(result) if result else "")

    def _formatted(self, result: SeedResult) -> str:
        return format_seed(result, self.format_combo.currentData(), self.opener_combo.currentText(),
                           self.notes.get(note_key(result), ""))

    def _share_changed(self, *_args, save=True) -> None:
        self.opener_combo.setEnabled(self.format_combo.currentData() == "danmaku")
        if save:
            self.ctx.settings.set("seed_share", {"format": self.format_combo.currentData(),
                "opener": self.opener_combo.currentText(), "click_copy": self.click_copy.isChecked()})
        self._update_preview()

    def _note_changed(self, text: str) -> None:
        result = self._selected_result()
        if not result or self._loading_note:
            return
        key = note_key(result)
        if text.strip():
            self.notes[key] = text.strip()
        else:
            self.notes.pop(key, None)
        self.ctx.settings.set("seed_notes", self.notes)
        self._update_preview()

    def _clicked_result(self, _row, _column) -> None:
        if self.click_copy.isChecked():
            self.copy_selected()

    def copy_selected(self) -> None:
        result = self._selected_result()
        if result:
            QApplication.clipboard().setText(self._formatted(result))
            self.copy_btn.setText("已复制 ✓")
            QTimer.singleShot(1800, self, lambda: self.copy_btn.setText("复制所选"))

    def _open_record(self, *_args) -> None:
        result = self._selected_result()
        if not result:
            return
        dialog = QDialog(self)
        dialog.setWindowTitle(f"种子档案 · {result.seed}")
        dialog.resize(820, 580)
        layout = QVBoxLayout(dialog)
        text = QTextEdit()
        text.setReadOnly(True)
        text.setPlainText(format_seed(result, "detail", note=self.notes.get(note_key(result), "")))
        layout.addWidget(text)
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        dialog.exec()

    def export_txt(self) -> None:
        if not self.results:
            QMessageBox.information(self, "导出", "还没有命中结果")
            return
        filename, _ = QFileDialog.getSaveFileName(self, "导出全部好种子", "好种子.txt", "文本文档 (*.txt)")
        if not filename:
            return
        path = Path(filename)
        if path.suffix.lower() != ".txt":
            path = path.with_suffix(".txt")
        content = format_collection(self.results, self.format_combo.currentData(), self.opener_combo.currentText(), self.notes)
        try:
            path.write_text(content, encoding="utf-8-sig")
        except OSError as error:
            QMessageBox.warning(self, "导出失败", f"无法写入 {path}\n{error}")
            return
        QMessageBox.information(self, "已导出", f"{len(self.results)} 条好种子已保存为 TXT：\n{path}")

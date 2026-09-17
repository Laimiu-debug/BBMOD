"""Seed expedition: readable filters, persistent text notes and click-to-copy sharing."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QKeySequence, QShortcut, QDesktopServices
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox,
    QDoubleSpinBox, QFileDialog, QFormLayout, QFrame, QGridLayout, QGroupBox,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMenu, QMessageBox, QPushButton,
    QSpinBox, QStackedWidget, QTableWidget, QTableWidgetItem, QTabWidget,
    QTextEdit, QVBoxLayout, QWidget,
)

from core import game as game_mod
from core.paths import resource_path
from core.seedgen.config_emitter import (
    ATTRIBUTES, CampaignConfig, CommonConfig, OriginConfig, ORIGIN_LABELS, ROLE_LABELS,
    DIFFICULTY_LABELS, BUDGET_LABELS,
    SCORE_EXPLANATION, SeedGenConfig, brother_condition, score_condition,
)
from core.seedgen.log_watcher import SeedResult, import_seed_log
from core.seedgen.orchestrator import SeedGenOrchestrator, StopLimits
from core.seedgen.library import SeedLibrary
from core.seedgen.protocol import seed_key, share_payload
from core.seedgen.sharing import upload_seed, PUBLIC_SITE
from core.seedgen.traits import trait_name, validate_traits
from core.seedgen.presentation import (
    FORMATS, OPENERS, format_collection, format_seed, highlights, note_key, raw_record,
)
from .app_context import AppContext
from .theme import style_button, style_table
from .seed_trait_dialog import SeedTraitDialog
from .workers import Worker

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
        self._automatic_stop_failed = False
        self._import_worker: Worker | None = None
        self._share_worker: Worker | None = None
        self.library = None
        self._library_error = ""
        limits = ctx.settings.get("seed_stop_limits", {})
        try:
            self._limits = StopLimits(**limits) if isinstance(limits, dict) else StopLimits()
        except (TypeError, ValueError):
            self._limits = StopLimits()
        folder = ctx.settings.get("seed_log_directory", "")
        self._log_directory = Path(folder) if isinstance(folder, str) and folder else None
        self.extra_attributes: dict[str, int] = {}
        self.required_traits, self.excluded_traits, self.trait_match = [], [], 'all'
        saved_traits = ctx.settings.get('seed_traits', {})
        if isinstance(saved_traits, dict):
            try:
                required, excluded = validate_traits(saved_traits.get('required', []), saved_traits.get('excluded', []), saved_traits.get('match', 'all'))
                self.required_traits, self.excluded_traits = required, excluded
                self.trait_match = saved_traits.get('match', 'all')
            except ValueError:
                pass
        saved_notes = ctx.settings.get("seed_notes", {})
        self.notes = {str(k): v for k, v in saved_notes.items() if isinstance(v, str)} if isinstance(saved_notes, dict) else {}
        self._loading_note = False
        self._campaign_levels = {key: 1 for key in ("combat_difficulty", "economic_difficulty", "budget_difficulty")}
        saved_campaign = ctx.settings.get("seed_campaign", {})
        if isinstance(saved_campaign, dict):
            for key in self._campaign_levels:
                value = saved_campaign.get(key)
                if type(value) is int and value in (0, 1, 2):
                    self._campaign_levels[key] = value
        root = QVBoxLayout(self)
        root.setSpacing(6)

        self.cfg_box = QGroupBox("Ⅰ  选择想要的开局")
        self.cfg_box.setObjectName("seedFilters")
        filters = QVBoxLayout(self.cfg_box)
        filters.setSpacing(4)
        top = QHBoxLayout()
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(MODE_LABELS)
        labeled_row(top, "寻找", self.mode_combo, 2)
        self.origin_combo = QComboBox()
        for key, label in ORIGIN_LABELS.items():
            if key != "common":
                self.origin_combo.addItem(label, key)
        self.origin_combo.setCurrentIndex(self.origin_combo.findData("scenario.militia"))
        if isinstance(saved_campaign, dict):
            index = self.origin_combo.findData(saved_campaign.get("origin"))
            if index >= 0:
                self.origin_combo.setCurrentIndex(index)
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
        bro_layout.setSpacing(4)
        rule_row = QHBoxLayout()
        self.rule_mode = QComboBox()
        for label, key in (("属性与特质（推荐）", "attributes"), ("沿用起源预设", "preset"), ("高级评分", "score"), ("仅按特质筛选", "traits")):
            self.rule_mode.addItem(label, key)
        rule_row.addWidget(self.rule_mode, 2)
        self.bro_count = spin(1, 27, 1)
        self.count_label = labeled_row(rule_row, "至少满足人数", self.bro_count)
        self.more_btn = QPushButton("其他属性…")
        self.more_btn.clicked.connect(self._edit_extra_attributes)
        rule_row.addWidget(self.more_btn)
        self.traits_btn = QPushButton('特质筛选…')
        self.traits_btn.clicked.connect(self._edit_traits)
        rule_row.addWidget(self.traits_btn)
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
        trait_only = QLabel('只筛选开局特质，不检查能力值。点击「特质筛选」设置必选或排除项。')
        trait_only.setWordWrap(True)
        self.rule_stack.addWidget(trait_only)
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
        self.stop_btn.setToolTip("可随时停止：结束刷种子的游戏进程，保留结果，并恢复之前的 MOD 和配置。")
        self.options_btn = QPushButton("生成设置…")
        self.options_btn.clicked.connect(self._generation_options)
        self.log_btn = QPushButton("日志")
        log_menu = QMenu(self.log_btn)
        self.import_action = log_menu.addAction("导入已有种子日志（TXT / HTML）…", self.import_log)
        log_menu.addAction("选择游戏日志目录…", self._choose_log_directory)
        log_menu.addAction("恢复自动查找日志目录", lambda: self._set_log_directory(None))
        log_menu.addAction("查看当前读取位置", self._show_log_location)
        self.log_btn.setMenu(log_menu)
        self.lower_check = QCheckBox("包含小写种子（大小写必须原样复制）")
        self.real11_check = QCheckBox("逐级模拟11级成长（关闭后使用星级平均成长）")
        self.real11_check.setChecked(True)
        self.progress_label = QLabel("待机 · 点击开始后自动进入所选起源刷种子")
        self.progress_label.setObjectName("runStatus")
        self.progress_label.setWordWrap(True)
        self._update_campaign_hint()
        self.start_btn.clicked.connect(self.start)
        self.stop_btn.clicked.connect(self.stop)
        run_row.addWidget(self.start_btn)
        run_row.addWidget(self.stop_btn)
        run_row.addWidget(self.options_btn)
        run_row.addWidget(self.log_btn)
        run_row.addWidget(self.progress_label, 1)
        root.addLayout(run_row)

        library_row = QHBoxLayout()
        self.library_label = QLabel("找到的种子自动保存在本机")
        library_row.addWidget(self.library_label, 1)
        self.save_btn = QPushButton("保存所选")
        self.publish_btn = QPushButton("分享给兄弟")
        self.publish_btn.setToolTip("无需登录。将所选种子的详情和介绍公开到 bbmod.site，分享成功后复制链接。")
        style_button(self.publish_btn, "copy", primary=True)
        self.gallery_btn = QPushButton("逛种子广场 ↗")
        library_row.addWidget(self.save_btn)
        library_row.addWidget(self.publish_btn)
        library_row.addWidget(self.gallery_btn)
        root.addLayout(library_row)

        self.table = QTableWidget(0, 4)
        style_table(self.table)
        self.table.setMinimumHeight(96)
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
        self.save_btn.clicked.connect(self.save_selected)
        self.publish_btn.clicked.connect(self.publish_selected)
        self.gallery_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(PUBLIC_SITE + "/seeds/")))
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
        try:
            self.library = SeedLibrary(ctx.settings.path.parent / "seeds.sqlite3")
            self.results = self.library.all()
            for result in self.results:
                self._append_result(result)
            self._library_status()
        except Exception as error:
            self._library_error = str(error)
            self.library_label.setText("本地种子库读取失败 · 原文件已保留，可导出 TXT 备份")
            self.library_label.setToolTip(str(error))
        self._show_detail()

    def _library_status(self):
        self.library_label.setText(f"本地已保存 {len(self.results)} 条 · 重新搜索与重启均保留")
        if self.library:
            self.library_label.setToolTip(str(self.library.path))

    def _accept_results(self, results):
        added = 0
        indexes = {seed_key(r): i for i, r in enumerate(self.results)}
        for result in results:
            if self.library:
                try:
                    result = self.library.save(result)
                    self._library_error = ""
                except Exception as error:
                    self._library_error = str(error)
            identity = seed_key(result)
            if identity in indexes:
                index = indexes[identity]
                old = self.results[index]
                if (result.done and not old.done) or (result.done == old.done and len(result.lines) > len(old.lines)):
                    self.results[index] = result
                    self._write_result(index, result)
                continue
            indexes[identity] = len(self.results)
            self.results.append(result)
            self._append_result(result)
            added += 1
        if self._library_error:
            self.library_label.setText("自动保存失败 · 结果仍在列表中，请导出 TXT 备份")
            self.library_label.setToolTip(self._library_error)
        else:
            self._library_status()
        self._show_detail()
        return added

    def save_selected(self):
        result = self._selected_result()
        if result:
            try:
                if not self.library:
                    raise RuntimeError(self._library_error or "本地种子库不可用")
                self.library.save(result)
            except Exception as error:
                QMessageBox.warning(self, "保存失败", f"{error}\n可用「导出全部 TXT」另存备份。")
                return
            self.library_label.setText(f"{result.seed} 已保存到本机 · 重启后仍可查看")

    def publish_selected(self):
        result = self._selected_result()
        if not result or (self._share_worker and self._share_worker.isRunning()):
            return
        note = self.notes.get(note_key(result), "")
        try:
            share_payload(result, note)
            if not self.library:
                raise RuntimeError(self._library_error or "本地种子库不可用")
            self.library.save(result)
        except Exception as error:
            QMessageBox.warning(self, "暂时无法分享", str(error))
            return
        self.publish_btn.setEnabled(False)
        self.publish_btn.setText("正在分享…")
        # The worker belongs to the application so changing pages cannot destroy it.
        self._share_worker = Worker(lambda: upload_seed(result, note), QApplication.instance())
        self._share_worker.done.connect(lambda url: self._published(result, url))
        self._share_worker.failed.connect(lambda error: QMessageBox.warning(self, "分享未完成", f"{error}\n种子仍保存在本机，可重新点击分享。"))
        self._share_worker.finished.connect(self._share_finished)
        QApplication.instance().aboutToQuit.connect(self._share_worker.wait)
        self._share_worker.start()

    def _published(self, result, url):
        QApplication.clipboard().setText(url)
        try:
            self.library.mark_shared(result, url)
        except Exception as error:
            self.library_label.setText("已分享到网站并复制链接 · 本地分享状态保存失败")
            self.library_label.setToolTip(str(error))
            return
        self.library_label.setText(f"{result.seed} 已分享 · 链接已复制，可直接发给兄弟")
        self.library_label.setToolTip(url)

    def _share_finished(self):
        self.publish_btn.setText("分享给兄弟")
        self._show_detail()

    def _rule_changed(self, *_args) -> None:
        index = self.rule_mode.currentIndex()
        self.rule_stack.setCurrentIndex(index)
        self.more_btn.setVisible(index == 0)
        self.traits_btn.setVisible(index in (0, 3))
        selected = len(self.required_traits) + len(self.excluded_traits)
        self.traits_btn.setText(f'特质筛选（{selected}项）' if selected else '特质筛选…')
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
            text = "原始起源预设可能较严格。想自己选条件，请切回「属性与特质」。"
        elif index == 2:
            text = "0.8 是综合潜力评分；可能超过1。这里按严格大于筛选，计算方法见「评分说明」。"
        else:
            text = '只筛特质 · 同一名兄弟须满足特质组合 · 达到人数门槛才保留'
        if index in (0, 3):
            def names(items):
                return '、'.join(trait_name(key) for key in items[:3]) + (f'等{len(items)}项' if len(items) > 3 else '')
            summary = []
            if self.required_traits:
                summary.append(('全部具备：' if self.trait_match == 'all' else '任意具备：') + names(self.required_traits))
            if self.excluded_traits:
                summary.append('排除：' + names(self.excluded_traits))
            text += '\n' + ('；'.join(summary) if summary else '特质不限；可选择铁肺、高大（巨人）、酒鬼等')
        self.attr_hint.setText(text)

    def _edit_traits(self):
        dialog = SeedTraitDialog(self.required_traits, self.excluded_traits, self.trait_match, self)
        if dialog.exec() == QDialog.Accepted:
            self.required_traits, self.excluded_traits, self.trait_match = dialog.selection()
            self.ctx.settings.set('seed_traits', {'required':self.required_traits,
                'excluded':self.excluded_traits, 'match':self.trait_match})
            self._rule_changed()

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
        campaign_form = QFormLayout()
        levels = {}
        for key, label, choices in (
            ("combat_difficulty", "战斗难度", DIFFICULTY_LABELS),
            ("economic_difficulty", "经济难度", DIFFICULTY_LABELS),
            ("budget_difficulty", "初始资金", BUDGET_LABELS),
        ):
            widget = QComboBox()
            widget.setObjectName(key)
            for value, caption in choices.items():
                widget.addItem(caption, value)
            widget.setCurrentIndex(widget.findData(self._campaign_levels[key]))
            levels[key] = widget
            campaign_form.addRow(label, widget)
        layout.addLayout(campaign_form)
        stop_form = QFormLayout()
        hits = spin(maximum=1_000_000, value=self._limits.hits, unlimited=True)
        hits.setObjectName("stop_hits")
        hits.setSuffix(" 条")
        minutes = spin(maximum=10080, value=self._limits.minutes, unlimited=True)
        minutes.setObjectName("stop_minutes")
        minutes.setSuffix(" 分钟")
        stop_form.addRow("找到好种子后停止", hits)
        stop_form.addRow("运行时限（含加载）", minutes)
        layout.addLayout(stop_form)
        lower = QCheckBox(self.lower_check.text())
        lower.setChecked(self.lower_check.isChecked())
        real = QCheckBox(self.real11_check.text())
        real.setChecked(self.real11_check.isChecked())
        layout.addWidget(lower)
        layout.addWidget(real)
        description = QLabel("软件会自动按所选起源和以上设置新建战役。复现红装时请保持起源、难度和 DLC 一致。\n"
                             "11级数值假设每级都提升对应属性；慢速起源仍使用星级平均成长。\n"
                             "结果边刷边显示。数量和时限均为不限时持续搜索；两项都设置时，先达到哪项就停止并恢复。")
        description.setWordWrap(True)
        layout.addWidget(description)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("确定")
        buttons.button(QDialogButtonBox.Cancel).setText("取消")
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        if dialog.exec() == QDialog.Accepted:
            self._limits = StopLimits(hits.value(), minutes.value())
            self.ctx.settings.set("seed_stop_limits", {"hits": hits.value(), "minutes": minutes.value()})
            self._campaign_levels = {key: widget.currentData() for key, widget in levels.items()}
            self._save_campaign()
            self._update_campaign_hint()
            self.lower_check.setChecked(lower.isChecked())
            self.real11_check.setChecked(real.isChecked())

    def _save_campaign(self) -> None:
        self.ctx.settings.set("seed_campaign", {"origin": self.origin_combo.currentData(), **self._campaign_levels})

    def _update_campaign_hint(self) -> None:
        levels = self._campaign_levels
        self.progress_label.setText(
            f"自动开局 · 战斗{DIFFICULTY_LABELS[levels['combat_difficulty']]} · "
            f"经济{DIFFICULTY_LABELS[levels['economic_difficulty']]} · "
            f"资金{BUDGET_LABELS[levels['budget_difficulty']]}"
            f"\n{self._limits.description}"
        )
        self.options_btn.setToolTip("设置战斗难度、经济难度、初始资金和自动停止条件")

    def _choose_log_directory(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "选择包含 log.html 或 log.txt 的 Battle Brothers 日志目录",
                                                  str(self._log_directory or ""))
        if folder:
            self._set_log_directory(Path(folder))

    def _set_log_directory(self, folder: Path | None) -> None:
        self._log_directory = folder
        self.ctx.settings.set("seed_log_directory", str(folder) if folder else "")
        if self.orch:
            self.orch.set_log_directory(folder)
            self.progress_label.setText("正在重新查找本次刷种子的日志…")

    def _show_log_location(self) -> None:
        path = self.orch.log_path if self.orch else None
        directories = game_mod.find_log_write_paths(self._log_directory)
        message = (f"正在读取：\n{path}" if path else "尚未连接本次刷种子日志。")
        message += "\n\n查找目录：\n" + "\n".join(str(folder) for folder in directories)
        message += "\n\n结果会边刷边显示。已有 log.txt 可用「导入已有种子日志」转为中文档案。"
        QMessageBox.information(self, "种子日志位置", message)

    def import_log(self) -> None:
        if self.orch or (self._import_worker and self._import_worker.isRunning()):
            return
        filename, _ = QFileDialog.getOpenFileName(self, "导入已有种子日志", "", "种子日志 (*.txt *.html *.htm)")
        if not filename:
            return
        self.start_btn.setEnabled(False)
        self.import_action.setEnabled(False)
        self.progress_label.setText("正在读取日志并生成中文档案…")
        self._import_worker = Worker(lambda: import_seed_log(Path(filename)), self)
        self._import_worker.done.connect(self._imported_results)
        self._import_worker.failed.connect(lambda error: self.progress_label.setText(f"导入失败：{error}"))
        self._import_worker.finished.connect(lambda: self.start_btn.setEnabled(True))
        self._import_worker.finished.connect(lambda: self.import_action.setEnabled(True))
        self._import_worker.start()

    def _imported_results(self, results: list[SeedResult]) -> None:
        self.table.setUpdatesEnabled(False)
        try:
            added = self._accept_results(results)
        finally:
            self.table.setUpdatesEnabled(True)
        self.format_combo.setCurrentIndex(self.format_combo.findData("detail"))
        partial = sum(not result.done for result in results)
        self.progress_label.setText((f"已导入 {added} 条 · 重复 {len(results) - added} 条" +
            (f" · 其中 {partial} 条日志未完整" if partial else "")) if results else
            "未找到种子记录，请选择生成器的原始 log.txt 或 log.html")
        self._show_detail()

    def _current_config(self) -> SeedGenConfig:
        mode = MODE_LABELS[self.mode_combo.currentText()]
        cfg = SeedGenConfig(common=CommonConfig.preset(mode))
        cfg.campaign = CampaignConfig(origin=self.origin_combo.currentData(), **self._campaign_levels)
        cfg.campaign.validate()
        cfg.common.EnableLowercaseSeed = self.lower_check.isChecked()
        cfg.common.UseBrotherLevel11RealAttr = self.real11_check.isChecked()
        if mode != "map_only" and self.rule_mode.currentData() != "preset":
            if self.rule_mode.currentData() in ("attributes", "traits"):
                thresholds = {}
                if self.rule_mode.currentData() == "attributes":
                    thresholds = {key: widget.value() for key, widget in self.attr_spins.items() if widget.value()}
                    thresholds.update(self.extra_attributes)
                if self.rule_mode.currentData() == 'traits' and not (self.required_traits or self.excluded_traits):
                    raise ValueError('请在「特质筛选」中选择至少一项必选或排除特质')
                condition = brother_condition(self.bro_count.value(), thresholds,
                    self.required_traits, self.excluded_traits, self.trait_match)
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
        if self.orch or (self._import_worker and self._import_worker.isRunning()):
            return
        if not self.ctx.game:
            QMessageBox.warning(self, "未找到游戏", "请先指定游戏目录")
            return
        if game_mod.is_game_running():
            QMessageBox.warning(self, "游戏运行中", "请先关闭游戏再开始")
            return
        try:
            cfg = self._current_config()
            self._save_campaign()
        except ValueError as error:
            QMessageBox.warning(self, "检查筛选条件", str(error))
            return
        self.orch = SeedGenOrchestrator(self.ctx.game, PAYLOAD_DIR,
            log_directory=self._log_directory, limits=self._limits)
        self._automatic_stop_failed = False
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
                self.import_action.setEnabled(False)
                QMessageBox.critical(self, "启动失败，恢复未完成", f"{error}\n{restore_error}")
                return
            QMessageBox.critical(self, "启动失败", str(error))
            return
        self.progress_label.setToolTip("")
        self.ctx.set_seedgen_active(True)
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.cfg_box.setEnabled(False)
        self.options_btn.setEnabled(False)
        self.import_action.setEnabled(False)
        self.progress_label.setText(f"正在启动游戏 · 加载完成后自动以「{self.origin_combo.currentText()}」开始")
        self.timer.start()
        self.ctx.data_changed.emit()
        self._show_detail()

    def stop(self, _checked=False, *, reason: str = "") -> None:
        if not self.orch:
            return
        self.timer.stop()
        self._automatic_stop_failed = False
        self.progress_label.setText("正在恢复游戏配置…")
        try:
            restored = self.orch.stop_and_restore()
        except Exception as error:
            self._automatic_stop_failed = True
            self.timer.start()
            QMessageBox.warning(self, "恢复未完成", str(error))
            return
        session_results = list(self.orch.results)
        self._accept_results(session_results)
        preserved = getattr(getattr(self.orch, "files", None), "preserved", [])
        self.orch = None
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.cfg_box.setEnabled(True)
        self.options_btn.setEnabled(True)
        self.import_action.setEnabled(True)
        self.ctx.set_seedgen_active(False)
        complete = sum(result.done for result in session_results)
        partial = len(session_results) - complete
        self.progress_label.setText(f"{reason or '已停止'} · 命中 {complete} 条 · 恢复 {restored} 个 MOD" +
                                   (f" · 保留 {partial} 条未完整记录" if partial else ""))
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
        startup = self.orch.startup
        elapsed = getattr(self.orch, "elapsed_seconds", 0)
        path = getattr(self.orch, "log_path", None)
        self.progress_label.setToolTip((f"实时读取：{path}\n" if path else "尚未连接本次日志\n") + self._limits.description)
        if startup.stage == "error":
            code = startup.detail.split(" ", 1)[0]
            message = {
                "origin-unavailable": "所选起源不可用，请检查对应 DLC 是否已安装并启用",
                "demo-unavailable": "当前游戏模式不支持新建战役",
                "banners-unavailable": "游戏未提供可用旗帜，请检查游戏文件",
                "settings-mismatch": "游戏开局设置与软件不一致，已阻止继续刷种子",
                "start-failed": "自动开局失败，请停止并恢复后查看营地诊断",
                "generation-failed": "生成脚本出错，请停止并恢复后查看营地诊断",
            }.get(code, "自动开局失败，请停止并恢复后查看营地诊断")
            self.progress_label.setText(message)
            self.progress_label.setToolTip(startup.detail)
        elif progress.loop_idx or self.orch.results:
            rounds = max(progress.loop_idx, max((result.loop_idx for result in self.orch.results), default=0))
            phase = {"map": "生成地图", "routes": "分析路线", "map-skipped": "复杂地图已跳过", "brothers": "筛选兄弟"}.get(getattr(progress, "phase", ""), "搜索中")
            silent = getattr(self.orch, "silent_seconds", 0)
            status = f"日志 {silent} 秒未更新，可停止并保留结果" if silent >= 30 else phase
            self.progress_label.setText(f"第 {rounds} 轮 · 本次命中 {len(self.orch.results)} 条 · {status} · {elapsed // 60:02}:{elapsed % 60:02}")
        elif startup.stage == "generating":
            self.progress_label.setText("已自动开局 · 正在生成第一批种子，地图生成可能需要较长时间")
        elif startup.stage == "requested":
            self.progress_label.setText(f"已选择「{self.origin_combo.currentText()}」· 正在加载战役")
        elif startup.stage == "loaded":
            self.progress_label.setText("生成器已加载 · 等待游戏主菜单准备就绪后自动开始")
        elif elapsed >= 45:
            self.progress_label.setText("尚未读到本次日志 · 游戏仍加载时请等待；已开始刷种子可在「日志」选择目录")
        if results:
            self._accept_results(results)
        if results:
            actual = results[-1].origin
            if actual and actual != self.origin_combo.currentData():
                self.progress_label.setText(f"记录起源「{ORIGIN_LABELS.get(actual, actual)}」与所选不符，请停止并检查游戏脚本")
        self.export_btn.setEnabled(bool(self.results))
        if self._automatic_stop_failed:
            self.progress_label.setText("恢复未完成，备份已保留 · 请点击「停止并恢复」重试")
        elif reason := getattr(self.orch, "stop_reason", ""):
            self.stop(reason=reason)

    def _append_result(self, result: SeedResult) -> None:
        row = self.table.rowCount()
        self.table.insertRow(row)
        self._write_result(row, result)
        self.export_btn.setEnabled(True)
        if row == 0:
            self.table.selectRow(0)
        if self.table.currentRow() >= row - 1:
            self.table.scrollToBottom()

    def _write_result(self, row, result):
        summary = " · ".join(highlights(result)) or "双击查看中文档案"
        if not result.done:
            summary = "记录未完整 · " + summary
        values = [result.seed, summary,
                  ORIGIN_LABELS.get(result.origin, result.origin) or "未记录", str(result.loop_idx)]
        for column, value in enumerate(values):
            item = QTableWidgetItem(value)
            item.setToolTip(value)
            if column == 0:
                item.setData(Qt.UserRole, result)
            self.table.setItem(row, column, item)

    def _selected_result(self) -> SeedResult | None:
        row = self.table.currentRow()
        item = self.table.item(row, 0) if row >= 0 else None
        return item.data(Qt.UserRole) if item else None

    def _show_detail(self) -> None:
        result = self._selected_result()
        self.copy_btn.setEnabled(result is not None)
        self.save_btn.setEnabled(result is not None)
        self.publish_btn.setEnabled(bool(result and result.done and not (self._share_worker and self._share_worker.isRunning())))
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
        raw = QCheckBox("查看英文原始记录（排查用）")
        raw.toggled.connect(lambda checked: text.setPlainText(raw_record(result) if checked else
            format_seed(result, "detail", note=self.notes.get(note_key(result), ""))))
        layout.addWidget(raw)
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

"""刷种子页：模式/条件配置 + 全自动编排（启动→实时结果→停止恢复）。"""
from __future__ import annotations

import csv
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFileDialog, QDoubleSpinBox, QGroupBox, QHBoxLayout,
    QHeaderView, QLabel, QMessageBox, QPushButton, QSpinBox, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from core import game as game_mod
from core.paths import resource_path
from core.seedgen.config_emitter import (
    BRO_OUTPUT, BRO_OUTPUT_LABELS, CommonConfig, OriginConfig, ORIGIN_LABELS,
    ROLE_LABELS, ROLES, SeedGenConfig, BroCondition,
)
from core.seedgen.orchestrator import SeedGenOrchestrator
from .app_context import AppContext

PAYLOAD_DIR = resource_path("seedgen/payload")
MODE_LABELS = {
    "仅地图（生成好地图）": "map_only",
    "仅人物（快速刷开局兄弟）": "bro_only",
    "人物+地图": "bro_map",
    "人物+红装": "bro_lair",
    "全开（人物+地图+红装）": "all",
}


class SeedGenPage(QWidget):
    def __init__(self, ctx: AppContext) -> None:
        super().__init__()
        self.ctx = ctx
        self.orch: SeedGenOrchestrator | None = None

        root = QVBoxLayout(self)

        # 模式与参数
        cfg_box = QGroupBox("配置")
        cl = QHBoxLayout(cfg_box)
        col1 = QVBoxLayout()
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(MODE_LABELS)
        col1.addWidget(QLabel("推荐模式"))
        col1.addWidget(self.mode_combo)
        self.lower_check = QCheckBox("启用小写字母（种子空间 x10000，速度更慢）")
        col1.addWidget(self.lower_check)
        self.real11_check = QCheckBox("用真实模拟的 11 级属性评分（稍慢更准）")
        self.real11_check.setChecked(True)
        col1.addWidget(self.real11_check)
        cl.addLayout(col1, 1)

        col2 = QVBoxLayout()
        col2.addWidget(QLabel("为指定起源追加人物条件"))
        combo_row = QHBoxLayout()
        self.origin_combo = QComboBox()
        self.origin_combo.addItems(sorted(ORIGIN_LABELS.values()))
        combo_row.addWidget(self.origin_combo, 1)
        col2.addLayout(combo_row)
        row1 = QHBoxLayout()
        self.bro_type_combo = QComboBox()
        self.bro_type_combo.addItems([BRO_OUTPUT_LABELS[k] for k in BRO_OUTPUT])
        self.bro_score = QDoubleSpinBox()
        self.bro_score.setRange(0.0, 1.5)
        self.bro_score.setSingleStep(0.01)
        self.bro_score.setValue(0.80)
        self.bro_count = QSpinBox()
        self.bro_count.setRange(0, 12)
        self.bro_count.setValue(1)
        self.bro_role = QComboBox()
        self.bro_role.addItems(list(ROLE_LABELS.values()))
        row1.addWidget(self.bro_type_combo)
        row1.addWidget(QLabel("分数≥"))
        row1.addWidget(self.bro_score)
        row1.addWidget(QLabel("人数≥"))
        row1.addWidget(self.bro_count)
        row1.addWidget(QLabel("职业"))
        row1.addWidget(self.bro_role)
        col2.addLayout(row1)
        self.extra_hint = QLabel("（条件以“或”关系附加到该起源默认条件之上；留默认即可开刷）")
        self.extra_hint.setWordWrap(True)
        col2.addWidget(self.extra_hint)
        cl.addLayout(col2, 2)
        root.addWidget(cfg_box)

        # 运行控制
        run_box = QGroupBox("运行（开始后：软件自动净化游戏→启动→你在游戏里选起源难度点「开始新战役」）")
        rl = QHBoxLayout(run_box)
        self.start_btn = QPushButton("▶ 开始刷种子")
        self.start_btn.setStyleSheet("font-weight: bold;")
        self.stop_btn = QPushButton("■ 停止并恢复")
        self.stop_btn.setEnabled(False)
        self.export_btn = QPushButton("导出结果 CSV")
        self.progress_label = QLabel("待机")
        self.start_btn.clicked.connect(self.start)
        self.stop_btn.clicked.connect(self.stop)
        self.export_btn.clicked.connect(self.export_csv)
        rl.addWidget(self.start_btn)
        rl.addWidget(self.stop_btn)
        rl.addWidget(self.export_btn)
        rl.addWidget(self.progress_label, 1)
        root.addWidget(run_box)

        # 结果表
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["种子", "循环", "队伍分", "兄弟数", "红装数", "命中条件"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setColumnWidth(0, 130)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        root.addWidget(self.table, 1)

        self.detail_label = QLabel("点击结果行查看详情（兄弟属性 / 红装 roll / 营地）")
        root.addWidget(self.detail_label)

        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self._poll)
        self.table.itemSelectionChanged.connect(self._show_detail)

    # ---------------- 构建/运行 ----------------

    def _current_config(self) -> SeedGenConfig:
        cfg = SeedGenConfig(common=CommonConfig.preset(MODE_LABELS[self.mode_combo.currentText()]))
        cfg.common.EnableLowercaseSeed = self.lower_check.isChecked()
        cfg.common.UseBrotherLevel11RealAttr = self.real11_check.isChecked()
        # 起源附加条件（TeamScore 或 RoleScore）
        label = self.origin_combo.currentText()
        origin = next(k for k, v in ORIGIN_LABELS.items() if v == label)
        type_label = self.bro_type_combo.currentText()
        type_key = next(k for k, v in BRO_OUTPUT_LABELS.items() if v == type_label)
        if type_key == "TeamScore":
            cond = BroCondition("TeamScore", [round(self.bro_score.value(), 2)])
        else:
            role_name = next(k for k, v in ROLE_LABELS.items() if v == self.bro_role.currentText())
            cond = BroCondition(type_key, [round(self.bro_score.value(), 2), self.bro_count.value(), role_name])
        cfg.origins = {origin: OriginConfig(conditions=[cond], max_roles={})}
        return cfg

    def start(self) -> None:
        if not self.ctx.game:
            QMessageBox.warning(self, "未找到游戏", "请先在设置中配置游戏路径")
            return
        if game_mod.is_game_running():
            QMessageBox.warning(self, "游戏运行中", "请先关闭游戏再开始")
            return
        cfg = self._current_config()
        self.orch = SeedGenOrchestrator(self.ctx.game, PAYLOAD_DIR)
        try:
            warnings = self.orch.prepare(cfg)
        except RuntimeError as e:
            QMessageBox.critical(self, "无法开始", str(e))
            self.orch = None
            return
        if warnings:
            QMessageBox.warning(self, "开始前的提示", "\n".join(warnings))
        try:
            self.orch.launch()
        except Exception as e:  # noqa: BLE001
            self.orch.stop_and_restore()
            self.orch = None
            QMessageBox.critical(self, "启动失败", str(e))
            return
        self.table.setRowCount(0)
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_label.setText("已启动游戏 —— 请在游戏内选择起源与难度后点「开始新战役」；本窗口将实时显示结果")
        self.timer.start()
        self.ctx.data_changed.emit()

    def stop(self) -> None:
        if not self.orch:
            return
        self.timer.stop()
        self.progress_label.setText("正在停止游戏并恢复 mod 配置…")
        restored = self.orch.stop_and_restore()
        n_results = len(self.orch.results)
        self.orch = None
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_label.setText(f"已结束：命中 {n_results} 个种子 · 恢复 {restored} 个 mod")
        self.ctx.data_changed.emit()

    def _poll(self) -> None:
        if not self.orch:
            self.timer.stop()
            return
        results, _progress = self.orch.poll()
        prog = self.orch.progress
        if prog.loop_idx:
            extra = f" 最高队伍分 {prog.best_team_score}" if prog.best_team_score else ""
            self.progress_label.setText(f"已刷 {prog.loop_idx} 个种子 · 命中 {prog.hits}{extra}")
        for r in results:
            self._append_result(r)

    def _append_result(self, r) -> None:
        i = self.table.rowCount()
        self.table.insertRow(i)
        conds = []
        if r.bro_output_type >= 0:
            conds.append(f"人物#{r.bro_output_type}")
        if r.map_output_type >= 0:
            conds.append(f"地图#{r.map_output_type}")
        if r.lair_output_type >= 0:
            conds.append(f"红装#{r.lair_output_type}")
        for col, val in enumerate([
            r.seed, r.loop_idx,
            f"{r.team_score:.2f}" if r.team_score is not None else "—",
            len(r.brothers), len(r.named_items), "、".join(conds) or "—",
        ]):
            self.table.setItem(i, col, QTableWidgetItem(str(val)))
        self.table.scrollToBottom()

    def _show_detail(self) -> None:
        rows = {idx.row() for idx in self.table.selectedIndexes()}
        if not rows or not self.orch:
            return
        row = min(rows)
        if row >= len(self.orch.results):
            return
        r = self.orch.results[row]
        lines = [f"种子 {r.seed}（第 {r.loop_idx} 轮命中）"]
        lines += r.lines[:40]
        self.detail_label.setText("\n".join(lines))

    def export_csv(self) -> None:
        if not self.orch or not self.orch.results:
            QMessageBox.information(self, "导出", "还没有结果可导出")
            return
        path, _ = QFileDialog.getSaveFileName(self, "导出 CSV", "seeds.csv", "CSV (*.csv)")
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["seed", "loop_idx", "bro/map/lair", "team_score", "detail"])
            for r in self.orch.results:
                writer.writerow([
                    r.seed, r.loop_idx, f"{r.bro_output_type}/{r.map_output_type}/{r.lair_output_type}",
                    r.team_score or "", " | ".join(r.lines),
                ])
        QMessageBox.information(self, "导出", f"已导出 {len(self.orch.results)} 条 → {path}")

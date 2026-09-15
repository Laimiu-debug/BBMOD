"""仪表盘页：游戏状态卡片 + 诊断问题列表。"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGroupBox, QHBoxLayout, QHeaderView, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from core import game as game_mod
from core.diagnostics import DiagnosisReport, diagnose
from core.gamelog import load_log
from core.modinfo import analyze_zip
from .app_context import AppContext
from .workers import Worker

SEVERITY_TEXT = {"error": "错误", "warning": "警告", "info": "提示"}


class DashboardPage(QWidget):
    def __init__(self, ctx: AppContext) -> None:
        super().__init__()
        self.ctx = ctx
        self.report: DiagnosisReport | None = None

        root = QVBoxLayout(self)

        # 游戏状态卡
        info_box = QGroupBox("游戏状态")
        info_layout = QHBoxLayout(info_box)
        self.info_label = QLabel("检测中…")
        self.info_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.refresh_btn = QPushButton("重新检测")
        self.refresh_btn.clicked.connect(self.refresh)
        info_layout.addWidget(self.info_label, 1)
        info_layout.addWidget(self.refresh_btn)
        root.addWidget(info_box)

        # 诊断结果
        diag_box = QGroupBox("健康诊断（冲突 / 版本 / 影响种子 / 上次启动报错）")
        diag_layout = QVBoxLayout(diag_box)
        self.summary_label = QLabel("—")
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["级别", "对象", "问题", "修复建议"])
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setWordWrap(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        diag_layout.addWidget(self.summary_label)
        diag_layout.addWidget(self.table, 1)
        root.addWidget(diag_box, 1)

    def refresh(self) -> None:
        g = self.ctx.game
        if not g:
            self.info_label.setText("未找到游戏，请到 设置 中手动指定安装目录")
            return
        base = game_mod.check_base_archive(g.data_dir)
        dlcs = game_mod.installed_dlcs(g.data_dir)
        base_txt = "⚠ 汉化重打包版（非原版）" if (base and base.repacked) else "原版"
        lines = [
            f"安装目录：{g.root}",
            f"游戏版本：{g.version}（本软件按 1.5.2.3 校准）   基座档案：{base_txt}",
            f"DLC：{sum(dlcs.values())}/{len(dlcs)}",
            f"日志目录：{self.ctx.log_dir() or '未找到'}",
        ]
        self.info_label.setText("\n".join(lines))

        self.refresh_btn.setEnabled(False)
        self._worker = Worker(self._run_diagnosis, self)
        self._worker.done.connect(self._show_report)
        self._worker.failed.connect(lambda e: (self.summary_label.setText(f"诊断失败：{e}"),
                                               self.refresh_btn.setEnabled(True)))
        self._worker.start()

    def _run_diagnosis(self) -> DiagnosisReport:
        g = self.ctx.game
        installed = [analyze_zip(z) for z in sorted(g.data_dir.glob("*.zip"))]
        log_dir = self.ctx.log_dir()
        rows = load_log(log_dir / "log.html") if log_dir else []
        return diagnose(g, installed, rows)

    def _show_report(self, report: DiagnosisReport) -> None:
        self.report = report
        issues = report.sorted()
        self.summary_label.setText(
            f"共 {len(issues)} 条 —— 错误 {report.error_count} · 警告 {report.warning_count} · 提示 "
            f"{len(issues) - report.error_count - report.warning_count}"
        )
        self.table.setRowCount(len(issues))
        for i, issue in enumerate(issues):
            level = QTableWidgetItem(SEVERITY_TEXT[issue.severity])
            if issue.severity == "error":
                level.setForeground(Qt.red)
            elif issue.severity == "warning":
                level.setForeground(Qt.darkYellow)
            else:
                level.setForeground(Qt.gray)
            self.table.setItem(i, 0, level)
            self.table.setItem(i, 1, QTableWidgetItem(issue.source))
            self.table.setItem(i, 2, QTableWidgetItem(issue.title + (f"\n{issue.detail[:200]}" if issue.detail else "")))
            self.table.setItem(i, 3, QTableWidgetItem(issue.fix or ""))
        self.table.resizeRowsToContents()
        self.refresh_btn.setEnabled(True)

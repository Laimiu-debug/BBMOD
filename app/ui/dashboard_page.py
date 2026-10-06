"""仪表盘页：游戏状态卡片 + 诊断问题列表。"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QGroupBox, QHBoxLayout, QHeaderView, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from core import game as game_mod
from core.diagnostics import DiagnosisReport, diagnose
from core.gamelog import load_log
from core.modinfo import analyze_zip
from .app_context import AppContext
from .workers import Worker, track
from .theme import GREEN, MUTED, RED, style_button, style_table
from PySide6.QtGui import QColor

SEVERITY_TEXT = {"error": "错误", "warning": "警告", "info": "提示"}


class DashboardPage(QWidget):
    choose_game = Signal()
    localization = Signal()
    browse_mods = Signal(str)
    support_requested = Signal()
    def __init__(self, ctx: AppContext) -> None:
        super().__init__()
        self.ctx = ctx
        self.report: DiagnosisReport | None = None

        root = QVBoxLayout(self)

        self.overview_label = QLabel('正在检查营地状态…')
        self.overview_label.setWordWrap(True)
        self.overview_label.setStyleSheet('color: #ead7a4; padding: 10px 4px;')
        self.overview_label.setTextFormat(Qt.PlainText)
        root.addWidget(self.overview_label)
        guide = QGroupBox('开始使用 · 三步完成整备')
        steps = QHBoxLayout(guide)
        for title, action in [('1. 确认游戏目录', self.choose_game.emit),
                              ('2. 检查当前汉化', self.localization.emit),
                              ('3. 浏览在线 MOD', lambda: self.browse_mods.emit(''))]:
            button = QPushButton(title)
            button.clicked.connect(lambda checked=False, callback=action: callback())
            steps.addWidget(button)
        root.addWidget(guide)

        # 游戏状态卡
        info_box = QGroupBox("游戏状态")
        info_layout = QHBoxLayout(info_box)
        self.info_label = QLabel("检测中…")
        self.info_label.setWordWrap(True)
        self.info_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.info_label.hide()
        details_btn = QPushButton('显示目录与技术详情')
        details_btn.setCheckable(True)
        details_btn.toggled.connect(self.info_label.setVisible)
        self.refresh_btn = QPushButton("重新检测")
        style_button(self.refresh_btn, "refresh")
        self.refresh_btn.clicked.connect(self.refresh)
        info_layout.addWidget(self.info_label, 1)
        info_layout.addWidget(details_btn)
        info_layout.addWidget(self.refresh_btn)
        root.addWidget(info_box)

        # 诊断结果
        diag_box = QGroupBox("健康诊断（冲突 / 版本 / 影响种子 / 上次启动报错）")
        diag_layout = QVBoxLayout(diag_box)
        self.summary_label = QLabel("—")
        self.show_info = QPushButton('显示普通提示')
        self.show_info.setCheckable(True)
        self.show_info.toggled.connect(lambda: self._show_report(self.report) if self.report else None)
        self.support_btn = QPushButton('提交错误报告…')
        self.support_btn.setToolTip('预览诊断结果和近期日志，确认后提交到官网；也可导出 TXT。')
        self.support_btn.clicked.connect(lambda: self.support_requested.emit())
        tools = QHBoxLayout()
        tools.addWidget(self.show_info)
        tools.addWidget(self.support_btn)
        diag_layout.addLayout(tools)
        self.table = QTableWidget(0, 4)
        style_table(self.table)
        self.table.setColumnWidth(0, 68)
        self.table.setColumnWidth(1, 230)
        self.table.setColumnWidth(3, 260)
        self.table.setHorizontalHeaderLabels(["级别", "对象", "问题", "修复建议"])
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setWordWrap(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        diag_layout.addWidget(self.summary_label)
        diag_layout.addWidget(self.table, 1)
        root.addWidget(diag_box, 1)

    def refresh(self) -> None:
        if getattr(self, "_worker", None) and self._worker.isRunning():
            self._refresh_pending = True
            return
        g = self.ctx.game
        if not g:
            self.info_label.setText("未找到游戏，请点击上方「更换目录」指定安装目录。")
            return
        base = game_mod.check_base_archive(g.data_dir)
        dlcs = game_mod.installed_dlcs(g.data_dir)
        base_txt = base.summary if base else "未找到 data_001.dat"
        lines = [
            f"安装目录：{g.root}",
            f"游戏版本：{g.version}（本软件按 1.5.2.3 校准）   基座档案：{base_txt}",
            f"DLC：{sum(dlcs.values())}/{len(dlcs)}",
            f"日志目录：{self.ctx.log_dir() or '未找到'}",
        ]
        self.info_label.setText("\n".join(lines))

        self.refresh_btn.setEnabled(False)
        track(self, "_worker", Worker(self._run_diagnosis, self))
        self._worker.done.connect(self._show_report)
        self._worker.failed.connect(lambda e: (self.summary_label.setText(f"诊断失败：{e}"),
                                               self.refresh_btn.setEnabled(True)))
        self._worker.finished.connect(self._finish_refresh)
        self._worker.start()

    def _finish_refresh(self) -> None:
        if getattr(self, "_refresh_pending", False):
            self._refresh_pending = False
            self.refresh()

    def _run_diagnosis(self) -> DiagnosisReport:
        g = self.ctx.game
        analyze = self.ctx.mm.analyze if self.ctx.mm else analyze_zip
        installed = [analyze(z) for z in sorted(g.data_dir.glob("*.zip"))]
        log_dir = self.ctx.log_dir()
        rows = load_log(log_dir / "log.html") if log_dir else []
        return diagnose(g, installed, rows)

    def _show_report(self, report: DiagnosisReport) -> None:
        self.report = report
        issues = [issue for issue in report.sorted() if issue.severity != 'info' or self.show_info.isChecked()]
        self.summary_label.setText(
            f"共 {len(report.issues)} 条 —— 错误 {report.error_count} · 警告 {report.warning_count} · 提示 "
            f"{len(report.issues) - report.error_count - report.warning_count}"
        )
        self.table.setRowCount(0)
        self.table.setRowCount(len(issues))
        for i, issue in enumerate(issues):
            level = QTableWidgetItem(SEVERITY_TEXT[issue.severity])
            if issue.severity == "error":
                level.setForeground(QColor(RED))
            elif issue.severity == "warning":
                level.setForeground(QColor("#8b601f"))
            else:
                level.setForeground(QColor(MUTED))
            self.table.setItem(i, 0, level)
            self.table.setItem(i, 1, QTableWidgetItem(issue.source))
            self.table.setItem(i, 2, QTableWidgetItem(issue.title + (f"\n{issue.detail[:200]}" if issue.detail else "")))
            self.table.setItem(i, 3, QTableWidgetItem(issue.fix or ""))
            if issue.dependency:
                button = QPushButton('查找前置：' + issue.dependency)
                button.setToolTip(issue.fix or '在官网军械库中查找前置')
                button.clicked.connect(lambda checked=False, target=issue.dependency: self.browse_mods.emit(target))
                self.table.setCellWidget(i, 3, button)
        self.table.resizeRowsToContents()
        self.refresh_btn.setEnabled(True)

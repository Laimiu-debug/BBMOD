"""主窗口：四页签 + 设置。"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import (
    QFileDialog, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox,
    QPushButton, QTabWidget, QVBoxLayout, QWidget,
)

from .app_context import AppContext
from .dashboard_page import DashboardPage
from .l10n_page import L10nPage
from .mods_page import ModsPage
from .seedgen_page import SeedGenPage


def apply_dark_palette(app) -> None:
    app.setStyle("Fusion")
    pal = QPalette()
    bg = QColor(37, 37, 38)
    base = QColor(30, 30, 30)
    text = QColor(214, 214, 214)
    highlight = QColor(66, 133, 244)
    for group in (QPalette.Active, QPalette.Inactive):
        pal.setColor(group, QPalette.Window, bg)
        pal.setColor(group, QPalette.WindowText, text)
        pal.setColor(group, QPalette.Base, base)
        pal.setColor(group, QPalette.AlternateBase, bg)
        pal.setColor(group, QPalette.Text, text)
        pal.setColor(group, QPalette.Button, bg)
        pal.setColor(group, QPalette.ButtonText, text)
        pal.setColor(group, QPalette.Highlight, highlight)
        pal.setColor(group, QPalette.HighlightedText, Qt.white)
        pal.setColor(group, QPalette.ToolTipBase, base)
        pal.setColor(group, QPalette.ToolTipText, text)
    pal.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(120, 120, 120))
    pal.setColor(QPalette.Disabled, QPalette.Text, QColor(120, 120, 120))
    app.setPalette(pal)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("BBMOD 管理器 —— 战场兄弟 1.5.2.3 汉化 / MOD / 刷种子")
        self.resize(1180, 780)
        self.ctx = AppContext()

        central = QWidget()
        lay = QVBoxLayout(central)

        # 顶部：游戏路径条
        path_bar = QHBoxLayout()
        self.path_edit = QLineEdit(str(self.ctx.game.root) if self.ctx.game else "未找到游戏")
        self.path_edit.setReadOnly(True)
        pick_btn = QPushButton("手动指定游戏目录…")
        pick_btn.clicked.connect(self.pick_game_dir)
        path_bar.addWidget(QLabel("游戏："), 0)
        path_bar.addWidget(self.path_edit, 1)
        path_bar.addWidget(pick_btn)
        lay.addLayout(path_bar)

        self.tabs = QTabWidget()
        self.dashboard = DashboardPage(self.ctx)
        self.mods = ModsPage(self.ctx)
        self.l10n = L10nPage(self.ctx)
        self.seedgen = SeedGenPage(self.ctx)
        self.tabs.addTab(self.dashboard, "仪表盘")
        self.tabs.addTab(self.mods, "MOD 管理")
        self.tabs.addTab(self.l10n, "一键汉化")
        self.tabs.addTab(self.seedgen, "刷种子")
        lay.addWidget(self.tabs, 1)
        self.setCentralWidget(central)

        # 数据变化 → 各页刷新
        self.ctx.data_changed.connect(self.dashboard.refresh)
        self.ctx.game_changed.connect(self._on_game_changed)

        # 首次加载
        self.dashboard.refresh()
        self.mods.refresh()
        self.l10n.refresh_status()

    def pick_game_dir(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "选择 Battle Brothers 安装目录（含 win32/BattleBrothers.exe）")
        if not d:
            return
        if self.ctx.relocate_game(d):
            self.path_edit.setText(str(self.ctx.game.root))
            QMessageBox.information(self, "游戏目录", f"已定位：{self.ctx.game.root}")
        else:
            QMessageBox.warning(self, "无效目录", "该目录下未找到 win32/BattleBrothers.exe")

    def _on_game_changed(self) -> None:
        self.path_edit.setText(str(self.ctx.game.root) if self.ctx.game else "未找到游戏")
        self.dashboard.refresh()
        self.mods.refresh()
        self.l10n.refresh_status()

    def closeEvent(self, event) -> None:  # noqa: N802
        # 刷种子会话未结束时提醒（自动恢复，避免 mod 留在暂存区）
        if self.seedgen.orch is not None:
            ans = QMessageBox.question(
                self, "刷种子进行中",
                "刷种子会话尚未结束（游戏 mod 已暂存）。现在停止并恢复吗？",
                QMessageBox.Yes | QMessageBox.Cancel,
            )
            if ans != QMessageBox.Yes:
                event.ignore()
                return
            self.seedgen.stop()
        event.accept()

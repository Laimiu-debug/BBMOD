"""Mercenary camp shell: persistent navigation and four workspaces."""
from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QButtonGroup, QFileDialog, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QMessageBox, QPushButton, QStackedWidget, QVBoxLayout, QWidget,
)
from .app_context import AppContext
from .dashboard_page import DashboardPage
from .l10n_page import L10nPage
from .mods_page import ModsPage
from .seedgen_page import SeedGenPage
from .theme import GOLD, CampHeader, ParchmentSurface, apply_theme, crest, icon, style_button

PAGES = [
    ('camp', '营地总览', 'CAMP OVERVIEW', '出发之前，检查游戏、依赖与战团整备情况。'),
    ('shield', 'MOD 军械库', 'THE ARMORY', '挑选装备，管理模组，为每一次战役保存配置。'),
    ('book', '汉化工坊', "THE SCRIBE’S WORKSHOP", '选择汉化 · 管理方案 · 整备后启动游戏。'),
    ('compass', '种子远征', 'SEED EXPEDITION', '设定开局条件，寻找值得出发的新世界。'),
]


def apply_dark_palette(app) -> None:
    """Compatibility entry point for existing launch scripts."""
    apply_theme(app)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle('BBMOD · 战团整备所')
        self.setWindowIcon(crest())
        self.resize(1360, 880)
        self.setMinimumSize(1080, 720)
        self.ctx = AppContext()
        root = QWidget()
        root.setObjectName('windowRoot')
        shell = QHBoxLayout(root)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)
        sidebar = ParchmentSurface()
        sidebar.setObjectName('sidebar')
        sidebar.setFixedWidth(208)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(12, 22, 16, 18)
        side.setSpacing(8)
        badge = QLabel()
        badge.setAlignment(Qt.AlignCenter)
        badge.setPixmap(crest().pixmap(164, 164))
        side.addWidget(badge)
        brand = QLabel('BBMOD')
        brand.setObjectName('brandName')
        brand.setAlignment(Qt.AlignCenter)
        side.addWidget(brand)
        subtitle = QLabel('战 团 整 备 所')
        subtitle.setObjectName('brandSubtitle')
        subtitle.setAlignment(Qt.AlignCenter)
        side.addWidget(subtitle)
        side.addSpacing(20)
        self.nav_group = QButtonGroup(self)
        self.nav_buttons = []
        for index, (glyph, title, _, _) in enumerate(PAGES):
            button = QPushButton(title)
            button.setObjectName('navButton')
            button.setIcon(icon(glyph, GOLD, 28))
            button.setIconSize(QSize(28, 28))
            button.setCheckable(True)
            button.setCursor(Qt.PointingHandCursor)
            button.setToolTip(f'{title}  ·  Alt+{index + 1}')
            button.setShortcut(f'Alt+{index + 1}')
            self.nav_group.addButton(button, index)
            self.nav_buttons.append(button)
            side.addWidget(button)
        side.addStretch()
        footer = QLabel('BATTLE BROTHERS\n\n为下一次战役做好准备\n游戏版本 1.5.2.3')
        footer.setObjectName('sidebarFooter')
        footer.setAlignment(Qt.AlignCenter)
        side.addWidget(footer)
        shell.addWidget(sidebar)
        workspace = ParchmentSurface()
        workspace.setObjectName('workspace')
        content = QVBoxLayout(workspace)
        content.setContentsMargins(17, 15, 17, 11)
        content.setSpacing(8)
        hero = CampHeader()
        header = QHBoxLayout(hero)
        header.setContentsMargins(20, 12, 18, 12)
        titles = QVBoxLayout()
        titles.setSpacing(5)
        self.eyebrow = QLabel()
        self.eyebrow.setObjectName('pageEyebrow')
        self.heading = QLabel()
        self.heading.setObjectName('pageHeading')
        self.subtitle = QLabel()
        self.subtitle.setObjectName('pageSubtitle')
        titles.addWidget(self.eyebrow)
        titles.addWidget(self.heading)
        titles.addWidget(self.subtitle)
        header.addLayout(titles, 1)
        self.version_badge = QLabel('BATTLE BROTHERS  /  1.5.2.3')
        self.version_badge.setObjectName('versionBadge')
        header.addWidget(self.version_badge, 0, Qt.AlignBottom)
        content.addWidget(hero)
        game_bar = QFrame()
        game_bar.setObjectName('gameBar')
        path_layout = QHBoxLayout(game_bar)
        path_layout.setContentsMargins(10, 3, 7, 3)
        path_layout.addWidget(QLabel('游戏目录'))
        self.path_edit = QLineEdit(str(self.ctx.game.root) if self.ctx.game else '未找到游戏，请指定安装目录')
        self.path_edit.setObjectName('gamePath')
        self.path_edit.setReadOnly(True)
        path_layout.addWidget(self.path_edit, 1)
        self.pick_btn = QPushButton('更换目录')
        style_button(self.pick_btn, 'folder')
        self.pick_btn.clicked.connect(self.pick_game_dir)
        path_layout.addWidget(self.pick_btn)
        self.launch_btn = QPushButton('启动游戏')
        style_button(self.launch_btn, 'play', primary=True)
        self.launch_btn.clicked.connect(self.launch_game)
        path_layout.addWidget(self.launch_btn)
        content.addWidget(game_bar)
        self.tabs = QStackedWidget()
        self.dashboard = DashboardPage(self.ctx)
        self.mods = ModsPage(self.ctx)
        self.l10n = L10nPage(self.ctx)
        self.seedgen = SeedGenPage(self.ctx)
        for page in (self.dashboard, self.mods, self.l10n, self.seedgen):
            page.layout().setContentsMargins(0, 0, 0, 0)
            self.tabs.addWidget(page)
        content.addWidget(self.tabs, 1)
        footnote = QLabel('BBMOD  ·  本地管理工具                                      Alt + 1–4 切换工作台')
        footnote.setObjectName('mainFooter')
        content.addWidget(footnote)
        shell.addWidget(workspace, 1)
        self.setCentralWidget(root)
        self.nav_group.idClicked.connect(self.select_page)
        self.select_page(0)
        self.ctx.data_changed.connect(self.dashboard.refresh)
        self.ctx.data_changed.connect(self.mods.refresh)
        self.ctx.data_changed.connect(self.l10n.refresh_status)
        self.ctx.session_changed.connect(self._session_changed)
        self.ctx.management_changed.connect(self._management_changed)
        self.ctx.game_changed.connect(self._on_game_changed)
        self.dashboard.refresh()
        self.mods.refresh()
        self.l10n.refresh_status()

    def _session_changed(self, active: bool) -> None:
        self._management_changed(self.ctx.management_busy)
        self.l10n.refresh_status()

    def _management_changed(self, busy: bool) -> None:
        locked = busy or self.ctx.seedgen_active
        for button in (self.mods.disable_btn, self.mods.enable_btn, self.mods.uninstall_btn,
                self.mods.save_profile_btn, self.mods.apply_profile_btn, self.mods.install_btn, self.pick_btn, self.launch_btn):
            button.setEnabled(not locked)
        self.seedgen.start_btn.setEnabled(not locked)
        self.l10n._set_busy(self.l10n._busy)
        self.l10n.management.update_controls()

    def launch_game(self) -> None:
        self.select_page(2)
        self.l10n.sections.setCurrentIndex(0)
        self.l10n.management.launch_current()

    def select_page(self, index: int) -> None:
        _, title, eyebrow, subtitle = PAGES[index]
        self.tabs.setCurrentIndex(index)
        self.nav_buttons[index].setChecked(True)
        self.heading.setText(title)
        self.eyebrow.setText(eyebrow)
        self.subtitle.setText(subtitle)
        if index == 1 and not hasattr(self.mods, '_repo_entries'):
            self.mods.refresh_repo()

    def pick_game_dir(self) -> None:
        if self.ctx.management_busy:
            return
        if self.seedgen.orch is not None:
            QMessageBox.information(self, '种子远征进行中', '请先停止并恢复当前游戏，再更换目录。')
            return
        directory = QFileDialog.getExistingDirectory(self, '选择游戏目录（含 win32/BattleBrothers.exe）')
        if directory and not self.ctx.relocate_game(directory):
            QMessageBox.warning(self, '无效目录', '该目录下未找到 win32/BattleBrothers.exe')

    def _on_game_changed(self) -> None:
        self.path_edit.setText(str(self.ctx.game.root) if self.ctx.game else '未找到游戏')
        self.dashboard.refresh()
        self.mods.refresh()
        self.l10n.refresh_status()

    def closeEvent(self, event) -> None:
        if self.seedgen.orch is not None:
            answer = QMessageBox.question(self, '种子远征进行中', '现在停止并恢复游戏配置吗？', QMessageBox.Yes | QMessageBox.Cancel)
            if answer != QMessageBox.Yes:
                event.ignore()
                return
            self.seedgen.stop()
            if self.seedgen.orch is not None:
                event.ignore()
                return
        from .workers import Worker
        if any(worker.isRunning() for worker in self.findChildren(Worker)):
            QMessageBox.information(self, '任务处理中', '正在读取或构建文件，请等待完成后关闭。')
            event.ignore()
            return
        event.accept()

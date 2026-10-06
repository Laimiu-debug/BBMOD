"""Mercenary camp shell: persistent navigation, workspaces and preferences."""
from __future__ import annotations

from PySide6.QtCore import QSize, Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices
from core.site_config import SITE_ORIGIN
from core.version import VERSION
from PySide6.QtWidgets import (
    QButtonGroup, QFileDialog, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QLayout, QMainWindow, QMessageBox, QPushButton, QScrollArea, QSizePolicy,
    QStackedWidget, QTableWidget, QVBoxLayout, QWidget,
)
from .app_context import AppContext
from .dashboard_page import DashboardPage
from .l10n_page import L10nPage
from .mods_page import ModsPage
from .profiles_page import ProfilesPage
from .seedgen_page import SeedGenPage
from .settings_page import SettingsPage
from .feedback_page import FeedbackPage
from .inspector_page import InspectorPage
from .update_service import UpdateService
from .update_dialog import UpdateDialog
from .update_notice import UpdateNotice
from .theme import GOLD, CampHeader, ParchmentSurface, apply_theme, crest, fit_table_font, icon, style_button

PAGES = [
    ('camp', '营地总览', 'CAMP OVERVIEW', '出发之前，检查游戏、依赖与战团整备情况。'),
    ('shield', 'MOD 军械库', 'THE ARMORY', '挑选装备，管理模组，为每一次战役保存配置。'),
    ('book', '汉化管理', 'LOCALIZATION', '查看当前汉化，按需切换；日常游玩直接启动游戏。'),
    ('compass', '种子远征', 'SEED EXPEDITION', '设定开局条件，寻找值得出发的新世界。'),
    ('settings', '设置', 'SETTINGS', '管理软件更新、错误报告、字体与字号。'),
    ('shield', '装备百科', 'EQUIPMENT CODEX', '查阅装备属性与红装范围；装备鉴定可对照游戏中实际获得的红装。'),
    ('book', '反馈与建议', 'FEEDBACK', '把问题和想法直接送达 BBMOD 管理后台。'),
    ('book', '方案管理', 'MOD PROFILES', '整理本地 MOD 组合，直接浏览并应用网站共享方案。'),
]
NAV_ORDER = (0, 1, 7, 2, 3, 5, 6, 4)


def apply_dark_palette(app) -> None:
    """Compatibility entry point for existing launch scripts."""
    from core.windows_shell import set_app_identity
    set_app_identity()
    apply_theme(app)


class MainWindow(QMainWindow):
    def __init__(self, *, auto_updates=True) -> None:
        super().__init__()
        self.setWindowTitle('BBMOD · 战团整备所')
        self.setWindowIcon(crest())
        self.resize(1360, 880)
        self.setMinimumSize(1080, 720)
        self.ctx = AppContext()
        self.updates = UpdateService(self.ctx.settings, self, automatic=auto_updates)
        self._update_dialog = None
        self._pending_update = None
        root = QWidget()
        root.setObjectName('windowRoot')
        shell = QHBoxLayout(root)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)
        sidebar = ParchmentSurface()
        self.sidebar = sidebar
        sidebar.setObjectName('sidebar')
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(12, 14, 16, 14)
        side.setSpacing(6)
        badge = self.website_badge = QPushButton()
        badge.setObjectName('websiteBadge')
        badge.setIcon(crest())
        badge.setIconSize(QSize(112, 112))
        badge.setFixedHeight(116)
        badge.setCursor(Qt.PointingHandCursor)
        badge.setAccessibleName('打开 BBMOD 官网')
        badge.setToolTip('打开 BBMOD 官网 · ' + SITE_ORIGIN)
        badge.setStyleSheet('QPushButton { background: transparent; border: none; padding: 0; }')
        badge.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(SITE_ORIGIN)))
        side.addWidget(badge)
        brand = QLabel('BBMOD')
        brand.setObjectName('brandName')
        brand.setAlignment(Qt.AlignCenter)
        side.addWidget(brand)
        subtitle = QLabel('战 团 整 备 所')
        subtitle.setObjectName('brandSubtitle')
        subtitle.setAlignment(Qt.AlignCenter)
        side.addWidget(subtitle)
        side.addSpacing(12)
        self.nav_group = QButtonGroup(self)
        self.nav_buttons = []
        for index, (glyph, title, _, _) in enumerate(PAGES):
            button = QPushButton(title)
            button.setObjectName('navButton')
            button.setIcon(icon(glyph, GOLD, 28))
            button.setIconSize(QSize(28, 28))
            button.setCheckable(True)
            button.setCursor(Qt.PointingHandCursor)
            shortcut = NAV_ORDER.index(index) + 1
            button.setToolTip(f'{title}  ·  Alt+{shortcut}')
            button.setShortcut(f'Alt+{shortcut}')
            self.nav_group.addButton(button, index)
            self.nav_buttons.append(button)
        for index in NAV_ORDER:
            if index == 4:
                side.addStretch()
                side.addSpacing(10)
            side.addWidget(self.nav_buttons[index])
        footer = QLabel('BATTLE BROTHERS\n游戏版本 1.5.2.3')
        footer.setObjectName('sidebarFooter')
        footer.setAlignment(Qt.AlignCenter)
        side.addWidget(footer)
        self.sidebar_scroll = QScrollArea()
        self.sidebar_scroll.setObjectName('sidebarScroll')
        self.sidebar_scroll.setFrameShape(QFrame.NoFrame)
        self.sidebar_scroll.setWidgetResizable(True)
        self.sidebar_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.sidebar_scroll.setFixedWidth(208)
        self.sidebar_scroll.setWidget(sidebar)
        shell.addWidget(self.sidebar_scroll)
        workspace = ParchmentSurface()
        workspace.setObjectName('workspace')
        content = QVBoxLayout(workspace)
        content.setContentsMargins(17, 15, 17, 11)
        content.setSpacing(8)
        hero = CampHeader()
        hero.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
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
        self.subtitle.setWordWrap(True)
        titles.addWidget(self.eyebrow)
        titles.addWidget(self.heading)
        titles.addWidget(self.subtitle)
        header.addLayout(titles, 1)
        self.version_badge = QPushButton(f'BBMOD {VERSION}\n版本与更新')
        self.version_badge.setObjectName('versionBadge')
        self.version_badge.setToolTip('查看软件版本、发布历史和自动更新设置')
        self.version_badge.clicked.connect(self.show_updates)
        self.updates.attention.connect(lambda tag: self.version_badge.setText(f'发现新版本 {tag}\n查看更新'))
        self.updates.changed.connect(self._update_badge)
        header.addWidget(self.version_badge, 0, Qt.AlignBottom)
        content.addWidget(hero)
        self.update_notice = UpdateNotice(self.updates, self.ctx, self)
        self.update_notice.history_requested.connect(self.show_latest_update)
        self.update_notice.install_requested.connect(self._request_update)
        content.addWidget(self.update_notice)
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
        self.game_status = QLabel()
        self.game_status.setObjectName('workspaceHint')
        self.game_status.setWordWrap(True)
        self.game_status.hide()
        content.addWidget(self.game_status)
        self.crash_notice = QPushButton()
        self.crash_notice.setObjectName('crashReportNotice')
        self.crash_notice.hide()
        self.crash_notice.clicked.connect(self.show_crash_reports)
        content.addWidget(self.crash_notice)
        self.tabs = QStackedWidget()
        self.dashboard = DashboardPage(self.ctx)
        self.mods = ModsPage(self.ctx, automatic_catalog=auto_updates)
        self.mods.choose_game_requested.connect(self.pick_game_dir)
        self.profiles = ProfilesPage(self.ctx, self.mods)
        self.profiles.choose_game_requested.connect(self.pick_game_dir)
        self.mods.profiles_requested.connect(self.browse_profiles)
        self.l10n = L10nPage(self.ctx)
        self.seedgen = SeedGenPage(self.ctx)
        self.settings_page = SettingsPage(self.ctx.settings, self.updates)
        self.settings_page.updates.install_requested.connect(self._request_update)
        self.settings_page.updates.history_requested.connect(self.show_updates)
        self.inspector = InspectorPage(self.ctx, register_hotkey=auto_updates)
        self.feedback = FeedbackPage()
        self.feedback.support_requested.connect(self.preview_support)
        self.dashboard.support_requested.connect(self.preview_support)
        from .crash_reports import CrashReports
        self.crash_reports = CrashReports(self.ctx, self, automatic=auto_updates)
        self.crash_reports.changed.connect(self._crash_reports_changed)
        self.settings_page.crash_reports_requested.connect(self.show_crash_reports)
        self.settings_page.crash_upload_changed.connect(self.crash_reports.pump)
        self._crash_dialog = None
        self._crash_reports_changed()
        self.dashboard.choose_game.connect(self.pick_game_dir)
        self.dashboard.localization.connect(lambda: self.select_page(2))
        self.dashboard.browse_mods.connect(self.browse_mods)
        self.page_scrolls = []
        for page in (self.dashboard, self.mods, self.l10n, self.seedgen, self.settings_page, self.inspector, self.feedback, self.profiles):
            page.layout().setContentsMargins(0, 0, 0, 0)
            page.layout().setSizeConstraint(QLayout.SetMinimumSize)
            scroll = QScrollArea()
            scroll.setObjectName('pageScroll')
            scroll.setFrameShape(QFrame.NoFrame)
            scroll.setWidgetResizable(True)
            scroll.setWidget(page)
            self.page_scrolls.append(scroll)
            self.tabs.addWidget(scroll)
        content.addWidget(self.tabs, 1)
        footnote = QLabel('BBMOD  ·  本地管理工具                         Alt + 1–8 切换页面')
        footnote.setObjectName('mainFooter')
        content.addWidget(footnote)
        shell.addWidget(workspace, 1)
        self.setCentralWidget(root)
        self.settings_page.applied.connect(self._fit_typography)
        self.nav_group.idClicked.connect(self.select_page)
        self.select_page(0)
        self.ctx.data_changed.connect(self.dashboard.refresh)
        self.ctx.data_changed.connect(self.mods.refresh)
        self.ctx.data_changed.connect(self.l10n.refresh_status)
        self.ctx.session_changed.connect(self._session_changed)
        self.ctx.management_changed.connect(self._management_changed)
        self.ctx.game_changed.connect(self._on_game_changed)
        self.l10n.management.review_requested.connect(self._review_localization)
        self.l10n.management.controls_changed.connect(self._update_launch_controls)
        self.ctx.game_session.changed.connect(self._update_launch_controls)
        from PySide6.QtWidgets import QApplication
        QApplication.instance().aboutToQuit.connect(self.ctx.game_session.shutdown)
        QApplication.instance().aboutToQuit.connect(self.crash_reports.shutdown)
        self.dashboard.refresh()
        self.mods.refresh()
        self.l10n.refresh_status()
        self._update_launch_controls()
        self.ctx.game_session.start()
        self._fit_typography()
        self._update_badge()

    def _fit_typography(self):
        # Recalculate after the stylesheet has updated widget font metrics.
        QTimer.singleShot(0, self._resize_navigation)

    def browse_mods(self, query=''):
        self.select_page(1)
        self.mods.open_online(query)

    def browse_profiles(self, online=False):
        self.select_page(7)
        if online:
            self.profiles.open_online()
        else:
            self.profiles.sections.setCurrentIndex(0)

    def open_web_link(self, link):
        self.showNormal()
        self.raise_()
        self.activateWindow()
        if not link:
            return
        from core.web_links import parse_link, fetch_seed
        from core.site_config import SITE_ORIGIN
        from .workers import Worker, track
        try:
            kind, identity = parse_link(link)
            if self.ctx.management_busy or self.ctx.seedgen_active:
                raise ValueError('请等待当前文件操作或种子远征结束，再打开网页链接。')
            if kind == 'mods':
                if self.mods.online.worker and self.mods.online.worker.isRunning():
                    raise ValueError('正在读取军械库，请稍后重试链接。')
                self.select_page(1)
                self.mods.sections.setCurrentIndex(2)
                self.mods.online.address.setText(SITE_ORIGIN)
                self.mods.online.pending_mod_id = identity
                self.mods.online.refresh()
            elif kind == 'profiles':
                self.select_page(7)
                self.profiles.sharing.import_link(identity, origin=SITE_ORIGIN)
            else:
                if getattr(self, '_seed_import_worker', None) and self._seed_import_worker.isRunning():
                    raise ValueError('正在导入种子，请稍后重试。')
                track(self, '_seed_import_worker', Worker(lambda: fetch_seed(identity), self))
                self._seed_import_worker.done.connect(self._preview_seed_import)
                self._seed_import_worker.failed.connect(lambda error: QMessageBox.warning(self, '种子读取失败', error))
                self._seed_import_worker.start()
        except ValueError as exc:
            QMessageBox.warning(self, '无法打开链接', str(exc))

    def _preview_seed_import(self, record):
        result, note = record
        from core.seedgen.presentation import format_seed
        from core.seedgen.protocol import seed_key
        from core.seedgen.presentation import note_key
        if QMessageBox.question(self, '导入网页种子', format_seed(result, note=note)[:6000] + '\n\n保存到「我的种子」？',
                                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            return
        try:
            if not self.seedgen.library:
                raise ValueError('本地种子库不可用，请先处理存储问题。')
            self.seedgen.library.save(result)
            self.seedgen.library.restore([seed_key(result)])
            if note and note_key(result) not in self.seedgen.notes:
                self.seedgen.notes[note_key(result)] = note
                self.ctx.settings.set('seed_notes', self.seedgen.notes)
            self.seedgen.results = self.seedgen.library.all()
            self.seedgen.library_view.setCurrentIndex(0)
            self.seedgen.library_search.setText(result.seed)
            self.seedgen._rebuild_library()
            self.select_page(3)
            self.seedgen.sections.setCurrentIndex(1)
            self.seedgen.library_label.setText('已导入网页种子。开局时请使用记录中的起源、版本和难度。')
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, '导入失败', str(exc))

    def preview_support(self):
        from core.support_report import build_report
        from .support_dialog import SupportDialog
        try:
            dialog = SupportDialog(build_report(self.ctx, self.dashboard.report), self)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, '诊断报告生成失败', str(exc))
            return
        if dialog.exec() == SupportDialog.DialogCode.Accepted:
            title = next((issue.title for issue in self.dashboard.report.sorted() if issue.severity == 'error'),
                         '游戏运行错误报告') if self.dashboard.report else '游戏运行错误报告'
            if not self.feedback.attach_report(dialog.editor.toPlainText(), title):
                QMessageBox.information(self, '报告未加入', self.feedback.status.text())
                return
            self.select_page(6)

    def _crash_reports_changed(self):
        pending = [item for item in self.crash_reports.store.records() if item['state'] != 'sent']
        self.crash_notice.setVisible(bool(pending) or bool(self.crash_reports.status))
        status = self.crash_reports.status.split('\n')[0]
        self.crash_notice.setText(f'错误报告：{len(pending)} 份待处理 · 点击查看' + (f' · {status[:70]}' if status else ''))

    def show_crash_reports(self):
        from .crash_report_dialog import CrashReportDialog
        if self._crash_dialog is None:
            self._crash_dialog = CrashReportDialog(self.crash_reports, self)
        else:
            self._crash_dialog.refresh()
        self._crash_dialog.show()
        self._crash_dialog.raise_()
        self._crash_dialog.activateWindow()

    def _resize_navigation(self):
        width = max(208, max(button.sizeHint().width() for button in self.nav_buttons) + 42)
        self.sidebar_scroll.setFixedWidth(width)
        self.sidebar_scroll.ensureWidgetVisible(self.nav_buttons[self.tabs.currentIndex()])
        for table in self.findChildren(QTableWidget):
            fit_table_font(table)

    def _update_badge(self):
        latest = self.updates.latest()
        if latest and latest.newer_than() and latest.tag != self.updates.preferences.get('ignored'):
            self.version_badge.setText(f'发现新版本 {latest.tag}\n查看更新')
        else:
            self.version_badge.setText(f'BBMOD {VERSION}\n版本与更新')

    def show_updates(self):
        if self._update_dialog is None:
            self._update_dialog = UpdateDialog(self.updates, self)
            self._update_dialog.install_requested.connect(self._request_update)
        self._update_dialog.show()
        self._update_dialog.raise_()
        self._update_dialog.activateWindow()

    def show_latest_update(self):
        self.show_updates()
        self._update_dialog.versions.setCurrentRow(0)

    def _request_update(self):
        from core.app_updates import prepare_install
        from .workers import Worker
        if self.ctx.management_busy or self.ctx.seedgen_active or self.seedgen.orch is not None or any(worker.isRunning() for worker in self.findChildren(Worker)):
            self.updates.status = '请先停止种子远征，并等待文件或 MOD 操作完成，再重启更新。'
            self.updates.changed.emit()
            return
        release = self.updates.download_release
        if not self.updates.downloaded or not release or not release.newer_than() or self.updates.busy:
            return
        try:
            self._pending_update = prepare_install(self.updates.downloaded, release)
            if not self.updates.save_preference('pending', str(self._pending_update.parent / 'result.json')):
                self._pending_update = None
                return
            self.close()
        except (OSError, ValueError) as error:
            self._pending_update = None
            self.updates.status = '暂时无法更新：' + str(error) + '；下载文件已保留。'
            self.updates.changed.emit()

    def _session_changed(self, active: bool) -> None:
        self._management_changed(self.ctx.management_busy)
        self.l10n.refresh_status()

    def _management_changed(self, busy: bool) -> None:
        locked = busy or self.ctx.seedgen_active
        for button in (self.mods.save_profile_btn, self.mods.apply_profile_btn, self.mods.install_btn, self.pick_btn):
            button.setEnabled(not locked)
        self.mods.update_controls()
        self.seedgen.start_btn.setEnabled(not locked)
        self.l10n._set_busy(self.l10n._busy)
        self.l10n.management.update_controls()
        self._update_launch_controls()

    def launch_game(self) -> None:
        self.l10n.management.launch_current()

    def _review_localization(self) -> None:
        self.select_page(2)
        self.l10n.sections.setCurrentIndex(0)

    def _update_launch_controls(self) -> None:
        session = self.ctx.game_session
        page = self.l10n.management
        pending = bool(self.ctx.mm and self.ctx.mm.transaction.journal.exists())
        locked = self.ctx.management_busy or self.ctx.seedgen_active or session.occupied or pending
        self.launch_btn.setEnabled(bool(self.ctx.game) and not locked)
        if session.occupied:
            text, hint = session.button_text, session.message
        elif not self.ctx.game:
            text, hint = '启动游戏', '请先指定游戏目录'
        elif not page.plan:
            text, hint = '检查汉化配置', '打开汉化管理，查看需要处理的问题；尚未启动游戏'
        elif page.plan.changed:
            text, hint = '确认汉化方案', '所选汉化尚未应用，先查看变更；尚未启动游戏'
        else:
            text, hint = '启动游戏', '使用当前已应用的配置启动一次游戏'
        self.launch_btn.setText(text)
        self.launch_btn.setToolTip(hint)
        self.game_status.setText(session.message)
        self.game_status.setVisible(bool(session.message))
        self.dashboard.overview_label.setText(f'{"需要恢复上次 MOD 操作" if pending else text}\n当前汉化：{page.current_name.text()}')

    def select_page(self, index: int) -> None:
        _, title, eyebrow, subtitle = PAGES[index]
        self.tabs.setCurrentIndex(index)
        self.nav_buttons[index].setChecked(True)
        self.heading.setText(title)
        self.eyebrow.setText(eyebrow)
        self.subtitle.setText(subtitle)
        self.sidebar_scroll.ensureWidgetVisible(self.nav_buttons[index])
        if index == 1 and not hasattr(self.mods, '_repo_entries'):
            self.mods.refresh_repo()
        if index == 1 and self.mods.automatic_catalog:
            self.mods.check_catalog()
        elif index == 7:
            self.profiles.refresh()

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
        # The periodic process probe is joined by GameSession.shutdown below;
        # it must not make closing depend on which 1.5-second tick was hit.
        if any(worker.isRunning() for worker in self.findChildren(Worker)
               if worker not in (self.seedgen._share_worker, self.ctx.game_session._worker)):
            QMessageBox.information(self, '任务处理中', '正在读取或构建文件，请等待完成后关闭。')
            event.ignore()
            return
        explicit_update = bool(self._pending_update)
        if not explicit_update:
            import sys
            from core.app_updates import prepare_install
            release = self.updates.download_release
            if (getattr(sys, 'frozen', False) and self.updates.preferences.get('install_on_exit')
                    and self.updates.downloaded and release and release.newer_than() and not self.updates.busy):
                try:
                    self._pending_update = prepare_install(self.updates.downloaded, release, restart=False)
                    if not self.updates.save_preference('pending', str(self._pending_update.parent / 'result.json')):
                        self._pending_update = None
                except (OSError, ValueError) as error:
                    self.updates.status = '静默更新未启动，下载文件已保留：' + str(error)
        if self._pending_update:
            from core.app_updates import launch_helper
            try:
                launch_helper(self._pending_update)
            except (OSError, ValueError) as error:
                self._pending_update = None
                self.updates.status = '无法启动更新，下载文件已保留：' + str(error)
                self.updates.changed.emit()
                if explicit_update:
                    event.ignore()
                    return
        self.seedgen.shutdown_sharing()
        self.updates.shutdown()
        self.ctx.game_session.shutdown()
        self.inspector.shutdown()
        self.feedback.shutdown()
        self.crash_reports.shutdown()
        if self._crash_dialog:
            self._crash_dialog.close()
        if self._update_dialog:
            self._update_dialog.close()
        event.accept()

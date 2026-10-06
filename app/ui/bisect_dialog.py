"""Guided MOD bisect: each round enables part of the suspects until the cause is narrowed down."""
import copy

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QMessageBox, QPushButton, QStackedWidget, QTextEdit, QVBoxLayout, QWidget)

from core import bisect
from core.crash_suspects import FRAMEWORK_IDS
from .theme import style_button

INTRO = ('游戏闪退、报错或出现异常，但不确定是哪个 MOD 时使用。\n'
         '每一轮只启用一部分 MOD（及它们需要的前置），请通过 BBMOD 启动游戏、尝试复现问题，退出后回答结果。'
         '通常十几个 MOD 只需四五轮。排查期间可随时结束并恢复原来的启用组合。')
SESSION_HINTS = {'crash': 'BBMOD 检测到刚才的启动疑似异常退出。如确实复现了问题，请选择「问题仍然出现」。',
                 'clean': '刚才的启动正常退出。如果没有遇到问题，请选择「没有出现问题」。',
                 'unknown': '刚才的启动没有留下可判断的日志，请按实际情况回答。'}


def _pinned_by_default(mod):
    from core.l10n import is_bbmod_l10n
    if any(r.mod_id in FRAMEWORK_IDS for r in mod.info.registrations):
        return True
    try:
        return is_bbmod_l10n(mod.path)
    except (OSError, ValueError):
        return False


class BisectDialog(QDialog):
    def __init__(self, page):
        super().__init__(page)
        self.page, self.ctx = page, page.ctx
        self.state = None
        self.setWindowTitle('排查问题 MOD')
        self.resize(640, 560)
        self.setModal(False)
        layout = QVBoxLayout(self)
        self.stack = QStackedWidget()
        layout.addWidget(self.stack, 1)
        self.stack.addWidget(self._build_setup())
        self.stack.addWidget(self._build_round())
        self.stack.addWidget(self._build_result())
        crash_reports = getattr(page.window(), 'crash_reports', None)
        if crash_reports is not None:
            crash_reports.session_ended.connect(self._session_ended)
        self.load()

    # ---------------- 页面 ----------------

    def _build_setup(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        intro = QLabel(INTRO)
        intro.setWordWrap(True)
        layout.addWidget(intro)
        layout.addWidget(QLabel('勾选的 MOD 每轮都保持启用（框架和汉化默认勾选）；未勾选的参与排查：'))
        self.candidates = QListWidget()
        layout.addWidget(self.candidates, 1)
        actions = QHBoxLayout()
        self.start_button = QPushButton('开始排查')
        style_button(self.start_button, 'play', primary=True)
        self.start_button.clicked.connect(self.begin)
        close = QPushButton('关闭')
        close.clicked.connect(self.close)
        actions.addStretch(1)
        actions.addWidget(self.start_button)
        actions.addWidget(close)
        layout.addLayout(actions)
        return widget

    def _build_round(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        self.round_title = QLabel()
        self.round_title.setStyleSheet('font-size: 16px; font-weight: 600;')
        layout.addWidget(self.round_title)
        self.round_info = QLabel()
        self.round_info.setWordWrap(True)
        layout.addWidget(self.round_info)
        self.round_list = QTextEdit()
        self.round_list.setReadOnly(True)
        layout.addWidget(self.round_list, 1)
        self.session_hint = QLabel()
        self.session_hint.setWordWrap(True)
        layout.addWidget(self.session_hint)
        actions = QHBoxLayout()
        self.launch_button = QPushButton('启动游戏')
        style_button(self.launch_button, 'play')
        self.launch_button.clicked.connect(self.launch)
        self.failed_button = QPushButton('问题仍然出现')
        self.passed_button = QPushButton('没有出现问题')
        self.failed_button.clicked.connect(lambda: self.answer(True))
        self.passed_button.clicked.connect(lambda: self.answer(False))
        self.abort_button = QPushButton('结束并恢复原组合')
        self.abort_button.clicked.connect(self.restore)
        for button in (self.launch_button, self.failed_button, self.passed_button):
            actions.addWidget(button)
        actions.addStretch(1)
        actions.addWidget(self.abort_button)
        layout.addLayout(actions)
        return widget

    def _build_result(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        self.result_text = QLabel()
        self.result_text.setWordWrap(True)
        self.result_text.setTextFormat(Qt.PlainText)
        self.result_text.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.result_text.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        layout.addWidget(self.result_text, 1)
        actions = QHBoxLayout()
        self.without_button = QPushButton('恢复原组合，但禁用问题 MOD')
        style_button(self.without_button, 'check', primary=True)
        self.without_button.clicked.connect(self.restore_without_found)
        self.restore_button = QPushButton('完全恢复原组合')
        self.restore_button.clicked.connect(self.restore)
        actions.addStretch(1)
        actions.addWidget(self.without_button)
        actions.addWidget(self.restore_button)
        layout.addLayout(actions)
        return widget

    # ---------------- 状态 ----------------

    def load(self):
        mm = self.ctx.mm
        try:
            self.state = bisect.load(mm) if mm else None
        except ValueError as error:
            if QMessageBox.question(self, '排查记录无法读取', f'{error}\n删除这份记录并重新开始？',
                                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No) == QMessageBox.Yes:
                bisect.clear(mm)
            self.state = None
        if self.state is None:
            self._fill_candidates()
            self.stack.setCurrentIndex(0)
        else:
            self.show_state()

    def _fill_candidates(self):
        self.candidates.clear()
        mods = [m for m in self.page._installed_mods if m.enabled]
        for mod in mods:
            item = QListWidgetItem(mod.path.name)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if _pinned_by_default(mod) else Qt.Unchecked)
            self.candidates.addItem(item)
        self.start_button.setEnabled(bool(mods))
        if not mods:
            self.candidates.addItem('当前没有启用的 MOD，无需排查。')

    def show_state(self):
        state = self.state
        if state['stage'] == 'done':
            self._show_result()
            return
        self.stack.setCurrentIndex(1)
        tested = bisect.tested(state)
        enabled = state.get('enabled', [])
        self.round_title.setText(f'第 {state["round"]} 轮')
        if state['stage'] == 'baseline':
            focus = '本轮先关闭全部可疑 MOD，只保留勾选的 MOD，确认问题是否与它们有关。'
        else:
            focus = f'本轮测试 {len(tested)} 个可疑 MOD；可疑范围 {len(state["suspects"])} 个。'
        if state['found']:
            focus += '\n已确认相关：' + '、'.join(state['found']) + '（之后保持启用，继续寻找与之冲突的另一个）。'
        self.round_info.setText(f'{focus}\n当前共启用 {len(enabled)} 个 MOD，预计还需约 {bisect.rounds_left(state)} 轮。\n'
                                '请启动游戏并尝试复现问题，退出游戏后在下方回答。')
        self.round_list.setPlainText('本轮启用的 MOD：\n' + ('\n'.join(enabled) or '（无）'))
        self.session_hint.clear()

    def _show_result(self):
        state = self.state
        self.stack.setCurrentIndex(2)
        found = state['found']
        if state['result'] == 'found' and len(found) == 1:
            text = f'问题很可能由「{found[0]}」引起。'
        elif state['result'] == 'found':
            text = '问题很可能在以下 MOD 同时启用时出现（相互冲突）：\n' + '\n'.join('· ' + name for name in found)
        elif state['result'] == 'outside':
            text = ('只保留勾选的 MOD 时问题仍然出现，原因不在参与排查的 MOD 中。\n'
                    '可以减少勾选的 MOD 重新排查，或检查游戏本体与存档。')
        else:
            text = '未能定位到具体 MOD；可能是回答不一致或问题不稳定复现，可以重新排查。'
        rounds = len(state['history'])
        self.result_text.setText(f'{text}\n\n共 {rounds} 轮。结果依据你的回答推断，请再确认一次；'
                                 '可以去作者页面查看已知问题、更新版本，或在方案中暂时停用。\n\n'
                                 '现在选择如何恢复 MOD：')
        self.without_button.setVisible(bool(found))

    # ---------------- 操作 ----------------

    def _ready(self):
        if not self.page._can_modify():
            return False
        return True

    def begin(self):
        if not self._ready():
            return
        pinned, suspects = [], []
        for row in range(self.candidates.count()):
            item = self.candidates.item(row)
            (pinned if item.checkState() == Qt.Checked else suspects).append(item.text())
        try:
            state = bisect.start(pinned + suspects, pinned, suspects)
        except ValueError as error:
            QMessageBox.information(self, '无法开始', str(error))
            return
        self._apply(state, '正在准备第 1 轮排查')

    def _apply(self, state, status):
        manager = self.ctx.mm

        def done(_count):
            self.state = state
            self.show_state()
        self.page._operate(status, '排查未能切换 MOD', lambda: bisect.apply_round(manager, state), done)

    def answer(self, failed):
        if not self._ready():
            return
        state = copy.deepcopy(self.state)
        bisect.record(state, failed, len(state.get('enabled', [])))
        if state['stage'] == 'done':
            manager = self.ctx.mm

            def done(_):
                self.state = state
                self.show_state()
            self.page._operate('正在保存排查结果', '排查结果保存失败', lambda: bisect.save(manager, state), done)
        else:
            self._apply(state, f'正在准备第 {state["round"]} 轮排查')

    def restore(self):
        if not self.state or not self._ready():
            return
        manager, state = self.ctx.mm, self.state
        self.page._operate('正在恢复原来的 MOD 组合', '恢复失败', lambda: bisect.restore(manager, state),
                           lambda _: self._finished('已恢复排查前的 MOD 组合。'))

    def restore_without_found(self):
        if not self.state or not self._ready():
            return
        manager, state = self.ctx.mm, self.state
        found = set(state['found'])

        def work():
            installed = {mod.path.name for mod in manager.scan(analyze=False)}
            result = manager.apply_enabled((set(state['original']) & installed) - found)
            bisect.clear(manager)
            return result
        self.page._operate('正在恢复 MOD 组合', '恢复失败', work,
                           lambda _: self._finished('已恢复排查前的组合，并禁用：' + '、'.join(sorted(found))))

    def _finished(self, message):
        self.state = None
        self.page.status_label.setText(message)
        self.close()

    def launch(self):
        launch = getattr(self.page.window(), 'launch_game', None)
        if launch is not None:
            launch()

    def _session_ended(self, outcome):
        if self.state and self.state['stage'] != 'done' and self.stack.currentIndex() == 1:
            self.session_hint.setText(SESSION_HINTS.get(outcome, ''))

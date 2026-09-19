"""Shared launch feedback, with process checks kept off the UI thread."""
import time

from PySide6.QtCore import QObject, QTimer, Signal

from core import game as game_mod
from .workers import Worker


class GameSession(QObject):
    changed = Signal()
    START_TIMEOUT = 45

    def __init__(self, parent=None, *, probe=None, clock=None):
        super().__init__(parent)
        self.state = 'checking'
        self.message = '正在检查游戏状态…'
        self._probe = probe or game_mod.is_game_running
        self._clock = clock or time.monotonic
        self._deadline = None
        self._revision = 0
        self._worker = None
        self._closed = False
        self.timer = QTimer(self)
        self.timer.setInterval(1500)
        self.timer.timeout.connect(self.poll)

    @property
    def occupied(self):
        return self.state in {'checking', 'starting', 'running'}

    @property
    def button_text(self):
        return {'checking': '检查游戏状态', 'starting': '正在启动…',
                'running': '游戏运行中'}.get(self.state, '启动游戏')

    def _set(self, state, message):
        if (state, message) != (self.state, self.message):
            self.state, self.message = state, message
            self.changed.emit()

    def start(self):
        self.timer.start()
        self.poll()

    def poll(self):
        if self._closed or self._worker is not None:
            return
        revision = self._revision
        self._worker = Worker(self._probe, self)
        self._worker.done.connect(lambda running: self.observe(running, revision=revision))
        self._worker.failed.connect(lambda error: self._check_failed(error, revision))
        self._worker.finished.connect(self._poll_finished)
        self._worker.start()

    def _poll_finished(self):
        worker, self._worker = self._worker, None
        if worker is not None:
            worker.deleteLater()

    def _check_failed(self, error, revision):
        if not self._closed and revision == self._revision:
            self._set(self.state, '暂时无法检查游戏状态：' + error)

    def observe(self, running, *, revision=None):
        if self._closed or (revision is not None and revision != self._revision):
            return
        if running:
            self._deadline = None
            self._set('running', '游戏已在运行，无需再次启动。切换汉化请先退出游戏。')
        elif self.state == 'starting':
            if self._deadline is not None and self._clock() >= self._deadline:
                self._deadline = None
                self._set('idle', '未检测到游戏启动，请检查 Steam 或游戏提示后重试。')
        elif self.state == 'running':
            self._set('idle', '游戏已退出，可以再次启动。')
        elif self.state == 'checking':
            self._set('idle', '')

    def begin_launch(self):
        if self.occupied or self._closed:
            return False
        # A process check started before this click cannot clear the new state.
        self._revision += 1
        self._deadline = None
        self._set('starting', '正在准备启动游戏，请稍候，无需重复点击。')
        return True

    def launch_submitted(self):
        if self.state == 'starting':
            self._deadline = self._clock() + self.START_TIMEOUT
            self._set('starting', '已发送启动请求，正在等待游戏出现，无需重复点击。')
        self.poll()

    def launch_failed(self, error):
        self._deadline = None
        if self.state != 'running':
            self._set('idle', '启动未完成：' + error)
        self.poll()

    def shutdown(self):
        self._closed = True
        self.timer.stop()
        if self._worker is not None:
            self._worker.wait()

"""后台工作线程：避免 zip 分析/构建等重活卡界面。"""
from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QThread, Signal


def modify_files(manager, function: Callable[[], object]):
    """Wait for file readers, then check the game immediately before mutation."""
    from core.game import is_game_running
    with manager.file_access():
        if is_game_running():
            raise ValueError('游戏已启动，请关闭游戏后再更改 MOD 或汉化配置。')
        return function()


class Worker(QThread):
    done = Signal(object)
    failed = Signal(str)

    def __init__(self, fn: Callable[[], object], parent=None) -> None:
        super().__init__(parent)
        self._fn = fn

    def run(self) -> None:  # noqa: D102
        try:
            result = self._fn()
        except Exception as e:  # noqa: BLE001
            self.failed.emit(f"{type(e).__name__}: {e}")
        else:
            self.done.emit(result)


def track(owner, name: str, worker: QThread) -> QThread:
    """把 worker 存到 owner.<name>；结束后释放，且只清空仍指向它的引用（旧线程的迟到信号不影响新线程）。"""
    setattr(owner, name, worker)

    def release() -> None:
        if getattr(owner, name, None) is worker:
            setattr(owner, name, None)
        worker.deleteLater()
    worker.finished.connect(release)
    return worker

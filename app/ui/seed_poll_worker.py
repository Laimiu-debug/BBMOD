"""Read seed logs outside Qt's GUI thread, with one acknowledged batch at a time."""
from threading import Event

from PySide6.QtCore import QThread, Signal


class SeedPollWorker(QThread):
    batch_ready = Signal(object)
    failed = Signal(str)

    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session
        self._acknowledged = Event()

    def acknowledge(self):
        self._acknowledged.set()

    def stop(self, timeout_ms=5000):
        self.requestInterruption()
        self._acknowledged.set()
        return self.wait(timeout_ms)

    def run(self):
        try:
            while not self.isInterruptionRequested():
                results, _ = self.session.poll()
                if self.isInterruptionRequested():
                    break
                self._acknowledged.clear()
                self.batch_ready.emit(results)
                # The GUI saves and displays this batch before another one can
                # be queued. Closing or stopping also releases this wait.
                while not self._acknowledged.wait(0.1):
                    if self.isInterruptionRequested():
                        return
                if not results and not self.isInterruptionRequested():
                    self.msleep(200)
        except Exception as error:
            self.failed.emit(str(error))

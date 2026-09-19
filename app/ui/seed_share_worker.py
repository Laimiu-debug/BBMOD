"""Qt bridge; all network waits run off the UI thread and can be stopped."""
from PySide6.QtCore import Signal
from .workers import Worker
from core.seedgen.share_queue import SeedShareQueue


class SeedShareWorker(Worker):
    progress = Signal(object)

    def __init__(self, library, items, upload, parent=None):
        self.queue = SeedShareQueue(library, items, upload=upload, progress=self._progress)
        super().__init__(self.queue.run, parent)

    def _progress(self, value):
        self.progress.emit(value)

    def cancel(self):
        self.queue.cancel()

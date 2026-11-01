"""Plain-text hints that retain all wrapped lines in compact layouts."""
from PySide6.QtCore import QEvent, QRect, Qt, QTimer
from PySide6.QtWidgets import QLabel


class ReadableLabel(QLabel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setWordWrap(True)

    def _fit_height(self):
        margins = self.contentsMargins()
        width = max(1, self.width() - margins.left() - margins.right() - 2 * self.margin())
        bounds = self.fontMetrics().boundingRect(QRect(0, 0, width, 1000000), Qt.TextWordWrap, self.text())
        height = bounds.height() + margins.top() + margins.bottom() + 2 * self.margin()
        if self.minimumHeight() != height:
            self.setMinimumHeight(height)

    def setText(self, text):
        super().setText(text)
        self._fit_height()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._fit_height()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() in (QEvent.FontChange, QEvent.StyleChange):
            QTimer.singleShot(0, self, self._fit_height)

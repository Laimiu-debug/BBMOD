"""Short, interruptible transitions that leave the live workspace interactive."""
from PySide6.QtCore import QEasingCurve, QEvent, QPropertyAnimation, Qt
from PySide6.QtWidgets import QApplication, QGraphicsOpacityEffect, QLabel, QStackedWidget

REDUCE_MOTION_KEY = 'reduce_motion'


class MotionStack(QStackedWidget):
    """Fade a disposable snapshot; never apply graphics effects to live tables."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._overlay = None
        self._animation = None
        self.installEventFilter(self)

    def clear_transition(self):
        if self._animation is not None:
            self._animation.stop()
            self._animation.deleteLater()
            self._animation = None
        if self._overlay is not None:
            self._overlay.hide()
            self._overlay.deleteLater()
            self._overlay = None

    def setCurrentIndex(self, index):
        if index == self.currentIndex() or not 0 <= index < self.count():
            return
        self.clear_transition()
        app = QApplication.instance()
        animate = self.isVisible() and not app.property('bbmodReduceMotion')
        snapshot = self.currentWidget().grab() if animate and self.currentWidget() else None
        super().setCurrentIndex(index)
        if snapshot is None:
            return
        self._overlay = QLabel(self)
        self._overlay.setPixmap(snapshot)
        self._overlay.setGeometry(self.contentsRect())
        self._overlay.setAttribute(Qt.WA_TransparentForMouseEvents)
        self._overlay.setFocusPolicy(Qt.NoFocus)
        effect = QGraphicsOpacityEffect(self._overlay)
        self._overlay.setGraphicsEffect(effect)
        self._animation = QPropertyAnimation(effect, b'opacity', self)
        self._animation.setDuration(170)
        self._animation.setStartValue(1.0)
        self._animation.setEndValue(0.0)
        self._animation.setEasingCurve(QEasingCurve.OutCubic)
        self._animation.finished.connect(self.clear_transition)
        self._overlay.show()
        self._overlay.raise_()
        self._animation.start()

    def eventFilter(self, watched, event):
        if event.type() in (QEvent.Resize, QEvent.Hide):
            self.clear_transition()
        return super().eventFilter(watched, event)

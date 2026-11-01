"""Popup lists that remain readable inside narrow forms and table cells."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QComboBox


class ReadableComboBox(QComboBox):
    def showPopup(self):
        screen = self.screen() or QGuiApplication.primaryScreen()
        available = screen.availableGeometry() if screen else None
        metrics = self.fontMetrics()
        width = max(self.width(), max((metrics.horizontalAdvance(self.itemText(i)) for i in range(self.count())), default=0)+56)
        if available:
            width = min(width, available.width()-32)
        view = self.view()
        view.setMinimumWidth(width)
        view.setTextElideMode(Qt.ElideNone)
        view.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        view.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setMaxVisibleItems(min(24, max(1, self.count())))
        # Use a scrolling list instead of a style-dependent native menu.
        self.setStyleSheet('QComboBox { combobox-popup: 0; }')
        for index in range(self.count()):
            self.setItemData(index, self.itemText(index), Qt.ToolTipRole)
        if self.isEditable() and self.completer():
            self.completer().setMaxVisibleItems(20)
            self.completer().popup().setMinimumWidth(width)
            self.completer().popup().setTextElideMode(Qt.ElideNone)
        super().showPopup()

"""Tab workspaces whose hidden pages do not reserve screen space."""
from PySide6.QtCore import QEvent, QSize
from PySide6.QtWidgets import QStyle, QTabWidget


class ActivePageTabs(QTabWidget):
    """Use the current page for both preferred and minimum layout sizes."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.currentChanged.connect(self._page_changed)

    def addTab(self, page, *args):
        page.installEventFilter(self)
        return super().addTab(page, *args)

    def eventFilter(self, watched, event):
        if watched is self.currentWidget() and event.type() in (
                QEvent.LayoutRequest, QEvent.FontChange, QEvent.StyleChange):
            # The private Qt stack can keep the same aggregate size while the
            # active page changes. Propagate its geometry requests ourselves.
            self.updateGeometry()
        return super().eventFilter(watched, event)

    def _page_changed(self, _index):
        self.updateGeometry()
        parent = self.parentWidget()
        if parent is not None and parent.layout() is not None:
            parent.layout().invalidate()

    def _chrome(self):
        frame = 2 * self.style().pixelMetric(QStyle.PM_DefaultFrameWidth)
        bar = self.tabBar().sizeHint() if self.tabBar().isVisibleTo(self) else QSize()
        return frame, bar

    def _page_size(self, minimum):
        page = self.currentWidget()
        if page is None:
            return super().minimumSizeHint() if minimum else super().sizeHint()
        size = page.minimumSizeHint() if minimum else page.sizeHint()
        size = size.expandedTo(page.minimumSize())
        frame, bar = self._chrome()
        return QSize(max(size.width(), bar.width()) + frame,
                     size.height() + bar.height() + frame)

    def minimumSizeHint(self):
        return self._page_size(True)

    def sizeHint(self):
        return self._page_size(False)

    def hasHeightForWidth(self):
        page = self.currentWidget()
        return page is not None and page.hasHeightForWidth()

    def heightForWidth(self, width):
        page = self.currentWidget()
        if page is None:
            return -1
        frame, bar = self._chrome()
        layout = page.layout()
        # Tables and splitters may prefer a large height; only their minimum
        # is required to keep the page usable inside a resizable viewport.
        height = (layout.totalMinimumHeightForWidth(max(0, width - frame))
                  if layout is not None and layout.hasHeightForWidth() else -1)
        return max(page.minimumSizeHint().height(), page.minimumHeight(), height) + bar.height() + frame

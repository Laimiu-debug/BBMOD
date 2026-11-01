"""Open only the standalone map workspace, without game discovery or launch."""
import argparse
from pathlib import Path
import sys
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ui.worldmap_page import WorldMapPage
from ui.theme import apply_theme


class PreviewSettings:
    def __init__(self, seed):
        self.values = {'worldmap_preview': {'seed': seed}}
    def get(self, key, default=None):
        return self.values.get(key, default)
    def set(self, key, value):
        self.values[key] = value


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seed', default='46U2HMOORH')
    parser.add_argument('--view', choices=('towns', 'trade', 'loot'), default='towns')
    args = parser.parse_args()
    app = QApplication([])
    apply_theme(app)
    page = WorldMapPage(PreviewSettings(args.seed))
    page.setWindowTitle('BBMOD · 离线地图、跑商与营地红装预览')
    page.resize(1280, 840); page.show()
    QTimer.singleShot(0, page.activate)
    def select_view():
        if page.world is None:
            if page._job is not None: QTimer.singleShot(100, select_view)
            return
        page.tabs.setCurrentIndex(('towns', 'trade', 'loot').index(args.view))
        if args.view == 'loot':
            row = next((i for i, (_, item) in enumerate(page._filtered_loot) if item.kind == 'weapon'), 0)
            if page.loot_table.rowCount(): page.loot_table.selectRow(row)
        elif args.view == 'trade' and page.offers.rowCount():
            page.offers.selectRow(0)
    QTimer.singleShot(100, select_view)
    app.aboutToQuit.connect(page.shutdown)
    raise SystemExit(app.exec())


if __name__ == '__main__':
    main()

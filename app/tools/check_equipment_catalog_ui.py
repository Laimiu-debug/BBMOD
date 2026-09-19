"""Exercise and render the equipment workspace with no game installation."""
from contextlib import ExitStack
import json
import os
from pathlib import Path
import sys
import tempfile
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QTextBrowser
from ui.main_window import MainWindow, apply_dark_palette
from ui.workers import Worker


def main():
    out = ROOT / 'build/review/equipment-catalog'
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='bbmod-equipment-ui-') as temporary, ExitStack() as guard:
        os.environ['APPDATA'] = temporary
        guard.enter_context(patch('core.game.locate_game', return_value=None))
        guard.enter_context(patch('core.game.launch_executable', side_effect=AssertionError('Game launch forbidden')))
        guard.enter_context(patch('ui.inspector_page.change', side_effect=AssertionError('MOD writes forbidden')))
        app = QApplication([]); apply_dark_palette(app)
        window = MainWindow(auto_updates=False)
        window.setAttribute(Qt.WA_DontShowOnScreen); window.show()
        deadline = time.monotonic() + 30
        while any(worker.isRunning() for worker in window.findChildren(Worker)):
            assert time.monotonic() < deadline
            QTest.qWait(30)
        window.select_page(5)
        workspace = window.inspector
        page = workspace.catalog_page
        assert workspace.sections.currentIndex() == 0 and window.ctx.game is None
        assert not workspace.install.isEnabled() and not workspace.hotkey.registered
        counts = []
        for width, height in ((1360, 880), (1080, 720)):
            window.resize(width, height); page.reset_filters(); QTest.qWait(80)
            assert window.size().toTuple() == (width, height)
            for widget in (page.search, page.group, page.rarity, page.detail_button):
                assert widget.visibleRegion().contains(widget.rect().adjusted(2, 2, -2, -2))
            assert page.table.viewport().height() // page.table.rowHeight(0) >= 5
            window.grab().save(str(out / f'equipment-{width}.png'))
            page.group.setCurrentIndex(page.group.findData('armor'))
            page.rarity.setCurrentIndex(page.rarity.findData('named')); QTest.qWait(60)
            assert page.table.rowCount() == 15 and page.table.isColumnHidden(3)
            page.table.sortItems(6, Qt.DescendingOrder)
            window.grab().save(str(out / f'named-armor-{width}.png'))
            counts.append({'size': [width, height], 'visible_rows': page.table.viewport().height() // page.table.rowHeight(0)})
        window.resize(1360, 880)
        page.reset_filters()
        QTest.mouseClick(page.search, Qt.LeftButton)
        QTest.keyClicks(page.search, 'Greatsword'); QTest.qWait(80)
        assert page.table.rowCount() >= 2
        page.rarity.setCurrentIndex(page.rarity.findData('named'))
        assert page.table.rowCount() == 1
        QTest.mouseClick(page.detail_button, Qt.LeftButton); QTest.qWait(80)
        dialog = page._dialog
        text = dialog.findChild(QTextBrowser).toPlainText()
        assert '25%' in text and '33% ～ 41%' in text and '随机抽取两组' in text
        dialog.grab().save(str(out / 'named-greatsword-detail.png'))
        dialog.close()
        page.search.setText('no-such-equipment'); QTest.qWait(40)
        assert not page.table.rowCount() and not page.detail_button.isEnabled()
        window.grab().save(str(out / 'empty-search.png'))
        workspace.sections.setCurrentIndex(1); QTest.qWait(80)
        assert workspace.install.isVisible() and not workspace.install.isEnabled()
        window.grab().save(str(out / 'appraisal-tab.png'))
        workspace.sections.setCurrentIndex(0); page.reset_filters()
        window.close(); app.processEvents()
        result = {'entries': len(page.items), 'named_entries': 94, 'game_directory': None,
                  'original_item_icons': sum(bool(art['small']) for art in page.artwork.values()),
                  'mod_installation': 'not used', 'offline_browsing': 'passed',
                  'search_filter_sort_detail_empty_state': 'passed', 'layouts': counts,
                  'actual_game_acceptance': 'not performed'}
        (out / 'result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__': main()

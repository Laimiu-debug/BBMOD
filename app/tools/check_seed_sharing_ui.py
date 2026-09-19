"""Render queue states with fake uploads and isolated settings; no game or network."""
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
os.environ['QT_QPA_PLATFORM'] = 'windows' if os.name == 'nt' else 'offscreen'
from PySide6.QtCore import Qt, QItemSelectionModel, QMimeData
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from core.appearance import Appearance
from core.seedgen.log_watcher import SeedResult
from core.seedgen.share_queue import SeedShareQueue
from core.seedgen.sharing import ShareReceipt, UploadError
from ui.main_window import MainWindow, apply_dark_palette
from ui.theme import apply_theme, font_families
from ui.workers import Worker


def wait_for(predicate):
    deadline = time.monotonic() + 12
    while not predicate():
        assert time.monotonic() < deadline
        QTest.qWait(20)


def main():
    output = ROOT/'build/review/seed-sharing'; output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='bbmod-share-ui-') as temp, ExitStack() as guard:
        os.environ['APPDATA'] = temp
        for name in ('core.game.launch_executable', 'core.game.kill_game'):
            guard.enter_context(patch(name, side_effect=AssertionError('Real game actions forbidden')))
        guard.enter_context(patch('core.game.locate_game', return_value=None))
        guard.enter_context(patch.object(SeedShareQueue, 'INTERVAL', 0))
        app = QApplication([]); apply_dark_palette(app)
        previous_clipboard = QMimeData()
        clipboard_data = app.clipboard().mimeData()
        if clipboard_data:
            for name in clipboard_data.formats():
                previous_clipboard.setData(name, clipboard_data.data(name))
        guard.callback(lambda: app.clipboard().setMimeData(previous_clipboard))
        window = MainWindow(auto_updates=False); window.setAttribute(Qt.WA_DontShowOnScreen); window.show()
        guard.callback(window.seedgen.shutdown_sharing)
        wait_for(lambda: not any(worker.isRunning() for worker in window.findChildren(Worker)))
        page = window.seedgen
        page._accept_results([SeedResult('AbCdEfGhI'+letter, i, origin='scenario.militia', done=True,
            game_version='1.5.2.3', lines=['CharInfo: 0 Melee:0.8 MeleeSkill:60(95)3', 'SettlementInfo: Port:8'])
            for i, letter in enumerate('abcdefgh')])
        window.select_page(3); page.sections.setCurrentIndex(1)
        # Copy codes without opening the preview or changing its chosen format.
        window.setFocus(); QApplication.setActiveWindow(window)
        page.table.setFocus(); QTest.qWait(50)
        assert not page.preview_btn.isChecked() and page.copy_codes_btn.isVisible()
        page.table.selectRow(0)
        page.copy_codes_btn.click()
        assert app.clipboard().text() == 'AbCdEfGhIa'
        page.table.selectRow(2)
        page.table.selectionModel().select(page.table.model().index(0, 0), QItemSelectionModel.Select | QItemSelectionModel.Rows)
        page.table.setFocus(); QTest.keyClick(page.table, Qt.Key_C, Qt.ControlModifier)
        assert app.clipboard().text() == 'AbCdEfGhIa\nAbCdEfGhIc'
        # A filtered-out row must not leak into a multi-selection copy.
        page.library_search.setText('AbCdEfGhIa'); page.table.selectAll()
        page.copy_codes_btn.click(); assert app.clipboard().text() == 'AbCdEfGhIa'
        page.library_search.setText('no match')
        assert not page.copy_codes_btn.isEnabled()
        page.copy_seed_codes(); assert app.clipboard().text() == 'AbCdEfGhIa'
        page.library_search.clear(); page.table.selectRow(0)
        page.table.setFocus(); QTest.keyClick(page.table, Qt.Key_C, Qt.ControlModifier | Qt.ShiftModifier)
        assert app.clipboard().text() == page._formatted(page._selected_result())
        page.table.setFocus(); QTest.keyClick(page.table, Qt.Key_C, Qt.ControlModifier)
        assert app.clipboard().text() == 'AbCdEfGhIa'
        # Changing the selection and refreshing results alone must not copy.
        page.table.selectRow(1); page._rebuild_library()
        assert app.clipboard().text() == 'AbCdEfGhIa'
        page.table.selectRow(0); page._selection_actions()
        images = []
        def capture(label, width, height, size):
            apply_theme(app, Appearance(font_families()[0], size))
            window._fit_typography()
            window.resize(width, height); QTest.qWait(120)
            scroll = window.page_scrolls[3]
            scroll.verticalScrollBar().setValue(0); scroll.horizontalScrollBar().setValue(0)
            QTest.qWait(80)
            assert window.size().toTuple() == (width, height)
            if scroll.horizontalScrollBar().maximum():
                window.grab().save(str(output/'overflow.png'))
                from PySide6.QtWidgets import QWidget
                print(json.dumps({'scroll':scroll.size().toTuple(),'overflow':scroll.horizontalScrollBar().maximum(),
                    'widgets': [(type(w).__name__, w.objectName(), getattr(w, 'text', lambda: '')(), w.width(), w.minimumSizeHint().width(), w.sizeHint().width())
                                for w in page.findChildren(QWidget) if w.isVisible() and w.minimumSizeHint().width()>170],
                    'layouts': [(i, page.sections.widget(1).layout().itemAt(i).minimumSize().width())
                                for i in range(page.sections.widget(1).layout().count())]},ensure_ascii=False),flush=True)
            assert scroll.horizontalScrollBar().maximum() == 0
            for widget in (page.publish_all_btn, page.publish_btn, page.cancel_share_btn, page.copy_codes_btn):
                assert widget.width() >= widget.fontMetrics().horizontalAdvance(widget.text()) + 12
                scroll.ensureWidgetVisible(widget, 4, 4); QTest.qWait(30)
                assert widget.visibleRegion().contains(widget.rect().adjusted(2, 2, -2, -2))
            scroll.verticalScrollBar().setValue(0); QTest.qWait(30)
            name = f'{label}-{width}-{size}.png'
            assert window.grab().save(str(output/name)); images.append(name)
        capture('ready', 1360, 880, 12)
        capture('copy-codes', 1080, 720, 18)
        apply_theme(app, Appearance(font_families()[0], 12)); window._fit_typography()
        calls = []
        def upload(result, note):
            calls.append(result.seed)
            if len(calls) == 1:
                return ShareReceipt('https://example.invalid/seeds/01234567-89ab-cdef-0123-456789abcdef/', True)
            raise UploadError('网站正在处理其他分享，请稍后重试。', status=503, retry_after=60, retryable=True)
        with patch('ui.seedgen_page.publish_seed', side_effect=upload):
            QTest.mouseClick(page.publish_all_btn, Qt.LeftButton)
            wait_for(lambda: '后继续' in page.share_status.text())
            assert len(calls) == 2 and not page.publish_all_btn.isEnabled()
            capture('waiting', 1360, 880, 12)
            capture('waiting', 1080, 720, 18)
            QTest.mouseClick(page.cancel_share_btn, Qt.LeftButton)
            wait_for(lambda: not page._share_active)
            assert len(calls) == 2 and page._share_report.created == 1 and page._share_report.remaining == 7
            capture('stopped', 1360, 880, 12)
        # Closing a queue during an hour-long cooldown must stop immediately.
        page.library.defer_sharing(3600, '网站限流')
        with patch('ui.seedgen_page.publish_seed', side_effect=AssertionError('Cooldown bypassed')):
            page.publish_all_btn.click(); wait_for(lambda: '后继续' in page.share_status.text())
            before = time.monotonic(); assert window.close()
            assert time.monotonic() - before < 2
            assert not page._share_worker.isRunning()
        result = dict(status='passed', screenshots=images, real_uploads=0, game_started=False,
                      stop_keeps_success=True, close_cancels_cooldown=True,
                      direct_code_copy=True, multi_selection_copy=True, keyboard_copy=True,
                      hidden_rows_excluded=True, formatted_copy_preserved=True)
        (output/'ui-check.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__': main()

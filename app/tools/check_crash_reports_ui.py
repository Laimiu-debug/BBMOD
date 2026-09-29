"""Render isolated crash-report UI fixtures; no game or remote report is sent."""
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

from PySide6.QtWidgets import QApplication
from core.crash_reports import begin_session
from ui.main_window import MainWindow, apply_dark_palette


def main():
    out = ROOT / 'build/deploy-rc33'
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='bbmod-crash-ui-') as temporary:
        os.environ['APPDATA'] = temporary
        app = QApplication([])
        apply_dark_palette(app)
        with patch('core.game.locate_game', return_value=None), patch('core.game.probe_game_running', return_value=False):
            window = MainWindow(auto_updates=False)
            window.ctx.game_session.shutdown()
            folder = Path(temporary) / 'logs'
            folder.mkdir()
            session = begin_session([folder])
            (folder / 'log.html').write_text('<div class="row error"><div class="time">20:45:00</div>'
                '<div class="tag">SQ</div><div class="text">演示日志：the index Big does not exist</div></div>', encoding='utf-8')
            item = window.crash_reports.store.capture(window.ctx, session, [folder])
            window.crash_reports._captured(item)
            window.show()
            for width, height in [(1360, 960), (1080, 720)]:
                window.resize(width, height)
                window.select_page(4)
                app.processEvents()
                window.page_scrolls[4].ensureWidgetVisible(window.settings_page.auto_crash_upload)
                app.processEvents()
                assert not window.settings_page.auto_crash_upload.isChecked()
                window.grab().save(str(out / f'settings-{width}.png'))
            window.settings_page.crash_reports_button.click()
            app.processEvents()
            dialog = window._crash_dialog
            assert dialog and dialog.listing.count() == 1 and 'Big' in dialog.editor.toPlainText()
            assert window.crash_reports.reply is None
            dialog.grab().save(str(out / 'crash-report-preview.png'))
            dialog.close()
            window.close()
            app.processEvents()
    print('Crash notice, settings entry and snapshot preview verified; no game launch or upload.')


if __name__ == '__main__':
    main()

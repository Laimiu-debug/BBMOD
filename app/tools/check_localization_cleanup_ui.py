"""Exercise localization cleanup through the desktop UI using isolated fixtures."""
import json
import os
from pathlib import Path
import sys
import tempfile
import time
from unittest.mock import patch
import zipfile

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMessageBox
from core.game import GameInfo
from core import l10n
from core.localization_profiles import LocalizationProfiles, BUILTIN, CURRENT, NONE
from ui.main_window import MainWindow, apply_dark_palette
from ui.workers import Worker


def main():
    output = Path(__file__).resolve().parents[1] / 'build/review/localization-cleanup'
    output.mkdir(parents=True, exist_ok=True)
    app = QApplication.instance() or QApplication([])
    apply_dark_palette(app)
    with tempfile.TemporaryDirectory(prefix='bbmod-localization-cleanup-') as temporary:
        base = Path(temporary)
        root = base / '演示游戏（不含可运行游戏）'
        (root / 'data').mkdir(parents=True)
        (root / 'win32').mkdir()
        official = root / 'data/data_001.dat'
        official.write_bytes(b'official fixture')
        source = base / 'mod_bbmod_zhcn.zip'
        with zipfile.ZipFile(source, 'w') as archive:
            archive.writestr('ui/main.html', 'fixture')
            archive.writestr(l10n.BRAND_META, json.dumps({
                'package_id': l10n.PACKAGE_ID, 'version': l10n.VERSION}))
        game = GameInfo(root, root / 'win32/BattleBrothers.exe', '1.5.2.3', root / 'data')
        with patch.dict(os.environ, APPDATA=str(base / 'profile')), \
                patch('ui.app_context.game_mod.locate_game', return_value=game), \
                patch('ui.app_context.game_mod.find_log_write_path', return_value=None), \
                patch('core.game.is_game_running', return_value=False), \
                patch('core.game.launch_executable', side_effect=AssertionError('No game launch allowed')), \
                patch.object(QMessageBox, 'warning', side_effect=AssertionError('Unexpected UI error')):
            profiles = LocalizationProfiles(root)
            profiles.register('BBMOD 独立汉化', [source], builtin=True)
            profiles.apply(profiles.plan(BUILTIN))
            window = MainWindow(auto_updates=False)
            window.setAttribute(Qt.WA_DontShowOnScreen)
            window.show()
            window.select_page(2)
            page = window.l10n.management

            def settled():
                deadline = time.monotonic() + 30
                while any(worker.isRunning() for worker in window.findChildren(Worker)) or page._busy:
                    app.processEvents()
                    assert time.monotonic() < deadline, 'UI workers timed out'
                    QTest.qWait(10)
                app.processEvents()

            settled()
            window.ctx.game_session.timer.stop()
            window.ctx.game_session.observe(False)
            report = []

            def capture(state):
                for width, height in ((1360, 880), (1080, 720)):
                    window.resize(width, height)
                    window.page_scrolls[2].verticalScrollBar().setValue(0)
                    QTest.qWait(80)
                    for widget in (page.current_name, page.choice):
                        assert widget.visibleRegion().contains(widget.rect().adjusted(2, 2, -2, -2))
                    if not page.delete_btn.isHidden():
                        assert page.delete_btn.visibleRegion().contains(page.delete_btn.rect().adjusted(2, 2, -2, -2))
                    image = output / f'{state}-{width}.png'
                    assert window.grab().save(str(image))
                    report.append({'image': image.name, 'size': [width, height], 'state': state})

            page.select_profile(BUILTIN)
            capture('installed')
            page.choice.setCurrentIndex(page.choice.findData(NONE))
            page.apply_btn.click()
            settled()
            assert page.table.item(0, 0).text() == '已停用'
            assert BUILTIN in profiles.profiles()
            capture('disabled')
            # Leave a saved choice selected to verify the cross-page refresh clears it.
            page.select_profile(BUILTIN)
            window.select_page(1)
            window.mods.sections.setCurrentIndex(0)
            window.mods.installed_search.setText(source.name)
            window.mods.table.selectAll()
            with patch.object(QMessageBox, 'question', return_value=QMessageBox.Yes) as confirm:
                window.mods.uninstall_btn.click()
                confirm.assert_called_once()
            assert profiles.profiles() == {}
            assert page.table.rowCount() == 0 and page.choice.findData(BUILTIN) == -1
            assert page.choice.currentData() == CURRENT and not page.plan.changed
            window.select_page(2)
            capture('uninstalled')
            # An old saved-only record can be removed without reinstalling it.
            profiles.register('BBMOD 独立汉化', [source], builtin=True)
            page.select_profile(BUILTIN)
            capture('saved-only')
            with patch.object(QMessageBox, 'question', return_value=QMessageBox.Yes) as confirm:
                page.delete_btn.click()
                settled()
                confirm.assert_called_once()
            assert profiles.profiles() == {} and page.choice.findData(BUILTIN) == -1
            assert page.choice.currentData() == CURRENT and page.start_btn.isEnabled()
            capture('deleted')
            assert source.is_file() and official.read_bytes() == b'official fixture'
            assert window.ctx.mm.scan() == []
            window.close()
            app.processEvents()
            (output / 'validation.json').write_text(json.dumps({
                'fixtures_only': True, 'game_started': False, 'layouts': report,
                'cross_page_cleanup': True, 'old_record_deleted': True}, indent=2), encoding='utf-8')
            print(json.dumps(report))


if __name__ == '__main__':
    main()

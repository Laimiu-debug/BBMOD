"""Offline desktop layout check with labeled fixtures; never launches a game."""
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
from PySide6.QtWidgets import QApplication
from core.game import GameInfo
from core import l10n
from core.localization_profiles import LocalizationProfiles, BUILTIN, CURRENT
from ui.main_window import MainWindow, apply_dark_palette
from ui.workers import Worker


def write_zip(path, entries):
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, 'w') as archive:
        for name, value in entries.items():
            archive.writestr(name, value)
    return path


def main():
    output = Path(__file__).resolve().parents[1] / 'build/review/launcher-layout'
    output.mkdir(parents=True, exist_ok=True)
    app = QApplication.instance() or QApplication([])
    apply_dark_palette(app)
    with tempfile.TemporaryDirectory(prefix='bbmod-launcher-layout-') as temporary:
        base = Path(temporary).resolve()
        assert base.is_relative_to(Path(tempfile.gettempdir()).resolve())
        game_root = base / '演示游戏（不含可运行游戏）'
        (game_root / 'win32').mkdir(parents=True)
        old = write_zip(game_root / 'data/示例旧汉化.zip', {'ui/main.html': 'fixture'})
        font = write_zip(game_root / 'data/示例专用字体.zip', {'gfx/fonts/example.png': 'fixture'})
        write_zip(game_root / 'data/data_001.dat', {'ui/main.html': 'fixture'})
        own = write_zip(base / 'packages/mod_bbmod_zhcn.zip', {
            'ui/main.html': 'fixture', l10n.BRAND_META: json.dumps({'package_id': l10n.PACKAGE_ID,
                'version': l10n.VERSION, 'full_text_files': 1, 'editorial_review': {'status': 'complete'}})})
        game = GameInfo(game_root, game_root / 'win32/BattleBrothers.exe', '1.5.2.3', game_root / 'data')
        with patch.dict(os.environ, APPDATA=str(base / 'profile')), \
                patch('ui.app_context.game_mod.locate_game', return_value=game), \
                patch('ui.app_context.game_mod.find_log_write_path', return_value=None), \
                patch('core.game.is_game_running', return_value=False), \
                patch('core.game.kill_game', side_effect=AssertionError('No game shutdown allowed')), \
                patch('core.game.launch_executable', side_effect=AssertionError('No game launch allowed')):
            profiles = LocalizationProfiles(game_root)
            profiles.register('示例旧汉化与专用字体', [old, font])
            profiles.register('BBMOD 独立汉化', [own], builtin=True)
            window = MainWindow(auto_updates=False)
            window.setAttribute(Qt.WA_DontShowOnScreen)
            window.show()
            window.select_page(2)
            window.l10n.management.select_profile(BUILTIN)
            deadline = time.monotonic() + 40
            while (any(worker.isRunning() for worker in window.findChildren(Worker))
                   or window.ctx.game_session.state == 'checking'):
                app.processEvents()
                if time.monotonic() > deadline:
                    raise TimeoutError('Desktop worker did not finish')
                time.sleep(0.02)
            report = []
            for width, height in ((1360, 880), (1080, 720)):
                window.resize(width, height)
                for tab, name in ((0, 'manager'), (1, 'editor')):
                    window.l10n.sections.setCurrentIndex(tab)
                    QTest.qWait(80)
                    assert (window.width(), window.height()) == (width, height)
                    image = output / f'{name}-{width}.png'
                    assert window.grab().save(str(image))
                    widgets = [window.pick_btn, window.launch_btn]
                    if tab == 0:
                        page = window.l10n.management
                        assert not page.builtin_btn.isVisible() and not page.advanced_panel.isVisible()
                        widgets += [page.apply_btn, page.start_btn, page.advanced_toggle, page.keep_current_btn]
                    for widget in widgets:
                        rectangle = widget.rect()
                        rectangle.moveTopLeft(widget.mapTo(window, rectangle.topLeft()))
                        assert window.rect().contains(rectangle), {
                            'button': widget.text(), 'rect': rectangle.getRect(),
                            'page_minimum': window.l10n.minimumSizeHint().toTuple(),
                            'tabs_minimum': window.l10n.sections.minimumSizeHint().toTuple(),
                            'manager_minimum': window.l10n.management.minimumSizeHint().toTuple(),
                            'page_size': window.l10n.size().toTuple(),
                            'tabs_size': window.l10n.sections.size().toTuple(),
                            'minimum_height': window.l10n.minimumHeight(),
                            'viewport': window.page_scrolls[2].viewport().size().toTuple(),
                        }
                        assert widget.width() >= widget.minimumSizeHint().width(), widget.text()
                    report.append({'image': image.name, 'size': [width, height], 'buttons_visible': True})
            session = window.ctx.game_session
            session.timer.stop()
            while session._worker is not None:
                app.processEvents()
                time.sleep(0.01)
            window.l10n.sections.setCurrentIndex(0)
            page.apply(False)
            deadline = time.monotonic() + 20
            while page._busy:
                app.processEvents()
                assert time.monotonic() < deadline
                time.sleep(0.01)
            assert l10n.VERSION in page.current_name.text() and '已启用' in page.current_name.text()
            assert '无需重新生成' in page.summary.text()
            assert page.keep_current_btn.isHidden()
            page.choice.setCurrentIndex(page.choice.findData(CURRENT))
            for width, height in ((1360, 880), (1080, 720)):
                window.resize(width, height)
                QTest.qWait(80)
                assert not page.builtin_btn.isVisible()
                assert not page.keep_current_btn.isVisible()
                for widget in (page.current_name, page.summary, page.start_btn):
                    assert widget.visibleRegion().contains(widget.rect().adjusted(2, 2, -2, -2))
                image = output / f'current-localization-{width}.png'
                assert window.grab().save(str(image))
                report.append({'image': image.name, 'size': [width, height],
                               'current_localization_visible': True, 'creation_collapsed': True})
            page.advanced_toggle.click()
            QTest.qWait(80)
            for widget in (page.import_btn, page.existing_btn, page.builtin_btn):
                window.page_scrolls[2].ensureWidgetVisible(widget)
                QTest.qWait(50)
                assert widget.visibleRegion().contains(widget.rect().adjusted(2, 2, -2, -2))
            page.advanced_toggle.click()
            page.choice.setCurrentIndex(page.choice.findData(CURRENT))
            window.select_page(5)
            with patch.object(LocalizationProfiles, 'launch', return_value={'mode': 'fixture'}) as launch:
                window.launch_btn.click()
                deadline = time.monotonic() + 20
                while page._busy or session._worker is not None:
                    app.processEvents()
                    assert time.monotonic() < deadline
                    time.sleep(0.01)
                launch.assert_called_once()
            for state in ('starting', 'running', 'exited'):
                if state == 'running':
                    session.observe(True)
                elif state == 'exited':
                    session.observe(False)
                for width, height in ((1360, 880), (1080, 720)):
                    window.resize(width, height)
                    QTest.qWait(80)
                    assert window.tabs.currentIndex() == 5
                    assert window.launch_btn.text() == page.start_btn.text()
                    assert window.launch_btn.isEnabled() == (state == 'exited')
                    for widget in (window.launch_btn, window.game_status):
                        rectangle = widget.rect()
                        rectangle.moveTopLeft(widget.mapTo(window, rectangle.topLeft()))
                        assert window.rect().contains(rectangle)
                    image = output / f'{state}-{width}.png'
                    assert window.grab().save(str(image))
                    report.append({'image': image.name, 'size': [width, height], 'state': state,
                                   'current_page_preserved': True, 'launch_button': window.launch_btn.text()})
            window.close()
            app.processEvents()
            (output / 'validation.json').write_text(json.dumps({'game_started': False, 'fixtures_only': True, 'layouts': report}, indent=2), encoding='utf8')
            print(json.dumps(report))


if __name__ == '__main__':
    main()

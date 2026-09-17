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

from PySide6.QtWidgets import QApplication
from core.game import GameInfo
from core import l10n
from core.localization_profiles import LocalizationProfiles, BUILTIN
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
            'ui/main.html': 'fixture', l10n.BRAND_META: json.dumps({'package_id': l10n.PACKAGE_ID})})
        game = GameInfo(game_root, game_root / 'win32/BattleBrothers.exe', '1.5.2.3', game_root / 'data')
        with patch.dict(os.environ, APPDATA=str(base / 'profile')), \
                patch('ui.app_context.game_mod.locate_game', return_value=game), \
                patch('ui.app_context.game_mod.find_log_write_path', return_value=None), \
                patch('core.game.is_game_running', return_value=False), \
                patch('core.localization_profiles.subprocess.Popen', side_effect=AssertionError('No game launch allowed')), \
                patch('core.native_font.launch_localized', side_effect=AssertionError('No game launch allowed')):
            profiles = LocalizationProfiles(game_root)
            profiles.register('示例旧汉化与专用字体', [old, font])
            profiles.register('BBMOD 独立汉化', [own], builtin=True)
            window = MainWindow()
            window.show()
            window.select_page(2)
            window.l10n.management.select_profile(BUILTIN)
            deadline = time.monotonic() + 40
            while any(worker.isRunning() for worker in window.findChildren(Worker)):
                app.processEvents()
                if time.monotonic() > deadline:
                    raise TimeoutError('Desktop worker did not finish')
                time.sleep(0.02)
            report = []
            for width, height in ((1360, 880), (1080, 720)):
                window.resize(width, height)
                for tab, name in ((0, 'manager'), (1, 'editor')):
                    window.l10n.sections.setCurrentIndex(tab)
                    app.processEvents()
                    assert (window.width(), window.height()) == (width, height)
                    widgets = [window.pick_btn, window.launch_btn]
                    if tab == 0:
                        page = window.l10n.management
                        widgets += [page.apply_btn, page.start_btn, page.import_btn, page.existing_btn, page.builtin_btn]
                    for widget in widgets:
                        rectangle = widget.rect()
                        rectangle.moveTopLeft(widget.mapTo(window, rectangle.topLeft()))
                        assert window.rect().contains(rectangle), widget.text()
                        assert widget.width() >= widget.minimumSizeHint().width(), widget.text()
                    image = output / f'{name}-{width}.png'
                    assert window.grab().save(str(image))
                    report.append({'image': image.name, 'size': [width, height], 'buttons_visible': True})
            window.close()
            app.processEvents()
            (output / 'validation.json').write_text(json.dumps({'game_started': False, 'fixtures_only': True, 'layouts': report}, indent=2), encoding='utf8')
            print(json.dumps(report))


if __name__ == '__main__':
    main()

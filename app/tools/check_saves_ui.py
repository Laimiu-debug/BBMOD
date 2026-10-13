"""Render both save-sharing tabs with isolated synthetic files and gallery data."""
import json
import os
from pathlib import Path
import sys
import tempfile
import time
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from core.game import GameInfo
from ui.main_window import MainWindow, apply_dark_palette
from ui.workers import Worker


def main():
    output = Path(__file__).resolve().parents[1] / 'build/review/save-sharing'
    output.mkdir(parents=True, exist_ok=True)
    app = QApplication.instance() or QApplication([])
    apply_dark_palette(app)
    identity = '00000000-0000-0000-0000-000000000001'
    gallery = {'page': 1, 'pages': 1, 'total': 1, 'items': [{'id': identity,
        'name': '示例战团 · 第 100 天', 'note': '演示数据：继续北方战团的远征，存档附带分享时的整套 MOD。',
        'dlcs': ['Lindwurm', 'Blazing Deserts'], 'mod_count': 21, 'total_size': 45 * 1024**2,
        'game_version': '1.5.2.3', 'page_path': f'/saves/{identity}/'}]}
    with tempfile.TemporaryDirectory(prefix='bbmod-save-ui-') as temporary:
        root = Path(temporary)
        directory = root / 'Documents/Battle Brothers/savegames'
        directory.mkdir(parents=True)
        (directory / '示例战团.sav').write_bytes(b'\xbb\x00\x02\x41\x00\x00\x00' + b'fixture' * 100)
        game_root = root / '演示游戏'
        (game_root / 'data').mkdir(parents=True)
        game = GameInfo(game_root, game_root / 'win32/BattleBrothers.exe', '1.5.2.3', game_root / 'data')
        with patch.dict(os.environ, APPDATA=str(root / 'profile')), \
             patch('ui.app_context.game_mod.locate_game', return_value=game), \
             patch('ui.app_context.game_mod.find_log_write_path', return_value=None), \
             patch('core.game.is_game_running', return_value=False), \
             patch('core.game.launch_executable', side_effect=AssertionError('No game launch')), \
             patch('ui.saves_page.shared_saves.fetch_saves', return_value=gallery):
            window = MainWindow(auto_updates=False)
            window.ctx.settings.set('savegames_directory', str(directory))
            window.setAttribute(Qt.WA_DontShowOnScreen)
            window.show()
            window.select_page(8)
            reports = []
            for width, height in ((1360, 880), (1080, 720)):
                window.resize(width, height)
                for tab in (0, 1):
                    window.saves.sections.setCurrentIndex(tab)
                    deadline = time.monotonic() + 30
                    while any(w.isRunning() for w in window.findChildren(Worker)):
                        app.processEvents()
                        assert time.monotonic() < deadline
                        QTest.qWait(20)
                    QTest.qWait(100)
                    assert (window.width(), window.height()) == (width, height)
                    target = output / f'saves-{tab}-{width}.png'
                    assert window.grab().save(str(target))
                    buttons = (window.saves.share_btn, window.saves.import_btn, window.saves.recover_btn) if not tab else (
                        window.saves.restore_btn, window.saves.copy_btn, window.saves.detail_btn)
                    for button in buttons:
                        if not button.isVisible():
                            continue
                        rect = button.rect()
                        rect.moveTopLeft(button.mapTo(window, rect.topLeft()))
                        assert window.rect().contains(rect), (button.text(), rect.getRect(), width, height,
                            window.saves.minimumSizeHint().toTuple(), window.saves.online_table.minimumSizeHint().toTuple(),
                            window.saves.online_table.minimumSize().toTuple(), window.saves.details.minimumSize().toTuple(),
                            window.tabs.size().toTuple(), window.saves.size().toTuple(), window.saves.minimumSize().toTuple())
                    reports.append({'width': width, 'tab': tab, 'path': str(target), 'buttons_in_bounds': True})
            window.close()
            app.processEvents()
    (output / 'layout.json').write_text(json.dumps(reports, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(reports, ensure_ascii=False))


if __name__ == '__main__':
    main()

"""Render website screenshots using isolated, explicitly fictional MOD data."""
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch
import zipfile

os.environ['QT_QPA_PLATFORM'] = 'offscreen'
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtWidgets import QApplication
from core.modmanager import ModManager
from ui.main_window import MainWindow, apply_dark_palette


def main():
    output = Path(__file__).resolve().parents[2] / 'web/static/screenshots'
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='bbmod-shots-') as temporary:
        os.environ['APPDATA'] = temporary
        application = QApplication([])
        apply_dark_palette(application)
        with patch('core.game.locate_game', return_value=None), patch('core.game.is_game_running', return_value=False):
            window = MainWindow(auto_updates=False)
            window.resize(1360, 880)
            window.ctx.game_session.shutdown()
            root = Path(temporary) / 'demo-game'
            for name, title, enabled in [('mod_demo_ui', '界面便捷工具（演示）', True),
                    ('mod_demo_equipment', '装备外观（演示）', True), ('mod_demo_balance', '战斗调整（演示）', False)]:
                directory = root / ('data' if enabled else 'bbmod_disabled')
                directory.mkdir(parents=True, exist_ok=True)
                with zipfile.ZipFile(directory / f'{name}.zip', 'w') as archive:
                    archive.writestr('scripts/!mods_preload/demo.nut', f'::Hooks.register("{name}", "1.0.0", "{title}");')
            window.ctx.mm = ModManager(root)
            window.mods.refresh()
            window.path_edit.setText('演示游戏目录 · 未连接真实游戏')
            window.game_status.setText('界面预览 · 未启动游戏')
            window.dashboard.overview_label.setText('请先确认游戏目录\n当前汉化：尚未连接游戏')
            window.dashboard.summary_label.setText('选择游戏目录后，这里会显示依赖、冲突与版本诊断。')
            window.select_page(1)
            window.mods.status_label.setText('界面预览 · 以下 3 项为演示数据')
            window.show()
            application.processEvents()
            assert window.grab().save(str(output / 'mod-manager.png'))
            window.select_page(0)
            application.processEvents()
            assert window.grab().save(str(output / 'camp-overview.png'))
            for worker in window.findChildren(__import__('ui.workers', fromlist=['Worker']).Worker):
                worker.wait(5000)
            window.close()
    print(output)


if __name__ == '__main__':
    main()

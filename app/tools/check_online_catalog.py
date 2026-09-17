"""Exercise the real online page against a local fixture server, using only a temporary game directory."""
import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication, QMessageBox
from core.settings import Settings
from core.modmanager import ModManager
from ui.online_mods import OnlineModsPage
from ui.theme import apply_theme


class Context(QObject):
    management_changed = Signal(bool)
    session_changed = Signal(bool)
    data_changed = Signal()
    management_busy = False
    seedgen_active = False
    def set_management_busy(self, active):
        self.management_busy = active
        self.management_changed.emit(active)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='http://127.0.0.1:8766')
    args = parser.parse_args()
    if not args.url.startswith(('http://127.0.0.1:', 'http://localhost:')):
        raise ValueError('此测试仅允许本地隔离服务器。')
    out = ROOT / 'build/review/online'
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='bbmod-online-test-') as temp:
        os.environ['APPDATA'] = temp
        app = QApplication([]); apply_theme(app)
        ctx = Context(); ctx.settings = Settings()
        game = Path(temp) / '隔离游戏'; (game / 'data').mkdir(parents=True)
        (game / 'data/data_001.dat').write_bytes(b'untouched original fixture')
        ctx.mm = ModManager(game)
        page = OnlineModsPage(ctx, lambda: not ctx.management_busy)
        page.resize(1050, 650); page.show()
        def wait():
            deadline = time.monotonic() + 20
            while page.worker and page.worker.isRunning() and time.monotonic() < deadline:
                app.processEvents(); time.sleep(.015)
            app.processEvents()
            assert not page.worker.isRunning(), 'network task did not finish'
        page.address.setText(args.url); page.refresh(); wait()
        assert len(page.items) == 1, page.status.text()
        assert '非正式 MOD' in page.items[0]['metadata']['title'], '只允许安装明确标注的测试样例'
        page.table.selectRow(0); app.processEvents()
        for button in [page.refresh_btn, page.install_btn, page.rollback_btn, page.cancel_btn]:
            assert page.rect().contains(button.mapTo(page, button.rect().bottomRight()))
        with patch.object(QMessageBox, 'question', return_value=QMessageBox.Yes), patch('core.game.is_game_running', return_value=False):
            page.install(); wait()
        item = page.items[0]
        installed = game / 'data' / item['file_name']
        assert installed.is_file(), page.status.text()
        assert (game / 'data/data_001.dat').read_bytes() == b'untouched original fixture'
        assert ctx.settings.get('online_catalog_url') == args.url
        assert not ctx.management_busy
        page.grab().save(str(out / 'online-mods.png'))
        report = {'game_started': False, 'isolated_ui_download_install': True, 'sha256': item['sha256'], 'status': page.status.text()}
        (out / 'integration.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(report, ensure_ascii=False)); page.close()


if __name__ == '__main__': main()

"""Qt interaction, real HTTP feedback retries, native hotkey and UI renders."""
import ctypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    with tempfile.TemporaryDirectory(prefix='bbmod-234-') as folder:
        os.environ['APPDATA'] = folder
        from PySide6.QtCore import Qt, QPoint, QRect
        from PySide6.QtGui import QKeySequence, QCursor
        from PySide6.QtTest import QTest
        from PySide6.QtWidgets import QApplication
        from ui.main_window import MainWindow, apply_dark_palette
        from ui.workers import Worker
        from core.item_inspector import MARKER, HoverLog, catalog
        app = QApplication([]); apply_dark_palette(app)
        window = MainWindow(auto_updates=False)
        window.setAttribute(Qt.WA_DontShowOnScreen); window.show()
        def wait(predicate, seconds=15):
            deadline = time.monotonic() + seconds
            while not predicate() and time.monotonic() < deadline:
                app.processEvents(); time.sleep(.01)
            assert predicate(), 'UI operation did not complete'
        wait(lambda: not any(w.isRunning() for w in window.findChildren(Worker)))
        out = ROOT / 'build/review/desktop-234'; out.mkdir(parents=True, exist_ok=True)
        assert window.tabs.count() == 7
        assert window.nav_buttons[4].y() == max(button.y() for button in window.nav_buttons)
        assert window.nav_buttons[4].shortcut().toString() == 'Alt+7'
        assert window.nav_buttons[5].text() == '装备百科' and window.nav_buttons[6].text() == '反馈与建议'
        QTest.mouseClick(window.nav_buttons[4], Qt.LeftButton)
        assert window.settings_page.updates.check.isVisible()
        window.grab().save(str(out / 'settings.png'))
        page = window.inspector
        page.overlay.setAttribute(Qt.WA_DontShowOnScreen)
        # Real RegisterHotKey and WM_HOTKEY dispatch, without typing into other apps.
        page.hotkey.set_shortcut('Ctrl+Alt+D')
        ctypes.windll.user32.PostThreadMessageW(ctypes.windll.kernel32.GetCurrentThreadId(), 0x0312, page.hotkey.identifier, 0)
        wait(lambda: not page.enabled.isChecked())
        assert not page.overlay.isVisible()
        ctypes.windll.user32.PostThreadMessageW(ctypes.windll.kernel32.GetCurrentThreadId(), 0x0312, page.hotkey.identifier, 0)
        wait(lambda: page.enabled.isChecked())
        page.shortcut.setKeySequence(QKeySequence('Ctrl+Shift+Q'))
        page.apply_key.click()
        assert page.hotkey.current == 'Ctrl+Shift+Q'
        assert window.ctx.settings.get('item_inspector')['shortcut'] == 'Ctrl+Shift+Q'
        page.opacity.setValue(82)
        assert page.overlay.background_opacity == .82 and window.ctx.settings.get('item_inspector')['opacity'] == 82
        log = Path(folder) / 'log.html'; log.write_text('<html>', encoding='utf-8')
        reader = HoverLog(log); reader.poll(); page.readers = [reader]
        record = {'schema':1, 'seq':1, 'kind':'item', 'token':1, 'id':'weapon.named_greatsword', 'name':'营地之刃', 'named':True,
                  'attachment':False, 'stats':{**catalog()['weapon.named_greatsword']['base'],
                    'RegularDamage':102, 'RegularDamageMax':120, 'DirectDamageAdd':.16, 'ConditionMax':100}}
        foreground = [True]
        page.foreground = lambda game: foreground[0]  # controlled game identity, never read real game memory
        native_tooltip = QRect(550, 100, 340, 580)
        page.tooltip_rect = lambda bounds: native_tooltip if bounds else None
        def feed(event):
            with log.open('a', encoding='utf8') as stream: stream.write(MARKER + json.dumps(event, ensure_ascii=False))
            page.poll(); app.processEvents()
        feed(record)
        wait(lambda: page.latest is not None)
        assert not page.overlay.isVisible()
        state = {'schema':1, 'seq':2, 'kind':'hover', 'token':1, 'visible':True, 'bounds':[550,100,340,580,1360,880]}
        feed(state)
        wait(lambda: page.overlay.isVisible())
        assert page.latest['valid'] and '41%' in page.overlay.content.toPlainText()
        assert not page.overlay.geometry().intersects(native_tooltip.adjusted(-9,-9,9,9))
        for native_tooltip in (QRect(30,30,450,600), QRect(830,30,450,600), QRect(450,300,500,450)):
            page.sync_overlay(); assert page.overlay.isVisible()
            assert not page.overlay.geometry().intersects(native_tooltip.adjusted(-9,-9,9,9))
        native_tooltip = QRect(550,100,340,580)
        page.sync_overlay()
        QTest.mouseClick(window.nav_buttons[5], Qt.LeftButton); app.processEvents()
        assert page.sections.currentIndex() == 0 and page.catalog_page.table.rowCount() > 94
        window.grab().save(str(out / 'equipment-table.png'))
        page.sections.setCurrentIndex(1); app.processEvents()
        window.grab().save(str(out / 'inspector.png'))
        page.overlay.grab().save(str(out / 'overlay.png'))
        feed({**state, 'seq':3, 'visible':False})
        assert not page.overlay.isVisible()
        feed({**state, 'seq':4}); assert page.overlay.isVisible()
        foreground[0] = False; page.sync_overlay(); assert not page.overlay.isVisible()
        foreground[0] = True; page.sync_overlay(); assert page.overlay.isVisible()
        page.hover.heartbeat -= 2; page.sync_overlay(); assert not page.overlay.isVisible()
        feed({**record, 'seq':5, 'token':2, 'named':False})
        feed({**state, 'seq':6, 'token':2}); assert not page.overlay.isVisible()
        feed({**record, 'seq':7, 'token':3}); feed({**state, 'seq':8, 'token':3})
        assert page.overlay.isVisible()
        page.toggle_overlay(); assert not page.overlay.isVisible()
        page.toggle_overlay(); page.sync_overlay(); assert page.overlay.isVisible()
        page.hover.reset(); page.sync_overlay(); assert not page.overlay.isVisible()
        page.hotkey.clear()
        assert not page.hotkey.registered
        feedback = window.feedback
        fixture = {'calls': [], 'fail': True, 'saved': set()}
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                body = json.dumps({'schema_version':1,'submission':'signed-ticket','csrf_token':'test-token'}).encode()
                self.send_response(200); self.send_header('Set-Cookie','sessionid=test-session; Path=/')
                self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body)
            def do_POST(self):
                record = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                assert 'sessionid=test-session' in self.headers.get('Cookie','')
                assert self.headers['X-CSRFToken'] == 'test-token'
                fixture['calls'].append(record); fixture['saved'].add(record['submission'])
                body = b'network interrupted' if fixture['fail'] else json.dumps({'schema_version':1,'reference':'A234B567C890'}).encode()
                self.send_response(503 if fixture['fail'] else 201)
                self.send_header('Content-Length', str(len(body))); self.end_headers(); self.wfile.write(body)
            def log_message(self, *_): pass
        server = ThreadingHTTPServer(('127.0.0.1',0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        try:
            feedback.origin = f'http://127.0.0.1:{server.server_port}'
            feedback.endpoint = feedback.origin + '/api/v1/suggestions/'
            QTest.mouseClick(window.nav_buttons[6], Qt.LeftButton)
            feedback.title.setText('希望增加鉴定快捷键选项')
            feedback.details.setPlainText('在游戏背包悬停查看红装时，希望能选择自己习惯的快捷键。')
            feedback.contact.setText('local-test@example.test')
            QTest.mouseClick(feedback.submit_button, Qt.LeftButton)
            wait(lambda: feedback.reply is None)
            assert feedback.title.text() and '内容已保留' in feedback.status.text()
            window.grab().save(str(out / 'feedback-retry.png'))
            fixture['fail'] = False
            QTest.mouseClick(feedback.submit_button, Qt.LeftButton)
            wait(lambda: feedback.reply is None)
            assert not feedback.title.text() and 'A234B567C890' in feedback.status.text()
            assert len(fixture['calls']) == 2 and len(fixture['saved']) == 1
            assert fixture['calls'][0] == fixture['calls'][1]
            window.grab().save(str(out / 'feedback-success.png'))
        finally:
            server.shutdown(); server.server_close(); thread.join(timeout=2)
        from core.seedgen.log_watcher import SeedResult
        seeds = window.seedgen
        seeds._accept_results([SeedResult('SEED' + f'{i:06d}', i + 1, origin='scenario.militia',
            done=True, game_version='1.5.2.3', lines=['CharInfo: 0 Melee:0.9 MeleeSkill:61(96)3',
            'Trait: trait.strong', f'SettlementInfo: Port:{i % 9 + 1}']) for i in range(28)])
        QTest.mouseClick(window.nav_buttons[3], Qt.LeftButton)
        seeds.sections.setCurrentIndex(1); app.processEvents()
        assert seeds.table.viewport().height() // seeds.table.rowHeight(0) >= 7
        window.grab().save(str(out / 'seed-library.png'))
        seeds.table.selectRow(1); QTest.mouseClick(seeds.delete_btn, Qt.LeftButton)
        seeds.library_view.setCurrentIndex(1); app.processEvents()
        assert seeds.table.rowCount() == 1 and seeds.restore_btn.isEnabled()
        window.grab().save(str(out / 'seed-trash.png'))
        QTest.mouseClick(seeds.restore_btn, Qt.LeftButton)
        assert len(seeds.results) == 28
        seeds.library_view.setCurrentIndex(0)
        window.resize(1080, 720); app.processEvents()
        window.grab().save(str(out / 'seed-library-small.png'))
        window.close(); app.processEvents()
        report = {'pages':7,'global_hotkey':'registered, dispatched, unregistered',
                  'live_log_to_overlay':'passed', 'feedback_retry':'same ticket, cookies and CSRF; one receipt',
                  'auto_hover':'matching token, leave, foreground loss, timeout, non-named, pause and resume passed',
                  'custom_hotkey':'Ctrl+Shift+Q applied and saved', 'background_opacity':82,
                  'native_tooltip_avoidance':'left, center, right and lower tooltip positions do not overlap',
                  'game_foreground':'controlled fixture; actual in-game acceptance remains pending',
                  'network_target':'isolated local fixture', 'seed_library':'28 records, delete and restore, 7+ visible rows', 'screenshots':9}
        (out / 'result.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__': main()

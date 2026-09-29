import json
import threading
import time
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace
import zipfile

import pytest
from PySide6.QtCore import QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from core.diagnostics import DiagnosisReport, Issue
from core.modmanager import ModManager
from core.support_report import MAX_REPORT_CHARS, build_report
from ui.feedback_page import FeedbackPage


def test_report_captures_error_context_versions_and_redacts_paths(tmp_path):
    root = tmp_path / 'game'
    (root / 'data').mkdir(parents=True)
    with zipfile.ZipFile(root / 'data/mod_example.zip', 'w') as archive:
        archive.writestr('scripts/!mods_preload/example.nut', '::mods_registerMod("example", 2.5);')
    error = "the index 'Big' does not exist"
    rows = [('error', error), ('info', 'stack: scripts/example.nut line 123'),
            ('info', r'C:\Users\Alice\game\log.html alice@example.test 192.168.1.5')]
    rows.extend(('info', 'later debug') for _ in range(100))
    (tmp_path / 'log.html').write_text(''.join(
        f'<div class="row {level}"><div class="time">08:19:50</div><div class="tag">SQ</div><div class="text">{escape(text)}</div></div>'
        for level, text in rows), encoding='utf-8')
    ctx = SimpleNamespace(game=SimpleNamespace(root=root, version='1.5.2.3'),
                          mm=ModManager(root), log_dir=lambda: tmp_path)
    report = DiagnosisReport(issues=[Issue('error', '运行时', error, 'complete diagnostic')])
    result = build_report(ctx, report)
    assert error in result and 'scripts/example.nut line 123' in result
    assert 'example v2.5' in result and '1.5.2.3' in result
    assert 'Alice' not in result and 'alice@' not in result and '192.168.1.5' not in result
    assert len(result) <= MAX_REPORT_CHARS


def test_report_without_game_and_large_diagnosis_is_bounded():
    ctx = SimpleNamespace(game=None, mm=None, log_dir=lambda: None)
    report = DiagnosisReport(issues=[Issue('error', 'test', 'error', 'x' * 8000) for _ in range(60)])
    result = build_report(ctx, report)
    assert '未选择游戏' in result and '未找到游戏 log.html' in result
    assert len(result) <= MAX_REPORT_CHARS and '已省略' in result


@pytest.fixture
def application():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def service():
    state = {'posts': [], 'saved': {}, 'fail': False, 'supports_report': True, 'cookies': [], 'expired': False}
    class Handler(BaseHTTPRequestHandler):
        def respond(self, code, data):
            raw = json.dumps({'schema_version': 1, **data}).encode()
            self.send_response(code)
            self.send_header('Set-Cookie', 'sessionid=local-test; Path=/')
            self.send_header('Content-Length', str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self):
            self.respond(200, {'submission': 'same-ticket', 'csrf_token': 'test-token',
                               **({'diagnostic_report_max_length': MAX_REPORT_CHARS} if state['supports_report'] else {})})

        def do_POST(self):
            data = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            state['posts'].append(data)
            state['cookies'].append(self.headers.get('Cookie', ''))
            if state['expired']:
                self.respond(400, {'code': 'ticket_expired', 'error': 'expired'})
                return
            state['saved'].setdefault(data['submission'], data)
            self.respond(503, {'error': '连接中断'}) if state['fail'] else self.respond(201, {'reference': 'A234B567C890'})

        def log_message(self, *_):
            pass
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    state['origin'] = f'http://127.0.0.1:{server.server_port}'
    yield state
    server.shutdown(); server.server_close(); thread.join(timeout=2)


def wait_for_reply(page, application):
    deadline = time.monotonic() + 5
    while page.reply is not None and time.monotonic() < deadline:
        application.processEvents()
        QTest.qWait(10)
    assert page.reply is None


def test_report_is_separate_and_retry_keeps_attachment_and_receipt(application, service):
    page = FeedbackPage()
    page.origin = service['origin']; page.endpoint = page.origin + '/api/v1/suggestions/'
    text = '诊断日志\n' * 2000
    try:
        assert page.attach_report(text, "the index 'Big' does not exist")
        assert page.kind.currentData() == 'bug'
        assert page.title.text() == "the index 'Big' does not exist"
        assert text not in page.details.toPlainText()
        assert service['posts'] == []
        page.details.setPlainText('进入新战役时发生。')
        service['fail'] = True
        page.submit(); wait_for_reply(page, application)
        assert page.diagnostic_report == text.strip()
        assert page.details.toPlainText() == '进入新战役时发生。'
        assert '已保留' in page.status.text()
        service['fail'] = False
        page.submit(); wait_for_reply(page, application)
        assert service['posts'][0] == service['posts'][1]
        assert len(service['saved']) == 1
        assert service['posts'][0]['diagnostic_report'] == text.strip()
        assert '错误报告已送达' in page.status.text() and 'A234B567C890' in page.status.text()
        assert not page.diagnostic_report and not page.details.toPlainText()
    finally:
        page.shutdown(); page.close()


def test_unsupported_server_keeps_report_without_silent_drop(application, service):
    service['supports_report'] = False
    page = FeedbackPage()
    page.origin = service['origin']; page.endpoint = page.origin + '/api/v1/suggestions/'
    try:
        page.attach_report('diagnostic')
        page.submit(); wait_for_reply(page, application)
        assert service['posts'] == [] and page.diagnostic_report == 'diagnostic'
        assert '暂不支持' in page.status.text()
    finally:
        page.shutdown(); page.close()


def test_report_edit_preserves_description_and_remove_omits_payload(application, service):
    page = FeedbackPage()
    page.origin = service['origin']; page.endpoint = page.origin + '/api/v1/suggestions/'
    try:
        page.title.setText('我的标题'); page.details.setPlainText('我的复现步骤')
        assert page.attach_report('old')
        assert not page.attach_report('x' * (MAX_REPORT_CHARS + 1))
        assert page.diagnostic_report == 'old'
        assert page.attach_report('edited')
        from ui.support_dialog import SupportDialog
        def accept_edit():
            dialog = next(w for w in application.topLevelWidgets() if isinstance(w, SupportDialog))
            dialog.editor.setPlainText('reviewed text')
            dialog.accept()
        QTimer.singleShot(10, accept_edit)
        page.edit_report_button.click()
        assert page.diagnostic_report == 'reviewed text'
        assert page.title.text() == '我的标题' and page.details.toPlainText() == '我的复现步骤'
        page.remove_report()
        page.submit(); wait_for_reply(page, application)
        assert 'diagnostic_report' not in service['posts'][0]
    finally:
        page.shutdown(); page.close()

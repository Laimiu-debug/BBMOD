import json
import time
from html import escape
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from PySide6.QtCore import QObject, Signal
from PySide6.QtTest import QTest

from core.crash_reports import AUTO_UPLOAD_KEY, MAX_LOG_BYTES, ReportStore, begin_session, read_session_log
from core.settings import Settings
from ui.crash_reports import CrashReports
from ui.game_session import GameSession
from test_error_reports import application, service  # Local HTTP server; never posts real reports.


def row(text, level='error'):
    return f'<div class="row {level}"><div class="time">12:00:00</div><div class="tag">SQ</div><div class="text">{escape(text)}</div></div>'


class Context(QObject):
    session_changed = Signal(bool)

    def __init__(self, root):
        super().__init__()
        self.settings = Settings()
        self.settings.path = root / 'settings.json'
        self.settings.data = {}
        self.game_session = GameSession(self, probe=lambda: False)
        self.game = None
        self.mm = None
        self.seedgen_active = False


@pytest.fixture
def ctx(application, tmp_path):
    result = Context(tmp_path)
    yield result
    result.game_session.shutdown()


def capture(store, root, ctx, automatic=False, error='new crash'):
    folder = root / 'game-log'
    folder.mkdir(exist_ok=True)
    path = folder / 'log.html'
    session = begin_session([folder])
    with path.open('a', encoding='utf-8') as stream:
        stream.write(row(error))
    return store.capture(ctx, session, [folder], automatic)


def settle(service, application):
    deadline = time.monotonic() + 6
    while (service.reply is not None or service.worker is not None) and time.monotonic() < deadline:
        application.processEvents()
        QTest.qWait(10)
    assert service.reply is None and service.worker is None


def test_unchanged_old_errors_and_clean_shutdown_are_ignored(tmp_path):
    path = tmp_path / 'log.html'
    path.write_text(row('old failure'), encoding='utf-8')
    session = begin_session([tmp_path])
    assert read_session_log(path, session) is None
    with path.open('a', encoding='utf-8') as stream:
        stream.write(row('ordinary debug', 'info'))
    assert read_session_log(path, session) is None
    with path.open('a', encoding='utf-8') as stream:
        stream.write(row('new failure') + row('Shutting down engine core.', 'info'))
    assert read_session_log(path, session) is None


def test_replaced_log_and_new_errors_are_collected(tmp_path, ctx):
    path = tmp_path / 'log.html'
    path.write_text(row('old failure') * 20, encoding='utf-8')
    session = begin_session([tmp_path])
    path.write_text(row('new failure') + row('stack: line 88', 'info'), encoding='utf-8')
    store = ReportStore(tmp_path / 'reports')
    item = store.capture(ctx, session, [tmp_path])
    assert item['state'] == 'manual' and not item['automatic']
    assert 'new failure' in item['payload']['diagnostic_report']
    assert 'stack: line 88' in item['payload']['diagnostic_report']
    assert 'old failure' not in item['payload']['diagnostic_report']
    snapshot = (store.folder(item['id']) / 'log.html').read_bytes()
    path.write_text('next launch', encoding='utf-8')
    assert (store.folder(item['id']) / 'log.html').read_bytes() == snapshot
    assert ReportStore(store.root).get(item['id']) == item


def test_missing_and_non_error_logs_do_not_report(tmp_path):
    path = tmp_path / 'log.html'
    session = begin_session([tmp_path])
    assert read_session_log(path, session) is None
    path.write_text(row('hello', 'info'), encoding='utf-8')
    assert read_session_log(path, session) is None


def test_large_log_is_bounded_and_personal_data_redacted(tmp_path, ctx):
    path = tmp_path / 'log.html'
    session = begin_session([tmp_path])
    path.write_text('x' * (MAX_LOG_BYTES + 100) + row(r'crash C:\Users\Alice\game alice@example.test 192.168.0.5'), encoding='utf-8')
    item = ReportStore(tmp_path / 'reports').capture(ctx, session, [tmp_path])
    assert item['partial_log']
    assert (tmp_path / 'reports' / item['id'] / 'log.html').stat().st_size <= MAX_LOG_BYTES
    assert 'Alice' not in item['payload']['diagnostic_report'] and 'Alice' not in item['payload']['title']
    assert len(item['payload']['diagnostic_report']) <= 60000


def test_queue_bound_preserves_unsubmitted_reports(tmp_path, ctx, monkeypatch):
    monkeypatch.setattr('core.crash_reports.MAX_RECORDS', 2)
    store = ReportStore(tmp_path / 'reports')
    first = capture(store, tmp_path, ctx)
    second = capture(store, tmp_path, ctx)
    with pytest.raises(OSError, match='已保留'):
        capture(store, tmp_path, ctx)
    assert len(store.records()) == 2
    first['state'] = 'sent'
    store.save(first)
    capture(store, tmp_path, ctx)
    assert len(store.records()) == 2 and store.get(second['id'])['state'] == 'manual'
    assert not store.folder(first['id']).exists()


def test_upload_off_by_default_and_manual_review_sends_saved_snapshot(application, service, ctx, tmp_path):
    monitor = CrashReports(ctx, automatic=True, origin=service['origin'])
    monitor.timer.stop()
    try:
        item = capture(monitor.store, tmp_path, ctx)
        monitor.pump()
        application.processEvents()
        assert service['posts'] == []
        from ui.crash_report_dialog import CrashReportDialog
        dialog = CrashReportDialog(monitor)
        dialog.editor.setPlainText('reviewed log')
        dialog.details.setPlainText('点击新战役时闪退')
        dialog.send()
        settle(monitor, application)
        assert service['posts'][0]['diagnostic_report'] == 'reviewed log'
        assert service['posts'][0]['details'] == '点击新战役时闪退'
        assert monitor.store.get(item['id'])['state'] == 'sent'
        assert monitor.store.get(item['id'])['reference'] == 'A234B567C890'
        dialog.close()
    finally:
        monitor.shutdown()


def test_retry_after_restart_preserves_payload_ticket_and_cookies(application, service, ctx, tmp_path):
    ctx.settings.set(AUTO_UPLOAD_KEY, True)
    monitor = CrashReports(ctx, automatic=True, origin=service['origin'])
    monitor.timer.stop()
    item = capture(monitor.store, tmp_path, ctx, automatic=True)
    service['fail'] = True
    monitor.pump()
    settle(monitor, application)
    saved = monitor.store.get(item['id'])
    assert saved['ticket'] and saved['cookies'] and saved['posted']
    monitor.shutdown()
    monitor = CrashReports(ctx, automatic=True, origin=service['origin'])
    monitor.timer.stop()
    try:
        saved['next_retry'] = 0
        monitor.store.save(saved)
        service['fail'] = False
        monitor.pump()
        settle(monitor, application)
        assert len(service['posts']) == 2 and len(service['saved']) == 1
        assert service['posts'][0] == service['posts'][1]
        assert all('sessionid=local-test' in value for value in service['cookies'])
        assert monitor.store.get(item['id'])['state'] == 'sent'
    finally:
        monitor.shutdown()


def test_auto_retry_limit_and_switch_off(application, service, ctx, tmp_path):
    ctx.settings.set(AUTO_UPLOAD_KEY, True)
    monitor = CrashReports(ctx, automatic=True, origin=service['origin'])
    monitor.timer.stop()
    try:
        item = capture(monitor.store, tmp_path, ctx, automatic=True)
        service['fail'] = True
        for _ in range(3):
            item = monitor.store.get(item['id']); item['next_retry'] = 0
            monitor.store.save(item)
            monitor.pump(); settle(monitor, application)
        monitor.pump(); settle(monitor, application)
        assert len(service['posts']) == 3
        ctx.settings.set(AUTO_UPLOAD_KEY, False)
        capture(monitor.store, tmp_path, ctx, automatic=True)
        monitor.pump(); settle(monitor, application)
        assert len(service['posts']) == 3
    finally:
        monitor.shutdown()


def test_unsupported_server_does_not_discard_or_post(application, service, ctx, tmp_path):
    monitor = CrashReports(ctx, automatic=False, origin=service['origin'])
    try:
        item = capture(monitor.store, tmp_path, ctx)
        service['supports_report'] = False
        monitor.send(item['id']); settle(monitor, application)
        assert service['posts'] == []
        saved = monitor.store.get(item['id'])
        assert saved['state'] == 'review' and '不支持' in saved['message']
    finally:
        monitor.shutdown()


def test_only_bbmod_launch_exit_collects_and_seedgen_is_excluded(application, ctx, tmp_path):
    monitor = CrashReports(ctx, automatic=False)
    session = ctx.game_session
    try:
        with patch('core.game.find_log_write_paths', return_value=[tmp_path]):
            session.observe(True); session.observe(False)
            assert monitor.worker is None
            session.begin_launch()
            (tmp_path / 'log.html').write_text(row('launch crash'), encoding='utf-8')
            session.observe(True); session.observe(False)
            assert session.state == 'collecting' and not session.begin_launch()
            settle(monitor, application)
            assert len(monitor.store.records()) == 1 and session.state == 'idle'
            session.begin_launch()
            ctx.seedgen_active = True
            ctx.session_changed.emit(True)
            (tmp_path / 'log.html').write_text(row('seedgen error'), encoding='utf-8')
            session.observe(True); session.observe(False)
            assert monitor.worker is None and len(monitor.store.records()) == 1
    finally:
        monitor.shutdown()


def test_quick_exit_during_start_timeout_collects(application, ctx, tmp_path):
    monitor = CrashReports(ctx, automatic=False)
    session = ctx.game_session
    try:
        with patch('core.game.find_log_write_paths', return_value=[tmp_path]):
            session.observe(False); session.begin_launch()
            (tmp_path / 'log.html').write_text(row('quick crash'), encoding='utf-8')
            session._deadline = -1
            session.observe(False)
            settle(monitor, application)
            assert len(monitor.store.records()) == 1
    finally:
        monitor.shutdown()


def test_settings_switch_persists_and_rolls_back_on_write_error(ctx):
    from ui.settings_page import SettingsPage
    page = SettingsPage(ctx.settings)
    try:
        assert not page.auto_crash_upload.isChecked()
        page.auto_crash_upload.click()
        assert json.loads(ctx.settings.path.read_text(encoding='utf-8'))[AUTO_UPLOAD_KEY] is True
        with patch.object(ctx.settings, 'save', side_effect=OSError('disk full')):
            page.auto_crash_upload.click()
        assert ctx.settings.get(AUTO_UPLOAD_KEY) is True and page.auto_crash_upload.isChecked()
    finally:
        page.close()


def test_expired_ambiguous_request_requires_review_and_never_auto_renews(application, service, ctx, tmp_path):
    ctx.settings.set(AUTO_UPLOAD_KEY, True)
    monitor = CrashReports(ctx, automatic=True, origin=service['origin'])
    monitor.timer.stop()
    try:
        item = capture(monitor.store, tmp_path, ctx, automatic=True)
        service['expired'] = True
        monitor.pump(); settle(monitor, application)
        assert monitor.store.get(item['id'])['state'] == 'review'
        monitor.pump(); settle(monitor, application)
        assert len(service['posts']) == 1
        assert not monitor.send(item['id'])
    finally:
        monitor.shutdown()


def test_disable_while_fetching_ticket_prevents_post(application, service, ctx, tmp_path):
    ctx.settings.set(AUTO_UPLOAD_KEY, True)
    monitor = CrashReports(ctx, automatic=True, origin=service['origin'])
    monitor.timer.stop()
    try:
        capture(monitor.store, tmp_path, ctx, automatic=True)
        monitor.pump()
        ctx.settings.set(AUTO_UPLOAD_KEY, False)
        settle(monitor, application)
        assert not service['posts'] and len(monitor.store.records()) == 1
    finally:
        monitor.shutdown()


def test_process_query_failure_does_not_emit_exit(application):
    from core.game import probe_game_running
    session = GameSession(probe=lambda: (_ for _ in ()).throw(RuntimeError('query failed')))
    ended = []
    session.launch_ended.connect(lambda: ended.append(True))
    session.observe(False); session.begin_launch(); session.observe(True)
    session.poll()
    deadline = time.monotonic() + 2
    while session._worker and time.monotonic() < deadline:
        application.processEvents(); QTest.qWait(10)
    assert session.state == 'running' and not ended
    with patch('core.game.subprocess.run', return_value=SimpleNamespace(returncode=1, stdout='')):
        with pytest.raises(RuntimeError):
            probe_game_running()
    session.shutdown()

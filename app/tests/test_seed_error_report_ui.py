"""Seed errors are snapshotted independently of normal game-exit reporting.

Every file lives in tmp_path; game process operations are mocked and uploads
only reach the existing loopback HTTP fixture.
"""
import time
from copy import deepcopy
from dataclasses import asdict
from html import escape
from threading import Event, Timer
from unittest.mock import Mock, patch

import pytest
from PySide6.QtCore import QObject, Signal
from PySide6.QtTest import QTest

from core.crash_reports import AUTO_UPLOAD_KEY, begin_session
from core.game import GameInfo
from core.seedgen.orchestrator import SeedGenOrchestrator
from core.settings import Settings
from ui.crash_reports import CrashReports
from ui.game_session import GameSession
from ui.seedgen_page import SeedGenPage
from test_error_reports import application, service


def row(text, level='info'):
    return ('<div class="row ' + level + '"><div class="time">12:00:00</div>'
            '<div class="tag">SQ</div><div class="text">' + escape(text) + '</div></div>')


class Context(QObject):
    session_changed = Signal(bool)
    data_changed = Signal()

    def __init__(self, root):
        super().__init__()
        self.settings = Settings.__new__(Settings)
        self.settings.path = root / 'settings.json'
        self.settings.data = {}
        game_root = root / 'game'
        (game_root / 'data').mkdir(parents=True)
        self.game = GameInfo(game_root, game_root / 'game.exe', '1.5.2.3', game_root / 'data')
        self.mm = Mock()
        self.seedgen_active = True
        self.game_session = GameSession(self, probe=lambda: True)
        self.game_session.observe(True)

    def set_seedgen_active(self, active):
        self.seedgen_active = active
        self.session_changed.emit(active)


@pytest.fixture
def ctx(application, tmp_path):
    context = Context(tmp_path)
    yield context
    context.game_session.shutdown()


@pytest.fixture
def page_session(application, ctx, tmp_path, monkeypatch):
    log_dir = tmp_path / 'logs'
    log_dir.mkdir()
    monkeypatch.setattr('core.game.find_log_write_paths', lambda *args: [log_dir])
    monkeypatch.setattr('core.game.is_game_running', lambda: False)
    monkeypatch.setattr('core.game.kill_game', Mock(side_effect=AssertionError('No real process control')))
    session = SeedGenOrchestrator(ctx.game, tmp_path / 'unused-payload', log_directory=log_dir)
    session.state.stage = 'running'
    session._started_at = time.monotonic() - 4 * 3600
    session.mm._audit = Mock()
    session._discover_readers()
    session._report_baseline = begin_session([log_dir])
    path = log_dir / 'log.html'
    path.write_text(row('BBMODSeedSession: ' + session._session_id)
                    + row('BBMODSeedStart: generating')
                    + row('BBMODSeedProgress: 100001(0) brothers'), encoding='utf-8')
    page = SeedGenPage(ctx)
    page.orch = session
    yield page, session, path
    page.timer.stop()
    page.shutdown_polling()
    page.orch = None
    page.close()


def append_error(path, error='generation-failed synthetic allocation error'):
    with path.open('a', encoding='utf-8') as stream:
        stream.write(row('BBMODSeedStart: error ' + error))


def test_repeated_error_polls_and_stop_emit_one_snapshot(page_session):
    page, session, path = page_session
    reports = []
    page.error_report_ready.connect(reports.append)
    append_error(path)
    page._poll()
    page._poll()
    page._poll()
    assert len(reports) == 1
    assert reports[0]['session_id'] == session._session_id
    assert 'synthetic allocation error' in reports[0]['error']
    assert '脚本出错' in page.progress_label.text()
    page.stop()
    assert len(reports) == 1


def test_stop_drains_and_reports_error_not_yet_seen_by_ui(page_session):
    page, session, path = page_session
    reports = []
    page.error_report_ready.connect(reports.append)
    page._poll()
    assert reports == []
    append_error(path, 'generation-failed final unconsumed error')
    page.stop()
    assert len(reports) == 1
    assert reports[0]['session_id'] == session._session_id
    assert 'final unconsumed error' in reports[0]['error']
    assert page.orch is None


def test_normal_stop_does_not_emit_error_report(page_session):
    page, _, _ = page_session
    reports = []
    page.error_report_ready.connect(reports.append)
    page._poll()
    page.stop()
    assert reports == []


def test_reader_failure_emits_report_without_script_error_marker(page_session):
    page, session, _ = page_session
    reports = []
    page.error_report_ready.connect(reports.append)
    page._poll()
    # A direct diagnostic invocation has no signal sender or poll worker.
    page._poll_failed('synthetic log reader failure')
    assert len(reports) == 1
    assert reports[0]['session_id'] == session._session_id
    assert 'synthetic log reader failure' in reports[0]['error']


def test_compile_error_is_reported_while_game_stays_in_menu(page_session):
    page, session, path = page_session
    reports = []
    page.error_report_ready.connect(reports.append)
    # No bootstrap/session marker was printed, but the game is still alive.
    path.write_text(row('synthetic compile failure before bootstrap', 'error'), encoding='utf-8')
    page._poll()
    page._poll()
    assert session.startup.stage == 'waiting'
    assert page.ctx.game_session.state == 'running'
    assert len(reports) == 1
    assert 'synthetic compile failure' in reports[0]['error']


def test_raw_script_error_without_generator_status_emits_report(page_session):
    page, session, path = page_session
    reports = []
    page.error_report_ready.connect(reports.append)
    with path.open('a', encoding='utf-8') as stream:
        stream.write(row('the index synthetic_test does not exist', 'error'))
    page._poll()
    page._poll()
    assert len(reports) == 1
    assert reports[0]['session_id'] == session._session_id
    assert 'synthetic_test' in reports[0]['error']


def test_game_exit_captures_fresh_compile_error_before_session_marker(page_session, ctx):
    page, _, path = page_session
    reports = []
    page.error_report_ready.connect(reports.append)
    # The preload script fails before it can print BBMODSeedSession.
    path.write_text(row('SQ compile error: synthetic invalid token', 'error'), encoding='utf-8')
    ctx.game_session.state = 'starting'
    ctx.game_session.observe(True)
    ctx.game_session.observe(False)
    assert len(reports) == 1
    assert 'synthetic invalid token' in reports[0]['error']
    assert b'BBMODSeedSession:' not in reports[0]['raw']
    assert page.orch is not None  # Evidence capture does not restore a live file session.


def test_report_freezes_search_configuration_and_progress(page_session):
    page, session, path = page_session
    reports = []
    page.error_report_ready.connect(reports.append)
    page.mode_combo.setCurrentText('人物 + 地图')
    page.origin_combo.setCurrentIndex(page.origin_combo.findData('scenario.cultists'))
    session._report_config = asdict(page._current_config())
    expected = deepcopy(session._report_config)
    append_error(path)
    page._poll()
    assert len(reports) == 1
    session._report_config['campaign']['origin'] = 'scenario.militia'
    page.mode_combo.setCurrentText('只找地图')
    assert reports[0]['metadata']['config'] == expected
    assert reports[0]['metadata']['progress']['loop_idx'] == 100001
    assert reports[0]['metadata']['elapsed_seconds'] >= 14400


def snapshot(session_id='a' * 32, error='synthetic script failure'):
    return {
        'session_id': session_id,
        'error': error,
        'metadata': {'origin': 'scenario.cultists', 'mode': 'bro_only',
                     'loop_idx': 100001, 'hits': 0, 'elapsed_seconds': 14400,
                     'game_version': '1.5.2.3'},
        'raw': (row(error, 'error') + row('stack: scripts/seed_generator.nut line 12')).encode('utf-8'),
        'partial_log': False,
        'log_name': 'log.html',
        'log_error': '',
    }


def settle(monitor, application, expected):
    deadline = time.monotonic() + 6
    while time.monotonic() < deadline:
        application.processEvents()
        if monitor.worker is None and monitor.reply is None and len(monitor.store.records()) == expected:
            return
        QTest.qWait(10)
    assert monitor.worker is None and monitor.reply is None
    assert len(monitor.store.records()) == expected


@pytest.mark.parametrize('automatic', [False, True])
def test_seed_capture_while_game_runs_is_saved_once_and_honors_upload_opt_in(
        application, service, ctx, tmp_path, automatic):
    ctx.settings.set(AUTO_UPLOAD_KEY, automatic)
    monitor = CrashReports(ctx, automatic=True, origin=service['origin'])
    monitor.timer.stop()
    outcomes = []
    monitor.session_ended.connect(outcomes.append)
    capture = snapshot()
    source = tmp_path / 'log.html'
    source.write_bytes(capture['raw'])
    capture['raw'] = source.read_bytes()
    try:
        with patch.object(monitor.network, 'get', wraps=monitor.network.get) as get, \
             patch.object(monitor.network, 'post', wraps=monitor.network.post) as post:
            monitor.collect_seed(capture)
            monitor.collect_seed(capture)
            source.write_text('replaced by the next game launch', encoding='utf-8')
            settle(monitor, application, 1)
            monitor.collect_seed(capture)
            settle(monitor, application, 1)
            item = monitor.store.records()[0]
            assert item['automatic'] is automatic
            assert item['state'] == ('sent' if automatic else 'manual')
            assert 'synthetic script failure' in item['payload']['diagnostic_report']
            assert (monitor.store.folder(item['id']) / 'log.html').read_bytes() == capture['raw']
            assert ctx.game_session.state == 'running'
            assert outcomes == []
            ctx.mm.remember_last_good.assert_not_called()
            if automatic:
                assert len(service['posts']) == 1
                assert 'synthetic script failure' in service['posts'][0]['diagnostic_report']
                assert item['reference'] == 'A234B567C890'
            else:
                get.assert_not_called()
                post.assert_not_called()
                assert service['posts'] == []
    finally:
        monitor.shutdown()


def test_second_seed_report_waits_for_current_capture_without_loss(application, ctx):
    monitor = CrashReports(ctx, automatic=False)
    entered, release = Event(), Event()
    original = monitor.store.capture_seed

    def slow_capture(value, automatic=False):
        if value['session_id'] == 'a' * 32:
            entered.set()
            assert release.wait(3), 'test did not release capture worker'
        return original(value, automatic=automatic)

    try:
        with patch.object(monitor.store, 'capture_seed', side_effect=slow_capture):
            first = snapshot()
            monitor.collect_seed(first)
            assert entered.wait(1)
            monitor.collect_seed(snapshot('b' * 32, 'second seed failure'))
            monitor.collect_seed(first)
            assert monitor.worker is not None
            release.set()
            settle(monitor, application, 2)
        assert ctx.game_session.state == 'running'
        titles = [item['payload']['title'] for item in monitor.store.records()]
        assert any('synthetic script failure' in title for title in titles)
        assert any('second seed failure' in title for title in titles)
    finally:
        release.set()
        monitor.shutdown()


def test_seed_capture_queued_behind_upload_runs_after_reply(application, service, ctx):
    monitor = CrashReports(ctx, automatic=False, origin=service['origin'])
    try:
        monitor.collect_seed(snapshot())
        settle(monitor, application, 1)
        first = monitor.store.records()[0]
        assert monitor.send(first['id'])
        assert monitor.reply is not None
        monitor.collect_seed(snapshot('b' * 32, 'failure while uploading'))
        settle(monitor, application, 2)
        assert len(service['posts']) == 1
        assert monitor.store.get(first['id'])['state'] == 'sent'
        assert any('failure while uploading' in item['payload']['title'] for item in monitor.store.records())
        assert ctx.game_session.state == 'running'
    finally:
        monitor.shutdown()


def test_shutdown_finishes_active_capture_and_persists_queued_seed(application, ctx):
    monitor = CrashReports(ctx, automatic=False)
    entered, release = Event(), Event()
    original = monitor.store.capture_seed
    releaser = Timer(0.05, release.set)

    def slow_capture(value, automatic=False):
        if value['session_id'] == 'a' * 32:
            entered.set()
            assert release.wait(3), 'shutdown test worker was not released'
        return original(value, automatic=automatic)

    try:
        with patch.object(monitor.store, 'capture_seed', side_effect=slow_capture):
            monitor.collect_seed(snapshot())
            assert entered.wait(1)
            monitor.collect_seed(snapshot('b' * 32, 'queued at application shutdown'))
            # Release the worker from a Python timer: shutdown may block Qt events.
            releaser.start()
            monitor.shutdown()
        assert len(monitor.store.records()) == 2
        assert any('queued at application shutdown' in item['payload']['title']
                   for item in monitor.store.records())
        application.processEvents()
        assert ctx.game_session.state == 'running'
    finally:
        release.set()
        if releaser.ident is not None:
            releaser.join(1)
        monitor.shutdown()


@pytest.mark.parametrize('retry', ['manual', 'shutdown'])
def test_failed_snapshot_is_retained_and_retried_after_live_log_replacement(
        application, ctx, tmp_path, retry):
    monitor = CrashReports(ctx, automatic=False)
    capture = snapshot()
    source = tmp_path / 'log.html'
    source.write_bytes(capture['raw'])
    capture['raw'] = source.read_bytes()
    original = monitor.store.capture_seed
    attempts = []

    def fail_once(value, automatic=False):
        attempts.append(value)
        if len(attempts) == 1:
            raise OSError('synthetic disk full or report capacity reached')
        return original(value, automatic=automatic)

    try:
        with patch.object(monitor.store, 'capture_seed', side_effect=fail_once):
            # Once frozen, even a storage failure after a new game log appears
            # must retain the original evidence for the later retry.
            source.write_text('replacement launch with no original error', encoding='utf-8')
            monitor.collect_seed(capture)
            settle(monitor, application, 0)
            assert len(monitor._seed_failed) == 1
            assert len(attempts) == 1
            if retry == 'shutdown':
                monitor.shutdown()
            else:
                monitor.retry_seed_captures()
                settle(monitor, application, 1)
                monitor.collect_seed(capture)
                settle(monitor, application, 1)
            items = monitor.store.records()
            assert len(items) == 1
            assert not monitor._seed_failed
            item = items[0]
            assert 'synthetic script failure' in item['payload']['diagnostic_report']
            assert (monitor.store.folder(item['id']) / 'log.html').read_bytes() == capture['raw']
            assert ctx.game_session.state == 'running'
    finally:
        monitor.shutdown()
        application.processEvents()


def test_open_report_dialog_refreshes_new_records_without_losing_unsent_draft(application, ctx):
    from ui.crash_report_dialog import CrashReportDialog

    monitor = CrashReports(ctx, automatic=False)
    dialog = CrashReportDialog(monitor)
    dialog.show()
    try:
        assert dialog.listing.count() == 0 and dialog.identity is None
        monitor.collect_seed(snapshot())
        settle(monitor, application, 1)
        assert dialog.listing.count() == 1
        first = dialog.identity
        assert first == monitor.store.records()[0]['id']
        assert 'synthetic script failure' in dialog.editor.toPlainText()
        assert not dialog.editor.isReadOnly()
        assert not dialog.details.isReadOnly()
        dialog.editor.setPlainText('Edited diagnostic draft, not submitted yet.')
        dialog.details.setPlainText('Unsubmitted reproduction steps, preserve these.')
        monitor.collect_seed(snapshot('b' * 32, 'another script failure'))
        settle(monitor, application, 2)
        assert dialog.listing.count() == 2
        assert dialog.identity == first
        assert dialog.editor.toPlainText() == 'Edited diagnostic draft, not submitted yet.'
        assert dialog.details.toPlainText() == 'Unsubmitted reproduction steps, preserve these.'
        assert not dialog.editor.isReadOnly()
        assert not monitor.store.get(first)['posted']
    finally:
        dialog.close()
        monitor.shutdown()


def test_normal_crash_waits_for_seed_capture_and_blocks_next_launch(
        application, ctx, tmp_path, monkeypatch):
    log_dir = tmp_path / 'ordinary-log'
    log_dir.mkdir()
    monkeypatch.setattr('core.game.find_log_write_paths', lambda *args: [log_dir])
    ctx.mm = None
    monitor = CrashReports(ctx, automatic=False)
    entered, release = Event(), Event()
    original = monitor.store.capture_seed

    def slow_capture(value, automatic=False):
        entered.set()
        assert release.wait(3), 'ordinary crash test did not release seed worker'
        return original(value, automatic=automatic)

    try:
        with patch.object(monitor.store, 'capture_seed', side_effect=slow_capture):
            monitor.collect_seed(snapshot())
            assert entered.wait(1)
            ctx.set_seedgen_active(False)
            ctx.game_session.observe(False)
            assert ctx.game_session.begin_launch()
            (log_dir / 'log.html').write_text(row('ordinary session failure', 'error'), encoding='utf-8')
            ctx.game_session.observe(True)
            ctx.game_session.observe(False)
            assert ctx.game_session.state == 'collecting'
            assert not ctx.game_session.begin_launch()
            release.set()
            settle(monitor, application, 2)
        records = monitor.store.records()
        assert sum(item.get('source') == 'seedgen' for item in records) == 1
        assert any('ordinary session failure' in item['payload']['diagnostic_report']
                   for item in records if item.get('source') != 'seedgen')
        assert ctx.game_session.state == 'idle'
    finally:
        release.set()
        monitor.shutdown()

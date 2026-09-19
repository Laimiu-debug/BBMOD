"""Network and recovery checks use isolated data; never publish fixture seeds."""
from dataclasses import replace
from datetime import datetime, timezone, timedelta
from email.utils import format_datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading
import time
from unittest.mock import patch

import pytest
from core.seedgen.library import SeedLibrary
from core.seedgen.protocol import seed_key
from core.seedgen.share_queue import SeedShareQueue
from core.seedgen.sharing import publish_seed, ShareReceipt, UploadError, _retry_after
from core.seedgen.presentation import note_key
from test_seed_history import record
from test_seed_live_ui import app, page


@pytest.fixture
def server():
    state = {'responses': [], 'requests': [], 'times': []}
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            state['requests'].append(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
            state['times'].append(time.monotonic())
            code, body, headers = state['responses'].pop(0)
            raw = body if isinstance(body, bytes) else json.dumps(body).encode()
            self.send_response(code)
            for key, value in headers.items(): self.send_header(key, value)
            self.send_header('Content-Length', str(len(raw)))
            self.end_headers(); self.wfile.write(raw)
        def log_message(self, *_): pass
    http = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    worker = threading.Thread(target=http.serve_forever, daemon=True); worker.start()
    yield f'http://127.0.0.1:{http.server_port}', state
    http.shutdown(); http.server_close(); worker.join(timeout=2)


PATH = '/seeds/01234567-89ab-cdef-0123-456789abcdef/'


def receipt(created=True):
    return ShareReceipt('https://bbmod.site' + PATH, created)


def test_http_created_and_duplicate_keep_original_link(server):
    origin, state = server
    state['responses'] = [(201, {'page_path': PATH, 'created': True}, {}),
                          (200, {'page_path': PATH, 'created': False}, {})]
    first = publish_seed(record(), '介绍', origin)
    second = publish_seed(record(), '改过的介绍', origin)
    assert first.url == second.url == origin + PATH
    assert first.created and not second.created
    assert state['requests'][0]['note'] == '介绍'


@pytest.mark.parametrize('code,body,headers,retry,delay', [
    (429, {'error': '分享次数较多'}, {'Retry-After': '123'}, True, 123),
    (429, [], {}, True, 3600),
    (503, b'<html>busy</html>', {'Retry-After': '5'}, True, 5),
    (409, {'error': '种子已下架'}, {}, False, None),
    (400, {'error': 42}, {}, False, None),
    (403, b'Forbidden', {}, False, None),
])
def test_http_errors_keep_status_and_retry_after(server, code, body, headers, retry, delay):
    origin, state = server; state['responses'] = [(code, body, headers)]
    with pytest.raises(UploadError) as caught:
        publish_seed(record(), origin=origin)
    error = caught.value
    assert error.status == code and error.retryable == retry and error.retry_after == delay
    assert f'HTTP {code}' in str(error)


def test_http_date_retry_after_and_invalid_value():
    future = datetime.now(timezone.utc) + timedelta(seconds=60)
    assert 58 <= _retry_after(format_datetime(future, usegmt=True)) <= 60
    assert _retry_after('nonsense') is None


def test_queue_waits_then_retries_same_seed_and_persists(server, tmp_path, monkeypatch):
    origin, state = server
    state['responses'] = [(429, {'error': '请等待'}, {'Retry-After': '1'}),
                          (201, {'page_path': PATH, 'created': True}, {})]
    monkeypatch.setattr(SeedShareQueue, 'INTERVAL', 0)
    monkeypatch.setattr(SeedShareQueue, 'RETRY_DELAYS', (0,))
    library = SeedLibrary(tmp_path/'seeds.sqlite3')
    progress = []
    queue = SeedShareQueue(library, [(record(), '原介绍')],
        upload=lambda result, note: publish_seed(result, note, origin), progress=progress.append)
    report = queue.run()
    assert report.created == 1 and report.failed == 0
    assert len(state['requests']) == 2 and state['requests'][0] == state['requests'][1]
    assert state['times'][1] - state['times'][0] >= 0.95
    assert any(value.get('waiting') for value in progress)
    assert SeedLibrary(library.path).shared_url(record()) == origin + PATH


def test_cancel_during_cooldown_preserves_server_wait_after_restart(tmp_path):
    library = SeedLibrary(tmp_path/'seeds.sqlite3')
    library.defer_sharing(3600, '网站限流')
    library.defer_sharing(2, '上传间隔')
    calls = []
    queue = SeedShareQueue(library, [(record(), '')], upload=lambda *_: calls.append(True))
    queue.progress = lambda state: queue.cancel() if state.get('waiting') else None
    started = time.monotonic(); report = queue.run()
    assert time.monotonic() - started < 1 and report.stopped and report.remaining == 1
    assert not calls
    seconds, reason = SeedLibrary(library.path).share_cooldown()
    assert seconds > 3590 and reason == '网站限流'
    assert library.shared_url(record()) == ''


def test_cancel_inflight_success_saved_and_next_batch_skips_it(tmp_path, monkeypatch):
    monkeypatch.setattr(SeedShareQueue, 'INTERVAL', 0)
    library = SeedLibrary(tmp_path/'seeds.sqlite3')
    items = [(record(), ''), (record('ABCDEFGHIJ'), '第二条')]
    def upload(*_):
        queue.cancel()
        return receipt()
    queue = SeedShareQueue(library, items, upload=upload)
    report = queue.run()
    assert report.created == 1 and report.remaining == 1 and report.stopped
    calls = []
    reopened = SeedLibrary(library.path)
    report = SeedShareQueue(reopened, items, upload=lambda *args: (calls.append(args) or receipt())).run()
    assert report.existing == 1 and report.created == 1
    assert calls == [items[1]]


def test_permanent_rejection_skips_one_but_outage_pauses_queue(tmp_path, monkeypatch):
    monkeypatch.setattr(SeedShareQueue, 'INTERVAL', 0)
    monkeypatch.setattr(SeedShareQueue, 'RETRY_DELAYS', (0, 0))
    library = SeedLibrary(tmp_path/'seeds.sqlite3')
    items = [(record(), ''), (record('ABCDEFGHIJ'), '')]
    def rejected(result, _):
        if result.seed == items[0][0].seed:
            raise UploadError('已下架', status=409)
        return receipt(False)
    report = SeedShareQueue(library, items, upload=rejected).run()
    assert report.failed == 1 and report.existing == 1 and not report.paused
    calls = []
    def busy(*args):
        calls.append(args)
        raise UploadError('网站忙', status=503, retryable=True)
    report = SeedShareQueue(library, items, upload=busy).run()
    assert len(calls) == 3 and all(args[0].seed == items[0][0].seed for args in calls)
    assert report.paused and report.failed == 1 and report.remaining == 1


def test_incomplete_and_duplicates_do_not_upload(tmp_path):
    library = SeedLibrary(tmp_path/'seeds.sqlite3')
    known = record(); library.mark_shared(known, receipt().url)
    incomplete = replace(record('ABCDEFGHIJ'), done=False)
    with patch('core.seedgen.share_queue.publish_seed') as upload:
        report = SeedShareQueue(library, [(known, ''), (known, ''), (incomplete, '')], upload=upload).run()
        upload.assert_not_called()
    assert report.total == 2 and report.existing == 1 and report.invalid == 1
    assert report.completed == 2 and '完整' in report.issues[0]


def test_disk_failure_after_success_keeps_link_and_pauses(tmp_path):
    library = SeedLibrary(tmp_path/'seeds.sqlite3')
    with patch.object(library, 'mark_shared', side_effect=OSError('disk full')):
        report = SeedShareQueue(library, [(record(), ''), (record('ABCDEFGHIJ'), '')], upload=lambda *_: receipt()).run()
    assert report.paused and report.created == 1 and report.remaining == 1
    assert report.links[0][1] == receipt().url and 'disk full' in report.issues[0]


def test_batch_includes_hidden_excludes_trash_and_does_not_copy_clipboard(page, app, monkeypatch):
    monkeypatch.setattr(SeedShareQueue, 'INTERVAL', 0)
    seeds = [record(), record('ABCDEFGHIJ'), record('ZZZZZZZZZZ')]
    page._accept_results(seeds)
    page.library.delete([seed_key(seeds[2])]); page.results = page.library.all(); page._rebuild_library()
    page.library_search.setText(seeds[0].seed)
    page.notes[note_key(seeds[1])] = '第二条介绍'
    app.clipboard().setText('keep')
    with patch('ui.seedgen_page.publish_seed', return_value=receipt()) as upload:
        page.publish_all_btn.click()
        assert not page.publish_btn.isEnabled() and not page.delete_btn.isEnabled()
        assert page._share_worker.wait(5000)
        app.processEvents()
        assert upload.call_count == 2
        assert upload.call_args_list[1].args == (seeds[1], '第二条介绍')
        assert app.clipboard().text() == 'keep'
        assert '新分享 2' in page.share_status.text()
        assert not page._share_active and page.publish_all_btn.isEnabled()
        page.publish_all_btn.click(); assert page._share_worker.wait(5000); app.processEvents()
        assert upload.call_count == 2 and '已存在 2' in page.share_status.text()


def test_single_already_shared_copies_link_without_http(page, app):
    seed = record(); page._accept_results([seed]); page.library.mark_shared(seed, receipt().url); page._show_detail()
    assert page.publish_btn.text() == '复制分享链接'
    with patch('ui.seedgen_page.publish_seed') as upload:
        page.publish_btn.click(); assert page._share_worker.wait(5000); app.processEvents()
        upload.assert_not_called()
    assert app.clipboard().text() == receipt().url and '原分享' in page.library_label.text()


def test_batch_snapshot_does_not_add_future_results(page, app, monkeypatch):
    monkeypatch.setattr(SeedShareQueue, 'INTERVAL', 0)
    page._accept_results([record()])
    started, release = threading.Event(), threading.Event()
    def upload(*_):
        started.set(); assert release.wait(3)
        return receipt()
    with patch('ui.seedgen_page.publish_seed', side_effect=upload) as send:
        page.publish_all_btn.click(); assert started.wait(3)
        page._accept_results([record('ABCDEFGHIJ')]); release.set()
        assert page._share_worker.wait(5000); app.processEvents()
        assert send.call_count == 1 and page.library.shared_url(record('ABCDEFGHIJ')) == ''

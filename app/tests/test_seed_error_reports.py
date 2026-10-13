from html import escape
import json
import os

import pytest

from core.crash_reports import MAX_LOG_BYTES, ReportStore, begin_session
from core.gamelog import LogRow
from core.seedgen.error_report import snapshot_seed_failure
from core.seedgen.log_watcher import SeedLogParser
from core.support_report import MAX_REPORT_CHARS


def row(text, level='info', tag='SQ'):
    return (f'<div class="row {level}"><div class="time">12:00:00</div>'
            f'<div class="tag">{tag}</div><div class="text">{escape(text)}</div></div>')


def snapshot(path, baseline, session_id='search-1', error='', metadata=None, paths=None):
    return snapshot_seed_failure(
        session_id=session_id, paths=paths or [path], baseline=baseline,
        metadata=metadata if metadata is not None else {
            'config': {'origin': 'scenario.militia', 'CommonConfig': {'PrintLairInfo': True}},
            'progress': {'loop_idx': 103001, 'hits': 8}, 'elapsed_seconds': 14400,
            'mods': [{'id': 'mod_seed_generator', 'version': '1.0'}],
        }, error=error,
    )


def fresh_failure(tmp_path, session_id='search-1'):
    path = tmp_path / 'log.html'
    baseline = begin_session([tmp_path])
    path.write_text(row(f'BBMODSeedSession: {session_id}') + row('index does not exist', 'error'),
                    encoding='utf-8')
    return snapshot(path, baseline, session_id)


def test_running_game_error_is_copied_immediately_and_metadata_is_frozen(tmp_path):
    path = tmp_path / 'log.html'
    baseline = begin_session([tmp_path])
    metadata = {'progress': {'loop_idx': 100001}, 'elapsed_seconds': 14400}
    content = row('BBMODSeedSession: search-1') + row('script failed', 'error')
    # The game has not shut down; capture is independent of process liveness.
    path.write_text(content, encoding='utf-8')
    captured = snapshot(path, baseline, metadata=metadata)
    assert captured['raw'] == content.encode() and captured['error'] == 'script failed'
    path.write_text(row('next game launch', 'error'), encoding='utf-8')
    metadata['progress']['loop_idx'] = 0
    assert captured['raw'] == content.encode()
    assert captured['metadata']['progress']['loop_idx'] == 100001
    store = ReportStore(tmp_path / 'reports')
    item = store.capture_seed(captured)
    assert (store.folder(item['id']) / 'log.html').read_bytes() == content.encode()
    assert item['source'] == 'seedgen' and item['state'] == 'manual'
    assert '100001' in item['payload']['diagnostic_report']


def test_unchanged_old_log_and_old_rows_in_append_only_log_are_excluded(tmp_path):
    path = tmp_path / 'log.html'
    path.write_text(row('old failure', 'error'), encoding='utf-8')
    baseline = begin_session([tmp_path])
    assert snapshot(path, baseline) is None
    with path.open('a', encoding='utf-8') as stream:
        stream.write(row('ordinary progress'))
    assert snapshot(path, baseline) is None
    with path.open('a', encoding='utf-8') as stream:
        stream.write(row('new failure', 'error'))
    captured = snapshot(path, baseline)
    assert captured['error'] == 'new failure' and captured['partial_log']
    assert b'old failure' not in captured['raw']


def test_stale_unregistered_log_and_foreign_session_are_excluded(tmp_path):
    path = tmp_path / 'log.html'
    baseline = begin_session([tmp_path])
    path.write_text(row('BBMODSeedSession: different-search') + row('foreign failure', 'error'),
                    encoding='utf-8')
    assert snapshot(path, baseline) is None
    captured = snapshot(path, baseline, error='launch failed')
    assert captured['raw'] == b'' and '其他' in captured['log_error']
    path.write_text(row('stale failure', 'error'), encoding='utf-8')
    os.utime(path, (baseline['started'] - 60, baseline['started'] - 60))
    assert snapshot(path, baseline) is None
    unknown = tmp_path / 'unregistered.html'
    unknown.write_text(row('unrelated failure', 'error'), encoding='utf-8')
    assert snapshot(unknown, baseline) is None


def test_other_session_context_is_not_copied_or_reported(tmp_path):
    path = tmp_path / 'log.html'
    baseline = begin_session([tmp_path])
    path.write_text(
        row('BBMODSeedSession: previous') + row('previous failure', 'error')
        + row('BBMODSeedSession: search-1') + row('our failure', 'error')
        + row('BBMODSeedSession: following') + row('following failure', 'error'),
        encoding='utf-8',
    )
    captured = snapshot(path, baseline)
    assert captured['error'] == 'our failure'
    assert b'previous failure' not in captured['raw'] and b'following failure' not in captured['raw']


@pytest.mark.parametrize('owner,accepted', [('search-1', True), ('different-search', False)])
def test_large_log_session_marker_before_retained_tail_is_checked(tmp_path, owner, accepted):
    path = tmp_path / 'log.html'
    baseline = begin_session([tmp_path])
    path.write_text(row(f'BBMODSeedSession: {owner}') + ' ' * (MAX_LOG_BYTES + 100)
                    + row('tail failure', 'error'), encoding='utf-8')
    captured = snapshot(path, baseline)
    assert (captured is not None) == accepted
    if captured:
        assert captured['error'] == 'tail failure' and len(captured['raw']) <= MAX_LOG_BYTES


@pytest.mark.parametrize('encoding,bom', [('utf-16-le', b'\xff\xfe'), ('utf-16-be', b'\xfe\xff')])
def test_utf16_tail_without_bom_remains_readable_and_owned(tmp_path, encoding, bom):
    path = tmp_path / 'log.txt'
    baseline = begin_session([tmp_path])
    content = ('BBMODSeedSession: search-1\n' + ' ' * (MAX_LOG_BYTES // 2 + 100)
               + '\n[error] SQ unicode failure 中文\nCALLSTACK\nfunction seed line 88\n')
    path.write_bytes(bom + content.encode(encoding))
    captured = snapshot(path, baseline)
    assert captured['log_encoding'] == encoding and captured['partial_log']
    assert len(captured['raw']) <= MAX_LOG_BYTES and 'unicode failure 中文' in captured['error']
    item = ReportStore(tmp_path / 'reports').capture_seed(captured)
    assert 'unicode failure 中文' in item['payload']['diagnostic_report']
    assert 'function seed line 88' in item['payload']['diagnostic_report']
    path.write_bytes(bom + content.replace('search-1', 'foreign-search').encode(encoding))
    assert snapshot(path, baseline) is None


def test_utf16_append_excludes_old_error_and_game_version_is_not_redacted(tmp_path):
    path = tmp_path / 'log.txt'
    path.write_text('[error] SQ old failure\n', encoding='utf-16')
    baseline = begin_session([tmp_path])
    with path.open('ab') as stream:
        stream.write('BBMODSeedSession: search-1\n[error] SQ new failure\n'.encode('utf-16-le'))
    captured = snapshot(path, baseline, metadata={'game_version': '1.5.2.3'})
    assert 'new failure' in captured['error'] and 'old failure' not in captured['raw'].decode('utf-16-le')
    item = ReportStore(tmp_path / 'reports').capture_seed(captured)
    assert '游戏版本：1.5.2.3' in item['payload']['diagnostic_report']


@pytest.mark.parametrize('message,level,tag', [
    ('script failed', 'error', 'SQ'), ('native failure', 'critical', 'CORE'),
    ('script index failed', 'error', 'Script Error'),
    ('BBMODSeedStart: error Cannot launch scenario', 'info', 'SQ'),
])
def test_normal_shutdown_after_search_error_does_not_hide_it(tmp_path, message, level, tag):
    path = tmp_path / 'log.html'
    baseline = begin_session([tmp_path])
    path.write_text(row(message, level, tag) + row('Shutting down engine core.'), encoding='utf-8')
    captured = snapshot(path, baseline)
    assert captured is not None and captured['error'] == message


def test_normal_stop_and_non_script_warning_do_not_report(tmp_path):
    path = tmp_path / 'log.html'
    baseline = begin_session([tmp_path])
    assert snapshot(path, baseline) is None
    path.write_text(row('BBMODSeedProgress: 3000(2) brothers')
                    + row('optional image unavailable', 'error', 'GFX')
                    + row('Shutting down engine core.'), encoding='utf-8')
    assert snapshot(path, baseline) is None


def test_plain_text_critical_chance_is_not_a_script_error(tmp_path):
    path = tmp_path / 'log.txt'
    baseline = begin_session([tmp_path])
    path.write_text('BBMODSeedSession: search-1\ncritical chance increased\n', encoding='utf-8')
    assert snapshot(path, baseline) is None


@pytest.mark.parametrize('line,is_error', [
    ('AN ERROR HAS OCCURRED [missing index]', True),
    ('[error] SQ missing index', True),
    ('critical chance increased', False),
])
def test_live_txt_parser_and_snapshot_agree_on_explicit_errors(tmp_path, line, is_error):
    parser = SeedLogParser(session_id='search-1')
    parser.feed([LogRow('info', '', 'TXT', 'BBMODSeedSession: search-1'),
                 LogRow('info', '', 'TXT', line)])
    assert bool(parser.script_error) == is_error
    path = tmp_path / 'log.txt'
    baseline = begin_session([tmp_path])
    path.write_text('BBMODSeedSession: search-1\n' + line + '\n', encoding='utf-8')
    assert (snapshot(path, baseline) is not None) == is_error


def test_explicit_error_without_log_still_produces_reviewable_report(tmp_path):
    captured = snapshot(tmp_path / 'log.html', begin_session([tmp_path]), error='failed to start')
    assert captured['raw'] == b'' and captured['log_error']
    item = ReportStore(tmp_path / 'reports').capture_seed(captured, automatic=True)
    assert item['automatic'] and item['state'] == 'pending'
    assert 'failed to start' in item['payload']['diagnostic_report']
    assert '无法读取' in item['payload']['diagnostic_report']


def test_txt_baseline_and_active_path_preference(tmp_path):
    html = tmp_path / 'log.html'
    txt = tmp_path / 'log.txt'
    txt.write_text('[error] SQ old text failure\n', encoding='utf-8')
    baseline = begin_session([tmp_path])
    assert str(txt) in baseline['logs']
    html.write_text(row('fallback failure', 'error'), encoding='utf-8')
    with txt.open('a', encoding='utf-8') as stream:
        stream.write('BBMODSeedSession: search-1\n[error] SQ active failure\n')
    captured = snapshot(txt, baseline, paths=[txt, html])
    assert 'active failure' in captured['error'] and b'old text failure' not in captured['raw']
    store = ReportStore(tmp_path / 'reports')
    item = store.capture_seed(captured)
    assert (store.folder(item['id']) / 'log.txt').read_bytes() == captured['raw']
    store.delete(item['id'])
    assert not store.records()


def test_html_stack_trace_preserved_and_upload_payload_redacted(tmp_path):
    path = tmp_path / 'log.html'
    baseline = begin_session([tmp_path])
    path.write_text(
        row('the index failed', 'error')
        + '<div class="stacktrace-container"><div>CALLSTACK</div>'
        + '<div>function generateBrother seed_generator/function_generate_brother.nut:1054</div>'
        + '<div>token="log-secret" alice@example.test 192.168.0.8</div>'
        + r'<div>C:\Users\Alice\game\private.nut</div></div>', encoding='utf-8')
    captured = snapshot(path, baseline, metadata={
        'mode': 'brothers', 'loop_idx': 100001, 'elapsed_seconds': 14400,
        'api_key': 'metadata-secret', 'mods': [{'name': 'original session mod'}],
        'path': r'C:\Users\Alice\game',
    })
    item = ReportStore(tmp_path / 'reports').capture_seed(captured)
    uploaded = json.dumps(item['payload'], ensure_ascii=False)
    assert 'CALLSTACK' in uploaded and 'function_generate_brother.nut:1054' in uploaded
    assert 'original session mod' in uploaded and '100001' in uploaded and '14400' in uploaded
    for secret in ('log-secret', 'metadata-secret', 'Alice', 'alice@example.test', '192.168.0.8'):
        assert secret not in uploaded
    assert item['metadata']['api_key'] == '[已隐藏]'
    assert b'log-secret' in captured['raw']  # Original stays in the local snapshot only.


def test_large_snapshot_and_diagnostic_are_bounded(tmp_path):
    path = tmp_path / 'log.html'
    baseline = begin_session([tmp_path])
    path.write_text('x' * (MAX_LOG_BYTES + 4096) + row('new failure', 'error')
                    + '<div class="stacktrace-container">' + 'stack frame\n' * 20000 + '</div>',
                    encoding='utf-8')
    captured = snapshot(path, baseline, metadata={'config': 'a' * 100000})
    assert captured['partial_log'] and len(captured['raw']) <= MAX_LOG_BYTES
    store = ReportStore(tmp_path / 'reports')
    item = store.capture_seed(captured)
    assert (store.folder(item['id']) / 'log.html').stat().st_size <= MAX_LOG_BYTES
    assert len(item['payload']['diagnostic_report']) <= MAX_REPORT_CHARS
    assert 'new failure' in item['payload']['diagnostic_report']


def test_progress_and_startup_precede_a_configuration_that_exceeds_excerpt_budget(tmp_path):
    captured = fresh_failure(tmp_path)
    captured['metadata'] = {
        'config': {f'option-{index}': 'x' * 1000 for index in range(30)},
        'progress': {'loop_idx': 123456, 'hits': 19}, 'elapsed_seconds': 14700,
        'startup': {'stage': 'error', 'detail': 'failed scenario'},
    }
    item = ReportStore(tmp_path / 'reports').capture_seed(captured)
    report = item['payload']['diagnostic_report']
    for value in ('搜索轮次：123456', '命中数量：19', '运行时长：14700 秒', 'failed scenario'):
        assert value in report and report.index(value) < report.index('option-0')


def test_session_identity_deduplicates_before_capacity_and_keeps_first_snapshot(tmp_path, monkeypatch):
    monkeypatch.setattr('core.crash_reports.MAX_RECORDS', 1)
    captured = fresh_failure(tmp_path)
    store = ReportStore(tmp_path / 'reports')
    first = store.capture_seed(captured)
    captured['raw'] = b'overwritten later log'
    captured['error'] = 'later error'
    assert store.capture_seed(captured, automatic=True) == first
    assert len(store.records()) == 1
    assert (store.folder(first['id']) / 'log.html').read_bytes() != captured['raw']
    assert ReportStore(store.root).capture_seed(captured) == first


def test_capacity_preserves_pending_reports_and_reclaims_sent_records(tmp_path, monkeypatch):
    monkeypatch.setattr('core.crash_reports.MAX_RECORDS', 2)
    store = ReportStore(tmp_path / 'reports')
    captured = fresh_failure(tmp_path)
    first = store.capture_seed(captured)
    second = store.capture_seed({**captured, 'session_id': 'search-2'})
    with pytest.raises(OSError, match='已保留'):
        store.capture_seed({**captured, 'session_id': 'search-3'})
    first['state'] = 'sent'
    store.save(first)
    store.capture_seed({**captured, 'session_id': 'search-3'})
    assert len(store.records()) == 2 and store.get(second['id'])['state'] == 'manual'
    assert not store.folder(first['id']).exists()

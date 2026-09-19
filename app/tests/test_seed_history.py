from dataclasses import replace
from unittest.mock import patch
from urllib.error import URLError
import pytest

from core.seedgen.library import SeedLibrary
from core.seedgen.log_watcher import SeedResult
from core.seedgen.protocol import seed_key, share_payload
from core.seedgen.sharing import upload_seed, ShareReceipt, UploadError
from test_seed_live_ui import app, page, fake_session, start


def record(code='AbCdEfGhIj', loop=123):
    return SeedResult(code, loop, origin='scenario.militia', done=True, game_version='1.5.2.3',
        lines=['CharInfo: 0 Melee:0.8 MeleeSkill:60(95)3'])


def test_history_survives_second_search_stop_and_restart(page, tmp_path):
    first = record(loop=999999)
    page._accept_results([first])
    session = fake_session()
    start(page, session)
    page._poll()
    assert len(page.results) == page.table.rowCount() == 1
    assert '999999' not in page.progress_label.text()
    second = record('ABCDEFGHIJ', 8)
    session.results.append(second)
    session.poll = lambda: ([second], [])
    page._poll()
    page.stop()
    assert len(page.results) == page.table.rowCount() == 2
    assert '命中 1 条' in page.progress_label.text()
    from ui.seedgen_page import SeedGenPage
    reopened = SeedGenPage(page.ctx)
    assert [r.seed for r in reopened.results] == [first.seed, second.seed]
    assert reopened.table.rowCount() == 2
    reopened.close()


def test_duplicate_keeps_complete_data_and_upgrades_partial(tmp_path):
    path = tmp_path / 'seeds.sqlite3'
    library = SeedLibrary(path)
    first = record()
    library.save(replace(first, done=False, lines=[]))
    library.save(first)
    library.mark_shared(first, 'https://bbmod.site/seeds/example/')
    library.save(replace(first, loop_idx=90000, done=False, lines=[]))
    assert SeedLibrary(path).all() == [first]
    assert library.shared_url(first).endswith('/example/')
    library.save(replace(first, combat_difficulty=2))
    assert len(library.all()) == 2
    assert seed_key(first) != seed_key(replace(first, seed=first.seed.swapcase()))


def test_failed_save_keeps_visible_record_for_export(page):
    with patch.object(page.library, 'save', side_effect=OSError('disk full')):
        page._accept_results([record()])
    assert page.table.rowCount() == 1 and page.export_btn.isEnabled()
    assert '保存失败' in page.library_label.text()


def test_no_automatic_upload_and_explicit_share_uses_selected_record(page, app):
    first, second = record(), record('ABCDEFGHIJ')
    with patch('ui.seedgen_page.publish_seed', return_value=ShareReceipt('https://bbmod.site/seeds/123/', True)) as upload:
        page._accept_results([first, second])
        upload.assert_not_called()
        page.table.selectRow(1)
        page.publish_btn.click()
        assert page._share_worker.wait(5000)
        app.processEvents()
        upload.assert_called_once_with(second, '')
        assert app.clipboard().text() == 'https://bbmod.site/seeds/123/'
        assert page.library.shared_url(second).endswith('/123/')
    assert len(SeedLibrary(page.library.path).all()) == 2


def test_upload_network_failure_does_not_change_local_record(tmp_path):
    library = SeedLibrary(tmp_path / 'seeds.sqlite3')
    seed = record(); library.save(seed)
    with patch('core.seedgen.sharing.build_opener') as opener:
        opener.return_value.open.side_effect = URLError('offline')
        with pytest.raises(UploadError, match='连接分享网站失败'):
            upload_seed(seed)
    assert SeedLibrary(library.path).all() == [seed]
    with pytest.raises(ValueError, match='完整'):
        share_payload(replace(seed, done=False))
    with pytest.raises(ValueError, match='HTTPS'):
        upload_seed(seed, origin='http://example.com')


def test_legacy_library_migration_trash_restore_and_reimport(tmp_path):
    import sqlite3
    import json
    from dataclasses import asdict
    path = tmp_path / 'seeds.sqlite3'
    first = record()
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE seeds (identity TEXT PRIMARY KEY, record TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP, share_url TEXT DEFAULT '')")
        db.execute('INSERT INTO seeds(identity, record, share_url) VALUES (?,?,?)',
                   (seed_key(first), json.dumps(asdict(first)), 'https://bbmod.site/seeds/kept/'))
    library = SeedLibrary(path)
    second = record('ABCDEFGHIJ'); library.save(second)
    assert library.delete([seed_key(first), seed_key(first), 'missing']) == 1
    assert library.all() == [second]
    library.save(replace(first, lines=first.lines + ['SettlementInfo: Port:8']))
    reopened = SeedLibrary(path)
    assert reopened.is_deleted(first) and reopened.all() == [second]
    assert reopened.all(deleted=True)[0].lines[-1] == 'SettlementInfo: Port:8'
    assert reopened.shared_url(first).endswith('/kept/')
    assert reopened.restore([seed_key(first)]) == 1
    assert len(reopened.all()) == 2 and reopened.all(deleted=True) == []


def test_filtered_bulk_delete_restore_and_reopen(page, app):
    from PySide6.QtCore import QItemSelectionModel
    from ui.seedgen_page import SeedGenPage
    seeds = [record('AAAAAAAaaa'), record('BBBBBBBbbb'), record('AAAAAAAbbb')]
    page._accept_results(seeds)
    page.sections.setCurrentIndex(1)
    page.library_search.setText('AAAA')
    page.table.selectAll()
    # Hidden selected rows must never be deleted by a filtered bulk operation.
    page.delete_selected()
    assert page.results == [seeds[1]]
    page._accept_results([seeds[0]])
    assert page.results == [seeds[1]]
    page.library_search.clear()
    page.library_view.setCurrentIndex(1)
    assert page.table.rowCount() == 2
    page.table.selectAll(); page.restore_selected()
    assert len(page.results) == 3 and page.table.rowCount() == 0
    page.library_view.setCurrentIndex(0)
    page.table.selectRow(2)
    page.table.selectionModel().select(page.table.model().index(0, 0), QItemSelectionModel.Select | QItemSelectionModel.Rows)
    selected = set(page._selected_keys())
    page._accept_results([record('CCCCCCCccc')])
    assert set(page._selected_keys()) == selected
    reopened = SeedGenPage(page.ctx)
    assert len(reopened.results) == 4
    reopened.close()


def test_delete_is_blocked_during_expedition(page):
    page._accept_results([record()])
    page.orch = object()
    page.delete_selected()
    assert len(page.library.all()) == 1
    page.orch = None

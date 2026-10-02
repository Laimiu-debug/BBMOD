"""Large local histories remain browsable without allocating every row in Qt."""
from dataclasses import replace
from unittest.mock import patch

from PySide6.QtCore import QItemSelectionModel, Qt
from PySide6.QtWidgets import QFileDialog, QMessageBox

from core.seedgen.protocol import seed_key
from core.seedgen.presentation import note_key
from test_seed_history import record
from test_seed_live_ui import app, page
from ui.seedgen_page import LIBRARY_PAGE_SIZE, SeedGenPage


def records(count):
    return [record(f'{index:010}', index) for index in range(count)]


def test_large_history_is_saved_in_full_and_browsable_on_all_pages(page, app):
    seeds = records(LIBRARY_PAGE_SIZE * 2 + 7)
    assert page._accept_results(seeds) == len(seeds)
    assert page.library.all() == seeds
    assert len(page.results) == len(seeds)
    assert page.table.rowCount() == LIBRARY_PAGE_SIZE
    assert f'全库匹配 {len(seeds)} 条' in page.library_page_label.text()
    page.next_page_btn.click()
    assert page.table.item(0, 0).text() == seeds[LIBRARY_PAGE_SIZE].seed
    page.latest_page_btn.click()
    assert page.table.rowCount() == 7
    assert page.table.item(6, 0).text() == seeds[-1].seed
    page.table.selectAll()
    page.copy_seed_codes()
    assert app.clipboard().text() == '\n'.join(result.seed for result in seeds[-7:])
    page.previous_page_btn.click()
    assert page.table.rowCount() == LIBRARY_PAGE_SIZE
    assert page.table.item(0, 0).text() == seeds[LIBRARY_PAGE_SIZE].seed
    reopened = SeedGenPage(page.ctx)
    try:
        assert reopened.results == seeds
        assert reopened.table.rowCount() == LIBRARY_PAGE_SIZE
    finally:
        reopened.close()


def test_live_results_preserve_current_items_multiselection_and_batch_save(page):
    seeds = records(LIBRARY_PAGE_SIZE + 2)
    page._accept_results(seeds)
    page.table.selectRow(3)
    page.table.selectionModel().select(page.table.model().index(7, 0),
                                      QItemSelectionModel.Select | QItemSelectionModel.Rows)
    selection = page._selected_keys()
    untouched = page.table.item(3, 0)
    more = [record('NEWRESULT0'), record('NEWRESULT1')]
    with patch.object(page.library, 'save_many', wraps=page.library.save_many) as save, \
         patch.object(page.library, 'save', side_effect=AssertionError('per-record save')), \
         patch.object(page.library, 'is_deleted', side_effect=AssertionError('per-record query')), \
         patch.object(page, '_write_result', wraps=page._write_result) as render:
        assert page._accept_results(more) == 2
        save.assert_called_once_with(more)
        assert render.call_count == 0
    assert page.table.item(3, 0) is untouched
    assert page._selected_keys() == selection
    assert len(page.library.all()) == len(seeds) + 2
    assert f'全库匹配 {len(seeds) + 2} 条' in page.library_page_label.text()


def test_search_finds_history_outside_page_and_tracks_partial_upgrades(page):
    seeds = records(LIBRARY_PAGE_SIZE + 5)
    page._accept_results(seeds)
    target = seeds[-1]
    page.library_search.setText(target.seed)
    assert page.table.rowCount() == 1
    assert page._selected_result() == target
    page.library_search.setText('港口')
    assert page.table.rowCount() == 0
    # Same identity becomes richer and starts matching; older history ordering is retained.
    partial = replace(record('PORTFOUND0'), done=False, lines=[])
    complete = replace(partial, done=True, lines=['SettlementInfo: Port:8'])
    page._accept_results([partial])
    assert page.table.rowCount() == 0
    page._accept_results([complete])
    assert page.table.rowCount() == 1
    assert page.table.item(0, 0).data(Qt.UserRole) == complete
    page.library_search.setText('000')
    page._accept_results([replace(seeds[0], lines=seeds[0].lines + ['SettlementInfo: Port:9'])])
    assert page.table.item(0, 0).text() == seeds[0].seed
    assert page.table.rowCount() == LIBRARY_PAGE_SIZE


def test_search_and_trash_work_across_pages_without_restoring_reimported_records(page):
    seeds = records(LIBRARY_PAGE_SIZE + 3)
    page._accept_results(seeds)
    page.latest_page_btn.click()
    page.table.selectAll()
    page.delete_selected()
    assert len(page.library.all(deleted=True)) == 3
    assert len(page.results) == LIBRARY_PAGE_SIZE
    page.library_view.setCurrentIndex(1)
    assert page.table.rowCount() == 3
    richer = replace(seeds[-1], lines=seeds[-1].lines + ['SettlementInfo: Port:8'])
    assert page._accept_results([richer]) == 0
    assert page.table.item(2, 0).data(Qt.UserRole) == richer
    page.library_search.setText(seeds[-1].seed)
    assert page.table.rowCount() == 1
    page.restore_selected()
    assert page.table.rowCount() == 0
    page.library_view.setCurrentIndex(0)
    assert page.table.rowCount() == 1
    assert page._selected_result() == richer
    assert seed_key(richer) not in {seed_key(result) for result in page.library.all(deleted=True)}


def test_selected_partial_row_is_updated_without_replacing_other_items(page):
    first = replace(record('PARTIAL000'), done=False, lines=[])
    second = record('COMPLETE00')
    page._accept_results([first, second])
    untouched = page.table.item(1, 0)
    completed = replace(first, done=True, lines=['SettlementInfo: Port:8'])
    page._accept_results([completed])
    assert page._selected_result() == completed
    assert page.table.item(1, 0) is untouched
    assert '记录未完整' not in page.table.item(0, 1).text()
    assert page.publish_btn.isEnabled()


def test_export_and_publish_all_include_history_outside_current_page(page, tmp_path):
    seeds = records(LIBRARY_PAGE_SIZE + 3)
    page._accept_results(seeds)
    page.notes[note_key(seeds[-1])] = '远处的路线介绍'
    page.library_search.setText(seeds[0].seed)
    with patch.object(page, '_publish_items') as publish:
        page.publish_all()
        items = publish.call_args.args[0]
        assert [result for result, _ in items] == seeds
        assert items[-1][1] == '远处的路线介绍'
    target = tmp_path / 'all-seeds.txt'
    with patch.object(QFileDialog, 'getSaveFileName', return_value=(str(target), '')), \
         patch.object(QMessageBox, 'information'):
        page.export_txt()
    text = target.read_text(encoding='utf-8-sig')
    assert seeds[0].seed in text and seeds[-1].seed in text
    assert '远处的路线介绍' in text


def test_search_inserts_upgraded_old_record_in_history_order_and_removes_stale_match(page):
    first = replace(record('FIRST00000'), done=False, lines=[])
    second = replace(record('SECOND0000'), lines=['SettlementInfo: Port:8'])
    page._accept_results([first, second])
    page.library_search.setText('8座港口')
    assert page._selected_result() == second
    upgraded = replace(first, done=True, lines=['SettlementInfo: Port:8'])
    page._accept_results([upgraded])
    assert [result.seed for result in page._view_results] == [first.seed, second.seed]
    assert page._selected_result() == second
    replaced = replace(second, lines=['SettlementInfo: Port:9', 'SettlementInfo: City:3'])
    page._accept_results([replaced])
    assert page.table.rowCount() == 1
    assert page._selected_result() == upgraded

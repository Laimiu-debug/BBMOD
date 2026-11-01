"""Check seed workspaces in the real desktop shell with an isolated profile."""
from contextlib import ExitStack
import gzip
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QAbstractSpinBox, QApplication, QComboBox, QLabel, QLineEdit, QPushButton
from core.seedgen.log_watcher import SeedResult
from core.settings import Settings
from core.worldmap.model import WorldMap
from ui.main_window import MainWindow
from ui.theme import apply_theme


def sample_map():
    fixtures = ROOT / 'tests/fixtures/worldmap'
    for path in fixtures.glob('map-*.json.gz'):
        value = json.loads(gzip.decompress(path.read_bytes()))['map']
        if value['seed'] == '46U2HMOORH':
            break
    else:
        raise AssertionError('Missing reference map')
    for path in fixtures.glob('camp-*.json.gz'):
        campaign = json.loads(gzip.decompress(path.read_bytes()))['campaign']
        if campaign['seed'] == value['seed']:
            value['campaign'] = campaign
            break
    return WorldMap.from_dict(value)


def main():
    output = ROOT / 'build/review/seed-expedition-ui'
    output.mkdir(parents=True, exist_ok=True)
    report = []
    with tempfile.TemporaryDirectory(prefix='bbmod-seed-layout-') as temporary, ExitStack() as guard:
        os.environ['APPDATA'] = temporary
        for name in ('core.game.launch_executable', 'core.game.kill_game'):
            guard.enter_context(patch(name, side_effect=AssertionError('Game actions forbidden in UI preview')))
        guard.enter_context(patch('ui.app_context.game_mod.locate_game', return_value=None))
        guard.enter_context(patch('ui.app_context._collection_candidates', return_value=[]))
        app = QApplication([])
        apply_theme(app, {'font_size': 12})
        settings = Settings()
        settings.set('reduce_motion', True)
        window = MainWindow(auto_updates=False)
        window.show()
        window.select_page(3)
        window.ctx.game_session.shutdown()
        page = window.seedgen
        page.map_preview.activate = lambda: None
        page.map_preview._accept_map(SimpleNamespace(world=sample_map(), cached=True, elapsed=0))
        sample = SeedResult('DEMOSEED01', 123, origin='scenario.militia', done=True, lines=[
            'CharInfo: 0 Melee:0.9 Hitpoints:60(95)0 Bravery:40(55)0 Stamina:80(115)3 '
            'MeleeSkill:60(95)3 RangedSkill:40(70)0 MeleeDefense:5(35)3 '
            'RangedDefense:0(30)0 Initiative:100(140)0', 'Trait: trait.determined'])
        page._accept_results([sample])
        page.note_edit.setText('界面演示数据 · 不代表可复现的真实种子')
        page._note_changed(page.note_edit.text())
        page._accept_results([SeedResult(f'DEMO{i:06}', i, origin=sample.origin, done=True,
                                       lines=sample.lines) for i in range(1, 24)])
        page.format_combo.setCurrentIndex(page.format_combo.findData('detail'))
        page.map_preview.towns.selectRow(0)

        def capture(name, controls, *, screenshot=False, allow_scroll=False):
            QTest.qWait(60)
            scroll = window.page_scrolls[3]
            scroll.verticalScrollBar().setValue(0)
            state = {'size': window.size().toTuple(), 'view': name, 'font_size': app.font().pointSize(),
                     'allow_scroll': allow_scroll,
                     'scroll': [scroll.horizontalScrollBar().maximum(), scroll.verticalScrollBar().maximum()],
                     'viewport': scroll.viewport().size().toTuple(), 'controls': []}
            for widget in controls:
                if allow_scroll:
                    for _ in range(2):
                        bottom = widget.mapTo(page, widget.rect().bottomRight())
                        top = widget.mapTo(page, widget.rect().topLeft())
                        scroll.ensureVisible(bottom.x(), bottom.y(), 3, 3)
                        scroll.ensureVisible(top.x(), top.y(), 3, 3)
                        QTest.qWait(30)
                minimum_height = widget.fontMetrics().height()
                if isinstance(widget, (QPushButton, QComboBox, QAbstractSpinBox, QLineEdit)):
                    minimum_height += 4
                elif isinstance(widget, QLabel) and widget.wordWrap():
                    minimum_height = max(minimum_height, widget.heightForWidth(widget.width()))
                state['controls'].append({
                    'name': widget.accessibleName() or widget.objectName() or type(widget).__name__,
                    'visible': widget.isVisible(),
                    'in_view': scroll.viewport().rect().contains(
                        widget.mapTo(scroll.viewport(), widget.rect().bottomRight())),
                    'height': widget.height(), 'font_height': widget.fontMetrics().height(),
                    'minimum_text_height': minimum_height})
            if screenshot:
                filename = f'{name}-{window.width()}.png'
                window.grab().save(str(output / filename))
                state['screenshot'] = filename
            report.append(state)

        for width, height in ((1360, 880), (1080, 720)):
            window.resize(width, height)
            page.sections.setCurrentIndex(0)
            for mode, name in (('只找开局兄弟（快）', 'expedition'), ('只找地图', 'map-filters'),
                               ('只找红装', 'weapon-filters')):
                page.mode_combo.setCurrentText(mode)
                controls = [page.start_btn, page.mode_combo, page.origin_combo, page.engine_combo]
                if name == 'expedition':
                    controls += [page.bro_count, *page.attr_spins.values(), page.attr_hint]
                capture(name, controls, screenshot=True)
            page.weapon_filter.weapons_enabled.setChecked(True)
            capture('weapon-rows', [page.weapon_filter.add, page.weapon_filter.rows[0].weapon], screenshot=True)
            page.sections.setCurrentIndex(1)
            page.preview_btn.setChecked(False)
            capture('library', [page.library_search, page.table, page.next_page_btn, page.selection_hint], screenshot=True)
            page.preview_btn.setChecked(True)
            page.archive_panel.setCurrentIndex(0)
            capture('library-detail', [page.table, page.detail_label, page.note_edit, page.copy_btn], screenshot=True)
            page.archive_panel.setCurrentIndex(1)
            capture('library-sharing', [page.publish_btn, page.publish_all_btn, page.cancel_share_btn], screenshot=True)
            page.sections.setCurrentIndex(2)
            for index, name in enumerate(('map', 'routes', 'loot')):
                page.map_preview.tabs.setCurrentIndex(index)
                if index == 1:
                    page.map_preview.offers.selectRow(0)
                elif index == 2:
                    page.map_preview.loot_table.selectRow(0)
                capture(name, [page.map_preview.canvas, page.map_preview.tabs,
                    page.map_preview.origin_combo, page.map_preview.combat_combo,
                    page.map_preview.economic_combo, page.map_preview.budget_combo], screenshot=True)
                if index == 1:
                    page.map_preview.route_details.setCurrentIndex(1)
                    capture('route-income', [page.map_preview.summary, page.map_preview.stop_list], screenshot=True)
                    page.map_preview.route_details.setCurrentIndex(2)
                    capture('route-options', [page.map_preview.quantity, page.map_preview.daily_cost], screenshot=True)
                    page.map_preview.route_details.setCurrentIndex(0)
                elif index == 2:
                    page.map_preview.loot_pages.setCurrentIndex(1)
                    capture('loot-detail', [page.map_preview.loot_detail, page.map_preview.loot_status], screenshot=True)
                    page.map_preview.loot_pages.setCurrentIndex(0)

        for font_size in (14, 18):
            apply_theme(app, {'font_size': font_size})
            window._fit_typography()
            for width, height in ((1360, 880), (1080, 720)):
                window.resize(width, height)
                page.sections.setCurrentIndex(0)
                page.mode_combo.setCurrentText('只找开局兄弟（快）')
                capture('large-font-filters', [page.start_btn, page.mode_combo, page.bro_count,
                        *page.attr_spins.values(), page.attr_hint], allow_scroll=True)
                page.sections.setCurrentIndex(1)
                page.preview_btn.setChecked(True)
                page.archive_panel.setCurrentIndex(0)
                capture('large-font-archive', [page.detail_label, page.note_edit, page.copy_btn], allow_scroll=True)
                page.sections.setCurrentIndex(2)
                page.map_preview.tabs.setCurrentIndex(1)
                page.map_preview.route_details.setCurrentIndex(2)
                capture('large-font-map', [page.map_preview.quantity, page.map_preview.daily_cost,
                    page.map_preview.origin_combo, page.map_preview.combat_combo,
                    page.map_preview.economic_combo, page.map_preview.budget_combo], allow_scroll=True)

        page.map_preview.shutdown()
        page.shutdown_polling()
        page.shutdown_sharing()
        window.close()
        app.processEvents()
    result = {'game_started': False, 'isolated_profile': True, 'fixture_data_used': True, 'layouts': report}
    (output / 'validation.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    issues = [state for state in report if (any(state['scroll']) and not state['allow_scroll']) or any(
        not c['visible'] or not c['in_view'] or c['height'] < c['minimum_text_height']
        for c in state['controls'])]
    print(json.dumps({'layouts': len(report), 'issues': issues, 'report': str(output / 'validation.json')}, ensure_ascii=False))
    return bool(issues)


if __name__ == '__main__':
    raise SystemExit(main())

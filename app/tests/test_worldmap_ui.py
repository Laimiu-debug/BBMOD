import gzip
import json
from pathlib import Path
import time
from types import SimpleNamespace

import pytest
from PySide6.QtCore import Qt, QPoint
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from core.worldmap.engine import SolveCancelled
from core.worldmap.model import WorldMap
from ui.worldmap_page import WorldMapPage


class Settings:
    def __init__(self): self.values = {}
    def get(self, key, default=None): return self.values.get(key, default)
    def set(self, key, value): self.values[key] = value


def wait(app, predicate):
    deadline = time.monotonic()+8
    while not predicate() and time.monotonic() < deadline:
        app.processEvents(); QTest.qWait(10)
    assert predicate()


@pytest.fixture(scope='module')
def app():
    application = QApplication.instance() or QApplication([])
    from ui.theme import apply_theme
    apply_theme(application)
    return application


@pytest.fixture
def page(app):
    files = (Path(__file__).with_name('fixtures')/'worldmap').glob('map-*.json.gz')
    maps = [WorldMap.from_dict(json.loads(gzip.decompress(p.read_bytes()))['map']) for p in files]
    data = next(m for m in maps if m.seed == '46U2HMOORH')
    raw = data.to_dict()
    for path in (Path(__file__).with_name('fixtures')/'worldmap').glob('camp-*.json.gz'):
        c = json.loads(gzip.decompress(path.read_bytes()))['campaign']
        if c['seed'] == data.seed: raw['campaign'] = c
    data = WorldMap.from_dict(raw)
    class Solver:
        def solve(self, seed, **kwargs): return SimpleNamespace(world=data, cached=False, elapsed=2.1)
    page = WorldMapPage(Settings(), solver=Solver()); page.resize(1280, 840); page.show(); page.solve()
    wait(app, lambda: page._job is None and page.world is not None)
    yield page
    page.shutdown(); page.close(); app.processEvents()


def test_map_selection_zoom_and_trade_path(page, app):
    assert page.towns.rowCount() == 19 and page.offers.rowCount() > 0
    before = page.canvas.scale
    page.canvas.zoom(1.5)
    assert page.canvas.scale > before
    p = page.canvas.screen_point(page.world.settlements[2].xy).toPoint()
    QTest.mouseClick(page.canvas, Qt.LeftButton, pos=p)
    assert page.canvas.selected == 2
    page.tabs.setCurrentIndex(1); page.offers.selectRow(0)
    wait(app, lambda: page._route_job is None)
    assert page.route is not None and len(page.stops) == 2 and '毛利' in page.summary.text()
    page.undo(); wait(app, lambda: page._route_job is None)
    assert len(page.stops) == 1 and page.canvas.route is None


def test_refresh_preserves_stops_and_bad_seed_keeps_old_map(page, app):
    page.stops = [0, 1, 2]; page.preview_route(); wait(app, lambda: page._route_job is None)
    old = page.world
    page.solve(); wait(app, lambda: page._job is None and page._route_job is None)
    assert page.stops == [0, 1, 2]
    class Broken:
        def solve(self, *args, **kwargs): raise ValueError('种子格式有误')
    page.solver = Broken(); page.solve(); wait(app, lambda: page._job is None)
    assert page.world is old and '种子格式有误' in page.status.text()


def test_inflight_routes_do_not_reappear_after_clear_and_export(page, app, tmp_path, monkeypatch):
    page.stops = [0, 1]; page.preview_route(); page.clear_route()
    wait(app, lambda: page._route_job is None)
    assert page.route is None and page.canvas.route is None
    page.stops = [0, 1]; page.preview_route(); wait(app, lambda: page._route_job is None)
    target = tmp_path/'route.json'
    monkeypatch.setattr('ui.worldmap_page.QFileDialog.getSaveFileName', lambda *a: (str(target), ''))
    page.export_route(); exported = json.loads(target.read_text('utf-8'))
    assert exported['seed'] == page.world.seed and exported['tiles']


def test_readable_render_at_desktop_and_small_width(page, app):
    output = Path(__file__).resolve().parents[1]/'build/offline-map/qa'
    output.mkdir(parents=True, exist_ok=True)
    page.tabs.setCurrentIndex(1); page.offers.selectRow(0); wait(app, lambda: page._route_job is None)
    for width, height in [(1280, 840), (840, 720)]:
        page.resize(width, height); app.processEvents(); page.canvas.fit(); app.processEvents()
        assert page.layout().minimumSize().width() <= width
        assert page.grab().save(str(output/f'map-{width}.png'))


def test_cancel_keeps_the_current_map(page, app):
    old = page.world
    class Slow:
        def solve(self, *args, cancelled, **kwargs):
            cancelled.wait(5)
            raise SolveCancelled()
    page.solver = Slow(); page.solve(); page.cancel()
    wait(app, lambda: page._job is None)
    assert page.world is old and '取消' in page.status.text()


def test_campaign_controls_forward_settings_and_recompute_the_same_seed(page, app):
    from unittest.mock import Mock
    seen = Mock(wraps=page.solver.solve)
    page.solver = SimpleNamespace(solve=seen)
    page.open_seed(page.world.seed, origin='scenario.deserters', combat=0, economic=1, budget=2)
    wait(app, lambda: page._job is None)
    assert page.origin_combo.currentData() == 'scenario.deserters'
    assert page.combat_combo.currentData() == 0 and page.economic_combo.currentData() == 1
    _, kwargs = seen.call_args
    assert {key: kwargs[key] for key in ('origin', 'combat', 'economic', 'budget')} == dict(
        origin='scenario.deserters', combat=0, economic=1, budget=2)
    assert page.settings.get('worldmap_preview')['origin'] == 'scenario.deserters'


def test_custom_or_incomplete_record_never_silently_uses_militia_camps(page, app):
    from unittest.mock import Mock
    seen = Mock(side_effect=AssertionError('must not solve another configuration'))
    page.solver = SimpleNamespace(solve=seen)
    page.open_seed('ABCDEFGHIJ', origin='scenario.afeix_expedition', combat=2, economic=2, budget=2)
    assert '自制起源' in page.status.text() and not seen.called
    page.open_seed('ABCDEFGHIJ', origin='scenario.militia')
    assert '缺少完整' in page.status.text() and not seen.called
    page.open_seed('ABCDEFGHIJ', origin='scenario.militia', combat=2, economic=2, budget=2, dlc_mask=0)
    assert 'DLC 或 MOD' in page.status.text() and not seen.called


def test_map_font_is_larger_adjustable_and_persistent(page, app):
    assert page.canvas.label_size == page.label_size.value() == 18
    page.label_size.setValue(26)
    assert page.canvas.label_size == 26 and page.settings.get('worldmap_label_size') == 26
    reopened = WorldMapPage(page.settings, solver=page.solver)
    assert reopened.canvas.label_size == reopened.label_size.value() == 26
    reopened.shutdown(); reopened.close()


def test_weapon_popup_shows_full_names_and_can_reach_last_option(app):
    from ui.readable_combo import ReadableComboBox
    from core.seedgen.weapons import WEAPON_CHOICES
    combo = ReadableComboBox(); combo.setFixedWidth(120)
    combo.addItems(list(WEAPON_CHOICES.values())); combo.show(); combo.showPopup(); app.processEvents()
    longest = max(combo.fontMetrics().horizontalAdvance(combo.itemText(i)) for i in range(combo.count()))
    assert combo.view().minimumWidth() >= longest+40
    assert combo.maxVisibleItems() == 24
    QTest.keyClick(combo.view(), Qt.Key_End); QTest.keyClick(combo.view(), Qt.Key_Return); app.processEvents()
    assert combo.currentIndex() == combo.count()-1
    assert combo.itemData(combo.currentIndex(), Qt.ToolTipRole) == combo.currentText()
    combo.close()


def test_chinese_towns_advice_and_quantity_profit(page, app):
    assert all(page.towns.item(row, 0).text() != '未收录地名' for row in range(page.towns.rowCount()))
    page.select_town(0)
    assert '在此买入' in page.detail.toPlainText() and '在此卖出' in page.detail.toPlainText()
    page.tabs.setCurrentIndex(1); page.offers.selectRow(0)
    wait(app, lambda: page._route_job is None)
    page.quantity.setValue(5); page.daily_cost.setValue(200)
    offer = page._offers[0]
    expected = offer.profit*5-page.route.hours/24*200
    assert f'采购 {offer.buy*5}' in page.summary.text()
    assert f'扣行程开销后 {expected:.0f}' in page.summary.text()
    assert '产地采购' in page.offer_detail.text()


def test_offline_loot_selection_centers_actual_camp_and_filter(page, app):
    assert page.world.campaign and len(page.world.campaign.camps) == 102
    assert page.loot_table.rowCount() == 10
    page.tabs.setCurrentIndex(2); page.loot_table.selectRow(0); app.processEvents()
    camp, item = page._filtered_loot[0]
    assert page.canvas.selected_camp == camp.index
    point = page.canvas.screen_point(camp.xy)
    assert abs(point.x()-page.canvas.width()/2) < 1 and abs(point.y()-page.canvas.height()/2) < 1
    assert f'{camp.xy[0]}, {camp.xy[1]}' in page.loot_detail.toPlainText()
    page.loot_kind.setCurrentIndex(page.loot_kind.findData('weapon'))
    assert page._filtered_loot and all(item.kind == 'weapon' for _, item in page._filtered_loot)
    page.loot_table.selectRow(0)
    assert '实用词条评分' in page.loot_detail.toPlainText() and 'roll 品质' in page.loot_detail.toPlainText()
    page.loot_search.setText('不存在的装备'); assert page.loot_table.rowCount() == 0
    assert page.canvas.selected_camp == -1
    page.select_camp(camp.index); app.processEvents()
    assert page.canvas.selected_camp == camp.index and page.loot_table.currentRow() >= 0
    QTest.mouseClick(page.canvas, Qt.LeftButton, pos=page.canvas.screen_point(camp.xy).toPoint())
    assert page.tabs.currentIndex() == 2


def test_camp_preview_is_cleared_on_switching_seed(page, app):
    page.loot_table.selectRow(0); assert page.canvas.selected_camp >= 0
    path = next((Path(__file__).with_name('fixtures')/'worldmap').glob('map-*.json.gz'))
    other = WorldMap.from_dict(json.loads(gzip.decompress(path.read_bytes()))['map'])
    page._accept_map(SimpleNamespace(world=other, cached=False, elapsed=2.0))
    assert page.canvas.selected_camp == -1 and page.loot_table.rowCount() == 0
    assert '选择红装' in page.loot_detail.toPlainText()


def test_camp_and_town_details_render_at_both_widths(page, app):
    output = Path(__file__).resolve().parents[1]/'build/offline-map/qa'
    for width, height in [(1280, 840), (840, 720)]:
        page.resize(width, height); page.canvas.fit(); app.processEvents()
        for tab, name in [(0, 'towns'), (2, 'loot')]:
            page.tabs.setCurrentIndex(tab)
            if tab == 2:
                page.loot_kind.setCurrentIndex(page.loot_kind.findData('weapon')); page.loot_table.selectRow(0)
            app.processEvents()
            assert page.layout().minimumSize().width() <= width
            assert page.grab().save(str(output/f'{name}-{width}.png'))

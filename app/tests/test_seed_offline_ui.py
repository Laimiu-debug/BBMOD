"""Independent Qt search completes and saves while no game is configured."""
from types import SimpleNamespace
from unittest.mock import patch
import time

import pytest
from PySide6.QtWidgets import QApplication

from core.seedgen.config_emitter import BroCondition, OriginConfig
from core.seedgen.orchestrator import StopLimits
from core.seedgen.protocol import share_payload
from core.settings import Settings
from core.worldmap.engine import Components
from ui.seedgen_page import SeedGenPage


@pytest.fixture(scope='module')
def app():
    return QApplication.instance() or QApplication([])


def test_search_and_library_need_no_game_and_ignore_running_game(app, tmp_path):
    if not Components.locate().binary.is_file():
        pytest.skip('Independent component unavailable')
    settings = Settings.__new__(Settings)
    settings.path, settings.data = tmp_path/'settings.json', {}
    context = SimpleNamespace(game=None, settings=settings,
        data_changed=SimpleNamespace(emit=lambda: None), set_seedgen_active=lambda value: None)
    page = SeedGenPage(context)
    assert page.mode_combo.currentText() == '只找开局兄弟（快）'
    assert '无需游戏目录' in page.engine_hint.text()
    cfg = page._current_config()
    cfg.origins = {cfg.campaign.origin: OriginConfig(conditions=[BroCondition('TeamScore', [-100])])}
    cfg.common.debug_seeds = ['AbCdEfGhIj', 'ABCDEFGHIJ', 'aaaaaaaaaa']
    page._current_config = lambda: cfg
    page._limits = StopLimits(hits=2)
    try:
        with patch('ui.seedgen_page.game_mod.is_game_running', side_effect=AssertionError('game probe')), \
             patch('ui.seedgen_page.SeedGenOrchestrator', side_effect=AssertionError('game session')):
            page.start()
            assert page.stop_btn.text() == '停止搜索'
            started = time.monotonic()
            while page.orch is not None and time.monotonic()-started < 6:
                app.processEvents()
                time.sleep(.01)
        assert page.orch is None
        assert len(page.results) == 2 and page.table.rowCount() == 2
        assert len(page.library.all()) == 2
        assert '独立解算' in page.progress_label.text() and '恢复' not in page.progress_label.text()
        assert page.start_btn.isEnabled() and not page.stop_btn.isEnabled()
        assert not page.timer.isActive() and page._poll_worker is None
        for result in page.results:
            payload = share_payload(result)
            assert payload['record']['seed'] == result.seed
    finally:
        if page.orch is not None:
            page.stop()
        page.close()


def test_game_fallback_is_visible_and_offline_mode_never_launches_it(app, tmp_path):
    settings = Settings.__new__(Settings)
    settings.path, settings.data = tmp_path/'settings.json', {}
    context = SimpleNamespace(game=None, settings=settings,
        data_changed=SimpleNamespace(emit=lambda: None), set_seedgen_active=lambda value: None)
    page = SeedGenPage(context)
    try:
        page.origin_combo.setCurrentIndex(page.origin_combo.findData('scenario.afeix_expedition'))
        page.engine_combo.setCurrentIndex(page.engine_combo.findData('offline'))
        assert '暂需游戏解算' in page.engine_hint.text()
        with patch('ui.seedgen_page.QMessageBox.warning') as warning, \
             patch('ui.seedgen_page.SeedGenOrchestrator') as game:
            page.start()
        warning.assert_called_once()
        game.assert_not_called()
        assert page.orch is None
    finally:
        page.close()


def test_cancel_saves_independent_burst_before_qt_receives_it(app, tmp_path):
    settings = Settings.__new__(Settings)
    settings.path, settings.data = tmp_path/'settings.json', {}
    context = SimpleNamespace(game=None, settings=settings,
        data_changed=SimpleNamespace(emit=lambda: None), set_seedgen_active=lambda value: None)
    page = SeedGenPage(context)
    cfg = page._current_config()
    cfg.origins = {cfg.campaign.origin: OriginConfig(conditions=[BroCondition('TeamScore', [-100])])}
    page._current_config = lambda: cfg
    page._limits = StopLimits()
    try:
        # Let the native pipe fill before the worker's first poll, so an empty
        # startup batch cannot wait for a GUI acknowledgement in this harness.
        with patch.object(page, '_start_polling'):
            page.start()
        search = page.orch
        deadline = time.monotonic() + 4
        while search._queue.qsize() < 10 and time.monotonic() < deadline:
            time.sleep(.005)
        assert search._queue.qsize() >= 10
        page._start_polling()
        # Do not pump Qt: the worker is collecting a burst and its signal may
        # still be queued when Stop is clicked.
        while len(search.results) < 5 and time.monotonic() < deadline:
            time.sleep(.005)
        assert search.results and not page.results
        page.stop()
        assert page.orch is None and page._poll_worker is None
        assert page.library.all() == page.results == search.results
        assert search._process is None and search._temporary is None
        count = len(page.results)
        app.processEvents()
        assert len(page.results) == count
    finally:
        if page.orch is not None:
            page.stop()
        page.close()


def test_combined_campaign_search_saves_configuration_and_opens_matching_map(app, tmp_path):
    from core.seedgen.config_emitter import CampaignConfig, CommonConfig, SeedGenConfig
    settings = Settings.__new__(Settings)
    settings.path, settings.data = tmp_path/'settings.json', {}
    context = SimpleNamespace(game=None, settings=settings,
        data_changed=SimpleNamespace(emit=lambda: None), set_seedgen_active=lambda value: None)
    page = SeedGenPage(context)
    origin = 'scenario.deserters'
    page.origin_combo.setCurrentIndex(page.origin_combo.findData(origin))
    page.mode_combo.setCurrentText('人物 + 地图 + 红装')
    cfg = SeedGenConfig(common=CommonConfig.preset('all'), campaign=CampaignConfig(origin, 0, 1, 2),
        origins={origin: OriginConfig(conditions=[BroCondition('TeamScore', [-100])])},
        map_conditions=[['SettlementNum', 1]], lair_conditions=[['NamedNumber', 0]])
    cfg.common.debug_seeds = ['AbCdEfGhIj', 'ABCDEFGHIJ']
    page._current_config = lambda: cfg
    page._limits = StopLimits(hits=1)
    try:
        with patch('ui.seedgen_page.game_mod.is_game_running', side_effect=AssertionError('game probe')), \
             patch('ui.seedgen_page.SeedGenOrchestrator', side_effect=AssertionError('game session')):
            page.start()
            deadline = time.monotonic()+25
            while page.orch is not None and time.monotonic() < deadline:
                app.processEvents(); time.sleep(.01)
        assert page.orch is None and len(page.results) == 1
        result = page.results[0]
        assert result.brothers and result.named_items and result.done
        assert len(page.library.all()) == 1
        page.table.selectRow(0)
        with patch.object(page.map_preview, 'open_seed') as open_map, patch.object(page.map_preview, 'activate'):
            page._open_selected_map()
        open_map.assert_called_once_with(result.seed, origin=origin, combat=0, economic=1, budget=2,
                                         dlc_mask=342, mods=[])
        assert share_payload(result)['record']['combat_difficulty'] == 0
    finally:
        if page.orch is not None: page.stop()
        page.map_preview.shutdown()
        page.close()

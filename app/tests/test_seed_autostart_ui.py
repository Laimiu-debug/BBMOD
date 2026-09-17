from types import SimpleNamespace
from unittest.mock import patch

import pytest
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QComboBox, QDialog, QDialogButtonBox, QSpinBox

from core.settings import Settings
from core.seedgen.log_watcher import Progress, StartupStatus
from ui.seedgen_page import SeedGenPage


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def context(tmp_path):
    settings = Settings.__new__(Settings)
    settings.path = tmp_path / "settings.json"
    settings.data = {}
    return SimpleNamespace(game=object(), settings=settings,
        data_changed=SimpleNamespace(emit=lambda: None), set_seedgen_active=lambda _: None)


def test_campaign_options_persist_and_reach_every_search_mode(app, context):
    page = SeedGenPage(context)
    page.origin_combo.setCurrentIndex(page.origin_combo.findData("scenario.lone_wolf"))
    def choose_levels():
        dialog = app.activeModalWidget()
        assert isinstance(dialog, QDialog)
        for key, value in (("combat_difficulty", 2), ("economic_difficulty", 0), ("budget_difficulty", 2)):
            combo = dialog.findChild(QComboBox, key)
            combo.setCurrentIndex(combo.findData(value))
        dialog.findChild(QSpinBox, "stop_hits").setValue(3)
        dialog.findChild(QSpinBox, "stop_minutes").setValue(20)
        dialog.findChild(QDialogButtonBox).button(QDialogButtonBox.Ok).click()
    QTimer.singleShot(0, choose_levels)
    page._generation_options()
    reopened = SeedGenPage(context)
    assert "战斗专家" in reopened.progress_label.text() and "经济新手" in reopened.progress_label.text()
    assert reopened._limits.hits == 3 and reopened._limits.minutes == 20
    assert "找到 3 条" in reopened.progress_label.text() and "运行 20 分钟" in reopened.progress_label.text()
    for mode in ("只找地图", "人物 + 地图", "人物 + 红装", "只找开局兄弟（快）"):
        reopened.mode_combo.setCurrentText(mode)
        cfg = reopened._current_config()
        assert cfg.campaign.origin == "scenario.lone_wolf"
        assert (cfg.campaign.combat_difficulty, cfg.campaign.economic_difficulty, cfg.campaign.budget_difficulty) == (2, 0, 2)
    QTimer.singleShot(0, lambda: app.activeModalWidget().reject())
    reopened._generation_options()
    assert reopened._campaign_levels == page._campaign_levels
    page.close()
    reopened.close()


def test_start_displays_readiness_and_errors_without_manual_origin_instruction(app, context):
    page = SeedGenPage(context)
    fake = SimpleNamespace(prepare=lambda cfg: [], launch=lambda: True, results=[],
        poll=lambda: ([], []), progress=Progress(), startup=StartupStatus("loaded"),
        stop_and_restore=lambda: 0)
    with patch("ui.seedgen_page.game_mod.is_game_running", return_value=False), \
         patch("ui.seedgen_page.SeedGenOrchestrator", return_value=fake):
        page.start()
    assert "自动" in page.progress_label.text()
    assert not page.cfg_box.isEnabled() and not page.options_btn.isEnabled()
    page._poll()
    assert "等待" in page.progress_label.text()
    fake.startup = StartupStatus("requested", "scenario.militia")
    page._poll()
    assert "正在加载战役" in page.progress_label.text()
    fake.startup = StartupStatus("generating")
    page._poll()
    assert "第一批种子" in page.progress_label.text()
    fake.startup = StartupStatus("error", "origin-unavailable scenario.militia")
    page._poll()
    assert "DLC" in page.progress_label.text() and "origin-unavailable" in page.progress_label.toolTip()
    page.stop()
    assert page.cfg_box.isEnabled() and page.options_btn.isEnabled()
    assert not page.timer.isActive()
    page.close()

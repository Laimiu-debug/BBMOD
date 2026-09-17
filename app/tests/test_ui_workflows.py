from types import SimpleNamespace
from unittest.mock import patch

import pytest
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

from core.settings import Settings
from core.seedgen.log_watcher import SeedResult
from ui.l10n_page import L10nPage
from ui.seedgen_page import SeedGenPage


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def context(tmp_path):
    settings = Settings.__new__(Settings)
    settings.path = tmp_path / "settings.json"
    settings.data = {}
    return SimpleNamespace(game=None, mm=None, settings=settings,
        data_changed=SimpleNamespace(emit=lambda: None), set_seedgen_active=lambda _: None)


def test_filtered_translation_edit_uses_stable_source_key(app, context):
    page = L10nPage(context)
    page.search.setText("Load Campaign")
    assert page.table.rowCount() == 1
    page.table.item(0, 2).setText("读取旧战役")
    assert page.overrides == {"Load Campaign": "读取旧战役"}
    reloaded = L10nPage(context)
    assert reloaded.overrides == page.overrides
    page.table.selectRow(0)
    page.reset_selected()
    assert page.overrides == {}


def test_workshop_works_without_game_or_reference_zip(app, context):
    page = L10nPage(context)
    assert len(page.entries) > 400
    assert page.table.rowCount() == min(len(page.entries), page._page_size)
    first = page.table.item(0, 1).data(Qt.UserRole)
    page.next_page.click()
    assert page.table.item(0, 1).data(Qt.UserRole) != first
    page.prev_page.click()
    assert page.table.item(0, 1).data(Qt.UserRole) == first
    assert not page.build_btn.isEnabled()


def test_place_editor_uses_chinese_display_translation_and_stable_english_key(app, context):
    page = L10nPage(context)
    page.search.setText('Wiesendorf')
    assert page.table.rowCount() == 1
    assert page.table.item(0,2).text() == '维森多夫'
    assert page.table.item(0,3).text() == '已校对'
    assert page.table.item(0,1).data(Qt.UserRole) == 'Wiesendorf'
    page.table.item(0,2).setText('维森村')
    assert page.overrides == {'Wiesendorf':'维森村'}
    page.table.selectRow(0);page.reset_selected()
    assert page.overrides == {} and page.table.item(0,2).text() == '维森多夫'
    assert '直接启动时显示英文' in page.scope_label.text()


def test_stopped_expedition_keeps_details_and_exports(app, context, tmp_path):
    page = SeedGenPage(context)
    result = SeedResult(seed="ABCDEFGHIJ", loop_idx=42, lines=["TeamInfo: 0.80"], done=True)
    page.orch = SimpleNamespace(results=[result], stop_and_restore=lambda: 1)
    page._append_result(result)
    page.stop()
    page.table.selectRow(0)
    page._show_detail()
    assert "ABCDEFGHIJ" in page.detail_label.toPlainText()
    output = tmp_path / "seeds.txt"
    with patch.object(QFileDialog, "getSaveFileName", return_value=(str(output), "")), patch.object(QMessageBox, "information"):
        page.export_txt()
    assert "ABCDEFGHIJ" in output.read_text(encoding="utf-8-sig")


def test_default_seed_config_preserves_origin_defaults(app, context):
    page = SeedGenPage(context)
    page.rule_mode.setCurrentIndex(page.rule_mode.findData("preset"))
    assert page._current_config().origins == {}
    page.rule_mode.setCurrentIndex(page.rule_mode.findData("attributes"))
    assert len(page._current_config().origins) == 1


def test_click_copy_preferences_and_notes_survive_reopen(app, context):
    page = SeedGenPage(context)
    result = SeedResult("AbCdEfGhIj", 15, origin="scenario.militia", lines=["SettlementInfo: Port:7"], done=True)
    page.results = [result]
    page._append_result(result)
    page.resize(1030, 700)
    page.show()
    app.processEvents()
    copied = []
    with patch.object(QApplication, "clipboard", return_value=SimpleNamespace(setText=copied.append)):
        rect = page.table.visualItemRect(page.table.item(0, 0))
        QTest.mouseClick(page.table.viewport(), Qt.LeftButton, pos=rect.center())
        assert copied == []
        page.click_copy.setChecked(True)
        QTest.mouseClick(page.table.viewport(), Qt.LeftButton, pos=rect.center())
        assert copied[-1].startswith("跑商发愁？AbCdEfGhIj")
        page._note_changed("出门金鹅，坐船去北港")
        assert len(copied) == 1
        page.copy_btn.click()
        assert copied[-1].endswith("出门金鹅，坐船去北港")
        page._append_result(SeedResult("NEXTSEED01", 16))
        assert len(copied) == 2  # New results never overwrite the clipboard.
        page.format_combo.setCurrentIndex(page.format_combo.findData("seed"))
        page.copy_btn.click()
        assert copied[-1] == "AbCdEfGhIj"
    reopened = SeedGenPage(context)
    assert reopened.click_copy.isChecked()
    assert reopened.format_combo.currentData() == "seed"
    assert reopened.notes["scenario.militia|AbCdEfGhIj"] == "出门金鹅，坐船去北港"
    page.close()


def test_plain_attribute_filter_and_modes(app, context):
    page = SeedGenPage(context)
    page.bro_count.setValue(3)
    cfg = page._current_config()
    condition = next(iter(cfg.origins.values())).conditions[0]
    assert condition.type == "RoleAttr"
    assert condition.args == [3, -100, -100, -100, 90, -100, 25, -100, -100]
    assert cfg.map_conditions == [["PortNum", 7, "SettlementNum", 0, "ArmorsmithNum", 0]]
    page.mode_combo.setCurrentText("只找地图")
    cfg = page._current_config()
    assert cfg.origins == {} and cfg.common.GenerateSettlementMode
    assert not page.filter_tabs.isTabEnabled(0)
    page.mode_combo.setCurrentText("人物 + 地图 + 红装")
    assert page._current_config().lair_conditions == [["NamedNumber", 20]]
    page.rule_mode.setCurrentIndex(page.rule_mode.findData("score"))
    page.bro_type_combo.setCurrentIndex(page.bro_type_combo.findData("AnyRoleScore"))
    cond = next(iter(page._current_config().origins.values())).conditions[0]
    assert cond.args == [0.8, 3]


def test_txt_danmaku_export_and_write_failure(app, context, tmp_path):
    page = SeedGenPage(context)
    page.results = [SeedResult("TESTSEED01", 1), SeedResult("TESTSEED02", 2)]
    output = tmp_path / "好种子"
    with patch.object(QFileDialog, "getSaveFileName", return_value=(str(output), "")), patch.object(QMessageBox, "information"):
        page.export_txt()
    lines = output.with_suffix(".txt").read_text(encoding="utf-8-sig").splitlines()
    assert len(lines) == 2 and "TESTSEED01" in lines[0] and "TESTSEED02" in lines[1]
    with patch.object(QFileDialog, "getSaveFileName", return_value=(str(tmp_path / "missing/file.txt"), "")), patch.object(QMessageBox, "warning") as warning:
        page.export_txt()
        warning.assert_called_once()

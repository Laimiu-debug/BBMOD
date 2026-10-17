from types import SimpleNamespace
from unittest.mock import patch

import pytest
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

from core.settings import Settings
from core.seedgen.log_watcher import Progress, SeedResult, StartupStatus
from ui.seedgen_page import SeedGenPage
from ui.seed_star_dialog import SeedStarDialog
from ui.seed_trait_dialog import SeedTraitDialog


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def page(app, tmp_path):
    settings = Settings.__new__(Settings)
    settings.path, settings.data = tmp_path / "settings.json", {}
    context = SimpleNamespace(game=object(), settings=settings, data_changed=SimpleNamespace(emit=lambda: None),
        set_seedgen_active=lambda _: None)
    page = SeedGenPage(context)
    yield page
    page.timer.stop()
    page.shutdown_sharing()
    if page._import_worker:
        page._import_worker.wait(5000)
    page.close()


def fake_session():
    return SimpleNamespace(prepare=lambda cfg: [], launch=lambda: True, results=[],
        poll=lambda: ([], []), progress=Progress(500, 999), startup=StartupStatus("generating"),
        stop_and_restore=lambda: 2, stop_reason="", elapsed_seconds=75, log_path=None)


def test_determined_can_be_found_and_selected_using_either_chinese_name(app):
    dialog = SeedTraitDialog()
    for text in ('毅然', '坚定', 'Determined'):
        dialog.search.setText(text)
        visible = [row for row in range(dialog.table.rowCount()) if not dialog.table.isRowHidden(row)]
        assert any('坚定（毅然）' in dialog.table.item(row, 0).text() for row in visible)
    dialog.choices['trait.determined'].setCurrentIndex(1)
    assert dialog.selection()[0] == ['trait.determined']
    dialog.close()


def test_star_dialog_supports_exact_zero_and_catches_conflicting_totals(app):
    dialog = SeedStarDialog()
    dialog._nine()
    for key in ('MeleeSkill', 'MeleeDefense', 'Stamina'):
        dialog.choices[key].setCurrentIndex(6)  # Exactly three stars.
    dialog.choices['RangedSkill'].setCurrentIndex(3)  # Exactly zero stars.
    low, high, ranges = dialog.selection()
    assert (low, high) == (9, 9) and ranges['RangedSkill'] == (0, 0)
    dialog.total.setValue(8)
    dialog._accept()
    assert '矛盾' in dialog.error.text()
    dialog.clear()
    assert dialog.selection() == (0, 24, {})
    dialog.close()


def test_star_only_rule_reaches_config_and_persists_on_reopen(page, app):
    dialog = SeedStarDialog(9, 9, {'MeleeSkill': (3, 3), 'RangedSkill': (0, 0)})
    with patch('ui.seedgen_page.SeedStarDialog', return_value=dialog), \
            patch.object(dialog, 'exec', return_value=1):
        page._edit_stars()
    page.mode_combo.setCurrentText('只找开局兄弟（快）')
    page.rule_mode.setCurrentIndex(page.rule_mode.findData('traits'))
    condition = page._current_config().origins[page.origin_combo.currentData()].conditions[0]
    assert condition.type == 'BrotherFilter' and condition.args[5:7] == [9, 9]
    assert condition.args[7][3] == 3 and condition.args[8][4] == 0
    reloaded = SeedGenPage(page.ctx)
    assert reloaded.star_min == reloaded.star_max == 9
    assert reloaded.star_ranges == {'MeleeSkill': (3, 3), 'RangedSkill': (0, 0)}
    page.rule_mode.setCurrentIndex(page.rule_mode.findData('score'))
    assert page.stars_btn.isHidden()
    reloaded.timer.stop()
    reloaded.close()
    dialog.close()


def start(page, fake):
    with patch("ui.seedgen_page.game_mod.is_game_running", return_value=False), \
         patch("ui.seedgen_page.SeedGenOrchestrator", return_value=fake):
        page.start_btn.click()


def test_live_table_chinese_preview_and_stop_keep_last_buffered_result(page):
    fake = fake_session()
    start(page, fake)
    result = SeedResult("CURRENT001", 510, origin="scenario.cultists", done=True, lines=[
        "CharInfo: 0 Melee:0.8 MeleeSkill:57(91)3", "Trait: trait.cultist_fanatic trait.fearless"])
    fake.results.append(result)
    fake.poll = lambda: ([result], [])
    # Preserve origin match so the assertion checks normal progress.
    page.origin_combo.setCurrentIndex(page.origin_combo.findData("scenario.cultists"))
    page._poll()
    assert page.orch is fake and page.table.rowCount() == 1  # Live, before stop.
    assert "本次命中 1 条" in page.progress_label.text() and "999" not in page.progress_label.text()
    page.format_combo.setCurrentIndex(page.format_combo.findData("detail"))
    assert "近战命中 57→91（3星）" in page.detail_label.toPlainText()
    assert "达夫库尔狂信徒" in page.detail_label.toPlainText() and "Trait:" not in page.detail_label.toPlainText()
    assert not page.import_action.isEnabled()
    def restore():
        fake.results.append(SeedResult("LASTBUFFER", 512, done=True))
        return 2
    fake.stop_and_restore = restore
    page.stop_btn.click()
    assert page.orch is None and page.table.rowCount() == 2
    assert page.export_btn.isEnabled() and page.import_action.isEnabled() and not page.timer.isActive()


def test_automatic_stop_uses_normal_restore_flow(page):
    fake = fake_session()
    start(page, fake)
    fake.stop_reason = "已达到 1 分钟时限"
    page._poll()
    assert page.orch is None and not page.timer.isActive()
    assert "1 分钟" in page.progress_label.text() and "恢复 2 个 MOD" in page.progress_label.text()


def test_failed_automatic_restore_keeps_retry_available_without_dialog_loop(page):
    fake = fake_session()
    start(page, fake)
    fake.stop_reason = "已达到 1 分钟时限"
    def failed():
        raise RuntimeError("暂时无法恢复")
    fake.stop_and_restore = failed
    with patch.object(QMessageBox, "warning") as warning:
        page._poll()
        page._poll()
        assert warning.call_count == 1
    assert page.orch is fake and page.stop_btn.isEnabled() and page.timer.isActive()
    fake.stop_and_restore = lambda: 2
    page.stop_btn.click()
    assert page.orch is None


def test_import_txt_runs_in_background_and_displays_chinese_without_game(page, app, tmp_path):
    path = tmp_path / "log.txt"
    path.write_text("Seed: IMPORTED00 LoopIdx:548 Origin:scenario.cultists\n"
        "CharInfo: 0 Leader:0.837847 Hitpoints:50(85)0 Bravery:55(103)3\n"
        "Trait: trait.cultist_fanatic trait.iron_jaw\n\n", encoding="utf-8")
    with patch.object(QFileDialog, "getOpenFileName", return_value=(str(path), "")), \
         patch("ui.seedgen_page.SeedGenOrchestrator") as orchestrator:
        page.import_action.trigger()
        assert page._import_worker.wait(5000)
        app.processEvents()
        orchestrator.assert_not_called()
    assert page.table.rowCount() == 1 and page.orch is None
    assert "生命 50→85（0星）" in page.detail_label.toPlainText()
    assert "达夫库尔狂信徒" in page.detail_label.toPlainText()
    assert page.export_btn.isEnabled() and page.start_btn.isEnabled()
    page._imported_results(page.results.copy())
    assert page.table.rowCount() == 1 and "重复 1 条" in page.progress_label.text()


def test_waiting_status_points_to_directory_selection_without_assuming_fast_load(page):
    fake = fake_session()
    start(page, fake)
    fake.progress = Progress()
    fake.startup = StartupStatus()
    fake.elapsed_seconds = 46
    page._poll()
    assert "仍加载时请等待" in page.progress_label.text()
    assert "日志" in page.progress_label.text() and "选择目录" in page.progress_label.text()

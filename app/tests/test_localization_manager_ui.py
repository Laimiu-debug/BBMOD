from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import zipfile
import json

import pytest
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtTest import QTest

from core.game import GameInfo
from core.localization_profiles import CURRENT, NONE, BUILTIN, LocalizationProfiles
from core.settings import Settings
from core import l10n
from ui.localization_manager import LocalizationManager
from ui.game_session import GameSession


@pytest.fixture(scope='module')
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def context(tmp_path):
    game = tmp_path / 'game'
    (game / 'data').mkdir(parents=True)
    (game / 'win32').mkdir()
    settings = Settings.__new__(Settings)
    settings.data = {}
    settings.path = tmp_path / 'user/settings.json'
    ctx = SimpleNamespace(game=GameInfo(game, game / 'win32/BattleBrothers.exe', '1.5.2.3', game / 'data'),
                          settings=settings, seedgen_active=False, management_busy=False,
                          data_changed=SimpleNamespace(emit=lambda: None))
    ctx.game_session = GameSession(probe=lambda: False)
    ctx.game_session.observe(False)
    yield ctx
    ctx.game_session.shutdown()


def wait_worker(page, app):
    for _ in range(200):
        app.processEvents()
        if not page._busy:
            if getattr(page, 'worker', None):
                page.worker.wait(1000)
            return
        QTest.qWait(10)
    pytest.fail('UI operation timed out')


def test_apply_and_launch_preserves_order_and_stops_on_failure(app, context):
    path = context.game.data_dir / 'chinese.zip'
    with zipfile.ZipFile(path, 'w') as archive:
        archive.writestr('ui/main.html', 'test')
    page = LocalizationManager(context, lambda: None)
    page.choice.setCurrentIndex(page.choice.findData(NONE))
    assert 'chinese.zip' in page.preview.toPlainText()
    assert page.start_btn.text() == '应用并启动'
    with patch('core.game.is_game_running', return_value=False), \
            patch.object(LocalizationProfiles, 'launch', return_value={'pid': 42}) as launch:
        page.start_btn.click()
        wait_worker(page, app)
        launch.assert_called_once()
        assert page.start_btn.text() == '正在启动…'
        assert not page.start_btn.isEnabled()
        assert not path.exists()
        assert (context.game.root / 'bbmod_disabled/chinese.zip').exists()
    context.game_session.observe(True)
    context.game_session.observe(False)
    page.refresh()
    with patch.object(LocalizationProfiles, 'apply', side_effect=RuntimeError('simulated failure')), \
            patch.object(LocalizationProfiles, 'launch') as launch, patch.object(QMessageBox, 'warning') as warning:
        page.start_btn.click()
        wait_worker(page, app)
        warning.assert_called_once()
        launch.assert_not_called()


def test_pending_or_missing_profile_does_not_launch_from_global_button(app, context):
    path = context.game.data_dir / 'chinese.zip'
    with zipfile.ZipFile(path, 'w') as archive:
        archive.writestr('ui/main.html', 'test')
    page = LocalizationManager(context, lambda: None)
    with patch.object(LocalizationProfiles, 'launch') as launch:
        page.choice.setCurrentIndex(page.choice.findData(NONE))
        page.launch_current()
        assert '还未应用' in page.preview.toPlainText()
        page.choice.setCurrentIndex(page.choice.findData(BUILTIN))
        page.launch_current()
        launch.assert_not_called()
        assert not page.start_btn.isEnabled()


def test_plan_selection_persists_and_background_operations_lock_buttons(app, context):
    page = LocalizationManager(context, lambda: None)
    page.choice.setCurrentIndex(page.choice.findData(NONE))
    reopened = LocalizationManager(context, lambda: None)
    assert reopened.choice.currentData() == NONE
    context.management_busy = True
    reopened.update_controls()
    assert not reopened.start_btn.isEnabled() and not reopened.import_btn.isEnabled()
    context.management_busy = False
    context.seedgen_active = True
    reopened.update_controls()
    assert not reopened.start_btn.isEnabled() and not reopened.choice.isEnabled()


def own_package(path, *, version='0.3.0-rc.3'):
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, 'w') as archive:
        archive.writestr('ui/main.html', 'fixture')
        archive.writestr(l10n.BRAND_META, json.dumps({'package_id': l10n.PACKAGE_ID, 'version': version}))
    return path


def test_current_localization_comes_from_enabled_files_not_selected_plan(app, context):
    installed = own_package(context.game.data_dir / 'mod_bbmod_zhcn.zip')
    own_package(context.game.root / 'bbmod_disabled/old_chinese.zip', version='old')
    with patch('core.game.is_game_running', return_value=False):
        backend = LocalizationProfiles(context.game.root)
        backend.register('BBMOD 独立汉化', [installed], builtin=True)
    page = LocalizationManager(context, lambda: None)
    current_name = page.current_name.text()
    assert '0.3.0-rc.3' in current_name and 'old' not in current_name
    assert '无需重新生成' in page.summary.text()
    assert page.advanced_panel.isHidden()
    page.choice.setCurrentIndex(page.choice.findData(NONE))
    assert page.current_name.text() == current_name
    assert '尚未应用' in page.summary.text()
    assert page.keep_current_btn.isHidden() is False
    before = installed.read_bytes()
    page.keep_current_btn.click()
    assert page.choice.currentData() == CURRENT and not page.plan.changed
    assert not page.keep_current_btn.isVisible()
    assert installed.read_bytes() == before
    assert not page._busy


def test_manually_installed_own_package_does_not_require_regeneration(app, context):
    installed = own_package(context.game.data_dir / 'mod_bbmod_zhcn.zip')
    page = LocalizationManager(context, lambda: None)
    assert '已安装，未存方案' in page.choice.itemText(page.choice.findData(BUILTIN))
    page.choice.setCurrentIndex(page.choice.findData(BUILTIN))
    assert '已经启用' in page.preview.toPlainText() and '无需重新生成' in page.preview.toPlainText()
    page.keep_current_btn.click()
    assert page.start_btn.isEnabled() and not page.plan.changed
    assert not page.backend.registry.exists() and installed.is_file()


def test_opening_advanced_making_tools_does_not_build_or_replace_active_package(app, context):
    from ui.l10n_page import L10nPage
    installed = own_package(context.game.data_dir / 'mod_bbmod_zhcn.zip')
    before = installed.read_bytes()
    page = L10nPage(context)
    with patch.object(l10n, 'build_localization') as build, patch.object(LocalizationProfiles, 'register') as register:
        page.management.advanced_toggle.click()
        page.management.builtin_btn.click()
        assert page.sections.currentIndex() == 1
        assert not page._busy
        build.assert_not_called()
        register.assert_not_called()
        assert installed.read_bytes() == before


def test_saved_package_without_active_files_is_not_reported_as_current(app, context, tmp_path):
    saved = own_package(tmp_path / 'package/chinese.zip')
    with patch('core.game.is_game_running', return_value=False):
        LocalizationProfiles(context.game.root).register('BBMOD 独立汉化', [saved], builtin=True)
    page = LocalizationManager(context, lambda: None)
    page.choice.setCurrentIndex(page.choice.findData(BUILTIN))
    assert '未检测到已启用' in page.current_name.text()
    assert '尚未应用' in page.preview.toPlainText()
    assert page.plan.changed


def test_uninstall_clears_saved_choice_and_does_not_offer_reinstall(app, context, tmp_path):
    from core.modmanager import ModManager
    saved = own_package(tmp_path / 'package/chinese.zip')
    backend = LocalizationProfiles(context.game.root)
    with patch('core.game.is_game_running', return_value=False):
        backend.register('BBMOD 独立汉化', [saved], builtin=True)
        backend.apply(backend.plan(BUILTIN))
        backend.apply(backend.plan(NONE))
    page = LocalizationManager(context, lambda: None)
    page.select_profile(BUILTIN)
    assert page.table.item(0, 0).text() == '已停用'
    assert page.plan.changed
    ModManager(context.game.root).uninstall(saved.name, from_disabled=True)
    page.refresh()
    assert page.table.rowCount() == 0
    assert page.choice.findData(BUILTIN) == -1
    assert page.choice.currentData() == CURRENT
    assert page.plan is not None and not page.plan.changed
    assert '未检测到已启用' in page.current_name.text()
    assert context.settings.get('localization_choices')[str(context.game.root.resolve())] == CURRENT
    reopened = LocalizationManager(context, lambda: None)
    assert reopened.choice.currentData() == CURRENT and not reopened.plan.changed


def test_delete_old_saved_scheme_from_ui_and_cancel_preserves_it(app, context, tmp_path):
    saved = own_package(tmp_path / 'package/chinese.zip')
    with patch('core.game.is_game_running', return_value=False):
        backend = LocalizationProfiles(context.game.root)
        backend.register('BBMOD 独立汉化', [saved], builtin=True)
        page = LocalizationManager(context, lambda: None)
        page.select_profile(BUILTIN)
        assert not page.delete_btn.isHidden() and page.delete_btn.isEnabled()
        with patch.object(QMessageBox, 'question', return_value=QMessageBox.No):
            page.delete_btn.click()
        assert BUILTIN in backend.profiles()
        with patch.object(QMessageBox, 'question', return_value=QMessageBox.Yes):
            page.delete_btn.click()
            wait_worker(page, app)
    assert page.choice.findData(BUILTIN) == -1
    assert page.choice.currentData() == CURRENT
    assert page.delete_btn.isHidden()
    assert backend.profiles() == {} and saved.exists()


def test_delete_saved_scheme_obeys_operation_locks(app, context, tmp_path):
    saved = own_package(tmp_path / 'package/chinese.zip')
    with patch('core.game.is_game_running', return_value=False):
        backend = LocalizationProfiles(context.game.root)
        backend.register('BBMOD 独立汉化', [saved], builtin=True)
    page = LocalizationManager(context, lambda: None)
    page.select_profile(BUILTIN)
    for attribute in ('management_busy', 'seedgen_active'):
        setattr(context, attribute, True)
        page.update_controls()
        assert not page.delete_btn.isEnabled()
        setattr(context, attribute, False)
    context.game_session.observe(True)
    assert not page.delete_btn.isEnabled()
    context.game_session.observe(False)
    backend.journal.write_text('{}')
    page.refresh()
    assert not page.delete_btn.isEnabled()


def test_deleting_active_saved_scheme_keeps_current_game_launchable(app, context):
    installed = own_package(context.game.data_dir / 'chinese.zip')
    with patch('core.game.is_game_running', return_value=False):
        backend = LocalizationProfiles(context.game.root)
        backend.register('BBMOD 独立汉化', [installed], builtin=True)
        page = LocalizationManager(context, lambda: None)
        page.select_profile(BUILTIN)
        with patch.object(QMessageBox, 'question', return_value=QMessageBox.Yes):
            page.delete_btn.click()
            wait_worker(page, app)
    assert backend.profiles() == {} and installed.exists()
    assert page.choice.currentData() == CURRENT
    assert page.start_btn.isEnabled() and not page.plan.changed

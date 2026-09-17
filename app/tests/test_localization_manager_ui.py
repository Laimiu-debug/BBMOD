from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import zipfile

import pytest
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtTest import QTest

from core.game import GameInfo
from core.localization_profiles import CURRENT, NONE, BUILTIN, LocalizationProfiles
from core.settings import Settings
from ui.localization_manager import LocalizationManager


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
    return ctx


def wait_worker(page, app):
    for _ in range(200):
        app.processEvents()
        if not page._busy:
            if hasattr(page, 'worker'):
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
        assert not path.exists()
        assert (context.game.root / 'bbmod_disabled/chinese.zip').exists()
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

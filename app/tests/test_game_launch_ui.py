"""Launch feedback regression coverage. Every actual game launch is blocked."""
from types import SimpleNamespace
from unittest.mock import patch
import zipfile

import pytest
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMessageBox

from core.game import GameInfo
from core.localization_profiles import BUILTIN, NONE, LocalizationProfiles
from ui.game_session import GameSession
from ui.main_window import MainWindow
from ui.workers import Worker


@pytest.fixture(scope='module')
def app():
    return QApplication.instance() or QApplication([])


def until(app, predicate):
    for _ in range(250):
        app.processEvents()
        if predicate():
            return
        QTest.qWait(10)
    pytest.fail('Launch UI did not settle')


@pytest.fixture
def window(app, tmp_path, monkeypatch):
    root = tmp_path / 'game'
    (root / 'data').mkdir(parents=True)
    (root / 'win32').mkdir()
    with zipfile.ZipFile(root / 'data/chinese.zip', 'w') as archive:
        archive.writestr('ui/main.html', 'fixture')
    game = GameInfo(root, root / 'win32/BattleBrothers.exe', '1.5.2.3', root / 'data')
    monkeypatch.setenv('APPDATA', str(tmp_path / 'profile'))
    running = SimpleNamespace(value=False)
    with patch('ui.app_context.game_mod.locate_game', return_value=game), \
            patch('core.game.find_log_write_path', return_value=None), \
            patch('core.game.is_game_running', side_effect=lambda: running.value), \
            patch('core.game.launch_executable', side_effect=AssertionError('Real game launch forbidden')):
        view = MainWindow(auto_updates=False)
        until(app, lambda: view.ctx.game_session.state == 'idle')
        view.ctx.game_session.timer.stop()
        view.process_fixture = running
        yield view
        view.ctx.game_session.shutdown()
        until(app, lambda: not any(worker.isRunning() for worker in view.findChildren(Worker)))
        view.close()
        app.processEvents()


def finish_launch(app, window):
    page = window.l10n.management
    until(app, lambda: not page._busy)
    if hasattr(page, 'worker'):
        page.worker.wait(1000)
    # Finish any old probe before manually advancing the simulated game process.
    until(app, lambda: window.ctx.game_session._worker is None)


def test_global_launch_stays_on_current_page_and_does_not_reenable_early(app, window):
    window.select_page(5)
    page = window.l10n.management
    with patch.object(LocalizationProfiles, 'launch', return_value={'mode': 'current'}) as launch:
        window.launch_btn.click()
        assert window.tabs.currentIndex() == 5
        assert window.launch_btn.text() == page.start_btn.text() == '正在启动…'
        window.launch_btn.click()
        page.start_btn.click()
        window.launch_game()  # Also guard direct/queued invocations.
        finish_launch(app, window)
        launch.assert_called_once()
        page.refresh()
        window._management_changed(False)
        assert not window.launch_btn.isEnabled() and not page.start_btn.isEnabled()
        assert '等待游戏' in window.game_status.text()
        window.process_fixture.value = True
        window.ctx.game_session.poll()
        until(app, lambda: window.ctx.game_session.state == 'running')
        assert window.launch_btn.text() == page.start_btn.text() == '游戏运行中'
        assert '无需再次启动' in page.preview.toPlainText()
        assert window.tabs.currentIndex() == 5
        window.process_fixture.value = False
        until(app, lambda: window.ctx.game_session._worker is None)
        window.ctx.game_session.poll()
        until(app, lambda: window.ctx.game_session.state == 'idle')
        assert window.launch_btn.isEnabled() and page.start_btn.isEnabled()
        launch.assert_called_once()


def test_only_pending_configuration_routes_to_review_then_launches_once(app, window):
    page = window.l10n.management
    page.choice.setCurrentIndex(page.choice.findData(NONE))
    window.select_page(0)
    assert window.launch_btn.text() == '确认汉化方案'
    with patch.object(LocalizationProfiles, 'launch', return_value={'pid': 42}) as launch:
        window.launch_btn.click()
        assert window.tabs.currentIndex() == 2
        assert '还未应用' in page.preview.toPlainText()
        launch.assert_not_called()
        page.start_btn.click()
        finish_launch(app, window)
        launch.assert_called_once()
        assert (window.ctx.game.root / 'bbmod_disabled/chinese.zip').is_file()
        assert window.launch_btn.text() == page.start_btn.text() == '正在启动…'


def test_running_game_blocks_both_buttons_and_configuration_changes(app, window):
    window.process_fixture.value = True
    until(app, lambda: window.ctx.game_session._worker is None)
    window.ctx.game_session.poll()
    until(app, lambda: window.ctx.game_session.state == 'running')
    page = window.l10n.management
    with patch.object(LocalizationProfiles, 'launch') as launch, patch.object(LocalizationProfiles, 'apply') as apply:
        window.launch_game()
        page.apply(True)
        window._management_changed(False)
        assert window.launch_btn.text() == page.start_btn.text() == '游戏运行中'
        assert not window.launch_btn.isEnabled() and not page.start_btn.isEnabled()
        assert not page.choice.isEnabled() and not page.apply_btn.isEnabled()
        launch.assert_not_called()
        apply.assert_not_called()


def test_launch_failure_is_visible_and_retry_stays_on_current_page(app, window):
    window.select_page(5)
    with patch.object(LocalizationProfiles, 'launch', side_effect=RuntimeError('fixture launch failed')), \
            patch.object(QMessageBox, 'warning') as warning:
        window.launch_btn.click()
        finish_launch(app, window)
        assert 'fixture launch failed' in window.game_status.text()
        assert window.launch_btn.isEnabled()
        assert window.tabs.currentIndex() == 5
        warning.assert_called_once()
    with patch.object(LocalizationProfiles, 'launch', return_value={'pid': 42}) as launch:
        window.launch_btn.click()
        finish_launch(app, window)
        launch.assert_called_once()
        assert window.launch_btn.text() == '正在启动…'


def test_missing_selected_profile_opens_explanation_without_launch(app, window):
    page = window.l10n.management
    page.choice.setCurrentIndex(page.choice.findData(BUILTIN))
    window.select_page(0)
    with patch.object(LocalizationProfiles, 'launch') as launch:
        assert window.launch_btn.text() == '检查汉化配置'
        window.launch_btn.click()
        assert window.tabs.currentIndex() == 2
        assert '尚无已保存' in page.preview.toPlainText()
        assert not page.start_btn.isEnabled()
        launch.assert_not_called()


def test_slow_launch_timeout_and_stale_check_do_not_report_success(app):
    now = [100.0]
    session = GameSession(probe=lambda: False, clock=lambda: now[0])
    session.observe(False)
    assert session.begin_launch()
    assert not session.begin_launch()
    # An old idle check must not undo the click, nor claim an unrelated game ran.
    session.observe(True, revision=0)
    assert session.state == 'starting'
    session.launch_submitted()
    until(app, lambda: session._worker is None)
    now[0] += session.START_TIMEOUT - 1
    session.observe(False)
    assert session.occupied
    now[0] += 2
    session.observe(False)
    assert not session.occupied and '未检测到' in session.message
    assert session.begin_launch()
    session.observe(True)
    session.observe(False)
    assert not session.occupied and '已退出' in session.message
    session.shutdown()

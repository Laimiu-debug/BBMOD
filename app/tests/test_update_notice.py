"""Reminder visibility and explicit actions, without downloading or restarting."""
import json
import sys
import time

import pytest
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication

from core.version import VERSION
from ui.update_notice import UpdateNotice
from ui.update_service import UpdateService
from test_app_updates import parsed, release_row, settings_at


class Context(QObject):
    management_changed = Signal(bool)
    session_changed = Signal(bool)
    management_busy = False
    seedgen_active = False


@pytest.fixture(scope='module')
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def notice(app, tmp_path):
    service = UpdateService(settings_at(tmp_path), automatic=False)
    context = Context()
    view = UpdateNotice(service, context)
    yield view
    service.shutdown()
    view.close()
    app.processEvents()


def publish(view, tag='v999.0.0'):
    view.service.releases = [parsed(release_row(tag, preview='-' in tag))]
    view.service.changed.emit()


def test_new_release_prompts_with_explicit_details_action(notice):
    assert notice.isHidden()
    opened = []
    notice.history_requested.connect(lambda: opened.append(True))
    publish(notice)
    assert not notice.isHidden() and 'v999.0.0' in notice.message.text()
    assert notice.action.text() == '查看更新'
    notice.action.click()
    assert opened == [True]
    assert notice.service.downloaded is None


@pytest.mark.parametrize('tag', ['v0.1.0', 'v' + VERSION])
def test_current_and_older_versions_do_not_prompt(notice, tag):
    publish(notice, tag)
    assert notice.isHidden()


def test_dismiss_stays_quiet_until_ready_or_newer_release(notice, monkeypatch, tmp_path):
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    monkeypatch.setattr(sys, 'platform', 'win32')
    publish(notice)
    notice.later.click()
    for _ in range(3):
        notice.service.changed.emit()
    assert notice.isHidden()
    notice.service.download_release = notice.service.latest()
    notice.service.downloaded = tmp_path / 'BBMOD.exe'
    notice.service.changed.emit()
    assert not notice.isHidden() and notice.action.text() == '重启并更新'
    requests = []
    notice.install_requested.connect(lambda: requests.append(True))
    notice.context.management_busy = True
    notice.context.management_changed.emit(True)
    assert not notice.action.isEnabled()
    notice.context.management_busy = False
    notice.context.management_changed.emit(False)
    notice.action.click()
    assert requests == [True]
    notice.later.click()
    notice.service.changed.emit()
    assert notice.isHidden()
    publish(notice, 'v999.0.1')
    assert not notice.isHidden() and notice.action.text() == '查看更新'


def test_channel_and_ignored_version_are_respected(notice):
    publish(notice, 'v999.0.0-rc.1')
    notice.service.save_preference('preview', False)
    assert notice.isHidden()
    notice.service.save_preference('preview', True)
    assert not notice.isHidden()
    notice.service.save_preference('ignored', 'v999.0.0-rc.1')
    assert notice.isHidden()


def test_download_progress_and_verification_are_not_ready_to_restart(notice):
    publish(notice)
    service = notice.service
    service.download_release = service.latest()
    service.busy, service.received, service.total = 'download', 50, 100
    service.changed.emit()
    assert '50%' in notice.message.text() and notice.action.text() == '查看更新'
    service.busy = 'verify'
    service.changed.emit()
    assert '正在校验' in notice.message.text() and notice.action.text() == '查看更新'
    service.busy = ''


def test_cached_release_prompts_even_during_six_hour_check_window(app, tmp_path, monkeypatch):
    settings = settings_at(tmp_path)
    settings.set('app_updates', {'automatic': True, 'last_check_epoch': time.time()})
    folder = settings.path.parent / 'updates'
    folder.mkdir()
    (folder / 'releases-cache.json').write_text(json.dumps([release_row('v999.0.0', preview=False)]))
    service = UpdateService(settings, automatic=False)
    monkeypatch.setattr(service, 'check', lambda: pytest.fail('Fresh cache must not force network request'))
    context = Context()
    first = UpdateNotice(service, context)
    service.automatic_check()
    assert not first.isHidden()
    first.dismiss()
    second = UpdateNotice(service, context)
    assert not second.isHidden()  # Dismissal is per run, not an ignored version preference.
    first.close()
    second.close()
    service.shutdown()

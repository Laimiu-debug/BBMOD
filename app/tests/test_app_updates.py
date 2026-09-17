import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from core import app_updates as updates
from core.settings import Settings
from core.version import VERSION


def release_row(tag='v0.3.0-rc.5', *, preview=True, data=b'MZ-new'):
    return {'tag_name': tag, 'name': '新版', 'body': '<img src="https://example.org/tracker">更新说明',
            'published_at': '2026-09-17T00:00:00Z', 'draft': False, 'prerelease': preview,
            'html_url': updates.RELEASES_URL + '/tag/' + tag,
            'assets': [{'name': 'BBMOD.exe', 'state': 'uploaded', 'size': len(data),
                        'digest': 'sha256:' + hashlib.sha256(data).hexdigest(),
                        'browser_download_url': updates.RELEASES_URL + '/download/' + tag + '/BBMOD.exe'}]}


def parsed(row=None):
    return updates.parse_releases(json.dumps([row or release_row()]).encode())[0]


def settings_at(tmp_path):
    settings = Settings.__new__(Settings)
    settings.path = tmp_path / 'settings.json'
    settings.data = {'game_path': 'unchanged', 'seed_traits': {'required': ['trait.huge']}}
    return settings


def test_semantic_version_order_and_channels():
    versions = ['0.3.0-alpha.2', '0.3.0-beta.1', '0.3.0-rc.2', '0.3.0-rc.10', '0.3.0', '0.3.1', '1.0.0']
    assert sorted(reversed(versions), key=updates.version_key) == versions
    assert updates.version_key('v0.3.0+build.10') == updates.version_key('0.3.0')
    with pytest.raises(ValueError): updates.version_key('0.3.0-rc.01')
    rows = [release_row('v0.3.0'), release_row('v0.3.0-rc.10'), release_row('v0.4.0', preview=False)]
    rows += [{**release_row('v9.0.0'), 'draft': True}, {**release_row('v8.0.0'), 'html_url': 'https://evil.org'}]
    result = updates.parse_releases(json.dumps(rows).encode())
    assert [r.tag for r in result] == ['v0.4.0', 'v0.3.0', 'v0.3.0-rc.10']
    assert [r.tag for r in updates.available_releases(result, False)] == ['v0.4.0']
    assert result[0].newer_than(VERSION)
    assert not parsed(release_row('v0.3.0-rc.2')).newer_than(VERSION)


@pytest.mark.parametrize('field,value', [('digest', None), ('digest', 'sha256:123'), ('size', -1),
    ('size', updates.MAX_DOWNLOAD + 1), ('size', True), ('browser_download_url', 'https://evil.org/BBMOD.exe'), ('state', 'new')])
def test_unverified_assets_cannot_install(field, value):
    row = release_row()
    row['assets'][0][field] = value
    result = parsed(row)
    assert not result.installable
    assert result.url.startswith(updates.RELEASES_URL)


def test_bad_metadata_and_download_hosts():
    for bad in (b'{}', b'not json'):
        with pytest.raises(ValueError): updates.parse_releases(bad)
    assert updates.parse_releases(b'[null, {}, {"tag_name": null}]') == []
    assert updates.download_host_allowed('https://release-assets.githubusercontent.com/a')
    assert not updates.download_host_allowed('http://github.com/a')
    assert not updates.download_host_allowed('https://github.com.evil.org/a')


def install_fixture(tmp_path):
    job = tmp_path / '缓存 & 中文' / 'job'
    job.mkdir(parents=True)
    source = job / 'BBMOD.exe'
    source.write_bytes(b'MZ-new')
    target = tmp_path / '旧程序 & folder' / '我的BBMOD.exe'
    target.parent.mkdir()
    target.write_bytes(b'MZ-old')
    release = parsed()
    request = updates.prepare_install(source, release, target=target, parent_pid=1234)
    return source, target, request


def test_install_keeps_settings_and_backup(tmp_path):
    settings = settings_at(tmp_path)
    settings.save()
    original_settings = settings.path.read_bytes()
    source, target, request = install_fixture(tmp_path)
    waited, launched = [], []
    result = updates.install_request(request, wait=waited.append, launch=launched.append)
    assert result['status'] == 'installed' and waited == [1234] and launched == [target]
    assert target.read_bytes() == source.read_bytes() == b'MZ-new'
    assert Path(result['backup']).read_bytes() == b'MZ-old'
    assert settings.path.read_bytes() == original_settings
    assert not list(target.parent.glob('*.lock'))


def test_corrupted_or_concurrently_changed_files_do_not_replace_current(tmp_path):
    source, target, request = install_fixture(tmp_path)
    source.write_bytes(b'MZ-bad')
    result = updates.install_request(request, wait=lambda _: None, launch=lambda _: pytest.fail('must not launch'))
    assert result['status'] == 'failed' and target.read_bytes() == b'MZ-old'
    source.write_bytes(b'MZ-new')
    target.write_bytes(b'another-update')
    result = updates.install_request(request, wait=lambda _: None)
    assert result['status'] == 'failed' and target.read_bytes() == b'another-update'


@pytest.mark.parametrize('failure', ['replace', 'launch'])
def test_failed_transaction_rolls_back(tmp_path, failure):
    source, target, request = install_fixture(tmp_path)
    real_replace = updates._replace_with_retry
    def replace(a, b):
        if failure == 'replace' and a.suffix == '.tmp': raise OSError('replacement failed')
        real_replace(a, b)
    def launch(_):
        if failure == 'launch': raise OSError('launch failed')
    with patch.object(updates, '_replace_with_retry', replace):
        result = updates.install_request(request, wait=lambda _: None, launch=launch)
    assert result['status'] == 'failed' and result['rolled_back']
    assert target.read_bytes() == b'MZ-old' and source.exists()


def test_locked_update_and_existing_stage_are_preserved(tmp_path):
    source, target, request = install_fixture(tmp_path)
    lock = target.with_name(f'.{target.name}.update.lock')
    lock.write_text('other-updater')
    result = updates.install_request(request, wait=lambda _: None)
    assert result['status'] == 'failed' and lock.read_text() == 'other-updater'
    lock.unlink()
    plan = json.loads(request.read_text())
    staged = target.with_name(f'.{target.name}.{plan["id"]}.tmp')
    staged.write_bytes(b'previous-stage')
    result = updates.install_request(request, wait=lambda _: None)
    assert result['status'] == 'failed' and staged.read_bytes() == b'previous-stage'


def test_cannot_install_in_source_mode_or_with_bad_hash(tmp_path):
    source = tmp_path / 'BBMOD.exe';source.write_bytes(b'MZ-corrupt')
    with pytest.raises(ValueError): updates.verify_download(source, parsed())
    with patch.object(updates.sys, 'frozen', False, create=True), pytest.raises(ValueError):
        updates.prepare_install(source, parsed())
    assert updates.restart_environment()['PYINSTALLER_RESET_ENVIRONMENT'] == '1'


@pytest.fixture(scope='module')
def app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def test_update_dialog_preferences_history_and_plain_text(app, tmp_path):
    from PySide6.QtCore import Qt
    from ui.update_service import UpdateService
    from ui.update_dialog import UpdateDialog
    service = UpdateService(settings_at(tmp_path), automatic=False)
    service.releases = [parsed(), parsed(release_row('v0.3.0', preview=False))]
    dialog = UpdateDialog(service)
    dialog.show();app.processEvents()
    assert dialog.versions.count() == 2
    assert '<img' in dialog.notes.toPlainText()  # No release-controlled HTML execution.
    assert not dialog.notes.openExternalLinks()
    cursor = dialog.notes.textCursor()
    cursor.setPosition(5)
    dialog.notes.setTextCursor(cursor)
    service.changed.emit()  # Download progress must not reset the notes document.
    assert dialog.notes.textCursor().position() == 5
    dialog.automatic.setChecked(False)
    dialog.channel.setCurrentIndex(0)
    assert dialog.versions.count() == 1 and dialog.selected().tag == 'v0.3.0'
    assert '新版本 v0.3.0。' in service.status
    assert service.settings.get('seed_traits') == {'required': ['trait.huge']}
    reloaded = UpdateService(service.settings, automatic=False)
    assert reloaded.preferences['automatic'] is False and reloaded.preferences['preview'] is False
    service.shutdown();reloaded.shutdown();dialog.close()


def test_automatic_check_respects_preferences_cooldown_and_shutdown(app, tmp_path):
    from ui.update_service import UpdateService
    service = UpdateService(settings_at(tmp_path), automatic=False)
    with patch.object(service, 'check') as check:
        service.automatic_check();check.assert_called_once()
        check.reset_mock()
        service.preferences['last_check_epoch'] = __import__('time').time()
        service.automatic_check();check.assert_not_called()
        service.preferences.update(last_check_epoch=0, automatic=False)
        service.automatic_check();check.assert_not_called()
        service.preferences['automatic'] = True
        service.shutdown();service.automatic_check();check.assert_not_called()


def test_windows_resource_version_matches_application():
    text = (Path(__file__).parents[1] / 'data/windows-version.txt').read_text(encoding='utf-8')
    assert f"StringStruct('FileVersion', '{VERSION}')" in text
    assert f"StringStruct('ProductVersion', '{VERSION}')" in text


def test_allowed_download_redirect_uses_qt_signal(app, tmp_path):
    from PySide6.QtCore import QUrl
    from ui.update_service import UpdateService
    from unittest.mock import Mock
    service = UpdateService(settings_at(tmp_path), automatic=False)
    service.busy = 'download'
    reply = SimpleNamespace(redirectAllowed=SimpleNamespace(emit=Mock()), abort=Mock())
    service._redirect(reply, QUrl('https://release-assets.githubusercontent.com/a'))
    reply.redirectAllowed.emit.assert_called_once()
    reply.abort.assert_not_called()
    service._redirect(reply, QUrl('https://evil.org/a'))
    reply.abort.assert_called_once()
    service.shutdown()


@pytest.mark.parametrize('busy', ['management', 'seedgen', 'worker', 'orchestrator'])
def test_restart_is_blocked_while_managing_files_or_seeds(busy):
    from ui.main_window import MainWindow
    from unittest.mock import Mock
    window = SimpleNamespace(ctx=SimpleNamespace(management_busy=busy=='management', seedgen_active=busy=='seedgen'),
                             seedgen=SimpleNamespace(orch=object() if busy=='orchestrator' else None),
                             findChildren=lambda _: [SimpleNamespace(isRunning=lambda: busy=='worker')], close=Mock())
    with patch('PySide6.QtWidgets.QMessageBox.information') as message, patch.object(updates,'prepare_install') as prepare:
        MainWindow._request_update(window)
        message.assert_called_once();prepare.assert_not_called();window.close.assert_not_called()

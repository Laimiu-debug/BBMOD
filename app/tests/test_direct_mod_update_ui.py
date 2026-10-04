"""Exercise the real installed-row update action in temporary game directories."""
import hashlib
import os
import threading
import uuid
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMessageBox

from core.modmanager import ModManager
from core.online_catalog import OnlineInstaller
from core.site_config import SITE_ORIGIN
from ui.mods_page import ModsPage


class Context(QObject):
    management_changed = Signal(bool)
    session_changed = Signal(bool)
    data_changed = Signal()

    def __init__(self, manager, settings_path):
        super().__init__()
        self.mm = manager
        self.management_busy = self.seedgen_active = False
        self.settings = SimpleNamespace(path=settings_path, get=lambda key, default=None: default,
                                        set=lambda *_: None)
        self.busy_events = []

    def set_management_busy(self, busy):
        self.management_busy = busy
        self.busy_events.append(busy)
        self.management_changed.emit(busy)


def archive(path, version, identity='mod_fixture'):
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, 'w') as package:
        package.writestr('scripts/!mods_preload/fixture.nut',
                         f'::Hooks.register("{identity}", "{version}", "English fixture");')
    return path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def catalog(path):
    identity, release_id = str(uuid.uuid4()), str(uuid.uuid4())
    return {'id': identity, 'release_id': release_id, 'version': '2.0.0',
            'file_name': 'mod_fixture_v2.zip', 'sha256': sha(path), 'size': path.stat().st_size,
            'download_path': f'/files/{release_id}/download/', 'page_path': f'/mods/{identity}/',
            'metadata': {'title': '中文测试 MOD', 'summary': '', 'description': '',
                         'category': '其他', 'author': 'test', 'game_version': '', 'license': 'original',
                         'mod_ids': ['mod_fixture'], 'requires': [], 'conflicts': []}}


def wait_idle(page, app):
    # Windows journal writes and rollback can exceed five seconds on busy disks.
    for _ in range(1500):
        app.processEvents()
        worker = page.online.worker
        if worker and not worker.isRunning() and not page.ctx.management_busy:
            assert worker.wait(1000)
            app.processEvents()
            return
        QTest.qWait(10)
    pytest.fail('direct MOD update did not finish')


def row_for(page, name):
    return next(row for row in range(page.table.rowCount())
                if page.table.item(row, 1).text() == name)


def update_button(page, local):
    row = row_for(page, local.name)
    button = page.table.cellWidget(row, 5)
    assert button is not None and button.text() == '更新' and button.isEnabled()
    return button


@pytest.fixture(scope='module')
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def view(app, tmp_path, monkeypatch):
    # Any accidental request fails; the row click receives a fully mocked download.
    monkeypatch.setattr('core.online_catalog._request',
                        Mock(side_effect=AssertionError('unexpected network request')))
    monkeypatch.setattr('core.game.is_game_running', lambda: False)
    question = Mock(side_effect=AssertionError('direct update must not ask confirmation'))
    browser = Mock(side_effect=AssertionError('direct update must not open a website'))
    monkeypatch.setattr(QMessageBox, 'question', question)
    monkeypatch.setattr(QDesktopServices, 'openUrl', browser)
    manager = ModManager(tmp_path / 'game')
    manager.data.mkdir(parents=True)
    (manager.data / 'data_001.dat').write_bytes(b'official data remains untouched')
    archive(manager.data / 'mod_modern_hooks.zip', '1.0.0', 'mod_modern_hooks')
    context = Context(manager, tmp_path / 'settings.json')
    page = ModsPage(context, automatic_catalog=False)
    # MainWindow makes this same connection in the actual application.
    context.data_changed.connect(page.refresh)
    page._installed_index = {}
    page._test_question = question
    page._test_browser = browser
    page._test_gates = []
    yield page
    for gate in page._test_gates:
        gate.set()
    if page.online.worker and page.online.worker.isRunning():
        page.online.cancelled.set()
        assert page.online.worker.wait(5000)
    if page.catalog_service and page.catalog_service.worker and page.catalog_service.worker.isRunning():
        assert page.catalog_service.worker.wait(5000)
    app.processEvents()
    page.close()
    page.deleteLater()
    app.processEvents()


def prepare(view, tmp_path, *, disabled=True):
    manager = view.ctx.mm
    local = archive((manager.disabled_dir if disabled else manager.data) / 'mod_fixture_v1.zip', '1.0.0')
    old_bytes = local.read_bytes()
    incoming = archive(tmp_path / 'release.zip', '2.0.0')
    item = catalog(incoming)
    stat = local.stat()
    view.refresh()
    view.set_installed_catalog([item], hashes={str(local.resolve()):
        (stat.st_mtime_ns, stat.st_size, sha(local))})
    return local, old_bytes, incoming, item


def downloader(monkeypatch, incoming, *, failure=None, gate=None, started=None):
    downloads = []

    def download(origin, item, cache, *, cancelled, progress):
        assert origin == SITE_ORIGIN
        if started:
            started.set()
        progress('正在下载 50%')
        if gate:
            assert gate.wait(3)
        if failure:
            raise failure
        cache.mkdir(parents=True, exist_ok=True)
        path = cache / f'{uuid.uuid4().hex}.zip'
        path.write_bytes(incoming.read_bytes())
        downloads.append(path)
        return path

    mocked = Mock(side_effect=download)
    monkeypatch.setattr('ui.online_mods.download_release', mocked)
    return mocked, downloads


@pytest.mark.parametrize('disabled', [False, True])
def test_inline_update_installs_and_can_restore_without_confirmation(view, app, tmp_path, monkeypatch, disabled):
    local, old_bytes, incoming, item = prepare(view, tmp_path, disabled=disabled)
    new_bytes = incoming.read_bytes()
    download, downloads = downloader(monkeypatch, incoming)
    update_button(view, local).click()
    assert view.ctx.management_busy
    wait_idle(view, app)

    assert local.read_bytes() == new_bytes
    other = (view.ctx.mm.data if disabled else view.ctx.mm.disabled_dir) / local.name
    assert not other.exists()
    assert not (view.ctx.mm.data / item['file_name']).exists()
    assert not (view.ctx.mm.disabled_dir / item['file_name']).exists()
    assert view.ctx.busy_events == [True, False]
    assert not view.online.cancel_btn.isEnabled()
    assert view.cancel_update_btn.isHidden()
    assert not view.ctx.management_busy
    assert download.call_count == 1
    assert downloads and all(not path.exists() for path in downloads)
    view._test_question.assert_not_called()
    view._test_browser.assert_not_called()

    row = row_for(view, local.name)
    assert view.table.item(row, 0).text() == ('已禁用' if disabled else '已启用')
    assert view.table.item(row, 3).text() == '2.0.0'
    assert view.table.cellWidget(row, 5) is None
    assert '已安装' in view.online.status.text()
    assert view.catalog_status.text() == view.online.status.text()
    installer = OnlineInstaller(view.ctx.mm)
    receipt = installer.state()['mods'][local.name]
    assert (installer.backups / receipt['backup']).read_bytes() == old_bytes
    installer.rollback(local.name)
    assert local.read_bytes() == old_bytes
    assert installer.state()['mods'][local.name]['version'] == '1.0.0'
    assert (view.ctx.mm.data / 'data_001.dat').read_bytes() == b'official data remains untouched'


def test_verified_old_preview_shows_button_and_updates_to_new_preview(view, app, tmp_path, monkeypatch):
    local, _, incoming, item = prepare(view, tmp_path)
    archive(local, '76')  # Script revision differs from the website release label.
    item['version'] = '0.29.0-preview.13'
    view.refresh()
    stat = local.stat()
    view.set_installed_catalog([item], hashes={str(local.resolve()):
        (stat.st_mtime_ns, stat.st_size, sha(local), stat.st_dev, stat.st_ino)},
        release_versions={item['id']: {sha(local): '0.29.0-preview.12'}})
    downloader(monkeypatch, incoming)

    update_button(view, local).click()
    wait_idle(view, app)

    record = OnlineInstaller(view.ctx.mm).state()['mods'][local.name]
    assert record['version'] == '0.29.0-preview.13'
    assert record['previous']['version'] == '0.29.0-preview.12'
    assert local.read_bytes() == incoming.read_bytes()
    # The normal background identity check runs after installation. This fixture
    # disables automatic network checks, so provide its newly verified hash.
    stat = local.stat()
    view.set_installed_catalog([item], hashes={str(local.resolve()):
        (stat.st_mtime_ns, stat.st_size, sha(local), stat.st_dev, stat.st_ino)})
    row = row_for(view, local.name)
    assert view.table.cellWidget(row, 5) is None
    assert view.table.item(row, 5).text() == '已是最新'


@pytest.mark.parametrize('failure', ['download', 'commit'])
def test_failed_inline_update_preserves_old_mod_and_releases_management_lock(view, app, tmp_path, monkeypatch, failure):
    local, old_bytes, incoming, _ = prepare(view, tmp_path)
    download, downloads = downloader(monkeypatch, incoming,
                                     failure=TimeoutError('download timed out') if failure == 'download' else None)
    installer = OnlineInstaller(view.ctx.mm)
    if failure == 'commit':
        original_replace = os.replace

        def fail_receipt_commit(source, target):
            if Path(target) == installer.state_path and str(source).endswith('.after'):
                raise OSError('receipt disk full')
            return original_replace(source, target)

        monkeypatch.setattr('core.mod_transactions.os.replace', fail_receipt_commit)
    update_button(view, local).click()
    wait_idle(view, app)

    assert local.read_bytes() == old_bytes
    assert not (view.ctx.mm.data / local.name).exists()
    assert not installer.state_path.exists()
    assert not view.ctx.mm.transaction.journal.exists()
    assert view.ctx.busy_events == [True, False]
    assert not view.ctx.management_busy
    assert not view.online.cancel_btn.isEnabled()
    assert view.cancel_update_btn.isHidden()
    assert update_button(view, local).isEnabled()
    assert view.online.status.text().startswith('操作失败：')
    assert view.catalog_status.text() == view.online.status.text()
    assert ('timed out' if failure == 'download' else 'disk full') in view.online.status.text()
    assert download.call_count == 1
    assert all(not path.exists() for path in downloads)
    view._test_question.assert_not_called()
    view._test_browser.assert_not_called()


def test_inline_download_locks_button_and_cancel_keeps_old_file(view, app, tmp_path, monkeypatch):
    local, old_bytes, incoming, _ = prepare(view, tmp_path)
    started, gate = threading.Event(), threading.Event()
    view._test_gates.append(gate)
    download, downloads = downloader(monkeypatch, incoming, gate=gate, started=started)
    button = update_button(view, local)
    button.click()
    assert started.wait(2)
    for _ in range(50):
        app.processEvents()
        if '50%' in view.online.status.text():
            break
        QTest.qWait(10)
    assert '50%' in view.online.status.text()
    assert '50%' in view.catalog_status.text()
    assert view.ctx.management_busy
    assert not button.isEnabled()
    assert view.online.cancel_btn.isEnabled()
    assert not view.cancel_update_btn.isHidden()
    button.click()
    assert download.call_count == 1
    view.cancel_update_btn.click()
    assert view.online.cancelled.is_set()
    gate.set()
    wait_idle(view, app)

    assert local.read_bytes() == old_bytes
    assert not OnlineInstaller(view.ctx.mm).state_path.exists()
    assert not view.ctx.management_busy
    assert not view.online.cancel_btn.isEnabled()
    assert view.cancel_update_btn.isHidden()
    assert update_button(view, local).isEnabled()
    assert '下载已取消' in view.online.status.text()
    assert view.catalog_status.text() == view.online.status.text()
    assert downloads and all(not path.exists() for path in downloads)
    view._test_question.assert_not_called()
    view._test_browser.assert_not_called()


def test_online_row_can_restore_updated_package_with_a_different_local_name(view, app, tmp_path, monkeypatch):
    local, old_bytes, incoming, item = prepare(view, tmp_path)
    assert local.name != item['file_name']
    download, downloads = downloader(monkeypatch, incoming)
    view.online.items = [item]
    view.online.origin = SITE_ORIGIN
    view.online.render()
    view.online.table.selectRow(0)
    update_button(view, local).click()
    wait_idle(view, app)

    view.online.table.selectRow(0)
    assert view.online.table.item(0, 3).text() == '已禁用 · v2.0.0'
    assert view.online.rollback_btn.isEnabled()
    view._test_question.assert_not_called()
    confirm = Mock(return_value=QMessageBox.Yes)
    monkeypatch.setattr(QMessageBox, 'question', confirm)
    rollback_names = []
    original_rollback = OnlineInstaller.rollback

    def record_rollback(installer, name):
        rollback_names.append(name)
        return original_rollback(installer, name)

    monkeypatch.setattr(OnlineInstaller, 'rollback', record_rollback)
    view.online.rollback_btn.click()
    wait_idle(view, app)

    assert rollback_names == [local.name]
    assert local.read_bytes() == old_bytes
    assert OnlineInstaller(view.ctx.mm).state()['mods'][local.name]['version'] == '1.0.0'
    assert view.online.table.item(0, 3).text() == '已禁用 · v1.0.0'
    assert not view.online.rollback_btn.isEnabled()
    assert not (view.ctx.mm.data / item['file_name']).exists()
    assert not (view.ctx.mm.disabled_dir / item['file_name']).exists()
    assert view.ctx.busy_events == [True, False, True, False]
    assert confirm.call_count == 1
    assert confirm.call_args.args[1] == '恢复上一版'
    assert download.call_count == 1
    assert downloads and all(not path.exists() for path in downloads)
    view._test_browser.assert_not_called()

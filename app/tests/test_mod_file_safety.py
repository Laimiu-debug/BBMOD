"""Real temporary ZIPs exercise queued writes, Windows file handles, and game checks."""
import hashlib
import threading
import uuid
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from PySide6.QtCore import QObject, Signal
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMessageBox

from core.modmanager import ModManager
from ui.mods_page import ModsPage
from ui.workers import Worker
from ui_wait import refreshed, settle_mods


class Context(QObject):
    management_changed = Signal(bool)
    session_changed = Signal(bool)
    data_changed = Signal()

    def __init__(self, manager, path):
        super().__init__()
        self.mm = manager
        self.management_busy = self.seedgen_active = False
        self.settings = SimpleNamespace(path=path, get=lambda key, default=None: default)

    def set_management_busy(self, active):
        self.management_busy = active
        self.management_changed.emit(active)


def package(path, version):
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, 'w') as archive:
        archive.writestr('scripts/fixture.nut', '// ' + version)
    return path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def wait_until(predicate):
    for _ in range(1500):
        QApplication.processEvents()
        if predicate():
            return
        QTest.qWait(10)
    pytest.fail('Background file operation did not finish')


@pytest.fixture
def view(tmp_path, monkeypatch):
    application = QApplication.instance() or QApplication([])
    manager = ModManager(tmp_path / 'game')
    package(manager.data / 'fixture.zip', '1.0.0')
    running = [False]
    monkeypatch.setattr('core.game.is_game_running', lambda: running[0])
    monkeypatch.setattr('core.online_catalog._request', lambda *_: pytest.fail('Network forbidden'))
    page = ModsPage(Context(manager, tmp_path / 'settings.json'), automatic_catalog=False)
    page._installed_index = {}
    refreshed(page)
    yield page, running
    for worker in page.findChildren(Worker):
        assert worker.wait(15000)
    application.processEvents()
    page.close()
    application.processEvents()


def test_game_started_while_local_operation_queued_keeps_mod_enabled(view, monkeypatch):
    page, running = view
    manager = page.ctx.mm
    entered, gate = threading.Event(), threading.Event()
    original = manager.scan

    def delayed_scan(*args, **kwargs):
        entered.set()
        assert gate.wait(15)
        return original(*args, **kwargs)

    monkeypatch.setattr(manager, 'scan', delayed_scan)
    page.table.selectAll()
    page.refresh()
    assert entered.wait(2)
    try:
        with patch.object(QMessageBox, 'warning') as warning:
            page._on_disable(False)
            assert page._pending_op is not None
            running[0] = True
            gate.set()
            settle_mods(page, timeout=15)
            assert warning.call_count == 1 and '游戏已启动' in warning.call_args.args[2]
        assert (manager.data / 'fixture.zip').exists()
        assert not (manager.disabled_dir / 'fixture.zip').exists()
        assert not manager.transaction.journal.exists()
        assert not page.ctx.management_busy
    finally:
        gate.set()


@pytest.mark.parametrize('start_game', [False, True])
def test_online_update_waits_for_zip_reader_and_rechecks_game(view, tmp_path, monkeypatch, start_game):
    page, running = view
    manager = page.ctx.mm
    local = manager.data / 'fixture.zip'
    old_digest = digest(local)
    archive = package(tmp_path / 'download' / local.name, '2.0.0')
    new_digest = digest(archive)
    identity, release = str(uuid.uuid4()), str(uuid.uuid4())
    item = {'id': identity, 'release_id': release, 'version': '2.0.0', 'file_name': local.name,
            'sha256': new_digest, 'size': archive.stat().st_size,
            'download_path': f'/files/{release}/download/', 'page_path': f'/mods/{identity}/',
            'metadata': {'title': '测试 MOD', 'summary': '', 'description': '', 'category': '其他',
                         'author': 'test', 'game_version': '', 'license': 'original',
                         'mod_ids': [], 'requires': [], 'conflicts': []}}
    entered, gate, downloaded = threading.Event(), threading.Event(), threading.Event()
    import core.modmanager as modmanager
    original = modmanager.analyze_zip
    first = [True]

    def held_reader(path):
        if path == local and first[0]:
            first[0] = False
            with zipfile.ZipFile(path):
                entered.set()
                assert gate.wait(15)
                return original(path)
        return original(path)

    def download(*args, **kwargs):
        downloaded.set()
        return archive

    manager._infos.clear()
    monkeypatch.setattr(modmanager, 'analyze_zip', held_reader)
    monkeypatch.setattr('ui.online_mods.download_release', download)
    page.refresh()
    assert entered.wait(2)
    try:
        page.online.update_installed(item, current_file_name=local.name,
                                     current_sha256=old_digest, installed_version='1.0.0')
        assert downloaded.wait(2)
        assert page.ctx.management_busy and digest(local) == old_digest
        running[0] = start_game
        gate.set()
        wait_until(lambda: page.online.worker is None and page.idle and not page.ctx.management_busy)
        assert digest(local) == (old_digest if start_game else new_digest)
        assert ('游戏已启动' if start_game else '已安装') in page.online.status.text()
        assert not manager.transaction.journal.exists()
    finally:
        gate.set()

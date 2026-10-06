"""Offline UI coverage for browsing, persistent links, and local profile management."""
import io
import threading
import zipfile
from types import SimpleNamespace

import pytest
from PySide6.QtCore import QObject, Signal
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QInputDialog, QMessageBox

from core.modmanager import ModManager
from ui.mods_page import ModsPage
from ui.profiles_page import ProfilesPage

IDENTITY = '00000000-0000-0000-0000-000000000001'
ORIGIN = 'https://bbmod.com'


def zipped(label='test', script=None):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w') as archive:
        archive.writestr(f'scripts/{label}.nut', script or '// ' + label)
    return stream.getvalue()


def catalog_response():
    return {'schema_version': 1, 'page': 1, 'pages': 1, 'total': 1, 'items': [
        {'id': IDENTITY, 'name': '<b>组合</b>', 'note': '新手 & 汉化', 'game_version': '1.5.2.3',
         'mod_count': 1, 'total_size': 100, 'created_at': '2026-09-28T10:00:00+08:00',
         'page_path': f'/profiles/{IDENTITY}/'}]}


class Context(QObject):
    management_changed = Signal(bool)
    session_changed = Signal(bool)
    data_changed = Signal()
    game_changed = Signal()

    def __init__(self, manager):
        super().__init__()
        self.mm = manager
        self.management_busy = self.seedgen_active = False
        self.settings = SimpleNamespace(get=lambda key, default=None: default)

    def set_management_busy(self, active):
        self.management_busy = active
        self.management_changed.emit(active)


@pytest.fixture(scope='module')
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def page(app, tmp_path, monkeypatch):
    manager = ModManager(tmp_path / 'game')
    manager.data.mkdir(parents=True)
    monkeypatch.setattr('core.game.is_game_running', lambda: False)
    ctx = Context(manager)
    mods = ModsPage(ctx)
    view = ProfilesPage(ctx, mods)
    yield view
    for worker in (view.worker, view.sharing.worker):
        if worker:
            worker.wait(3000)
    app.processEvents()
    view.close()
    mods.close()


def settle(app, page):
    for _ in range(300):
        QTest.qWait(10)
        # Thread exit can precede queued finished slots; wait for UI recovery too.
        if page.worker is None and page.refresh_btn.isEnabled():
            app.processEvents()
            return
    pytest.fail('Website list worker did not settle')


def test_website_browse_without_game_copy_and_selected_apply(app, page, monkeypatch):
    calls = []
    monkeypatch.setattr('ui.profiles_page.fetch_profiles', lambda *args: calls.append(args) or catalog_response())
    page.ctx.mm = None
    page.refresh()
    page.open_online()
    settle(app, page)
    assert calls == [(ORIGIN, '', 1)]
    assert page.online_table.rowCount() == 1
    assert '<b>组合</b>' in page.online_details.toPlainText()
    assert page.online_apply_btn.isEnabled()
    page.copy_online_btn.click()
    assert QApplication.clipboard().text() == ORIGIN + f'/profiles/{IDENTITY}/'
    imports = []
    monkeypatch.setattr(page.sharing, 'import_link', lambda identity, origin: imports.append((identity, origin)))
    page.online_apply_btn.click()
    assert imports == [(IDENTITY, ORIGIN)]
    assert not page.ctx.management_busy  # Reading the gallery must not lock local management.


def test_pagination_search_failure_and_retry(app, page, monkeypatch):
    calls = []
    def fetch(origin, query, number):
        calls.append((query, number))
        if query == '断网':
            raise OSError('offline fixture')
        result = catalog_response()
        return {**result, 'page': number, 'pages': 2, 'total': 13}
    monkeypatch.setattr('ui.profiles_page.fetch_profiles', fetch)
    page.open_online()
    settle(app, page)
    assert page.next_btn.isEnabled() and not page.prev_btn.isEnabled()
    page.next_btn.click()
    settle(app, page)
    assert page.catalog_page == 2 and page.prev_btn.isEnabled()
    page.search.setText('汉化')
    page.prev_btn.click()
    settle(app, page)
    assert calls[-1] == ('汉化', 1)
    page.search.setText('断网')
    page.refresh_btn.click()
    settle(app, page)
    assert 'offline fixture' in page.status_label.text()
    assert page.online_table.rowCount() == 0 and not page.online_apply_btn.isEnabled()
    assert page.refresh_btn.isEnabled()
    page.search.clear()
    page.refresh_btn.click()
    settle(app, page)
    assert page.online_table.rowCount() == 1


def test_source_change_discards_inflight_response(app, page, monkeypatch):
    release = threading.Event()
    monkeypatch.setattr('ui.profiles_page.fetch_profiles', lambda *_: release.wait(2) and catalog_response())
    page.open_online()
    page.mods.online.address.setText('https://other.example')
    release.set()
    settle(app, page)
    assert not page.rows and not page.catalog_loaded
    assert '来源已更改' in page.page_label.text()
    assert not page.copy_online_btn.isEnabled()


def test_local_rename_delete_save_and_share_link_persist(app, page, monkeypatch):
    manager = page.ctx.mm
    original = zipped()
    (manager.data / 'mod.zip').write_bytes(original)
    manager.save_profile('组合')
    monkeypatch.setattr(QMessageBox, 'information', lambda *_: QMessageBox.Ok)
    monkeypatch.setattr(QMessageBox, 'question', lambda *_: QMessageBox.Yes)
    page.sharing._shared(ORIGIN + f'/profiles/{IDENTITY}/', manager, '组合', ORIGIN)
    page.copy_local_btn.click()
    assert QApplication.clipboard().text() == ORIGIN + f'/profiles/{IDENTITY}/'
    monkeypatch.setattr(QInputDialog, 'getText', lambda *_, **__: ('新名称', True))
    page.rename_btn.click()
    assert list(manager.load_profiles()) == ['新名称']
    page.refresh()
    assert page.copy_local_btn.isEnabled()
    page.delete_btn.click()
    assert manager.load_profiles() == {}
    assert (manager.data / 'mod.zip').read_bytes() == original
    page.save_btn.click()
    assert manager.load_profiles()['新名称']['enabled'] == ['mod.zip']
    assert not page.copy_local_btn.isEnabled()


def test_busy_pending_recovery_and_cancel_do_not_change_files(app, page, monkeypatch):
    manager = page.ctx.mm
    (manager.data / 'mod.zip').write_bytes(zipped())
    manager.save_profile('组合')
    page.refresh()
    page.ctx.set_management_busy(True)
    assert not page.delete_btn.isEnabled() and not page.share_btn.isEnabled()
    assert not page.import_link_btn.isEnabled()
    page.ctx.set_management_busy(False)
    monkeypatch.setattr(QMessageBox, 'question', lambda *_: QMessageBox.No)
    page.delete_btn.click()
    assert '组合' in manager.load_profiles()
    manager.transaction.journal.parent.mkdir(parents=True, exist_ok=True)
    manager.transaction.journal.write_text('{}')
    page.refresh()
    assert not page.apply_btn.isEnabled() and not page.save_btn.isEnabled()


def test_armory_import_opens_website_profiles(page):
    destinations = []
    page.mods.profiles_requested.connect(destinations.append)
    page.mods.import_profile_btn.click()
    page.mods.manage_profiles_btn.click()
    assert destinations == [True, False]


def test_local_apply_previews_changes_and_cancel_preserves_state(page, monkeypatch):
    manager = page.ctx.mm
    (manager.data / 'wanted.zip').write_bytes(zipped('wanted'))
    manager.save_profile('组合')
    manager.disabled_dir.mkdir(exist_ok=True)
    (manager.data / 'wanted.zip').rename(manager.disabled_dir / 'wanted.zip')
    (manager.data / 'extra.zip').write_bytes(zipped('extra'))
    page.refresh()
    previews = []
    def cancel(*args):
        previews.append(args[3])
        return False
    monkeypatch.setattr('ui.profiles_page.preview_dialog', cancel)
    page.apply_local()
    assert 'wanted.zip' in previews[0] and 'extra.zip' in previews[0]
    assert manager.installed_zip_names() == {'extra.zip'}
    monkeypatch.setattr('ui.profiles_page.preview_dialog', lambda *_: True)
    page.apply_local()
    assert manager.installed_zip_names() == {'wanted.zip'}
    assert (manager.disabled_dir / 'extra.zip').exists()
    assert '已应用' in page.status_label.text()


def test_saved_import_uses_pinned_website_after_rename(page, monkeypatch):
    from core.mod_transactions import atomic_json
    manager = page.ctx.mm
    atomic_json(manager._profiles_path(), {'自定名称': {'enabled': ['missing.zip'],
        'shared_id': IDENTITY, 'shared_origin': ORIGIN}})
    page.refresh()
    calls = []
    monkeypatch.setattr(page.sharing, 'import_link', lambda value, origin: calls.append((value, origin)))
    page.apply_local()
    assert calls == [(IDENTITY, ORIGIN)]

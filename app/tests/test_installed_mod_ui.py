"""Installed MOD labels and update actions use isolated files and no network."""
import hashlib
import os
import zipfile
from types import SimpleNamespace

import pytest
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication

from core.modmanager import ModManager
from core.site_config import SITE_ORIGIN
from ui.mods_page import ModsPage


IDENTITY = '00000000-0000-0000-0000-000000000001'


class Context(QObject):
    management_changed = Signal(bool)
    session_changed = Signal(bool)
    data_changed = Signal()

    def __init__(self, manager):
        super().__init__()
        self.mm = manager
        self.management_busy = self.seedgen_active = False
        self.settings = SimpleNamespace(get=lambda key, default=None: default)


def archive(path, version='1.0.0', mod_id='mod_fixture', name='English fixture'):
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, 'w') as package:
        package.writestr('scripts/!mods_preload/fixture.nut',
                         f'::Hooks.register("{mod_id}", "{version}", "{name}");')
    return path


def catalog(*, version='1.1.0', title='中文测试 MOD', file_name='fixture.zip'):
    return {'id': IDENTITY, 'version': version, 'file_name': file_name,
            'sha256': 'b' * 64, 'page_path': f'/mods/{IDENTITY}/',
            'metadata': {'title': title, 'mod_ids': ['mod_fixture']}}


def hashes(path):
    stat = path.stat()
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return {str(path.resolve()): (stat.st_mtime_ns, stat.st_size, digest)}


@pytest.fixture(scope='module')
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def page(app, tmp_path):
    manager = ModManager(tmp_path / 'game')
    manager.data.mkdir(parents=True)
    view = ModsPage(Context(manager))
    yield view
    view.close()
    app.processEvents()


def test_offline_chinese_names_versions_and_id_search(page):
    archive(page.ctx.mm.data / 'fixture.zip')
    archive(page.ctx.mm.disabled_dir / 'other.zip', mod_id='mod_other', name='另一 MOD')
    page._installed_index = {'fixture.zip': {'name_cn': '离线中文 MOD', 'mod_ids': ['mod_fixture']}}
    page.refresh()
    assert page.table.item(0, 2).text() == '离线中文 MOD'
    assert page.table.item(0, 3).text() == '1.0.0'
    assert page.table.item(0, 4).text() == '—'
    assert page.table.cellWidget(0, 5) is None
    assert page.table.item(0, 6).text() == 'modern'
    assert 'English fixture' in page.table.item(0, 2).toolTip()
    for query in ('离线中文', 'mod_fixture', 'fixture.zip', 'English fixture'):
        page.installed_search.setText(query)
        assert not page.table.isRowHidden(0)
        assert page.table.isRowHidden(1)
    page.installed_search.clear()
    page.state_filter.setCurrentText('已禁用')
    page.table.selectAll()
    assert page._selected_mods() == [('other.zip', False)]


def test_catalog_refresh_preserves_selection_and_update_uses_real_file(page, monkeypatch):
    installed = archive(page.ctx.mm.disabled_dir / 'renamed-by-user.zip')
    page.refresh()
    page.table.selectRow(0)
    monkeypatch.setattr(page.ctx.mm, 'scan', lambda *args, **kwargs: pytest.fail('catalog labels must not rescan ZIPs'))
    item = catalog()
    verified = hashes(installed)
    page.set_installed_catalog([item], hashes=verified)
    assert page.table.item(0, 2).text() == '中文测试 MOD'
    assert page.table.item(0, 3).text() == '1.0.0'
    assert page.table.item(0, 4).text() == '1.1.0'
    assert page._selected_mods() == [('renamed-by-user.zip', False)]
    calls = []
    monkeypatch.setattr(page.online, 'update_installed',
                        lambda target, **kwargs: calls.append((target, kwargs)), raising=False)
    button = page.table.cellWidget(0, 5)
    assert button and button.text() == '更新' and button.isEnabled()
    button.click()
    assert calls == [(item, {'origin': SITE_ORIGIN, 'current_file_name': installed.name,
                            'current_sha256': verified[str(installed.resolve())][2],
                            'installed_version': '1.0.0'})]
    assert installed.exists() and not (page.ctx.mm.data / 'fixture.zip').exists()
    page.set_installed_catalog([catalog(version='1.0.0')], hashes=verified)
    assert page.table.cellWidget(0, 5) is None
    assert page._selected_mods() == [('renamed-by-user.zip', False)]


def test_update_buttons_follow_management_seed_and_pending_locks(page):
    installed = archive(page.ctx.mm.data / 'fixture.zip')
    page.refresh()
    page.set_installed_catalog([catalog()])
    button = page.table.cellWidget(0, 5)
    assert button and not button.isEnabled()  # File identity is verified before a direct update.
    page.set_installed_catalog([catalog()], hashes=hashes(installed))
    button = page.table.cellWidget(0, 5)
    assert button and button.isEnabled()
    for field in ('management_busy', 'seedgen_active'):
        setattr(page.ctx, field, True)
        page.update_controls()
        assert not button.isEnabled()
        setattr(page.ctx, field, False)
    page.ctx.mm.transaction.journal.parent.mkdir(parents=True, exist_ok=True)
    page.ctx.mm.transaction.journal.write_text('{}', encoding='utf-8')
    page.update_controls()
    assert not button.isEnabled()
    page.ctx.mm.transaction.journal.unlink()
    page.online.worker = SimpleNamespace(isRunning=lambda: True)
    page.update_controls()
    assert not button.isEnabled()
    page.online.worker = None
    page.update_controls()
    assert button.isEnabled()


def test_changed_archive_cannot_reuse_cached_release_hash(page):
    installed = archive(page.ctx.mm.data / 'fixture.zip', version='62')
    page.refresh()
    verified = hashes(installed)
    digest = verified[str(installed.resolve())][2]
    page.set_installed_catalog([catalog(version='0.28.12')], hashes=verified,
                               release_versions={IDENTITY: {digest: '0.28.11'}})
    assert page.table.item(0, 3).text() == '0.28.11'
    assert page.table.cellWidget(0, 5) is not None
    installed.write_bytes(installed.read_bytes() + b'changed externally')
    page.refresh_installed_metadata()
    assert page.table.item(0, 3).text() == '62'
    assert page.table.cellWidget(0, 5) is None
    assert page.table.item(0, 4).toolTip() == '官网版本：0.28.12\n版本待确认'


def test_replacement_with_same_size_and_timestamp_invalidates_verified_identity(page, tmp_path):
    installed = archive(page.ctx.mm.data / 'fixture.zip', version='62')
    page.refresh()
    info = page._installed_mods[0].info
    stat = installed.stat()
    digest = hashlib.sha256(installed.read_bytes()).hexdigest()
    verified = {str(installed.resolve()): (stat.st_mtime_ns, stat.st_size, digest, stat.st_dev, stat.st_ino)}
    page.set_installed_catalog([catalog(version='0.28.12')], hashes=verified,
                               release_versions={IDENTITY: {digest: '0.28.11'}})
    assert page._installed_hash(info) == digest
    replacement = archive(tmp_path / 'replacement.zip', version='63')
    os.replace(replacement, installed)
    os.utime(installed, ns=(stat.st_atime_ns, stat.st_mtime_ns))
    assert installed.stat().st_size == stat.st_size
    assert page._installed_hash(info) is None
    page.refresh_installed_metadata()
    assert page.table.cellWidget(0, 5) is None

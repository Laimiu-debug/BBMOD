import hashlib
import json
import os
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from PySide6.QtWidgets import QApplication

from core.installed_mod_catalog import resolve_installed_mod
from core.modinfo import ModInfo, Registration
from core.online_catalog import parse_catalog
from core.site_config import SITE_ORIGIN
from ui.installed_catalog_service import InstalledCatalogService


WORK = '00000000-0000-0000-0000-000000000001'
RELEASE = '00000000-0000-0000-0000-000000000002'


class Signal:
    def __init__(self):
        self.slots = []

    def connect(self, slot):
        self.slots.append(slot)

    def emit(self, *args):
        for slot in self.slots:
            slot(*args)


class ImmediateWorker:
    """Exercise the real work closure synchronously with no live background job."""
    def __init__(self, fn, parent=None):
        self.fn, self.running = fn, False
        self.done, self.failed, self.finished = Signal(), Signal(), Signal()

    def isRunning(self):
        return self.running

    def start(self):
        self.running = True
        try:
            self.done.emit(self.fn())
        except Exception as error:
            self.failed.emit(str(error))
        finally:
            self.running = False
            self.finished.emit()


@pytest.fixture(scope='module')
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def service(app, tmp_path, monkeypatch):
    monkeypatch.setattr('ui.installed_catalog_service.Worker', ImmediateWorker)
    monkeypatch.setattr('ui.installed_catalog_service.fetch_catalog', Mock(side_effect=TimeoutError('offline')))
    monkeypatch.setattr('ui.installed_catalog_service.identify_release_versions', Mock(side_effect=TimeoutError('offline')))
    return InstalledCatalogService(SimpleNamespace(path=tmp_path / 'settings.json'))


def catalog(*, name='fixture.zip', version='0.28.14', sha='b' * 64, ids=('mod_fixture',)):
    return parse_catalog({'schema_version': 1, 'mods': [{
        'id': WORK, 'release_id': RELEASE, 'version': version, 'file_name': name,
        'size': 123, 'sha256': sha, 'page_path': f'/mods/{WORK}/',
        'download_path': f'/files/{RELEASE}/download/',
        'metadata': {'title': '中文测试 MOD', 'summary': 'test', 'description': 'test',
                     'category': '其他', 'author': 'test', 'game_version': '1.5.2.3',
                     'license': 'original', 'mod_ids': list(ids), 'requires': [], 'conflicts': []}}]})[0]


def info(tmp_path, *, name='fixture.zip', ids=('mod_fixture',), content=b'old archive'):
    path = tmp_path / name
    path.write_bytes(content)
    result = ModInfo(path, name)
    result.registrations = [Registration(ident, '62', 'Fixture', 'legacy') for ident in ids]
    return result


def digest(value):
    return hashlib.sha256(value).hexdigest()


def test_valid_offline_cache_keeps_catalog_history_and_filters_invalid_checksums(app, tmp_path):
    item = catalog()
    path = tmp_path / 'installed-mod-catalog.json'
    path.write_text(json.dumps({'schema_version': 1, 'origin': SITE_ORIGIN,
                               'mods': [item], 'checked_at': 123,
                               'release_versions': {WORK: {'a' * 64: '0.28.12', 'bad': 'invalid'}}}), 'utf-8')
    service = InstalledCatalogService(SimpleNamespace(path=tmp_path / 'settings.json'))
    assert service.items == [item]
    assert service.release_versions == {WORK: {'a' * 64: '0.28.12'}}
    assert service.checked_at == 123 and service.hashes == {}


@pytest.mark.parametrize('origin', ['https://foreign.example', None])
def test_foreign_or_missing_cache_origin_is_not_used(app, tmp_path, origin):
    (tmp_path / 'installed-mod-catalog.json').write_text(
        json.dumps({'schema_version': 1, 'origin': origin, 'mods': [catalog()]}), 'utf-8')
    service = InstalledCatalogService(SimpleNamespace(path=tmp_path / 'settings.json'))
    assert service.items == [] and service.release_versions == {}


def test_offline_refresh_preserves_and_saves_existing_catalog(service):
    item = catalog()
    service.use_catalog([item])
    service.release_versions = {WORK: {'a' * 64: '0.28.12'}}
    results = []
    service.changed.connect(results.append)
    service.check([], force=True)
    assert service.items == [item]
    assert service.release_versions == {WORK: {'a' * 64: '0.28.12'}}
    assert '保留已有目录' in results[-1]['status']
    saved = json.loads(service.path.read_text('utf-8'))
    assert saved['origin'] == SITE_ORIGIN and saved['mods'] == [item]
    assert saved['release_versions'] == service.release_versions


def test_check_identifies_old_manual_archive_by_hash_without_changing_file(service, tmp_path, monkeypatch):
    local = info(tmp_path)
    old_sha = digest(local.path.read_bytes())
    item = catalog()
    fetch = Mock(return_value=[item])
    identify = Mock(return_value={old_sha: '0.28.12', item['sha256']: item['version']})
    monkeypatch.setattr('ui.installed_catalog_service.fetch_catalog', fetch)
    monkeypatch.setattr('ui.installed_catalog_service.identify_release_versions', identify)
    service.check([local], force=True, local_index={})
    cached = service.hashes[str(local.path.resolve())]
    assert cached[2] == old_sha and len(cached) == 5
    result = resolve_installed_mod(local, service.items, local_sha256=cached[2],
                                   release_versions=service.release_versions, local_index={})
    assert result.installed_version == '0.28.12' and result.update_available
    fetch.assert_called_once_with(SITE_ORIGIN)
    identify.assert_called_once()
    assert identify.call_args.args[:3] == (SITE_ORIGIN, item, old_sha)
    assert local.path.read_bytes() == b'old archive'


def test_fresh_catalog_and_unchanged_archive_reuse_cached_hash_and_version(service, tmp_path, monkeypatch):
    local = info(tmp_path)
    item = catalog(sha=digest(local.path.read_bytes()))
    service.use_catalog([item])
    fetch, history = Mock(), Mock()
    monkeypatch.setattr('ui.installed_catalog_service.fetch_catalog', fetch)
    monkeypatch.setattr('ui.installed_catalog_service.identify_release_versions', history)
    service.check([local], local_index={})
    first = service.hashes.copy()
    monkeypatch.setattr('ui.installed_catalog_service.hashlib.file_digest',
                        lambda *_: pytest.fail('unchanged archives should reuse verified hashes'))
    service.check([local], local_index={})
    assert service.hashes == first
    fetch.assert_not_called()
    history.assert_not_called()


def test_changed_archive_cannot_use_prior_hash_during_an_unstable_read(service, tmp_path, monkeypatch):
    local = info(tmp_path)
    item = catalog(sha=digest(local.path.read_bytes()))
    service.use_catalog([item])
    service.check([local], local_index={})
    key = str(local.path.resolve())
    assert service.hashes[key]
    local.path.write_bytes(b'external update')
    original = hashlib.file_digest
    def changed(stream, algorithm):
        value = original(stream, algorithm)
        local.path.write_bytes(b'changed again during file read')
        return value
    monkeypatch.setattr('ui.installed_catalog_service.hashlib.file_digest', changed)
    history = Mock()
    monkeypatch.setattr('ui.installed_catalog_service.identify_release_versions', history)
    service.check([local], local_index={})
    assert service.hashes[key] is None
    result = resolve_installed_mod(local, service.items, local_index={})
    assert result.installed_version == '62' and result.status == '版本待确认'
    history.assert_not_called()


def test_replaced_file_with_same_time_and_size_is_rehashed(service, tmp_path, monkeypatch):
    local = info(tmp_path, content=b'first')
    item = catalog(sha=digest(b'first'))
    service.use_catalog([item])
    service.check([local], local_index={})
    old_stat = local.path.stat()
    replacement = tmp_path / 'replacement.zip'
    replacement.write_bytes(b'other')
    os.utime(replacement, ns=(old_stat.st_atime_ns, old_stat.st_mtime_ns))
    os.replace(replacement, local.path)
    history = Mock(return_value={digest(b'first'): '0.28.14', digest(b'other'): '0.28.12'})
    monkeypatch.setattr('ui.installed_catalog_service.identify_release_versions', history)
    service.check([local], local_index={})
    assert service.hashes[str(local.path.resolve())][2] == digest(b'other')
    history.assert_called_once()


def test_missing_file_invalidates_hash_and_does_not_check_history(service, tmp_path, monkeypatch):
    local = info(tmp_path)
    item = catalog(sha=digest(local.path.read_bytes()))
    service.use_catalog([item])
    service.check([local], local_index={})
    local.path.unlink()
    history = Mock()
    monkeypatch.setattr('ui.installed_catalog_service.identify_release_versions', history)
    service.check([local], local_index={})
    assert service.hashes[str(local.path.resolve())] is None
    history.assert_not_called()


def test_trusted_receipt_identifies_renamed_resource_package_after_hash(service, tmp_path, monkeypatch):
    local = info(tmp_path, name='renamed-resource.zip', ids=())
    sha = digest(local.path.read_bytes())
    item = catalog(name='official-resource.zip', ids=())
    records = {local.file_name: {'id': item['id'], 'origin': SITE_ORIGIN,
                               'sha256': sha, 'version': '0.28.12'}}
    service.use_catalog([item])
    service.check([local], receipts=records, local_index={})
    cached = service.hashes[str(local.path.resolve())]
    result = resolve_installed_mod(local, service.items, receipts=records,
                                   local_sha256=cached[2], local_index={})
    assert result.catalog_item == item and result.installed_version == '0.28.12'
    assert result.update_available


def test_unrelated_archive_and_foreign_receipt_do_not_trigger_hash_or_history(service, tmp_path, monkeypatch):
    local = info(tmp_path, name='unrelated.zip', ids=())
    item = catalog()
    service.use_catalog([item])
    records = {local.file_name: {'id': item['id'], 'origin': 'https://foreign.example',
                               'sha256': digest(local.path.read_bytes()), 'version': '0.28.12'}}
    monkeypatch.setattr('ui.installed_catalog_service.hashlib.file_digest',
                        lambda *_: pytest.fail('foreign receipts must not identify unrelated files'))
    service.check([local], receipts=records, local_index={})
    assert service.hashes == {}


def test_pending_check_retains_receipt_and_local_index_arguments(service, tmp_path, monkeypatch):
    local = info(tmp_path)
    records, index = {'record': {}}, {'fixture.zip': {'name_cn': '离线名称'}}
    service.worker = SimpleNamespace(isRunning=lambda: True)
    service.check([local], force=True, receipts=records, local_index=index)
    resume = Mock()
    monkeypatch.setattr(service, 'check', resume)
    service._finished()
    resume.assert_called_once_with([local], force=True, receipts=records, local_index=index)
    assert service._pending is None

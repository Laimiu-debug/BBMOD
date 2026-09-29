import copy
import hashlib
import io
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import zipfile

import pytest

from core.modmanager import ModManager
from core.mod_transactions import digest, atomic_json
from core.profile_protocol import validate_manifest
from core import shared_profiles as sharing

IDENTITY = '00000000-0000-0000-0000-000000000001'
ORIGIN = 'https://bbmod.site'


def zipped(label='test', script=None):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w') as archive:
        archive.writestr(f'scripts/{label}.nut', script or '// ' + label)
    return stream.getvalue()


def manifest(files):
    return validate_manifest({'schema_version': 1, 'name': '共享组合', 'game_version': '1.5.2.3',
        'mods': [{'file_name': name, 'sha256': hashlib.sha256(data).hexdigest(), 'size': len(data)}
                 for name, data in files.items()]})


@pytest.fixture
def manager(tmp_path, monkeypatch):
    root = tmp_path / 'game'
    (root / 'data').mkdir(parents=True)
    (root / 'data/data_001.dat').write_bytes(b'official')
    monkeypatch.setattr('core.game.is_game_running', lambda: False)
    return ModManager(root)


def mock_site(monkeypatch, value, files, downloads=None):
    monkeypatch.setattr(sharing, 'fetch_profile', lambda *_: copy.deepcopy(value))
    def download(origin, identity, item, destination):
        if downloads is not None:
            downloads.append(item['file_name'])
        destination.write_bytes(files[item['file_name']])
    monkeypatch.setattr(sharing, '_download', download)


def test_shared_localization_uses_package_name_and_version(manager):
    from core.l10n import BRAND_META, PACKAGE_ID
    from core.l10n_compat import write_hooks
    with zipfile.ZipFile(manager.data / 'custom.zip', 'w') as archive:
        write_hooks(archive)
        archive.writestr(BRAND_META, json.dumps({'package_id': PACKAGE_ID, 'version': '0.3.0-rc.9'}))
    manager.save_profile('汉化')
    item = sharing.prepare_share(manager, '汉化')['manifest']['mods'][0]
    assert item['title'] == 'BBMOD 独立汉化'
    assert item['version'] == '0.3.0-rc.9'


def test_download_only_missing_reuses_disabled_bytes_and_saves_full_scheme(manager, monkeypatch):
    files = {'a.zip': zipped('a'), 'b.zip': zipped('b')}
    value = manifest(files)
    manager.disabled_dir.mkdir()
    (manager.disabled_dir / 'a.zip').write_bytes(files['a.zip'])
    (manager.data / 'old.zip').write_bytes(zipped('old'))
    calls = []
    mock_site(monkeypatch, value, files, calls)
    plan = sharing.preview_apply(manager, value)
    assert plan['download'] == ['b.zip']
    result = sharing.apply_shared(manager, ORIGIN, IDENTITY, value, expected=plan)
    assert calls == ['b.zip']
    assert manager.installed_zip_names() == {'a.zip', 'b.zip'}
    assert (manager.disabled_dir / 'old.zip').is_file()
    assert not (manager.disabled_dir / 'a.zip').exists()
    assert manager.load_profiles()[result['name']]['enabled'] == ['a.zip', 'b.zip']
    assert (manager.data / 'data_001.dat').read_bytes() == b'official'
    assert (Path(result['backup']) / 'completed.json').exists()


def test_same_filename_new_content_replaced_and_old_bytes_backed_up(manager, monkeypatch):
    old = zipped('old')
    (manager.data / 'mod.zip').write_bytes(old)
    manager.save_profile('共享组合')
    original_profile = manager.load_profiles()['共享组合']
    atomic_json(manager.disabled_dir / 'online-catalog.json', {'mods': {'mod.zip': {'sha256': digest(manager.data / 'mod.zip'), 'version': 'old'}}})
    files = {'mod.zip': zipped('new')}
    value = manifest(files)
    mock_site(monkeypatch, value, files)
    plan = sharing.preview_apply(manager, value)
    assert plan['download'] == ['mod.zip']
    result = sharing.apply_shared(manager, ORIGIN, IDENTITY, value, expected=plan)
    assert (manager.data / 'mod.zip').read_bytes() == files['mod.zip']
    assert manager.load_profiles()['共享组合'] == original_profile
    assert result['name'] == '共享组合（共享 2）'
    assert old in [p.read_bytes() for p in Path(result['backup']).glob('*.before')]
    assert json.loads((manager.disabled_dir / 'online-catalog.json').read_text()) == {'mods': {}}


def test_renamed_identical_file_is_reused_without_network(manager, monkeypatch):
    data = zipped()
    (manager.data / 'old_name.zip').write_bytes(data)
    value = manifest({'new_name.zip': data})
    monkeypatch.setattr(sharing, 'fetch_profile', lambda *_: value)
    monkeypatch.setattr(sharing, '_download', lambda *_: pytest.fail('must reuse bytes'))
    plan = sharing.preview_apply(manager, value)
    assert plan['download'] == []
    sharing.apply_shared(manager, ORIGIN, IDENTITY, value, expected=plan)
    assert manager.installed_zip_names() == {'new_name.zip'}


@pytest.mark.parametrize('failure', ['download', 'checksum', 'compatibility', 'running', 'changed'])
def test_failure_before_commit_never_changes_game(manager, monkeypatch, failure):
    existing = manager.data / 'existing.zip'
    existing.write_bytes(zipped('existing'))
    manager.save_profile('original')
    before = manager.load_profiles()
    files = {'new.zip': zipped('new')}
    if failure == 'compatibility':
        files['new.zip'] = zipped('new', '::Hooks.register("mod_new", "1.0.0", "New").require("mod_missing");')
    value = manifest(files)
    mock_site(monkeypatch, value, files)
    plan = sharing.preview_apply(manager, value)
    if failure == 'download':
        monkeypatch.setattr(sharing, '_download', lambda *_: (_ for _ in ()).throw(OSError('offline')))
    elif failure == 'checksum':
        files['new.zip'] = zipped('corrupt_version')
    elif failure == 'running':
        monkeypatch.setattr('core.game.is_game_running', lambda: True)
    elif failure == 'changed':
        (manager.data / 'other.zip').write_bytes(zipped('other'))
    with pytest.raises((ValueError, OSError)):
        sharing.apply_shared(manager, ORIGIN, IDENTITY, value, expected=plan)
    assert existing.exists()
    assert not (manager.data / 'new.zip').exists()
    assert manager.load_profiles() == before
    assert not manager.transaction.journal.exists()


@pytest.mark.parametrize('interrupt', [False, True])
def test_metadata_commit_failure_or_interruption_recovers_whole_collection(manager, monkeypatch, interrupt):
    current = manager.data / 'current.zip'
    current.write_bytes(zipped('current'))
    manager.save_profile('original')
    before = manager.load_profiles()
    files = {'new.zip': zipped('new')}
    value = manifest(files)
    mock_site(monkeypatch, value, files)
    plan = sharing.preview_apply(manager, value)
    import os
    replace = os.replace
    def fail(source, destination):
        if Path(destination) == manager._profiles_path() and str(source).endswith('.after'):
            if interrupt:
                raise KeyboardInterrupt('power loss')
            raise PermissionError('disk locked')
        return replace(source, destination)
    with patch('core.mod_transactions.os.replace', side_effect=fail):
        with pytest.raises(KeyboardInterrupt if interrupt else PermissionError):
            sharing.apply_shared(manager, ORIGIN, IDENTITY, value, expected=plan)
    if interrupt:
        assert manager.transaction.journal.exists()
        ModManager(manager.root).transaction.recover()
    assert current.exists()
    assert not (manager.data / 'new.zip').exists()
    assert manager.load_profiles() == before


def test_during_download_external_change_is_not_overwritten(manager, monkeypatch):
    path = manager.data / 'current.zip'
    path.write_bytes(zipped('current'))
    files = {'new.zip': zipped('new')}
    value = manifest(files)
    mock_site(monkeypatch, value, files)
    def download(origin, identity, item, destination):
        destination.write_bytes(files['new.zip'])
        path.write_bytes(zipped('external'))
    monkeypatch.setattr(sharing, '_download', download)
    with pytest.raises(ValueError, match='下载期间'):
        sharing.apply_shared(manager, ORIGIN, IDENTITY, value, expected=sharing.preview_apply(manager, value))
    assert path.read_bytes() == zipped('external')
    assert not (manager.data / 'new.zip').exists()


def test_recovery_and_duplicate_names_block_apply(manager):
    value = manifest({'mod.zip': zipped()})
    (manager.data / 'mod.zip').write_bytes(zipped())
    manager.disabled_dir.mkdir()
    (manager.disabled_dir / 'mod.zip').write_bytes(zipped())
    with pytest.raises(ValueError, match='同名'):
        sharing.preview_apply(manager, value)
    manager.transaction.directory.mkdir(parents=True)
    manager.transaction.journal.write_text('{}')
    with pytest.raises(ValueError, match='恢复'):
        sharing.preview_apply(manager, value)


def test_publishing_uploads_only_missing_hashes_once(monkeypatch, tmp_path):
    a, b = zipped('a'), zipped('b')
    value = manifest({'a.zip': a, 'b.zip': b, 'b_alias.zip': b})
    paths = {}
    for item in value['mods']:
        path = tmp_path / item['file_name']
        path.write_bytes(a if item['file_name'] == 'a.zip' else b)
        paths[item['sha256']] = path
    prepared = {'manifest': value, 'sources': paths}
    rows = [{'file_name': m['file_name'], 'sha256': m['sha256'], 'status': 'available' if m['file_name'] == 'a.zip' else 'missing', 'ticket': 'test'} for m in value['mods']]
    monkeypatch.setattr(sharing, 'negotiate', lambda *_: rows)
    uploaded = []
    monkeypatch.setattr(sharing, '_upload', lambda origin, item, ticket, path: uploaded.append(item['sha256']))
    monkeypatch.setattr(sharing, '_json', lambda *_: {'id': IDENTITY, 'page_path': f'/profiles/{IDENTITY}/'})
    assert sharing.publish_share(ORIGIN, prepared) == f'{ORIGIN}/profiles/{IDENTITY}/'
    assert uploaded == [hashlib.sha256(b).hexdigest()]


@pytest.mark.parametrize('value', ['https://evil.example/profiles/' + IDENTITY, '../' + IDENTITY,
    'bbmod://profiles/' + IDENTITY + '?url=https://evil.example', 'bbmod://mods/' + IDENTITY])
def test_external_or_malformed_links_cannot_redirect_downloads(value):
    with pytest.raises(ValueError):
        sharing.profile_identity(value, ORIGIN)


def test_web_link_roundtrip_and_literal_ui_text():
    from core.web_links import parse_link
    assert parse_link('bbmod://profiles/' + IDENTITY) == ('profiles', IDENTITY)
    assert sharing.profile_identity(f'{ORIGIN}/profiles/{IDENTITY}/', ORIGIN) == IDENTITY


def test_profile_rename_delete_preserve_files_and_share_receipt(manager):
    (manager.data / 'mod.zip').write_bytes(zipped())
    manager.save_profile('原组合')
    manager.record_profile_share('原组合', ORIGIN, IDENTITY)
    receipt = manager.load_profiles()['原组合']
    assert receipt['published_id'] == IDENTITY
    assert 'shared_id' not in receipt  # Publishing does not turn a local profile into an import.
    manager.save_profile('已有组合')
    with pytest.raises(ValueError, match='同名'):
        manager.rename_profile('原组合', '已有组合')
    manager.rename_profile('原组合', '新的组合')
    assert manager.load_profiles()['新的组合'] == receipt
    manager.delete_profile('新的组合')
    assert list(manager.load_profiles()) == ['已有组合']
    assert (manager.data / 'mod.zip').read_bytes() == zipped()


def test_profile_edits_stop_during_pending_recovery(manager):
    manager.save_profile('原组合')
    manager.transaction.journal.parent.mkdir(parents=True, exist_ok=True)
    manager.transaction.journal.write_text('{}')
    for action in (lambda: manager.save_profile('新组合'), lambda: manager.rename_profile('原组合', '新组合'),
                   lambda: manager.delete_profile('原组合'), lambda: manager.record_profile_share('原组合', ORIGIN, IDENTITY)):
        with pytest.raises(ValueError, match='恢复'):
            action()
    assert list(manager.load_profiles()) == ['原组合']


def test_renamed_import_reapply_keeps_local_name_and_receipt(manager, monkeypatch):
    files = {'mod.zip': zipped()}
    value = manifest(files)
    mock_site(monkeypatch, value, files)
    sharing.apply_shared(manager, ORIGIN, IDENTITY, value, expected=sharing.preview_apply(manager, value))
    manager.rename_profile(value['name'], '我的名称')
    manager.record_profile_share('我的名称', ORIGIN, IDENTITY)
    result = sharing.apply_shared(manager, ORIGIN, IDENTITY, value, expected=sharing.preview_apply(manager, value))
    assert result['name'] == '我的名称'
    assert list(manager.load_profiles()) == ['我的名称']
    assert manager.load_profiles()['我的名称']['published_id'] == IDENTITY


def catalog_response():
    return {'schema_version': 1, 'page': 1, 'pages': 1, 'total': 1, 'items': [
        {'id': IDENTITY, 'name': '<b>组合</b>', 'note': '新手 & 汉化', 'game_version': '1.5.2.3',
         'mod_count': 1, 'total_size': 100, 'created_at': '2026-09-28T10:00:00+08:00',
         'page_path': f'/profiles/{IDENTITY}/'}]}


def test_catalog_encodes_search_and_keeps_untrusted_text_literal(monkeypatch):
    calls = []
    monkeypatch.setattr(sharing, '_json', lambda origin, path: calls.append((origin, path)) or catalog_response())
    result = sharing.fetch_profiles(ORIGIN, '新手 & 汉化', 2)
    assert result['items'][0]['name'] == '<b>组合</b>'
    from urllib.parse import parse_qs, urlsplit
    assert parse_qs(urlsplit(calls[0][1]).query) == {'q': ['新手 & 汉化'], 'page': ['2']}


@pytest.mark.parametrize('change', [lambda r: r.update(schema_version=2), lambda r: r.update(page=True),
    lambda r: r.update(items='bad'), lambda r: r['items'][0].update(page_path='https://evil.example/'),
    lambda r: r['items'][0].update(id=None), lambda r: r['items'][0].update(total_size=-1),
    lambda r: r['items'][0].update(mod_count=True), lambda r: r['items'].append(r['items'][0])])
def test_catalog_rejects_invalid_responses(monkeypatch, change):
    response = catalog_response()
    change(response)
    monkeypatch.setattr(sharing, '_json', lambda *_: response)
    with pytest.raises(ValueError):
        sharing.fetch_profiles(ORIGIN)


def test_share_cancel_and_busy_controls(manager, monkeypatch):
    from PySide6.QtCore import QObject, Signal
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication, QInputDialog
    from ui.mods_page import ModsPage
    from ui import profile_sharing as ui
    class Context(QObject):
        management_changed = Signal(bool)
        session_changed = Signal(bool)
        data_changed = Signal()
        def __init__(self):
            super().__init__()
            self.mm = manager
            self.management_busy = self.seedgen_active = False
            self.settings = SimpleNamespace(get=lambda key, default=None: default)
        def set_management_busy(self, active):
            self.management_busy = active
            self.management_changed.emit(active)
    app = QApplication.instance() or QApplication([])
    context = Context()
    page = ModsPage(context)
    (manager.data / 'mod.zip').write_bytes(zipped())
    manager.save_profile('shared')
    prepared = sharing.prepare_share(manager, 'shared')
    monkeypatch.setattr(QInputDialog, 'getItem', lambda *_: ('shared', True))
    monkeypatch.setattr(QInputDialog, 'getMultiLineText', lambda *_: ('', True))
    monkeypatch.setattr(ui, 'negotiate', lambda *_: [{'file_name': 'mod.zip', 'sha256': prepared['manifest']['mods'][0]['sha256'], 'status': 'available'}])
    monkeypatch.setattr(ui, 'preview_dialog', lambda *_: False)
    monkeypatch.setattr(ui, 'publish_share', lambda *_: pytest.fail('cancel must not publish'))
    context.set_management_busy(True)
    assert not page.share_profile_btn.isEnabled()
    assert not page.import_profile_btn.isEnabled()
    context.set_management_busy(False)
    page.sharing.share()
    for _ in range(100):
        QTest.qWait(10)
        if not context.management_busy:
            break
    assert not context.management_busy
    assert '已取消' in page.status_label.text()
    assert manager.installed_zip_names() == {'mod.zip'}
    # A saved imported scheme keeps the website workflow, so later uninstalls or
    # upgrades are repaired using the pinned bytes instead of filenames alone.
    atomic_json(manager._profiles_path(), {'shared': {'enabled': ['missing.zip'],
                'shared_id': IDENTITY, 'shared_origin': ORIGIN}})
    imports = []
    monkeypatch.setattr(page.sharing, 'import_link', lambda value, origin: imports.append((value, origin)))
    page.apply_profile()
    assert imports == [(IDENTITY, ORIGIN)]
    page.close()
    app.processEvents()

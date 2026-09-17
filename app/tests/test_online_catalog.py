import copy
import hashlib
import io
import json
import uuid
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import pytest
from core.modmanager import ModManager
from core.online_catalog import OnlineInstaller, parse_catalog, site_origin, download_release


def package(tmp_path, version='1.0', mod_id=None, name='mod_fixture.zip', content='// test only'):
    path = tmp_path / f'{uuid.uuid4()}.zip'
    with zipfile.ZipFile(path, 'w') as z: z.writestr('scripts/fixture.nut', content)
    rel_id = str(uuid.uuid4())
    mid = mod_id or str(uuid.uuid4())
    return path, {'id': mid, 'release_id': rel_id, 'version': version, 'file_name': name,
        'size': path.stat().st_size, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
        'download_path': f'/files/{rel_id}/download/', 'page_path': f'/mods/{mid}/',
        'metadata': {'title': '隔离测试 MOD', 'summary': '测试', 'description': '测试', 'category': '其他',
                     'author': 'test', 'game_version': '1.5.2.3', 'license': 'original', 'mod_ids': [], 'requires': [], 'conflicts': []}}


@pytest.fixture
def manager(tmp_path):
    game = tmp_path / '游戏'; (game / 'data').mkdir(parents=True)
    (game / 'data/data_001.dat').write_bytes(b'official untouched')
    return ModManager(game)


def test_install_update_disabled_and_rollback(tmp_path, manager):
    installer = OnlineInstaller(manager)
    old, one = package(tmp_path)
    new, two = package(tmp_path, '2.0', one['id'], content='// new')
    installer.install('http://localhost:8765', one, old)
    assert (manager.data / one['file_name']).read_bytes() == old.read_bytes()
    manager.disable(one['file_name'])
    installer.install('http://localhost:8765', two, new)
    assert not (manager.data / one['file_name']).exists()
    assert (manager.disabled_dir / one['file_name']).read_bytes() == new.read_bytes()
    preserved = installer.state_path.read_bytes()
    installer.install('http://localhost:8765', two, new)
    assert installer.state_path.read_bytes() == preserved
    installer.rollback(one['file_name'])
    assert (manager.disabled_dir / one['file_name']).read_bytes() == old.read_bytes()
    assert installer.state()['mods'][one['file_name']]['version'] == '1.0'
    assert (manager.data / 'data_001.dat').read_bytes() == b'official untouched'


def test_reject_manual_and_foreign_overwrite(tmp_path, manager):
    archive, item = package(tmp_path)
    (manager.data / item['file_name']).write_bytes(b'manual file')
    installer = OnlineInstaller(manager)
    with pytest.raises(ValueError, match='未由在线'): installer.install('http://localhost:8765', item, archive)
    assert (manager.data / item['file_name']).read_bytes() == b'manual file'
    (manager.data / item['file_name']).unlink()
    installer.install('http://localhost:8765', item, archive)
    with pytest.raises(ValueError, match='另一网站'): installer.install('http://other:8765', item, archive)


def test_install_failure_restores_bytes_and_state(tmp_path, manager):
    archive, one = package(tmp_path)
    installer = OnlineInstaller(manager)
    installer.install('http://localhost:8765', one, archive)
    state = installer.state_path.read_bytes()
    new, two = package(tmp_path, '2.0', one['id'], content='// new')
    with patch('core.online_catalog._atomic_json', side_effect=OSError('disk full')):
        with pytest.raises(OSError): installer.install('http://localhost:8765', two, new)
    assert installer.state_path.read_bytes() == state
    assert (manager.data / one['file_name']).read_bytes() == archive.read_bytes()


def test_first_install_failure_leaves_no_active_mod(tmp_path, manager):
    archive, item = package(tmp_path)
    with patch('core.online_catalog._atomic_json', side_effect=OSError('disk full')):
        with pytest.raises(OSError): OnlineInstaller(manager).install('http://localhost:8765', item, archive)
    assert not (manager.data / item['file_name']).exists()


def test_dependency_conflict_and_duplicate_ids(tmp_path, manager):
    archive, item = package(tmp_path)
    installer = OnlineInstaller(manager)
    item['metadata']['requires'] = ['missing_id']
    with pytest.raises(ValueError, match='前置'): installer.install('http://localhost:8765', item, archive)
    item['metadata']['requires'] = []
    fake = SimpleNamespace(enabled=True, path=Path('other.zip'), info=SimpleNamespace(registrations=[SimpleNamespace(mod_id='existing')], declared_conflicts=[]))
    with patch.object(manager, 'scan', return_value=[fake]):
        item['metadata']['conflicts'] = ['existing']
        with pytest.raises(ValueError, match='冲突'): installer.install('http://localhost:8765', item, archive)
        item['metadata']['conflicts'] = []; item['metadata']['mod_ids'] = ['existing']
        with pytest.raises(ValueError, match='同一 MOD'): installer.install('http://localhost:8765', item, archive)


@pytest.mark.parametrize('url', ['file:///etc', 'https://user:pass@host', 'http://host/path', 'http://host?x', 'javascript:evil', 'http://host:abc'])
def test_reject_invalid_origins(url):
    with pytest.raises(ValueError): site_origin(url)


def test_catalog_host_and_filename_validation(tmp_path):
    _, item = package(tmp_path)
    for field, value in [('download_path', '//evil/file'), ('file_name', '../evil.zip'), ('sha256', 'wrong'), ('size', -1)]:
        bad = copy.deepcopy(item); bad[field] = value
        with pytest.raises(ValueError): parse_catalog({'schema_version': 1, 'mods': [bad]})
    with pytest.raises(ValueError): parse_catalog({'schema_version': 1, 'mods': [item, item]})


def test_download_hash_and_cancellation(tmp_path):
    archive, item = package(tmp_path)
    with patch('core.online_catalog._request', return_value=io.BytesIO(archive.read_bytes())):
        result = download_release('http://localhost:8765', item, tmp_path / 'cache')
    assert result.read_bytes() == archive.read_bytes()
    result.unlink()
    for data, cancel in [(b'tampered', False), (archive.read_bytes(), True)]:
        with patch('core.online_catalog._request', return_value=io.BytesIO(data)):
            with pytest.raises(ValueError): download_release('http://localhost:8765', item, tmp_path / 'cache', cancelled=lambda: cancel)
        assert not list((tmp_path / 'cache').iterdir())

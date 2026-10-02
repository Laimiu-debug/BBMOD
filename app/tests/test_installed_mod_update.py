"""Direct local updates are exercised only against isolated temporary games."""
import hashlib
import json
import uuid
import zipfile
from unittest.mock import patch

import pytest

from core.l10n_identity import BRAND_META, PACKAGE_ID
from core.modmanager import ModManager
from core.online_catalog import OnlineInstaller


def release(tmp_path, version='1.0.0', *, identity=None, name='mod_fixture.zip',
            registrations=('mod_fixture',), package=False):
    archive = tmp_path / f'{uuid.uuid4().hex}.zip'
    script = '\n'.join(f'::Hooks.register("{mod_id}", "{version}", "测试 MOD");'
                       for mod_id in registrations) or f'// Resource release {version}'
    with zipfile.ZipFile(archive, 'w') as bundle:
        bundle.writestr('scripts/!mods_preload/fixture.nut', script)
        if package:
            bundle.writestr(BRAND_META, json.dumps({'package_id': PACKAGE_ID, 'version': version}))
    identity = identity or str(uuid.uuid4())
    release_id = str(uuid.uuid4())
    item = {'id': identity, 'release_id': release_id, 'version': version, 'file_name': name,
            'size': archive.stat().st_size, 'sha256': sha(archive),
            'download_path': f'/files/{release_id}/download/', 'page_path': f'/mods/{identity}/',
            'metadata': {'title': '隔离更新测试', 'summary': '', 'description': '',
                         'category': '其他', 'author': 'test', 'game_version': '', 'license': 'original',
                         'mod_ids': list(registrations), 'requires': [], 'conflicts': []}}
    return archive, item


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def installer(tmp_path):
    game = tmp_path / '游戏'
    data = game / 'data'
    data.mkdir(parents=True)
    (data / 'data_001.dat').write_bytes(b'official file remains untouched')
    with zipfile.ZipFile(data / 'mod_modern_hooks.zip', 'w') as archive:
        archive.writestr('scripts/!mods_preload/hooks.nut',
                         '::Hooks.register("mod_modern_hooks", "1.0.0", "Hooks");')
    return OnlineInstaller(ModManager(game))


def install_local(installer, archive, *, name='mod_fixture.zip', disabled=False):
    directory = installer.disabled if disabled else installer.data
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    path.write_bytes(archive.read_bytes())
    return path


def update(installer, item, archive, local, version='1.0.0', **kwargs):
    return installer.install('https://bbmod.com', item, archive, local_file_name=local.name,
                             expected_current_sha256=kwargs['expected'] if 'expected' in kwargs else sha(local),
                             installed_version=version)


@pytest.mark.parametrize('disabled', [False, True])
def test_manual_update_preserves_status_and_rolls_back(tmp_path, installer, disabled):
    old, one = release(tmp_path)
    new, two = release(tmp_path, '2.0.0', identity=one['id'])
    local = install_local(installer, old, disabled=disabled)
    message = update(installer, two, new, local)
    assert local.read_bytes() == new.read_bytes()
    assert ('保持禁用' in message) == disabled
    other = (installer.data if disabled else installer.disabled) / local.name
    assert not other.exists()
    record = installer.state()['mods'][local.name]
    assert record['previous']['adopted_from_local'] is True
    assert record['previous']['version'] == '1.0.0'
    assert (installer.backups / record['backup']).read_bytes() == old.read_bytes()
    installer.rollback(local.name)
    assert local.read_bytes() == old.read_bytes()
    assert installer.state()['mods'][local.name]['sha256'] == sha(old)
    assert (installer.data / 'data_001.dat').read_bytes() == b'official file remains untouched'


def test_renamed_release_updates_original_file_and_receipt(tmp_path, installer):
    old, one = release(tmp_path, name='mod_fixture_v1.zip')
    new, two = release(tmp_path, '2.0.0', identity=one['id'], name='mod_fixture_v2.zip')
    local = install_local(installer, old, name=one['file_name'])
    update(installer, two, new, local)
    assert local.read_bytes() == new.read_bytes()
    assert not (installer.data / two['file_name']).exists()
    assert set(installer.state()['mods']) == {local.name}
    installer.rollback(local.name)
    assert local.read_bytes() == old.read_bytes()


def test_default_install_still_refuses_manual_overwrite(tmp_path, installer):
    old, one = release(tmp_path)
    new, two = release(tmp_path, '2.0.0', identity=one['id'])
    local = install_local(installer, old)
    with pytest.raises(ValueError, match='未由在线'):
        installer.install('https://bbmod.com', two, new)
    assert local.read_bytes() == old.read_bytes()


@pytest.mark.parametrize('omit', ['local_file_name', 'expected_current_sha256', 'installed_version'])
def test_local_update_requires_complete_snapshot(tmp_path, installer, omit):
    old, one = release(tmp_path)
    new, two = release(tmp_path, '2.0.0', identity=one['id'])
    local = install_local(installer, old)
    args = {'local_file_name': local.name, 'expected_current_sha256': sha(local), 'installed_version': '1.0.0'}
    del args[omit]
    with pytest.raises(ValueError, match='本地更新须提供'):
        installer.install('https://bbmod.com', two, new, **args)
    assert local.read_bytes() == old.read_bytes()


@pytest.mark.parametrize('change', ['modify', 'remove'])
def test_download_period_change_does_not_replace_file(tmp_path, installer, change):
    old, one = release(tmp_path)
    new, two = release(tmp_path, '2.0.0', identity=one['id'])
    local = install_local(installer, old)
    expected = sha(local)
    if change == 'modify':
        local.write_bytes(b'changed while downloading')
    else:
        local.unlink()
    with pytest.raises(ValueError, match='已改变或已不存在'):
        update(installer, two, new, local, expected=expected)
    assert not installer.state_path.exists()
    if change == 'modify':
        assert local.read_bytes() == b'changed while downloading'
    else:
        assert not local.exists()


@pytest.mark.parametrize('new_ids', [('mod_other',), ('mod_fixture',)])
def test_manual_bundle_identity_cannot_be_changed_or_partially_replaced(tmp_path, installer, new_ids):
    old, one = release(tmp_path, registrations=('mod_fixture', 'mod_second'))
    new, two = release(tmp_path, '2.0.0', identity=one['id'], registrations=new_ids)
    local = install_local(installer, old)
    with pytest.raises(ValueError, match='注册身份不一致'):
        update(installer, two, new, local)
    assert local.read_bytes() == old.read_bytes()
    assert not installer.state_path.exists()


def test_manual_release_may_add_registrations(tmp_path, installer):
    old, one = release(tmp_path)
    new, two = release(tmp_path, '2.0.0', identity=one['id'],
                       registrations=('mod_fixture', 'mod_added'))
    local = install_local(installer, old)
    update(installer, two, new, local)
    assert local.read_bytes() == new.read_bytes()


def test_trusted_receipt_allows_work_to_change_its_registration(tmp_path, installer):
    old, one = release(tmp_path)
    new, two = release(tmp_path, '2.0.0', identity=one['id'], registrations=('mod_replacement',))
    installer.install('https://bbmod.com', one, old)
    local = installer.data / one['file_name']
    update(installer, two, new, local)
    assert local.read_bytes() == new.read_bytes()


@pytest.mark.parametrize('managed', [False, True])
def test_package_identity_must_remain_the_same(tmp_path, installer, managed):
    old, one = release(tmp_path, package=True)
    new, two = release(tmp_path, '2.0.0', identity=one['id'], package=False)
    if managed:
        installer.install('https://bbmod.com', one, old)
        local = installer.data / one['file_name']
    else:
        local = install_local(installer, old)
    with pytest.raises(ValueError, match='包身份不一致'):
        update(installer, two, new, local)
    assert local.read_bytes() == old.read_bytes()


def test_package_identity_has_priority_over_bundled_registrations(tmp_path, installer):
    old, one = release(tmp_path, package=True)
    new, two = release(tmp_path, '2.0.0', identity=one['id'], package=True,
                       registrations=('mod_different_component',))
    local = install_local(installer, old)
    update(installer, two, new, local)
    assert local.read_bytes() == new.read_bytes()


@pytest.mark.parametrize('name,allowed', [('mod_fixture.zip', True), ('renamed.zip', False)])
def test_unregistered_manual_package_requires_same_filename(tmp_path, installer, name, allowed):
    old, one = release(tmp_path, registrations=())
    new, two = release(tmp_path, '2.0.0', identity=one['id'], name=name, registrations=())
    local = install_local(installer, old)
    if allowed:
        update(installer, two, new, local)
        assert local.read_bytes() == new.read_bytes()
    else:
        with pytest.raises(ValueError, match='没有可核实的注册身份'):
            update(installer, two, new, local)
        assert local.read_bytes() == old.read_bytes()


@pytest.mark.parametrize('foreign', ['origin', 'work'])
def test_direct_update_refuses_foreign_receipt(tmp_path, installer, foreign):
    old, one = release(tmp_path)
    installer.install('https://custom.example' if foreign == 'origin' else 'https://bbmod.com', one, old)
    new, two = release(tmp_path, '2.0.0', identity=one['id'] if foreign == 'origin' else None)
    local = installer.data / one['file_name']
    state = installer.state_path.read_bytes()
    with pytest.raises(ValueError, match='另一网站或作品'):
        update(installer, two, new, local)
    assert local.read_bytes() == old.read_bytes()
    assert installer.state_path.read_bytes() == state


def test_selected_version_cannot_ignore_changed_receipt(tmp_path, installer):
    old, one = release(tmp_path)
    installer.install('https://bbmod.com', one, old)
    new, two = release(tmp_path, '2.0.0', identity=one['id'])
    local = installer.data / one['file_name']
    with pytest.raises(ValueError, match='记录版本已改变'):
        update(installer, two, new, local, version='0.9.0')
    assert local.read_bytes() == old.read_bytes()


def test_renamed_release_does_not_leave_a_second_local_install(tmp_path, installer):
    old, one = release(tmp_path)
    new, two = release(tmp_path, '2.0.0', identity=one['id'], name='mod_new_name.zip')
    local = install_local(installer, old)
    second = install_local(installer, old, name=two['file_name'], disabled=True)
    with pytest.raises(ValueError, match='新版文件名已存在'):
        update(installer, two, new, local)
    assert local.read_bytes() == old.read_bytes()
    assert second.read_bytes() == old.read_bytes()


def test_same_release_version_with_changed_bytes_is_not_overwritten(tmp_path, installer):
    old, one = release(tmp_path)
    new, two = release(tmp_path, identity=one['id'], registrations=('mod_fixture', 'mod_new'))
    local = install_local(installer, old)
    with pytest.raises(ValueError, match='同一版本'):
        update(installer, two, new, local)
    assert local.read_bytes() == old.read_bytes()


@pytest.mark.parametrize('failure', ['receipt', 'apply'])
def test_failed_manual_update_preserves_old_file_and_no_receipt(tmp_path, installer, failure):
    old, one = release(tmp_path)
    new, two = release(tmp_path, '2.0.0', identity=one['id'])
    local = install_local(installer, old)
    target = 'core.online_catalog._atomic_json' if failure == 'receipt' else 'core.modmanager.ModManager._apply'
    with patch(target, side_effect=OSError('disk full')):
        with pytest.raises(OSError, match='disk full'):
            update(installer, two, new, local)
    assert local.read_bytes() == old.read_bytes()
    assert not installer.state_path.exists()
    assert not list(installer.backups.glob('*.zip'))


def test_change_after_backup_is_not_overwritten(tmp_path, installer):
    old, one = release(tmp_path)
    new, two = release(tmp_path, '2.0.0', identity=one['id'])
    local = install_local(installer, old)
    from core.online_catalog import _atomic_json

    def mutate_after_receipt(path, data):
        _atomic_json(path, data)
        local.write_bytes(b'external writer changed old mod')

    with patch('core.online_catalog._atomic_json', side_effect=mutate_after_receipt):
        with pytest.raises(ValueError, match='更新前 MOD 文件已改变'):
            update(installer, two, new, local)
    assert local.read_bytes() == b'external writer changed old mod'
    assert not installer.state_path.exists()
    assert not list(installer.backups.glob('*.zip'))

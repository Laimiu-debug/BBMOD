import io
import json
import shutil
import uuid
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest

from core import shared_saves
from core.archive_safety import inspect_archive
from core.modmanager import ModManager
from core.save_protocol import inspect_save, validate_manifest
from core.web_links import parse_link


def campaign(label=b'fixture'):
    return b'\xbb\x00\x02\x41\x00\x00\x00' + label * 100


def package(path, label='fixture'):
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, 'w') as archive:
        archive.writestr(f'scripts/{label}.nut', '// fixture')
    return path


@pytest.fixture
def setup(tmp_path, monkeypatch):
    monkeypatch.setattr('core.game.is_game_running', lambda: False)
    sender, receiver = ModManager(tmp_path/'sender'), ModManager(tmp_path/'receiver')
    sender.data.mkdir(parents=True)
    receiver.data.mkdir(parents=True)
    source = tmp_path/'campaign.sav'
    source.write_bytes(campaign())
    package(sender.data/'required.zip')
    package(receiver.data/'old.zip', 'old')
    prepared = shared_saves.prepare_share(sender, source, '兄弟战团', game_version='1.5.2.3')
    return receiver, prepared, tmp_path/'savegames'


def downloads(prepared):
    def download(url, destination, **_):
        sha = url.strip('/').split('/')[-1]
        source = prepared['save_path'] if sha == prepared['manifest']['save']['sha256'] else prepared['sources'][sha]
        shutil.copyfile(source, destination)
    return download


def test_restore_write_failure_rolls_back_both_mods_and_preserves_old_save(setup):
    manager, prepared, directory = setup
    directory.mkdir()
    old_save = directory/'existing.sav'
    old_save.write_bytes(campaign(b'old'))
    originals = {manager.data/'old.zip': (manager.data/'old.zip').read_bytes(), old_save: old_save.read_bytes()}
    manifest = prepared['manifest']
    plan = shared_saves.preview_restore(manager, manifest, directory, '1.5.2.3')
    from core.mod_transactions import os
    replace = os.replace
    def fail_save(source, target):
        if Path(target).suffix == '.sav':
            raise OSError('simulated disk failure')
        return replace(source, target)
    with patch.object(shared_saves, 'fetch_save', return_value=manifest), \
            patch('core.downloads.download_verified', side_effect=downloads(prepared)), \
            patch('core.mod_transactions.os.replace', side_effect=fail_save):
        with pytest.raises(OSError, match='disk failure'):
            shared_saves.restore(manager, 'https://bbmod.com', str(uuid.uuid4()), manifest,
                expected=plan, game_version='1.5.2.3')
    assert all(path.read_bytes() == data for path, data in originals.items())
    assert not (manager.data/'required.zip').exists()
    assert not Path(plan['target']).exists()
    assert not manager.transaction.journal.exists()


def test_interruption_retains_journal_and_wrong_save_directory_cannot_recover(setup):
    manager, prepared, directory = setup
    manifest = prepared['manifest']
    plan = shared_saves.preview_restore(manager, manifest, directory, '1.5.2.3')
    from core.mod_transactions import os
    replace = os.replace
    def interrupt(source, target):
        if Path(target).suffix == '.sav':
            raise KeyboardInterrupt('simulated termination')
        return replace(source, target)
    with patch.object(shared_saves, 'fetch_save', return_value=manifest), \
            patch('core.downloads.download_verified', side_effect=downloads(prepared)), \
            patch('core.mod_transactions.os.replace', side_effect=interrupt):
        with pytest.raises(KeyboardInterrupt):
            shared_saves.restore(manager, 'https://bbmod.com', str(uuid.uuid4()), manifest,
                expected=plan, game_version='1.5.2.3')
    assert manager.transaction.journal.exists()
    with pytest.raises(ValueError, match='目录与当前选择不一致'):
        shared_saves.recover(manager, directory.parent/'wrong')
    assert manager.transaction.journal.exists()
    shared_saves.recover(manager, directory)
    assert not manager.transaction.journal.exists()
    assert (manager.data/'old.zip').exists()
    assert not (manager.data/'required.zip').exists()


def test_target_appearing_after_preview_is_never_overwritten(setup):
    manager, prepared, directory = setup
    manifest = prepared['manifest']
    plan = shared_saves.preview_restore(manager, manifest, directory, '1.5.2.3')
    directory.mkdir()
    target = Path(plan['target'])
    target.write_bytes(campaign(b'keep'))
    before = target.read_bytes()
    with patch('core.downloads.download_verified') as download:
        with pytest.raises(ValueError, match='已改变'):
            shared_saves.restore(manager, 'https://bbmod.com', str(uuid.uuid4()), manifest,
                expected=plan, game_version='1.5.2.3')
        download.assert_not_called()
    assert target.read_bytes() == before


def test_missing_dlc_wrong_version_and_running_game_block_before_download(setup):
    manager, prepared, directory = setup
    manifest = prepared['manifest']
    with pytest.raises(ValueError, match='相同游戏版本'):
        shared_saves.preview_restore(manager, manifest, directory, '0.0.0')
    manifest = {**manifest, 'dlcs': ['Lindwurm']}
    with pytest.raises(ValueError, match='缺少配套 DLC'):
        shared_saves.preview_restore(manager, manifest, directory, '1.5.2.3')
    with patch('core.game.is_game_running', return_value=True), pytest.raises(ValueError, match='退出游戏'):
        shared_saves.preview_restore(manager, prepared['manifest'], directory, '1.5.2.3')


def test_changed_source_mod_or_save_prevents_publishing(setup):
    _, prepared, _ = setup
    prepared['save_path'].write_bytes(campaign(b'changed'))
    with patch.object(shared_saves, '_json') as network, pytest.raises(ValueError, match='存档已改变'):
        shared_saves.publish_share('https://bbmod.com', prepared)
    network.assert_not_called()


def test_excludes_msu_resource_save_and_accepts_unnamed_campaign(tmp_path):
    (tmp_path/'MSU#cache.sav').write_bytes(b'\xbb\x00\x02' + b'\0' * 700)
    source = tmp_path/'      .sav'
    source.write_bytes(campaign())
    rows = shared_saves.list_saves(tmp_path)
    assert len(rows) == 1 and rows[0]['path'] == source and rows[0]['name'] == '未命名战役'
    with pytest.raises(ValueError):
        inspect_save(io.BytesIO(b'MZ' + b'x' * 700))


def test_save_links_are_same_site_only_and_manifest_paths_are_safe(setup):
    _, prepared, _ = setup
    identity = str(uuid.uuid4())
    assert parse_link('bbmod://saves/' + identity) == ('saves', identity)
    assert shared_saves.save_identity('https://bbmod.com/saves/' + identity + '/', 'https://bbmod.com') == identity
    with pytest.raises(ValueError):
        shared_saves.save_identity('https://evil.example/saves/' + identity + '/', 'https://bbmod.com')
    manifest = {**prepared['manifest'], 'save': {**prepared['manifest']['save'], 'file_name': '../escape.sav'}}
    with pytest.raises(ValueError):
        validate_manifest(manifest)


@pytest.mark.parametrize('namespace', ['mod_nested_tooltips', 'mod_maxi_tooltips', 'script_hooks'])
def test_legacy_mod_namespaces_and_backslash_paths_can_be_shared_without_repacking(namespace):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w') as archive:
        archive.writestr(namespace + '\\fixture.nut', '// fixture')
    assert inspect_archive(stream)['script_count'] == 1
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w') as archive:
        archive.writestr(namespace + '\\..\\escape.nut', '// fixture')
    with pytest.raises(ValueError, match='不安全'):
        inspect_archive(stream)

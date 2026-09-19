import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import zipfile

import pytest

from core import l10n
from core.localization_profiles import BUILTIN, CURRENT, NONE, GUARD, LocalizationProfiles, digest


def package(path, entries=None, *, own=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, 'w') as archive:
        for name, value in (entries or {'scripts/items/example.cnut': 'example'}).items():
            archive.writestr(name, value)
        if own:
            archive.writestr(l10n.BRAND_META, json.dumps({'package_id': l10n.PACKAGE_ID, 'requires_bbmod_launcher': True}))
    return path


@pytest.fixture
def setup(tmp_path):
    root = tmp_path / 'game'
    (root / 'data').mkdir(parents=True)
    (root / 'win32').mkdir()
    (root / 'win32/BattleBrothers.exe').write_bytes(b'fake-test-only')
    (root / 'data/data_001.dat').write_bytes(b'official archive stays identical')
    backend = LocalizationProfiles(root)
    with patch('core.game.is_game_running', return_value=False):
        yield backend, tmp_path


def test_switches_multifile_packages_and_preserves_other_mods(setup):
    manager, tmp = setup
    text = package(manager.data / 'other_chinese.zip')
    font = package(manager.data / 'font-for-language.zip', {'gfx/fonts/special.png': 'font'})
    ordinary = package(manager.data / 'ordinary_mod.zip', {'scripts/unrelated.cnut': 'unchanged'})
    before = {p.name: p.read_bytes() for p in (text, font, ordinary)}
    original = manager.register('原有汉化及字体', [text, font])
    own = package(tmp / 'new/independent.zip', own=True)
    key = manager.register('独立汉化', [own], builtin=True)
    plan = manager.plan(key)
    assert set(plan.disable) == {text.name, font.name}
    assert plan.install == [own.name]
    manager.apply(plan)
    assert ordinary.read_bytes() == before[ordinary.name]
    assert (manager.data / own.name).read_bytes() == own.read_bytes()
    assert not text.exists() and not font.exists()
    assert (manager.root / 'bbmod_disabled' / text.name).read_bytes() == before[text.name]
    manager.apply(manager.plan(original))
    assert text.read_bytes() == before[text.name] and font.read_bytes() == before[font.name]
    assert not (manager.data / own.name).exists()
    assert (manager.data / 'data_001.dat').read_bytes() == b'official archive stays identical'
    assert not manager.plan(original).changed
    assert not manager.journal.exists()


def test_same_filename_keeps_old_bytes_and_restores_saved_profile(setup):
    manager, tmp = setup
    old = package(manager.data / 'chinese.zip', {'ui/main.html': 'old'})
    old_bytes = old.read_bytes()
    old_id = manager.register('旧汉化', [old])
    package(manager.root / 'bbmod_disabled/chinese.zip', {'ui/main.html': 'different backup'})
    new = package(tmp / 'new/chinese.zip', {'ui/main.html': 'new'})
    new_id = manager.register('新汉化', [new])
    manager.apply(manager.plan(new_id))
    assert old.read_bytes() == new.read_bytes()
    assert old_bytes in [p.read_bytes() for p in (manager.root / 'bbmod_disabled').glob('*.zip')]
    manager.apply(manager.plan(old_id))
    assert old.read_bytes() == old_bytes


def test_case_only_filename_change_uses_one_target(setup):
    manager, tmp = setup
    old = package(manager.data / 'chinese.zip', {'ui/main.html': 'old'})
    new = package(tmp / 'other/CHINESE.zip', {'ui/main.html': 'new'})
    key = manager.register('新版', [new])
    plan = manager.plan(key)
    assert plan.disable == plan.install == ['chinese.zip']
    manager.apply(plan)
    assert old.read_bytes() == new.read_bytes()


def test_preview_lists_overlapping_mods_without_moving_them(setup):
    manager, tmp = setup
    conflict = package(manager.data / 'unknown_ui.zip', {'ui/main.html': 'other UI'})
    untouched = conflict.read_bytes()
    new = package(tmp / 'language.zip', {'ui/main.html': 'translated'})
    key = manager.register('汉化', [new])
    plan = manager.plan(key)
    assert plan.conflicts == [conflict.name]
    assert conflict.read_bytes() == untouched
    manager.apply(plan)
    assert not conflict.exists()


def test_stale_preview_aborts_before_mutation(setup):
    manager, tmp = setup
    old = package(manager.data / 'chinese.zip')
    plan = manager.plan(NONE)
    old.write_bytes(b'externally changed')
    with pytest.raises(RuntimeError, match='已改变'):
        manager.apply(plan)
    assert old.read_bytes() == b'externally changed'
    assert not manager.journal.exists()


def test_write_failure_rolls_back_and_preserves_package_library(setup):
    manager, tmp = setup
    old = package(manager.data / 'chinese.zip')
    before = old.read_bytes()
    new = package(tmp / 'new/next_chinese.zip', {'ui/main.html': 'new'})
    key = manager.register('新汉化', [new])
    copy = manager._copy_verified
    failed = False
    def interrupted(source, target, expected):
        nonlocal failed
        if target == manager.data / new.name and not failed:
            failed = True
            raise OSError('simulated disk error')
        copy(source, target, expected)
    with patch.object(manager, '_copy_verified', side_effect=interrupted):
        with pytest.raises(OSError, match='simulated'):
            manager.apply(manager.plan(key))
    assert old.read_bytes() == before
    assert not (manager.data / new.name).exists()
    assert not manager.journal.exists()
    assert manager.profiles()[key]['name'] == '新汉化'


def test_disabled_file_changed_during_backup_is_never_overwritten(setup):
    manager, tmp = setup
    old = package(manager.data / 'chinese.zip')
    before = old.read_bytes()
    disabled = manager.root / 'bbmod_disabled/chinese.zip'
    disabled.parent.mkdir()
    disabled.write_bytes(before)
    copy = manager._copy_verified
    changed = False
    def external_edit(source, target, expected):
        nonlocal changed
        copy(source, target, expected)
        if source == disabled and target.parent.name == 'before' and not changed:
            changed = True
            disabled.write_bytes(b'external edit during switch')
    with patch.object(manager, '_copy_verified', side_effect=external_edit), pytest.raises(RuntimeError, match='外部修改'):
        manager.apply(manager.plan(NONE))
    assert old.read_bytes() == before
    assert disabled.read_bytes() == b'external edit during switch'
    assert manager.journal.exists()


def test_crashed_switch_can_recover_on_next_start_without_game(setup):
    manager, tmp = setup
    old = package(manager.data / 'chinese.zip')
    before = old.read_bytes()
    new = package(tmp / 'next_chinese.zip')
    key = manager.register('另一个汉化', [new])
    copy = manager._copy_verified
    def crash(source, target, expected):
        if target == manager.data / new.name:
            raise SystemExit('simulated crash')
        copy(source, target, expected)
    with patch.object(manager, '_copy_verified', side_effect=crash), pytest.raises(SystemExit):
        manager.apply(manager.plan(key))
    assert manager.journal.exists() and not old.exists()
    reopened = LocalizationProfiles(manager.root)
    with pytest.raises(RuntimeError, match='上次切换'):
        reopened.plan(CURRENT)
    reopened.recover()
    assert old.read_bytes() == before
    assert not reopened.journal.exists()


def test_running_game_seed_session_and_preview_guard_block_writes(setup):
    manager, tmp = setup
    old = package(manager.data / 'chinese.zip')
    plan = manager.plan(NONE)
    with patch('core.game.is_game_running', return_value=True), pytest.raises(RuntimeError, match='正在运行'):
        manager.apply(plan)
    session = manager.root / 'bbmod_seedgen_session/session.json'
    session.parent.mkdir()
    session.write_text('{}')
    with pytest.raises(RuntimeError, match='种子远征'):
        manager.apply(plan)
    session.unlink()
    package(manager.data / GUARD, {'BBMOD_PREVIEW_GUARD.json': '{}'})
    with pytest.raises(RuntimeError, match='开发测试副本'):
        manager.apply(plan)
    assert old.exists()


def test_import_only_copies_zip_and_rejects_nested_bundles(setup):
    manager, tmp = setup
    external = package(tmp / 'download/chinese.zip')
    before = external.read_bytes()
    key = manager.register('朋友的汉化', [external])
    assert external.read_bytes() == before
    assert not (manager.data / external.name).exists()
    assert LocalizationProfiles(manager.root).profiles()[key]['name'] == '朋友的汉化'
    nested = package(tmp / 'bundle.zip', {'nested.zip': 'not an actual package'})
    with pytest.raises(ValueError, match='合集'):
        manager.register('错误合集', [nested])
    unsafe = package(tmp / 'unsafe.zip', {'../outside.nut': 'bad'})
    with pytest.raises(ValueError, match='越界'):
        manager.register('越界', [unsafe])


def test_plain_launch_uses_exact_directory_and_legacy_package_requires_update(setup):
    manager, tmp = setup
    game = SimpleNamespace(root=manager.root, exe=manager.root / 'win32/BattleBrothers.exe')
    other = package(manager.data / 'other_chinese.zip')
    with patch('core.game.os.startfile', create=True) as launch, \
            patch('core.game.find_steam_root', return_value=None):
        assert manager.launch(game, tmp)['mode'] == 'current'
        assert launch.call_args.args == (str(game.exe),)
        assert launch.call_args.kwargs['cwd'] == str(game.exe.parent)
    other.unlink()
    package(manager.data / 'our.zip', own=True)
    with patch('core.game.launch_executable') as launch:
        with pytest.raises(RuntimeError, match='依赖旧中文启动组件'):
            manager.launch(game, tmp)
        launch.assert_not_called()


def test_copied_game_cannot_bootstrap_into_registered_steam_install(setup):
    manager, tmp = setup
    game = SimpleNamespace(root=manager.root, exe=manager.root / 'win32/BattleBrothers.exe')
    steam = tmp / 'steam'
    registered = steam / 'steamapps/common/Battle Brothers'
    registered.mkdir(parents=True)
    (steam / 'steamapps/appmanifest_365360.acf').write_text('"installdir" "Battle Brothers"')
    with patch('core.game.find_steam_root', return_value=steam), \
            patch('core.game.list_steam_libraries', return_value=[steam]), \
            patch('core.game.os.startfile', create=True) as start:
        with pytest.raises(RuntimeError, match='隔离测试'):
            manager.launch(game, tmp)
        start.assert_not_called()
        (registered / 'data').mkdir()
        (registered / 'win32').mkdir()
        correct = SimpleNamespace(root=registered, exe=registered / 'win32/BattleBrothers.exe')
        correct.exe.write_bytes(b'test executable')
        assert LocalizationProfiles(registered).launch(correct, tmp)['mode'] == 'current'
        start.assert_called_once_with(str(correct.exe), cwd=str(correct.exe.parent))


def test_conflicting_localizations_and_pending_journal_block_launch(setup):
    manager, tmp = setup
    game = SimpleNamespace(root=manager.root, exe=manager.root / 'win32/BattleBrothers.exe')
    package(manager.data / 'ours.zip', own=True)
    package(manager.data / 'other_chinese.zip')
    with patch('core.game.launch_executable') as launch, pytest.raises(RuntimeError, match='多套汉化'):
        manager.launch(game, tmp)
    launch.assert_not_called()


def test_legacy_direct_launch_package_cannot_invoke_retired_native_loader(setup):
    manager, tmp = setup
    game = SimpleNamespace(root=manager.root, exe=manager.root / 'win32/BattleBrothers.exe')
    package(manager.data / 'ours.zip', {l10n.BRAND_META: json.dumps({
        'package_id': l10n.PACKAGE_ID, 'requires_bbmod_launcher': False,
        'uses_bbmod_map_font': True, 'supports_direct_launch': True})})
    with patch('core.game.launch_executable') as launch:
        with pytest.raises(RuntimeError, match='旧中文启动组件'):
            manager.launch(game, tmp)
        launch.assert_not_called()


def test_recovery_rejects_paths_to_official_files_before_changes(setup):
    manager, tmp = setup
    manager.store.mkdir()
    manager.journal.write_text(json.dumps({'schema': 1, 'before': {'data/data_001.dat': {'sha256': None}},
                                           'after': {'data/data_001.dat': None}}))
    with pytest.raises(ValueError):
        manager.recover()
    assert (manager.data / 'data_001.dat').read_bytes() == b'official archive stays identical'


def test_manual_game_path_does_not_fall_back_to_another_installation(tmp_path):
    from core.game import locate_game
    with patch('core.game.find_steam_root') as steam:
        assert locate_game(str(tmp_path / 'missing')) is None
        steam.assert_not_called()


def test_corrupt_library_or_external_changes_during_recovery_are_preserved(setup):
    manager, tmp = setup
    source = package(tmp / 'chinese.zip')
    key = manager.register('汉化', [source])
    stored = manager._stored(manager.profiles()[key]['files'][0]['stored'])
    stored.write_bytes(b'altered package')
    with pytest.raises(ValueError, match='已改变'):
        manager.plan(key)
    current = package(manager.data / 'old_chinese.zip')
    manager.journal.write_text(json.dumps({'schema': 1, 'before': {'data/old_chinese.zip': {'sha256': None, 'backup': 'unused.zip'}},
                                           'after': {'data/old_chinese.zip': 'not-current-hash'}}))
    before = current.read_bytes()
    with pytest.raises(RuntimeError, match='外部修改'):
        manager.recover()
    assert current.read_bytes() == before and manager.journal.exists()

import hashlib
import json
import runpy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from core import native_font


@pytest.fixture
def assets(tmp_path, monkeypatch):
    paths = {}
    source = tmp_path/'assets'
    source.mkdir()
    for name in ('bbmod_launch.exe', 'bbmod_han.dll', 'NotoSerifSC-SemiBold.ttf', 'FONT-LICENSE.txt', 'MINHOOK-LICENSE.txt'):
        paths[name] = source/name
        paths[name].write_bytes(('non-executable fixture: ' + name).encode())
    monkeypatch.setattr(native_font, 'component_paths', lambda: paths)
    return paths


def test_missing_bundled_component_reports_name_and_never_launches(tmp_path, assets):
    assets['bbmod_launch.exe'].unlink()
    game = SimpleNamespace(exe=tmp_path/'not-a-game.exe')
    with patch('core.game.is_game_running', return_value=False), patch.object(native_font, 'check_executable'), \
            patch.object(native_font.subprocess, 'run') as run:
        with pytest.raises(native_font.NativeComponentError, match='bbmod_launch.exe') as error:
            native_font.launch_localized(game, tmp_path/'runtime')
        assert '保护历史记录' in str(error.value)
        assert not (tmp_path/'runtime').exists()
        run.assert_not_called()


def test_dictionary_change_keeps_same_binary_cache_and_private_dictionaries(tmp_path, assets):
    runtime = native_font.prepare_runtime(tmp_path/'runtime', b'first dictionary')
    stamp = (runtime/'bbmod_launch.exe').stat().st_mtime_ns
    again = native_font.prepare_runtime(tmp_path/'runtime', b'second dictionary')
    assert again == runtime
    assert (runtime/'bbmod_launch.exe').stat().st_mtime_ns == stamp
    assert native_font._place_data_path(runtime, b'first dictionary').read_bytes() == b'first dictionary'
    assert native_font._place_data_path(runtime, b'second dictionary').read_bytes() == b'second dictionary'


@pytest.mark.parametrize('damage', ['removed', 'modified', 'missing_receipt', 'invalid_receipt'])
def test_prepared_runtime_is_not_silently_repaired(tmp_path, assets, damage):
    parent = tmp_path/'runtime'
    runtime = native_font.prepare_runtime(parent, b'first dictionary')
    binary = runtime/'bbmod_launch.exe'
    if damage == 'removed':
        binary.unlink()
    elif damage == 'modified':
        binary.write_bytes(b'changed by another program')
    elif damage == 'missing_receipt':
        (runtime/'manifest.json').unlink()
    else:
        (runtime/'manifest.json').write_text('invalid receipt')
    before = {str(p.relative_to(parent)): p.read_bytes() for p in parent.rglob('*') if p.is_file()}
    with pytest.raises(native_font.NativeComponentError):
        native_font.prepare_runtime(parent, b'different dictionary')
    after = {str(p.relative_to(parent)): p.read_bytes() for p in parent.rglob('*') if p.is_file()}
    assert before == after


def test_missing_rc5_copy_cannot_be_recreated_by_changing_dictionary(tmp_path, assets):
    parent = tmp_path/'runtime'
    hashes = {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in assets.items()}
    hashes['place_names.tsv'] = hashlib.sha256(b'old dictionary').hexdigest()
    version = hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()[:16]
    old = parent/'chinese-font'/version
    old.mkdir(parents=True)
    (old/'manifest.json').write_text(json.dumps(hashes), encoding='utf-8')
    for name, source in assets.items():
        if name != 'bbmod_launch.exe':
            (old/name).write_bytes(source.read_bytes())
    with pytest.raises(native_font.NativeComponentError, match='bbmod_launch.exe'):
        native_font.prepare_runtime(parent, b'new dictionary')
    assert list((parent/'chinese-font').iterdir()) == [old]
    assert not (old/'bbmod_launch.exe').exists()


def test_packaging_fails_before_analysis_when_native_input_missing(tmp_path):
    (tmp_path/'core').mkdir()
    (tmp_path/'core/version.py').write_text("VERSION = '0.3.0-test.1'\n")
    spec = Path(__file__).parents[1]/'BBMOD.spec'
    with pytest.raises(SystemExit, match='bbmod_launch.exe'):
        runpy.run_path(str(spec), init_globals={'SPECPATH': str(tmp_path)})


def test_security_block_during_launch_is_not_retried(tmp_path, assets):
    game = SimpleNamespace(exe=tmp_path/'not-a-game.exe')
    error = OSError('blocked by security software')
    error.winerror = 225
    with patch('core.game.is_game_running', return_value=False), patch.object(native_font, 'check_executable'), \
            patch.object(native_font.subprocess, 'run', side_effect=error) as run:
        with pytest.raises(native_font.NativeComponentError, match='bbmod_launch.exe'):
            native_font.launch_localized(game, tmp_path/'runtime')
        assert run.call_count == 1

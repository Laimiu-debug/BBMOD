"""Compatibility checks for the ordinary MOD build and its desktop package."""
import hashlib
import os
from pathlib import Path
import runpy

import pytest

from core import map_labels


def test_build_rejects_an_unverified_game_without_modifying_it(tmp_path, monkeypatch):
    exe = tmp_path / 'BattleBrothers.exe'
    original = b'non-executable game fixture'
    exe.write_bytes(original)
    with pytest.raises(ValueError, match='独立汉化构建验证'):
        map_labels.check_executable(exe)
    assert exe.read_bytes() == original
    monkeypatch.setattr(map_labels, 'SUPPORTED_EXE_SHA256', hashlib.sha256(original).hexdigest())
    map_labels.check_executable(exe)
    assert exe.read_bytes() == original


def test_spec_does_not_collect_retired_injection_components(tmp_path, monkeypatch):
    (tmp_path / 'core').mkdir()
    (tmp_path / 'core/version.py').write_text("VERSION = '0.3.0-test.1'\n")
    spec = Path(__file__).parents[1] / 'BBMOD.spec'
    class Collected(Exception):
        pass
    def inspect(*args, **kwargs):
        assert kwargs['binaries'] == []
        assert not any('native' in source for source, target in kwargs['datas'])
        raise Collected()
    monkeypatch.setenv('PATH', os.environ['PATH'])
    with pytest.raises(Collected):
        runpy.run_path(str(spec), init_globals={'SPECPATH': str(tmp_path), 'Analysis': inspect})

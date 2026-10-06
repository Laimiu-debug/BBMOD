import hashlib
import json
from pathlib import Path
from unittest.mock import patch
import zipfile

import pytest

from core import io_util, local_mod_archive
from core.settings import Settings


def test_atomic_write_keeps_previous_file_when_replace_fails(tmp_path):
    target = tmp_path / 'state' / 'value.json'
    io_util.atomic_write_json(target, {'name': '旧值'})
    with patch.object(io_util.os, 'replace', side_effect=OSError('disk full')), pytest.raises(OSError):
        io_util.atomic_write_json(target, {'name': '新值'})
    assert json.loads(target.read_text(encoding='utf-8')) == {'name': '旧值'}
    assert [p.name for p in target.parent.iterdir()] == ['value.json']


def test_file_sha256_streams_content(tmp_path):
    path = tmp_path / 'blob.bin'
    path.write_bytes(b'x' * (3 * 1024 * 1024 + 7))
    assert io_util.file_sha256(path) == hashlib.sha256(path.read_bytes()).hexdigest()


def test_unreadable_settings_are_preserved_before_reset(tmp_path, monkeypatch):
    monkeypatch.setenv('APPDATA', str(tmp_path))
    path = tmp_path / 'BBMOD' / 'settings.json'
    path.parent.mkdir()
    path.write_text('{"game_path": "E:/Game"', encoding='utf-8')
    settings = Settings()
    assert settings.data == {}
    assert path.with_name('settings.json.corrupt').read_text(encoding='utf-8') == '{"game_path": "E:/Game"'
    settings.set('theme', 'dark')
    assert json.loads(path.read_text(encoding='utf-8')) == {'theme': 'dark'}
    assert Settings().get('theme') == 'dark'


def test_settings_reject_non_object_json(tmp_path, monkeypatch):
    monkeypatch.setenv('APPDATA', str(tmp_path))
    path = tmp_path / 'BBMOD' / 'settings.json'
    path.parent.mkdir()
    path.write_text('[1, 2]', encoding='utf-8')
    assert Settings().get('anything', 'default') == 'default'
    assert path.with_name('settings.json.corrupt').exists()



def test_locked_settings_are_kept_and_merged_on_save(tmp_path, monkeypatch):
    monkeypatch.setenv('APPDATA', str(tmp_path))
    path = tmp_path / 'BBMOD' / 'settings.json'
    path.parent.mkdir()
    path.write_text('{"game_path": "E:/Game", "theme": "light"}', encoding='utf-8')
    original = Path.read_text
    locked = [True]

    def read_text(self, *args, **kwargs):
        if self == path and locked[0]:
            raise PermissionError(32, 'sharing violation')
        return original(self, *args, **kwargs)
    monkeypatch.setattr(Path, 'read_text', read_text)
    monkeypatch.setattr('core.settings.time.sleep', lambda _: None)
    settings = Settings()
    assert settings.data == {} and not path.with_name('settings.json.corrupt').exists()
    locked[0] = False
    settings.set('theme', 'dark')
    assert json.loads(path.read_text(encoding='utf-8')) == {'game_path': 'E:/Game', 'theme': 'dark'}


def test_invalid_utf8_settings_are_backed_up_before_reset(tmp_path, monkeypatch):
    monkeypatch.setenv('APPDATA', str(tmp_path))
    path = tmp_path / 'BBMOD' / 'settings.json'
    path.parent.mkdir()
    original = b'\xff\xfeinvalid'
    path.write_bytes(original)
    settings = Settings()
    assert settings.data == {}
    assert path.with_name('settings.json.corrupt').read_bytes() == original
    settings.set('theme', 'dark')
    assert Settings().get('theme') == 'dark'


def test_persistent_read_failure_never_overwrites_settings(tmp_path, monkeypatch):
    monkeypatch.setenv('APPDATA', str(tmp_path))
    path = tmp_path / 'BBMOD' / 'settings.json'
    path.parent.mkdir()
    original = b'{"game_path": "E:/Game", "theme": "light"}'
    path.write_bytes(original)
    with patch.object(Settings, '_read', side_effect=PermissionError('locked')):
        settings = Settings()
        with pytest.raises(PermissionError):
            settings.set('theme', 'dark')
    assert path.read_bytes() == original
    settings.save()
    assert json.loads(path.read_text(encoding='utf-8')) == {'game_path': 'E:/Game', 'theme': 'dark'}


def test_failed_corrupt_backup_blocks_save_until_preserved(tmp_path, monkeypatch):
    monkeypatch.setenv('APPDATA', str(tmp_path))
    path = tmp_path / 'BBMOD' / 'settings.json'
    path.parent.mkdir()
    path.write_bytes(b'\xffbroken')
    with patch('core.settings.os.replace', side_effect=PermissionError('locked')):
        settings = Settings()
        with pytest.raises(PermissionError):
            settings.set('theme', 'dark')
    assert path.read_bytes() == b'\xffbroken'
    settings.save()
    assert path.with_name('settings.json.corrupt').read_bytes() == b'\xffbroken'
    assert Settings().get('theme') == 'dark'

def test_staged_packages_stream_outer_and_nested_archives(tmp_path, monkeypatch):
    inner = tmp_path / 'inner.zip'
    with zipfile.ZipFile(inner, 'w') as archive:
        archive.writestr('scripts/inner.nut', 'y' * 4096)
    source = tmp_path / 'mod.zip'
    with zipfile.ZipFile(source, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('scripts/a.nut', 'x' * 4096)
        archive.write(inner, 'mod_inner.zip')
    staging = tmp_path / 'stage'
    staging.mkdir()
    staged = {p.name: p.read_bytes() for p in local_mod_archive.staged_packages(source, staging)}
    assert staged == {'mod.zip': source.read_bytes(), 'mod_inner.zip': inner.read_bytes()}
    monkeypatch.setattr(local_mod_archive, 'MAX_ARCHIVE', inner.stat().st_size - 1)
    second = tmp_path / 'stage2'
    second.mkdir()
    with pytest.raises(ValueError):
        local_mod_archive.staged_packages(source, second)

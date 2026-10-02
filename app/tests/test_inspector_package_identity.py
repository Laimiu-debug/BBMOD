"""Existing reader manifests supply display metadata without filename guessing."""
import hashlib
import json
import zipfile

import pytest

from core.inspector_mod import MANIFEST, SCRIPT, UI_MODULE
from core.modinfo import analyze_zip


def reader_package(tmp_path, *, filename='renamed.zip', change=None, extras=None, raw=None):
    files = {SCRIPT: b'// existing reader script', UI_MODULE: b'// existing tooltip UI'}
    manifest = {'id': 'bbmod_item_inspector', 'schema': 1, 'version': 3,
                'files': {name: hashlib.sha256(value).hexdigest() for name, value in files.items()}}
    if change:
        change(manifest)
    path = tmp_path / filename
    with zipfile.ZipFile(path, 'w') as archive:
        for name, value in files.items():
            archive.writestr(name, value)
        archive.writestr(MANIFEST, raw if raw is not None else json.dumps(manifest))
        for name, value in (extras or {}).items():
            archive.writestr(name, value)
    return path


@pytest.mark.parametrize('filename', ['renamed.zip', 'mod_bbmod_item_inspector.zip'])
def test_existing_reader_manifest_supplies_chinese_name_and_real_version(tmp_path, filename):
    info = analyze_zip(reader_package(tmp_path, filename=filename))
    assert info.package_id == info.primary_id == 'bbmod_item_inspector'
    assert info.package_name == 'BBMOD 装备读取器'
    assert info.package_version == '3'
    assert not info.analysis_errors


@pytest.mark.parametrize('change', [
    lambda meta: meta.update(id='third_party'),
    lambda meta: meta.update(schema=2),
    lambda meta: meta.update(schema=True),
    lambda meta: meta.update(version=True),
    lambda meta: meta.update(version=-1),
    lambda meta: meta.update(version='3'),
    lambda meta: meta.update(version=3.5),
    lambda meta: meta.update(files=[]),
    lambda meta: meta['files'].pop(SCRIPT),
    lambda meta: meta['files'].update({SCRIPT: 'not a SHA-256'}),
    lambda meta: meta['files'].update({'missing.nut': 'a' * 64}),
])
def test_unrecognized_reader_metadata_does_not_claim_package_identity(tmp_path, change):
    info = analyze_zip(reader_package(tmp_path, change=change))
    assert info.package_id == info.package_name == info.package_version == ''


def test_reader_manifest_does_not_label_unrelated_bundled_scripts(tmp_path):
    info = analyze_zip(reader_package(tmp_path, extras={'scripts/other.nut': '// another mod'}))
    assert info.package_id == ''


@pytest.mark.parametrize('raw', [b'{broken json', b' ' * (64 * 1024 + 1)],
                         ids=['invalid-json', 'oversized-manifest'])
def test_reader_manifest_parse_errors_are_bounded_and_reported(tmp_path, raw):
    info = analyze_zip(reader_package(tmp_path, raw=raw))
    assert info.package_id == ''
    assert any(MANIFEST in message for message in info.analysis_errors)


def test_reader_filename_without_manifest_does_not_supply_identity(tmp_path):
    path = tmp_path / 'mod_bbmod_item_inspector.zip'
    with zipfile.ZipFile(path, 'w') as archive:
        archive.writestr(SCRIPT, '// unregistered script without a manifest')
    info = analyze_zip(path)
    assert info.package_id == info.package_name == info.package_version == ''

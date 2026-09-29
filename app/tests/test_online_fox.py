import hashlib
import io
import zipfile
from unittest.mock import patch

import pytest

from core.archive_safety import inspect_archive, valid_install_name
from core.online_catalog import OnlineInstaller
from core.preload_merge import FILENAME
from core.diagnostics import diagnose_mods
from core.modinfo import analyze_zip
from test_online_catalog import package, manager


def archive(*names):
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w') as z:
        for name in names:
            z.writestr(name, '// fixture')
    output.seek(0)
    return output


def test_framework_script_trees_and_preloads_are_accepted():
    result = inspect_archive(archive('scripts/!mods_preload/test.nut',
        'modern_hooks/hooks.nut', 'msu/class.nut', 'preload/brushes.txt'))
    assert result['script_count'] == 3
    assert valid_install_name('data_fox_zhcn.zip')
    assert not valid_install_name('data_001.zip')
    assert not valid_install_name('bbmod_payload.zip')


def test_modern_hooks_optional_msu_adapter_is_not_a_reverse_dependency(tmp_path):
    path=tmp_path/'modern.zip'
    with zipfile.ZipFile(path,'w') as z:
        z.writestr('scripts/!mods_preload/modern.nut',
            '::Hooks.register("mod_modern_hooks", "0.6.0", "Modern Hooks");\n'
            'if ("MSU" in getroottable()) { ::MSU.Log.printData("optional"); }')
    info=analyze_zip(path)
    assert info.uses_msu
    assert not [i for i in diagnose_mods([info]).issues if i.severity=='error' and i.dependency=='mod_msu']


@pytest.mark.parametrize('path', ['msu/../evil.nut', 'modern_hooks/run.exe',
    'msu/install.py', 'preload/load.nut', 'unknown/mod.nut', 'wrapper/scripts/test.nut'])
def test_custom_root_extension_does_not_accept_installers_or_wrappers(path):
    with pytest.raises(ValueError):
        inspect_archive(archive('scripts/ok.nut', path))


def with_preload(path, item, text):
    with zipfile.ZipFile(path, 'a') as z:
        z.writestr('preload/brushes.txt', text)
    item.update(size=path.stat().st_size, sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def test_online_update_and_rollback_rebuild_preloads(tmp_path, manager):
    old, one = package(tmp_path)
    with_preload(old, one, 'first.brush\n')
    new, two = package(tmp_path, '2.0', one['id'])
    with_preload(new, two, 'second.brush\n')
    installer = OnlineInstaller(manager)
    def contents():
        with zipfile.ZipFile(manager.data / FILENAME) as z:
            return z.read('preload/brushes.txt')
    installer.install('http://localhost:8765', one, old)
    assert contents() == b'first.brush\n'
    installer.install('http://localhost:8765', two, new)
    assert contents() == b'second.brush\n'
    installer.rollback(one['file_name'])
    assert contents() == b'first.brush\n'


def test_failed_receipt_preparation_keeps_preload_and_mod(tmp_path, manager):
    old, one = package(tmp_path)
    with_preload(old, one, 'first.brush\n')
    new, two = package(tmp_path, '2.0', one['id'])
    with_preload(new, two, 'second.brush\n')
    installer = OnlineInstaller(manager)
    installer.install('http://localhost:8765', one, old)
    before = {p: p.read_bytes() for p in [manager.data / one['file_name'],
        manager.data / FILENAME, installer.state_path]}
    with patch('core.online_catalog._atomic_json', side_effect=OSError('disk full')):
        with pytest.raises(OSError):
            installer.install('http://localhost:8765', two, new)
    assert all(p.read_bytes() == value for p, value in before.items())

import io
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import zipfile

import pytest
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication, QMessageBox

from core.modmanager import ModManager
from core.mod_transactions import digest
from core.dependency_versions import satisfies
from core.support_report import redact
from core.web_links import parse_link
from ui.mods_page import ModsPage


def package(path, contents=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, 'w') as z:
        for name, value in (contents or {'scripts/test.nut': '// test'}).items():
            z.writestr(name, value)
    return path


@pytest.fixture
def manager(tmp_path):
    root = tmp_path / 'game'
    (root / 'data').mkdir(parents=True)
    (root / 'data/data_001.dat').write_bytes(b'official')
    return ModManager(root)


@pytest.mark.parametrize('disabled', [True, False])
def test_uninstall_is_different_from_disable(manager, tmp_path, disabled):
    source = package(tmp_path / 'repo' / 'mod.zip')
    manager.install(source)
    if disabled:
        manager.disable(source.name)
        assert manager.scan()[0].enabled is False
    manager.uninstall(source.name, from_disabled=disabled)
    assert manager.scan() == []
    assert source.exists()
    assert (manager.data / 'data_001.dat').read_bytes() == b'official'


@pytest.mark.parametrize('name', ['../other.zip', '..\\other.zip', 'data_001.dat', 'settings.json'])
def test_uninstall_rejects_other_files(manager, name):
    with pytest.raises(ValueError):
        manager.uninstall(name)


def test_bad_zip_and_bad_nested_zip_never_touch_game(manager, tmp_path):
    source = tmp_path / 'broken.zip'
    source.write_bytes(b'invalid')
    with pytest.raises(ValueError):
        manager.install(source)
    source = package(tmp_path / 'outer.zip', {'nested.zip': b'bad ZIP'})
    with pytest.raises(ValueError):
        manager.install(source)
    assert manager.scan() == []


def test_nested_zip_install_is_complete_or_unchanged(manager, tmp_path):
    inner = io.BytesIO()
    with zipfile.ZipFile(inner, 'w') as z:
        z.writestr('scripts/inner.nut', '// inner')
    source = package(tmp_path / 'outer.zip', {'folder/inner.zip': inner.getvalue()})
    package(manager.data / 'inner.zip')
    with pytest.raises(FileExistsError):
        manager.install(source)
    assert not (manager.data / source.name).exists()
    (manager.data / 'inner.zip').unlink()
    assert len(manager.install(source)) == 2


def test_profile_missing_file_keeps_existing_mod(manager):
    wanted = package(manager.data / 'wanted.zip')
    manager.save_profile('wanted')
    wanted.unlink()
    current = package(manager.data / 'current.zip')
    with pytest.raises(FileNotFoundError):
        manager.apply_profile('wanted')
    assert current.exists()


def test_profile_preview_and_failed_commit_restore_all_files(manager):
    package(manager.data / 'wanted.zip')
    manager.save_profile('wanted')
    manager.disable('wanted.zip')
    package(manager.data / 'current.zip')
    expected = {'enable': ['wanted.zip'], 'disable': ['current.zip']}
    assert manager.preview_profile('wanted') == expected
    import os
    replace = os.replace

    def fail_once(source, target):
        if Path(target) == manager.disabled_dir / 'current.zip' and str(source).endswith('.after'):
            raise PermissionError('locked')
        return replace(source, target)

    with patch('core.mod_transactions.os.replace', side_effect=fail_once):
        with pytest.raises(PermissionError):
            manager.apply_profile('wanted', expected=expected)
    assert (manager.disabled_dir / 'wanted.zip').exists()
    assert (manager.data / 'current.zip').exists()
    assert not (manager.data / 'wanted.zip').exists()
    assert not manager.transaction.journal.exists()
    assert manager.apply_profile('wanted', expected=expected) == (1, 1)


def test_interrupted_uninstall_recovers_file_and_receipt(manager):
    name = 'mod.zip'
    package(manager.data / name)
    state = manager.disabled_dir / 'online-catalog.json'
    state.parent.mkdir(exist_ok=True)
    state.write_text(json.dumps({'mods': {name: {'id': 'test'}}}), encoding='utf-8')
    import os
    replace = os.replace

    def interrupt(source, target):
        if Path(target) == state and str(source).endswith('.after'):
            raise KeyboardInterrupt('simulated interruption')
        return replace(source, target)

    with patch('core.mod_transactions.os.replace', side_effect=interrupt):
        with pytest.raises(KeyboardInterrupt):
            manager.uninstall(name)
    assert manager.transaction.journal.exists()
    assert not (manager.data / name).exists()
    ModManager(manager.root).transaction.recover()
    assert (manager.data / name).exists()
    assert name in json.loads(state.read_text())['mods']


def test_receipt_failure_rolls_back_uninstall(manager):
    package(manager.data / 'mod.zip')
    state = manager.disabled_dir / 'online-catalog.json'
    state.parent.mkdir(exist_ok=True)
    state.write_text(json.dumps({'mods': {'mod.zip': {'id': 'test'}}}))
    import os
    replace = os.replace

    def fail(source, target):
        if Path(target) == state and str(source).endswith('.after'):
            raise OSError('full disk')
        return replace(source, target)

    with patch('core.mod_transactions.os.replace', side_effect=fail):
        with pytest.raises(OSError):
            manager.uninstall('mod.zip')
    assert (manager.data / 'mod.zip').exists()
    assert 'mod.zip' in json.loads(state.read_text())['mods']


@pytest.mark.parametrize('disabled', [True, False])
def test_uninstall_removes_linked_localization_profiles(manager, tmp_path, disabled):
    from core.localization_profiles import LocalizationProfiles, BUILTIN
    from core.l10n import BRAND_META, PACKAGE_ID
    folder = manager.disabled_dir if disabled else manager.data
    source = package(folder / 'custom.zip', {BRAND_META: json.dumps({'package_id': PACKAGE_ID}),
                                            'ui/chinese.js': 'translation'})
    font = package(manager.data / 'font.zip', {'gfx/fonts/example.png': 'font'})
    unrelated = package(tmp_path / 'imported.zip', {'ui/unrelated.js': 'other translation'})
    profiles = LocalizationProfiles(manager.root)
    with patch('core.game.is_game_running', return_value=False):
        profiles.register('BBMOD 独立汉化', [source], builtin=True)
        linked = profiles.register('汉化与字体', [source, font])
        keep = profiles.register('尚未应用的方案', [unrelated])
    manager.uninstall(source.name, from_disabled=disabled)
    assert set(profiles.profiles()) == {keep}
    assert BUILTIN not in profiles.profiles() and linked not in profiles.profiles()
    assert font.exists() and unrelated.exists()
    assert len(list(profiles.store.rglob('*.zip'))) == 4


def test_uninstall_preserves_profile_until_last_copy_is_removed(manager):
    from core.localization_profiles import LocalizationProfiles
    active = package(manager.data / 'chinese.zip')
    disabled = package(manager.disabled_dir / 'chinese.zip')
    profiles = LocalizationProfiles(manager.root)
    with patch('core.game.is_game_running', return_value=False):
        key = profiles.register('汉化', [active])
    manager.uninstall(active.name)
    assert key in profiles.profiles() and disabled.exists()
    manager.uninstall(disabled.name, from_disabled=True)
    assert profiles.profiles() == {}


def test_uninstall_last_renamed_backup_removes_profile(manager):
    from core.localization_profiles import LocalizationProfiles
    source = package(manager.data / 'chinese.zip')
    profiles = LocalizationProfiles(manager.root)
    with patch('core.game.is_game_running', return_value=False):
        key = profiles.register('汉化', [source])
    renamed = manager.disabled_dir / 'chinese-backup.zip'
    renamed.parent.mkdir(exist_ok=True)
    renamed.write_bytes(source.read_bytes())
    manager.uninstall(source.name)
    assert key in profiles.profiles()
    manager.uninstall(renamed.name, from_disabled=True)
    assert profiles.profiles() == {}


@pytest.mark.parametrize('interrupted', [False, True])
def test_failed_localization_cleanup_recovers_mod_and_profile(manager, interrupted):
    from core.localization_profiles import LocalizationProfiles
    source = package(manager.data / 'chinese.zip')
    profiles = LocalizationProfiles(manager.root)
    with patch('core.game.is_game_running', return_value=False):
        key = profiles.register('汉化', [source])
    original = source.read_bytes()
    import os
    replace = os.replace

    def fail(source, target):
        if Path(target) == profiles.registry and str(source).endswith('.after'):
            raise KeyboardInterrupt('interrupted') if interrupted else OSError('full disk')
        return replace(source, target)

    with patch('core.mod_transactions.os.replace', side_effect=fail):
        with pytest.raises(KeyboardInterrupt if interrupted else OSError):
            manager.uninstall(source.name)
    if interrupted:
        assert not source.exists() and manager.transaction.journal.exists()
        ModManager(manager.root).transaction.recover()
    assert source.read_bytes() == original
    assert key in profiles.profiles()
    assert not manager.transaction.journal.exists()


def test_uninstall_waits_for_localization_recovery(manager):
    source = package(manager.data / 'chinese.zip')
    pending = manager.root / 'bbmod_localizations/pending-switch.json'
    pending.parent.mkdir()
    pending.write_text('{}')
    with pytest.raises(ValueError, match='恢复'):
        manager.uninstall(source.name)
    assert source.exists()


@pytest.mark.parametrize('relative', ['bbmod_localizations/other.json',
                                     'bbmod_localizations/packages/mod.zip',
                                     'bbmod_localizations/mod.zip'])
def test_mod_transaction_only_allows_exact_localization_registry(manager, relative):
    with pytest.raises(ValueError, match='路径'):
        manager.transaction.target(relative)


@pytest.mark.parametrize('requirement,version,expected', [
    ('mod_x >= 1.2.0', '1.10', True), ('mod_x(>=1.2)', '1.1.9', False),
    ('mod_x >= 1.2, < 2.0', '2.0', False), ('mod_x ^1.0', '1.2', None),
    ('mod_x >= 1.0', '1.1-beta', None), ('mod_x', '1.0', True)])
def test_dependency_comparison(requirement, version, expected):
    assert satisfies(requirement, version) is expected


def test_report_redacts_personal_information():
    source = 'C:\\Users\\Alice\\game\\log.html\ncontact alice@example.com\nserver 192.168.1.5'
    result = redact(source)
    assert 'Alice' not in result and 'alice@' not in result and '192.168' not in result


@pytest.mark.parametrize('link', ['bbmod://mods/../file', 'bbmod://evil/abcd',
    'https://bbmod.site/', 'bbmod://mods/00000000-0000-0000-0000-000000000001?url=https://evil'])
def test_web_link_cannot_inject_sources_or_files(link):
    with pytest.raises(ValueError):
        parse_link(link)


def test_valid_web_link():
    assert parse_link('bbmod://seeds/00000000-0000-0000-0000-000000000001') == ('seeds', '00000000-0000-0000-0000-000000000001')


def test_pending_recovery_blocks_other_file_workflows(manager):
    from core.online_catalog import OnlineInstaller
    from core.localization_profiles import LocalizationProfiles
    manager.transaction.directory.mkdir(parents=True)
    manager.transaction.journal.write_text('{}')
    with pytest.raises(ValueError, match='恢复'):
        OnlineInstaller(manager).install('', {}, None)
    with pytest.raises(ValueError, match='恢复'):
        OnlineInstaller(manager).rollback('mod.zip')
    with pytest.raises(RuntimeError, match='恢复'):
        LocalizationProfiles(manager.root)._ensure_idle()


def test_seed_download_is_bounded_and_validated(monkeypatch):
    from core import web_links
    calls = []
    def request(url):
        calls.append(url)
        return io.BytesIO(b'x' * (64 * 1024 + 1))
    monkeypatch.setattr(web_links, '_request', request)
    with pytest.raises(ValueError, match='大小限制'):
        web_links.fetch_seed('00000000-0000-0000-0000-000000000001')
    assert calls == [web_links.SITE_ORIGIN + '/api/v1/seeds/00000000-0000-0000-0000-000000000001/']


def test_existing_instance_receives_link(tmp_path):
    import subprocess
    import sys
    from ui.single_instance import SingleInstance
    from PySide6.QtTest import QTest
    application = QApplication.instance() or QApplication([])
    first = SingleInstance(tmp_path)
    received = []
    first.received.connect(received.append)
    try:
        assert first.start()
        link = 'bbmod://mods/00000000-0000-0000-0000-000000000001'
        script = ('from pathlib import Path; from PySide6.QtCore import QCoreApplication; '
                  'from ui.single_instance import SingleInstance; import sys; '
                  'app=QCoreApplication([]); instance=SingleInstance(Path(sys.argv[1])); '
                  'sys.exit(1 if instance.start(sys.argv[2]) else 0)')
        child = subprocess.Popen([sys.executable, '-c', script, str(tmp_path), link],
                                 cwd=Path(__file__).resolve().parents[1])
        for _ in range(150):
            QTest.qWait(20)
            if child.poll() is not None:
                break
        if child.poll() is None:
            child.kill()
        assert child.wait(timeout=5) == 0
        application.processEvents()
        assert received == [link]
    finally:
        first.server.close()
        first.lock.unlock()


class Context(QObject):
    management_changed = Signal(bool)
    session_changed = Signal(bool)
    data_changed = Signal()

    def __init__(self, manager):
        super().__init__()
        self.mm = manager
        self.management_busy = self.seedgen_active = False
        self.settings = SimpleNamespace(get=lambda key, default=None: default)


def test_localization_row_names_package_and_labels_embedded_hooks(manager):
    from core.l10n import BRAND_META, PACKAGE_ID
    from core.l10n_compat import hooks_assets
    application = QApplication.instance() or QApplication([])
    package(manager.data / 'custom.zip', {**hooks_assets(), BRAND_META: json.dumps({
        'package_id': PACKAGE_ID, 'version': '0.3.0-rc.9'})})
    context = Context(manager)
    page = ModsPage(context)
    try:
        page.refresh()
        text = page.table.item(0, 2).text()
        tooltip = page.table.item(0, 2).toolTip()
        assert 'BBMOD 独立汉化' in text
        assert page.table.item(0, 3).text() == '0.3.0-rc.9'
        assert PACKAGE_ID in tooltip and 'mod_hooks' in tooltip and '21.1' in tooltip
        for query in ('BBMOD 独立汉化', PACKAGE_ID, 'mod_hooks'):
            page.installed_search.setText(query)
            assert not page.table.isRowHidden(0)
    finally:
        page.close()
        application.processEvents()


def test_filter_and_batch_operations_use_visible_selected_rows(manager, monkeypatch):
    application = QApplication.instance() or QApplication([])
    monkeypatch.setattr('core.game.is_game_running', lambda: False)
    package(manager.data / 'active.zip')
    package(manager.disabled_dir / 'disabled.zip')
    context = Context(manager)
    page = ModsPage(context)
    page.refresh()
    page.state_filter.setCurrentText('已禁用')
    page.table.selectAll()
    with patch.object(QMessageBox, 'question', return_value=QMessageBox.Yes):
        page.uninstall()
    assert (manager.data / 'active.zip').exists()
    assert not (manager.disabled_dir / 'disabled.zip').exists()
    page.state_filter.setCurrentText('全部状态')
    page.table.selectAll()
    page._on_disable(False)
    assert page.table.item(0, 0).text() == '已禁用'
    page.table.selectAll()
    with patch.object(QMessageBox, 'question', return_value=QMessageBox.No):
        page.uninstall()
    assert page.table.rowCount() == 1
    page.close()
    application.processEvents()

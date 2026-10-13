"""Game discovery must survive missing/offline drives on a fresh profile."""
import os
from pathlib import Path, PureWindowsPath
import stat
import struct
from unittest.mock import Mock, patch

import pytest

from core import game


def make_game(root):
    (root / 'win32').mkdir(parents=True)
    (root / 'win32' / game.EXE_NAME).write_bytes(b'test fixture, not executable')
    (root / 'data').mkdir()
    return root


def write_pe_imports(executable, dependencies, delayed=()):
    """Small PE32 fixture with real import tables; never run this binary."""
    content = bytearray(4096)
    content[:2] = b'MZ'
    struct.pack_into('<I', content, 0x3C, 0x80)
    content[0x80:0x84] = b'PE\0\0'
    struct.pack_into('<HHIIIHH', content, 0x84, 0x14C, 1, 0, 0, 0, 224, 0x102)
    optional = 0x98
    struct.pack_into('<H', content, optional, 0x10B)
    struct.pack_into('<III', content, optional + 28, 0x400000, 0x1000, 0x200)
    struct.pack_into('<II', content, optional + 56, 0x2000, 0x200)
    struct.pack_into('<I', content, optional + 92, 16)
    section = optional + 224
    content[section:section + 8] = b'.rdata\0\0'
    struct.pack_into('<IIII', content, section + 8, 0xE00, 0x1000, 0xE00, 0x200)
    struct.pack_into('<I', content, section + 36, 0x40000040)
    cursor = 0x200

    def allocate(value):
        nonlocal cursor
        offset = cursor
        content[offset:offset + len(value)] = value
        cursor += len(value)
        return offset, 0x1000 + offset - 0x200

    for dlls, directory, width in ((dependencies, 1, 20), (delayed, 13, 32)):
        if not dlls:
            continue
        table, table_rva = allocate(bytes(width * (len(dlls) + 1)))
        struct.pack_into('<II', content, optional + 96 + directory * 8,
                         table_rva, width * (len(dlls) + 1))
        for index, dll in enumerate(dlls):
            _, name_rva = allocate(dll.encode('ascii') + b'\0')
            _, symbol_rva = allocate(b'\0\0FixtureFunction\0')
            _, thunk_rva = allocate(struct.pack('<II', symbol_rva, 0))
            if directory == 1:
                struct.pack_into('<IIIII', content, table + width * index,
                                 thunk_rva, 0, 0, name_rva, thunk_rva)
            else:
                struct.pack_into('<IIIIIIII', content, table + width * index,
                                 1, name_rva, 0, thunk_rva, thunk_rva, 0, 0, 0)
    executable.write_bytes(content)


@pytest.fixture(autouse=True)
def isolated_discovery(monkeypatch):
    monkeypatch.setattr(game, 'find_steam_root', Mock(return_value=None))
    monkeypatch.setattr(game, 'read_file_version', lambda _: game.SUPPORTED_VERSION)


def fallback_filesystem(monkeypatch, installed=None, winerror=87):
    """Intercept only default game paths; never access the machine's drives."""
    original_stat = Path.stat
    seen = []
    installed = PureWindowsPath(installed) if installed else None

    def fake_stat(path, *args, **kwargs):
        windows_path = PureWindowsPath(path)
        if (game.GAME_DIRNAME not in windows_path.parts
                or not {'SteamLibrary', 'Program Files (x86)'}.intersection(windows_path.parts)):
            return original_stat(path, *args, **kwargs)
        seen.append(windows_path)
        if windows_path.drive == 'D:':
            raise OSError(22, 'simulated unavailable drive', str(path), winerror)
        if installed and windows_path in (installed, installed / 'data'):
            mode = stat.S_IFDIR
        elif installed and windows_path == installed / 'win32' / game.EXE_NAME:
            mode = stat.S_IFREG
        else:
            raise FileNotFoundError(2, 'simulated missing path', str(path))
        return os.stat_result((mode, 0, 0, 0, 0, 0, 0, 0, 0, 0))

    monkeypatch.setattr(Path, 'stat', fake_stat)
    return seen


@pytest.mark.parametrize('library', ['E:/SteamLibrary', 'E:/Program Files (x86)/Steam'])
def test_fallback_uses_absolute_paths_and_continues_after_bad_drive(monkeypatch, library):
    root = Path(library) / 'steamapps/common' / game.GAME_DIRNAME
    seen = fallback_filesystem(monkeypatch, root)
    detected = game.locate_game()
    assert detected is not None and detected.root == root
    assert detected.exe == root / 'win32' / game.EXE_NAME
    assert detected.data_dir == root / 'data'
    assert all(path.is_absolute() for path in seen)
    assert any(path.drive == 'D:' for path in seen)
    assert not any(path.drive in ('F:', 'G:') for path in seen)


@pytest.mark.parametrize('winerror', [5, 21, 87])
def test_no_game_and_unavailable_drive_return_none(monkeypatch, winerror):
    fallback_filesystem(monkeypatch, winerror=winerror)
    assert game.locate_game() is None


@pytest.mark.parametrize('component', ['win32/BattleBrothers.exe', 'data'])
def test_inaccessible_manual_path_does_not_crash_or_select_another_game(tmp_path, monkeypatch, component):
    root = make_game(tmp_path / 'manual game')
    original_stat = Path.stat

    def denied(path, *args, **kwargs):
        if path == root / component:
            raise OSError(22, 'simulated invalid parameter', str(path), 87)
        return original_stat(path, *args, **kwargs)

    monkeypatch.setattr(Path, 'stat', denied)
    assert game.locate_game(str(root)) is None
    game.find_steam_root.assert_not_called()


def test_valid_manual_path_is_preserved(tmp_path):
    root = make_game(tmp_path / '中文游戏目录')
    detected = game.locate_game(str(root))
    assert detected.root == root and detected.version == game.SUPPORTED_VERSION
    game.find_steam_root.assert_not_called()


@pytest.mark.parametrize(('dependencies', 'delayed', 'expected'), [
    (['Galaxy.dll', 'KERNEL32.dll'], [], True),
    ([], ['GALAXY.DLL'], True),
    (['steam_api.dll'], [], False),
    (['Galaxy.dll', 'Steam_API.dll'], [], False),
    (['Galaxy.dll'], ['steam_api64.dll'], False),
    (['KERNEL32.dll'], [], False),
])
def test_gog_detection_reads_real_normal_and_delay_imports(tmp_path, dependencies, delayed, expected):
    executable = tmp_path / game.EXE_NAME
    write_pe_imports(executable, dependencies, delayed)
    assert game._is_gog_executable(executable) is expected


@pytest.mark.parametrize('contents', [None, b'not a PE file'])
def test_missing_or_invalid_exe_keeps_steam_guard(tmp_path, contents):
    executable = tmp_path / game.EXE_NAME
    if contents is not None:
        executable.write_bytes(contents)
    assert not game._is_gog_executable(executable)


@pytest.mark.parametrize('mode', ['plain', 'localization', 'seed'])
def test_gog_launch_with_another_steam_install_preserves_selected_game(tmp_path, monkeypatch, mode):
    root = make_game(tmp_path / '独立游戏')
    executable = root / 'win32' / game.EXE_NAME
    write_pe_imports(executable, ['Galaxy.dll'])
    selected = game.locate_game(str(root))
    steam = tmp_path / 'steam'
    (steam / 'steamapps/common' / game.GAME_DIRNAME).mkdir(parents=True)
    (steam / f'steamapps/appmanifest_{game.APP_ID}.acf').write_text('"installdir" "Battle Brothers"')
    # A leftover Steam DLL must not override what the EXE actually imports.
    (executable.parent / 'steam_api.dll').write_bytes(b'unused fixture')
    discovery = Mock(return_value=steam)
    monkeypatch.setattr(game, 'find_steam_root', discovery)
    before = {path: path.read_bytes() for path in root.rglob('*') if path.is_file()}
    with patch.object(game.os, 'startfile', create=True) as start, \
            patch.object(game, 'is_game_running', return_value=False):
        if mode == 'localization':
            from core.localization_profiles import LocalizationProfiles
            assert LocalizationProfiles(root).launch(selected, tmp_path / 'runtime') == {'mode': 'current'}
        elif mode == 'seed':
            assert game.launch_game(selected, via_steam=False)
        else:
            assert game.launch_executable(selected) == {'mode': 'current'}
        start.assert_called_once_with(str(executable), cwd=str(executable.parent))
    discovery.assert_not_called()
    assert all(path.read_bytes() == contents for path, contents in before.items())


def test_custom_windows_manual_path_does_not_require_steam():
    root = Path('E:/gaME/Battle Brothers1.5.2.3/Battle Brothers')

    def custom_stat(path, *args, **kwargs):
        if path == root / 'win32' / game.EXE_NAME:
            mode = stat.S_IFREG
        elif path == root / 'data':
            mode = stat.S_IFDIR
        else:
            raise FileNotFoundError(2, 'unrelated path', str(path))
        return os.stat_result((mode, 0, 0, 0, 0, 0, 0, 0, 0, 0))

    with patch.object(Path, 'stat', custom_stat):
        detected = game.locate_game(str(root))
    assert detected.root == root
    game.find_steam_root.assert_not_called()


def test_steam_libraries_skip_inaccessible_and_missing_entries(tmp_path, monkeypatch):
    steam = tmp_path / 'steam'
    (steam / 'steamapps').mkdir(parents=True)
    missing, offline, available = (tmp_path / name for name in ('missing', 'offline', 'available'))
    available.mkdir()
    paths = [missing, offline, available, available, steam]
    text = '\n'.join('"path" "' + str(path).replace('\\', '\\\\') + '"' for path in paths)
    (steam / 'steamapps/libraryfolders.vdf').write_text(text, encoding='utf-8')
    original_stat = Path.stat

    def denied(path, *args, **kwargs):
        if path == offline:
            raise OSError(22, 'simulated unavailable library', str(path), 87)
        return original_stat(path, *args, **kwargs)

    monkeypatch.setattr(Path, 'stat', denied)
    assert game.list_steam_libraries(steam) == [steam, available]


@pytest.mark.parametrize('missing', [False, True])
def test_unreadable_library_index_keeps_primary_steam_root(tmp_path, missing):
    error = FileNotFoundError(2, 'missing index') if missing else PermissionError(13, 'unreadable index')
    with patch.object(Path, 'stat', side_effect=error), patch.object(Path, 'read_text', side_effect=error):
        assert game.list_steam_libraries(tmp_path) == [tmp_path]


@pytest.mark.parametrize('problem', ['exe_inaccessible', 'data_inaccessible', 'exe_is_directory', 'data_missing'])
def test_steam_scan_skips_invalid_game_and_stops_at_valid_install(tmp_path, monkeypatch, problem):
    first, second = tmp_path / 'first', tmp_path / 'second'
    bad = make_game(first / 'steamapps/common' / game.GAME_DIRNAME)
    good = make_game(second / 'steamapps/common' / game.GAME_DIRNAME)
    if problem == 'exe_is_directory':
        (bad / 'win32' / game.EXE_NAME).unlink()
        (bad / 'win32' / game.EXE_NAME).mkdir()
    elif problem == 'data_missing':
        (bad / 'data').rmdir()
    monkeypatch.setattr(game, 'find_steam_root', lambda: first)
    monkeypatch.setattr(game, 'list_steam_libraries', lambda _: [first, second])
    original_stat = Path.stat

    def guarded_stat(path, *args, **kwargs):
        if not path.is_relative_to(tmp_path):
            pytest.fail(f'Unrelated drive scanned despite an available Steam installation: {path}')
        if ((problem == 'exe_inaccessible' and path == bad / 'win32' / game.EXE_NAME)
                or (problem == 'data_inaccessible' and path == bad / 'data')):
            raise OSError(22, 'simulated unavailable game file', str(path), 87)
        return original_stat(path, *args, **kwargs)

    with patch.object(Path, 'stat', guarded_stat):
        detected = game.locate_game()
    assert detected.root == good


@pytest.mark.parametrize('saved_path', [False, True])
def test_window_opens_and_directory_picker_recovers_after_detection_error(tmp_path, monkeypatch, saved_path):
    from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox
    from core.settings import Settings
    from ui.main_window import MainWindow
    from ui.workers import Worker

    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv('APPDATA', str(tmp_path / 'profile'))
    fallback_filesystem(monkeypatch)
    monkeypatch.setattr(game, 'find_log_write_path', lambda: None)
    offline = 'D:/SteamLibrary/steamapps/common/Battle Brothers'
    if saved_path:
        Settings().set('game_path', offline)
    root = make_game(tmp_path / 'gaME/Battle Brothers1.5.2.3/Battle Brothers')
    window = MainWindow(auto_updates=False)
    try:
        window.show()
        app.processEvents()
        assert window.isVisible() and window.ctx.game is None
        assert '未找到游戏' in window.path_edit.text()
        assert window.pick_btn.isEnabled()
        with patch.object(QFileDialog, 'getExistingDirectory', return_value=offline), \
                patch.object(QMessageBox, 'warning') as warning:
            window.pick_btn.click()
            warning.assert_called_once()
        assert window.ctx.game is None
        with patch.object(QFileDialog, 'getExistingDirectory', return_value=str(root)):
            window.pick_btn.click()
        assert window.ctx.game.root == root
        assert window.path_edit.text() == str(root)
        assert Settings().get('game_path') == str(root)
    finally:
        for worker in window.findChildren(Worker):
            assert worker.wait(5000)
        app.processEvents()
        window.close()
        window.deleteLater()
        app.processEvents()

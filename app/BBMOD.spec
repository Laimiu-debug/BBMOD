# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from pathlib import Path

# Resolve native dependencies from Python and Windows only. Unrelated tools on
# PATH can ship identically named ICU/OpenSSL/CRT DLLs with incompatible exports.
windows_dir = Path(os.environ.get('SystemRoot', r'C:\Windows'))
build_path = [Path(sys.base_prefix), Path(sys.base_prefix) / 'DLLs',
              windows_dir / 'System32', windows_dir]
os.environ['PATH'] = os.pathsep.join(str(path) for path in build_path if path.is_dir())

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('data', 'data'), ('seedgen', 'seedgen'), ('assets', 'assets'), ('localization', 'localization'),
           ('build/native/bbmod_launch.exe', 'native/bin'), ('build/native/bbmod_han.dll', 'native/bin'),
           ('native/vendor/minhook/LICENSE.txt', 'native/licenses')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
# Windows 10/11 supply the Universal CRT. Do not pick up obsolete UCRT/API
# shims from unrelated tools on PATH (e.g. image-conversion runtimes).
a.binaries = [entry for entry in a.binaries
              if entry[0].replace('\\', '/').rsplit('/', 1)[-1].lower() != 'ucrtbase.dll'
              and not entry[0].replace('\\', '/').rsplit('/', 1)[-1].lower().startswith('api-ms-win-')]
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='BBMOD',
    version='data/windows-version.txt',
    icon='assets/bbmod.ico',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

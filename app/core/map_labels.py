"""Package the script/UI map renderer, without executable font components."""
from __future__ import annotations

import hashlib
from pathlib import Path
import struct
import zlib

from .paths import resource_path

MODE = 'mod_ui'
SUPPORTED_EXE_SHA256 = '345126b48b57719e71c80cd21b778f1a0bfda52295cc136ce3895ef43bbafd6a'
SCRIPT_ENTRY = 'scripts/!mods_preload/bbmod_map_labels.nut'
REGION_FONT = 'gfx/fonts/cinzel_bold_100.png'
ASSETS = {
    SCRIPT_ENTRY: 'map_labels.nut',
    'ui/mods/bbmod_l10n/map_labels.js': 'map_labels.js',
    'ui/mods/bbmod_l10n/map_labels.css': 'map_labels.css',
    'ui/mods/bbmod_l10n/NotoSerifSC-SemiBold.ttf': 'NotoSerifSC-SemiBold.ttf',
    'ui/mods/bbmod_l10n/MAP-FONT-LICENSE.txt': 'MAP-FONT-LICENSE.txt',
}


def check_executable(exe: Path) -> None:
    """Pin the official input used to build translated bytecode and UI assets."""
    with Path(exe).open('rb') as source:
        digest = hashlib.file_digest(source, 'sha256').hexdigest()
    if digest != SUPPORTED_EXE_SHA256:
        raise ValueError('当前游戏主程序尚未通过独立汉化构建验证。当前支持 Steam 原版 1.5.2.3。')


def transparent_region_font() -> bytes:
    # Exact atlas size of the supported vanilla region font. Retain the native
    # metrics and region objects; the ordinary ZIP resource overlay hides ink.
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))
    header = struct.pack('>IIBBBBB', 2048, 1024, 8, 6, 0, 0, 0)
    pixels = zlib.compress(bytes((2048 * 4 + 1) * 1024), 9)
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', header) + chunk(b'IDAT', pixels) + chunk(b'IEND', b'')


def write_assets(archive) -> dict:
    files = {entry: resource_path('localization/' + name).read_bytes() for entry, name in ASSETS.items()}
    files[REGION_FONT] = transparent_region_font()
    for entry, raw in files.items():
        archive.writestr(entry, raw)
    return {'map_renderer': MODE, 'map_renderer_sha256': {
        entry: hashlib.sha256(raw).hexdigest() for entry, raw in files.items()}}


def validate_assets(archive, manifest) -> None:
    hashes = manifest.get('map_renderer_sha256')
    if manifest.get('map_renderer') != MODE or not isinstance(hashes, dict) or set(hashes) != {*ASSETS, REGION_FONT}:
        raise ValueError('中文地图显示资源不完整，请重新生成并应用独立汉化')
    for entry, expected in hashes.items():
        if archive.getinfo(entry).file_size > 32 * 1024 * 1024:
            raise ValueError('中文地图显示资源过大：' + entry)
        if hashlib.sha256(archive.read(entry)).hexdigest() != expected:
            raise ValueError('中文地图显示资源校验失败：' + entry)

"""Shared, bounded ZIP validation. Reads data; never extracts or executes a MOD."""
from __future__ import annotations

import hashlib
import re
import stat
import zipfile
from pathlib import PurePosixPath

INSTALL_NAME = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,94}\.zip\Z')
ROOTS = {'scripts', 'ui', 'gfx', 'sounds', 'music', 'brushes', 'fonts'}
FORBIDDEN = {'.exe', '.dll', '.com', '.bat', '.cmd', '.ps1', '.vbs', '.msi', '.scr', '.lnk', '.jar', '.zip', '.rar', '.7z'}


def valid_install_name(name):
    return isinstance(name, str) and bool(INSTALL_NAME.fullmatch(name)) and not name.lower().startswith(('data_', 'bbmod_'))


def inspect_archive(stream, *, max_bytes=100 * 1024 * 1024):
    stream.seek(0, 2)
    size = stream.tell()
    if not 0 < size <= max_bytes:
        raise ValueError(f'ZIP 大小须在 1 字节至 {max_bytes // 1024 // 1024} MB 之间。')
    stream.seek(0)
    sha = hashlib.sha256()
    while block := stream.read(1024 * 1024):
        sha.update(block)
    stream.seek(0)
    try:
        with zipfile.ZipFile(stream) as archive:
            infos = archive.infolist()
            if not infos or len(infos) > 10000:
                raise ValueError('ZIP 为空或包含超过 10000 个文件。')
            total = 0
            seen = set()
            has_game_file = False
            script_count = 0
            for entry in infos:
                # ZipInfo normalizes backslashes on Windows and strips NULs. Validate
                # the original name so server and desktop enforce the same policy.
                name = entry.orig_filename
                path = PurePosixPath(name)
                if (not name or '\\' in name or ':' in name or '\x00' in name or path.is_absolute()
                        or '..' in path.parts or any(ord(c) < 32 for c in name)):
                    raise ValueError('ZIP 包含不安全的文件路径。')
                canonical = str(path).casefold()
                if canonical in seen:
                    raise ValueError('ZIP 包含重复文件名（忽略大小写）。')
                seen.add(canonical)
                if stat.S_ISLNK(entry.external_attr >> 16) or entry.flag_bits & 1:
                    raise ValueError('不接受符号链接或加密 ZIP。')
                if entry.is_dir():
                    continue
                if path.suffix.lower() in FORBIDDEN:
                    raise ValueError('仅接受可直接放入 data 目录的 MOD ZIP，不接受程序、脚本安装器或套娃压缩包。')
                if path.parts[0].lower() in ROOTS:
                    has_game_file = True
                elif len(path.parts) != 1 or path.suffix.lower() not in {'.txt', '.md', '.json', '.png', '.jpg', '.jpeg'}:
                    raise ValueError('ZIP 需要直接包含 scripts、ui 或 gfx 等游戏目录；请移除外层文件夹。')
                total += entry.file_size
                if total > 512 * 1024 * 1024 or entry.file_size > 64 * 1024 * 1024 or entry.file_size > max(entry.compress_size, 1) * 1000:
                    raise ValueError('ZIP 解压大小或压缩比例超过限制。')
                if path.suffix.lower() in {'.nut', '.cnut'}:
                    script_count += 1
                # Read every entry in chunks to verify CRC without unbounded allocation.
                with archive.open(entry) as src:
                    consumed = 0
                    while block := src.read(1024 * 1024):
                        consumed += len(block)
                        if consumed > entry.file_size:
                            raise ValueError('ZIP 文件长度不一致。')
            if not has_game_file:
                raise ValueError('ZIP 中没有找到可加载的游戏资源目录。')
    except (zipfile.BadZipFile, NotImplementedError, RuntimeError, EOFError) as exc:
        raise ValueError('ZIP 损坏或使用了不支持的压缩方式。') from exc
    finally:
        stream.seek(0)
    return {'sha256': sha.hexdigest(), 'size': size, 'entry_count': len(infos),
            'uncompressed_size': total, 'script_count': script_count,
            'method': 'archive_structure_and_crc', 'game_tested': False}

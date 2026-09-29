"""Bounded CRC validation of local MOD ZIPs, including separately installed nested ZIPs."""
import io
from pathlib import Path, PurePosixPath
import stat
import zipfile

MAX_ARCHIVE = 512 * 1024 * 1024
MAX_EXPANDED = 1024 * 1024 * 1024


def validate_name(name):
    if (not name or any(c in name for c in '/\\:') or Path(name).name != name
            or Path(name).suffix.lower() not in {'.zip', '.rar'}):
        raise ValueError('请选择有效的 MOD ZIP 或 RAR 文件名。')
    return name


def staged_packages(source, directory):
    source = Path(source)
    validate_name(source.name)
    if source.stat().st_size > MAX_ARCHIVE:
        raise ValueError('MOD 文件超过 512 MB，请拆分后安装。')
    # Legacy .rar entries are supported only when they are ZIP-format packages.
    # A real RAR must be unpacked by the user before it can be installed safely.
    packages = {}
    total = [0]

    def validate(stream, name, depth=0):
        if depth > 3 or len(packages) >= 50:
            raise ValueError('内嵌 ZIP 过多或层级过深。')
        key = name.casefold()
        if key in packages:
            raise ValueError(f'压缩包内存在重名安装文件：{name}')
        output = directory / name
        data = stream.read(MAX_ARCHIVE + 1)
        if len(data) > MAX_ARCHIVE:
            raise ValueError('内嵌 ZIP 超过大小限制。')
        output.write_bytes(data)
        packages[key] = output
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            entries = archive.infolist()
            if not entries or len(entries) > 20000:
                raise ValueError('ZIP 为空或文件数量过多。')
            seen = set()
            for entry in entries:
                path = PurePosixPath(entry.orig_filename)
                if (not entry.orig_filename or '\\' in entry.orig_filename or ':' in entry.orig_filename
                        or path.is_absolute() or '..' in path.parts or '\x00' in entry.orig_filename
                        or stat.S_ISLNK(entry.external_attr >> 16) or entry.flag_bits & 1):
                    raise ValueError('ZIP 包含不安全路径、链接或加密文件。')
                if str(path).casefold() in seen:
                    raise ValueError('ZIP 包含重复路径。')
                seen.add(str(path).casefold())
                if entry.is_dir():
                    continue
                total[0] += entry.file_size
                if total[0] > MAX_EXPANDED or entry.file_size > MAX_ARCHIVE:
                    raise ValueError('ZIP 展开大小超过限制。')
                with archive.open(entry) as member:
                    if path.suffix.lower() == '.zip' and path.parts[0].lower() not in {'ui', 'gfx', 'scripts', 'sounds', 'music', 'brushes'}:
                        validate_name(path.name)
                        validate(member, path.name, depth + 1)
                    else:
                        while member.read(128 * 1024):
                            pass
    try:
        with source.open('rb') as stream:
            validate(stream, source.name)
    except (zipfile.BadZipFile, RuntimeError, NotImplementedError, EOFError) as exc:
        raise ValueError('压缩包损坏或格式不支持；RAR 请先解压，选择实际 MOD ZIP。') from exc
    return list(packages.values())

"""Versioned desktop downloads. Uploaded programs are inspected, never executed."""
import hashlib
from pathlib import Path
import re
import struct
import uuid
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from .models import DesktopRelease
from .services import audit


VERSION_PATTERN = re.compile(r'^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$')


def version_key(value):
    match = VERSION_PATTERN.fullmatch(value)
    if not match:
        raise ValueError('请输入版本号，例如 0.3.0 或 0.3.0-rc.5。')
    major, minor, patch, preview = match.groups()
    parts = []
    for part in preview.split('.') if preview else []:
        if part.isdigit() and len(part) > 1 and part.startswith('0'):
            raise ValueError('测试版序号不能带前导零，例如使用 rc.5。')
        parts.append((0, int(part)) if part.isdigit() else (1, part))
    return int(major), int(minor), int(patch), not bool(preview), tuple(parts)


def inspect_desktop(upload):
    if not upload.name.lower().endswith('.exe'):
        raise ValidationError('请上传 Windows EXE 文件。')
    upload.seek(0, 2)
    size = upload.tell()
    if not 64 <= size <= settings.MAX_DESKTOP_BYTES:
        raise ValidationError(f'程序大小不能超过 {settings.MAX_DESKTOP_BYTES // 1024 // 1024} MB。')
    try:
        upload.seek(0)
        header = upload.read(64)
        if header[:2] != b'MZ':
            raise ValueError
        offset = struct.unpack_from('<I', header, 60)[0]
        if not 64 <= offset <= min(size - 26, 1024 * 1024):
            raise ValueError
        upload.seek(offset)
        pe = upload.read(26)
        machine, = struct.unpack_from('<H', pe, 4)
        characteristics, magic = struct.unpack_from('<HH', pe, 22)
        if (pe[:4] != b'PE\0\0' or machine not in {0x14c, 0x8664, 0xaa64}
                or not characteristics & 2 or characteristics & 0x2000
                or magic not in {0x10b, 0x20b}):
            raise ValueError
        digest = hashlib.sha256()
        upload.seek(0)
        while chunk := upload.read(1024 * 1024):
            digest.update(chunk)
    except (ValueError, OSError, struct.error) as exc:
        raise ValidationError('无法识别为 Windows EXE 格式，请选择打包完成的程序。') from exc
    finally:
        upload.seek(0)
    return {'size': size, 'sha256': digest.hexdigest()}


def desktop_available(release):
    try:
        path = Path(release.file.path)
        root = Path(settings.DESKTOP_DOWNLOAD_ROOT).resolve()
        return (path.resolve().is_relative_to(root) and not path.is_symlink()
                and path.is_file() and path.stat().st_size == release.size)
    except (OSError, ValueError):
        return False


def public_desktop_releases(channel='all'):
    rows = DesktopRelease.objects.filter(status='published')
    if channel in {'stable', 'preview'}:
        rows = rows.filter(prerelease=channel == 'preview')
    return sorted([r for r in rows if desktop_available(r)], key=lambda r: version_key(r.version), reverse=True)


def recommended_desktop(releases):
    return next((r for r in releases if not r.prerelease), releases[0] if releases else None)


def create_desktop_release(user, form):
    if not user.is_active or not user.is_superuser:
        raise ValidationError('只有管理员可以发布桌面程序。')
    stored = None
    try:
        with transaction.atomic():
            version = form.cleaned_data['version']
            if DesktopRelease.objects.filter(version=version).exists():
                raise ValidationError('该版本已存在，请使用新版本号，历史文件不能覆盖。')
            release = DesktopRelease(version=version, notes=form.cleaned_data['notes'],
                prerelease=not version_key(version)[3], uploaded_by=user, **form.inspection)
            release.file.save(f'{uuid.uuid4().hex}.exe', form.cleaned_data['file'], save=False)
            stored = (release.file.storage, release.file.name)
            if form.cleaned_data.get('publish'):
                release.status = 'published'
                release.published_at = timezone.now()
            release.save()
            audit(user, '发布程序' if release.status == 'published' else '暂存程序', release.pk, version)
            return release
    except Exception:
        if stored:
            stored[0].delete(stored[1])
        raise

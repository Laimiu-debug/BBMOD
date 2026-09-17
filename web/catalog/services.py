import uuid
from datetime import timedelta
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from .models import Mod, Release, AuditLog


def audit(user, action, target, detail=''):
    AuditLog.objects.create(actor=user, action=action, target=str(target), detail=detail[:1000])


def public_releases():
    return Release.objects.filter(status='published', mod__blocked=False, mod__owner__is_active=True).select_related('mod', 'mod__owner')


def can_inspect(user, release):
    return user.is_authenticated and (user.is_superuser or release.mod.owner_id == user.pk)


def create_release(user, mod, form):
    # All file validation finishes before storing bytes. Files are never exposed via MEDIA_URL.
    existing_files = []
    try:
        with transaction.atomic():
            mod = Mod.objects.select_for_update().get(pk=mod.pk)
            if mod.owner_id != user.pk and not user.is_superuser:
                raise ValidationError('无权更新此作品。')
            if mod.blocked:
                raise ValidationError('作品已被管理员下架，请先联系管理员处理。')
            releases = Release.objects.filter(mod__owner=mod.owner)
            used = releases.aggregate(total=Sum('size'))['total'] or 0
            if used + form.inspection['size'] > settings.AUTHOR_QUOTA_BYTES:
                raise ValidationError('账号存储空间不足，请联系管理员。')
            if releases.filter(created_at__gte=timezone.now() - timedelta(days=1)).count() >= settings.UPLOADS_PER_DAY:
                raise ValidationError('已达到今日上传次数限制，请稍后再试。')
            if mod.releases.filter(version=form.cleaned_data['version']).exists():
                raise ValidationError('这个版本号已存在，请使用新版本号。历史文件不可覆盖。')
            release = Release(mod=mod, version=form.cleaned_data['version'], notes=form.cleaned_data['notes'],
                              metadata=mod.snapshot(), sha256=form.inspection['sha256'], size=form.inspection['size'], inspection=form.inspection)
            release.archive.save(f'{uuid.uuid4().hex}.zip', form.cleaned_data['archive'], save=False)
            existing_files.append((release.archive.storage, release.archive.name))
            if cover := form.cleaned_data.get('cover'):
                release.cover.save(f'{uuid.uuid4().hex}.webp', cover, save=False)
                existing_files.append((release.cover.storage, release.cover.name))
            if form.cleaned_data.get('publish'):
                release.status = 'published'
                release.published_at = timezone.now()
            release.save()
            audit(user, '发布版本' if release.status == 'published' else '上传草稿', release.pk, f'{mod.title} {release.version}')
            return release
    except Exception:
        for storage, name in existing_files:
            storage.delete(name)
        raise

"""Native collection sharing: negotiate hashes, upload only misses, publish last."""
from datetime import timedelta
import hashlib
import hmac
import json
import uuid

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.core import signing
from django.core.exceptions import RequestDataTooBig
from django.core.paginator import Paginator
from django.db import transaction, OperationalError
from django.db.models import F, Q, Sum
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST, require_http_methods, require_safe

from app.core.archive_safety import inspect_archive
from app.core.profile_protocol import MAX_MANIFEST_BYTES, MAX_MOD_BYTES, HASH, validate_manifest, manifest_key
from .models import Release, SharedModFile, SharedProfile, SharedProfileFile, ProfileUploadBudget
from .services import audit, public_releases

HEADER = 'X-BBMOD-Profile-Share'
SALT = 'bbmod-profile-file-v1'


def _native(request):
    if request.headers.get(HEADER) != '1' or request.headers.get('Origin'):
        raise ValueError('请从 BBMOD 管理器分享方案。')


def _manifest(request):
    _native(request)
    if request.content_type != 'application/json':
        raise ValueError('方案需使用 JSON 格式。')
    if int(request.META.get('CONTENT_LENGTH') or 0) > MAX_MANIFEST_BYTES:
        raise ValueError('方案清单过大。')
    raw = request.body
    if len(raw) > MAX_MANIFEST_BYTES:
        raise ValueError('方案清单过大。')
    return validate_manifest(json.loads(raw))


def _source(sha, size=None):
    """No private, withdrawn, moderated or missing disk files may be reused."""
    blob = SharedModFile.objects.filter(pk=sha).first()
    releases = Release.objects.filter(sha256=sha)
    if ((blob and blob.blocked) or releases.filter(
            Q(mod__blocked=True) | Q(mod__owner__is_active=False) | ~Q(status='published')).exists()):
        return 'blocked', None
    for release in public_releases().filter(sha256=sha):
        if (size is None or release.size == size) and release.archive and release.archive.storage.exists(release.archive.name):
            return 'available', release.archive
    if (blob and (size is None or blob.size == size) and blob.archive
            and blob.archive.storage.exists(blob.archive.name)):
        return 'available', blob.archive
    return 'missing', None


class QuotaExceeded(ValueError):
    pass


def _quota(request, kind, size=0):
    now = timezone.now()
    ProfileUploadBudget.objects.filter(since__lt=now - timedelta(days=2)).delete()
    ip = request.META.get('REMOTE_ADDR', '')
    if settings.TRUST_PROXY:
        ip = request.META.get('HTTP_X_REAL_IP', ip)
    for scope, count_limit, size_limit in [('ip:' + ip, 500, 2 * 1024**3), ('global', 5000, 20 * 1024**3)]:
        key = hmac.new(settings.SECRET_KEY.encode(),
            (now.strftime('%Y%m%d') + ':' + kind + ':' + scope).encode(), hashlib.sha256).hexdigest()
        ProfileUploadBudget.objects.get_or_create(key=key)
        if not ProfileUploadBudget.objects.filter(key=key, count__lt=count_limit,
                size__lte=size_limit - size).update(count=F('count') + 1, size=F('size') + size):
            raise QuotaExceeded('今日方案分享额度已用完，请明天再试。已上传的文件可在重试时复用。')


def _error(error):
    if isinstance(error, QuotaExceeded):
        response = JsonResponse({'error': str(error)}, status=429)
        response['Retry-After'] = '86400'
        return response
    if isinstance(error, OperationalError):
        return JsonResponse({'error': '网站忙，请稍后重试；已上传的文件会自动复用。'}, status=503)
    return JsonResponse({'error': str(error)[:300]}, status=400)


@csrf_exempt
@require_POST
def negotiate(request):
    try:
        manifest = _manifest(request)
        if SharedProfile.objects.filter(fingerprint=manifest_key(manifest), blocked=True).exists():
            raise ValueError('这份方案已被下架，不能重复发布。')
        with transaction.atomic():
            _quota(request, 'plan')
        files = []
        for item in manifest['mods']:
            status, _ = _source(item['sha256'], item['size'])
            row = {'sha256': item['sha256'], 'file_name': item['file_name'], 'status': status}
            if status == 'missing':
                row['ticket'] = signing.dumps({'sha256': item['sha256'], 'size': item['size']}, salt=SALT)
            files.append(row)
        return JsonResponse({'schema_version': 1, 'fingerprint': manifest_key(manifest), 'files': files})
    except (ValueError, TypeError, UnicodeError, RequestDataTooBig, OperationalError) as error:
        return _error(error)


@csrf_exempt
@require_POST
def upload_file(request, sha):
    stored = None
    try:
        _native(request)
        if not HASH.fullmatch(sha) or request.content_type != 'multipart/form-data':
            raise ValueError('MOD 上传请求无效。')
        if int(request.META.get('CONTENT_LENGTH') or 0) > MAX_MOD_BYTES + 64 * 1024:
            raise ValueError('单个 MOD 超过 100 MB。')
        ticket = signing.loads(request.POST.get('ticket', ''), salt=SALT, max_age=86400)
        if not isinstance(ticket, dict) or ticket.get('sha256') != sha:
            raise ValueError('上传凭据不匹配，请重新分享。')
        archive = request.FILES.get('archive')
        if not archive or len(request.FILES) != 1 or archive.size != ticket.get('size'):
            raise ValueError('MOD 大小与方案不一致。')
        status, _ = _source(sha, archive.size)
        if status == 'blocked':
            raise ValueError('这个 MOD 文件已被下架或未公开，不能通过方案重新发布。')
        if status == 'available':
            return JsonResponse({'sha256': sha, 'created': False})
        inspection = inspect_archive(archive, max_bytes=min(MAX_MOD_BYTES, settings.MAX_MOD_BYTES))
        if inspection['sha256'] != sha:
            raise ValueError('MOD 校验失败，文件内容与方案不一致。')
        with transaction.atomic():
            _quota(request, 'file', archive.size)
            used = SharedModFile.objects.aggregate(total=Sum('size'))['total'] or 0
            if used + archive.size > getattr(settings, 'PROFILE_STORAGE_BYTES', 20 * 1024**3):
                raise QuotaExceeded('网站方案文件空间不足，请联系管理员。')
            # The quota write serializes uploads on SQLite; the unique digest is
            # also enforced in the database. Concurrent retries store one copy.
            status, _ = _source(sha, archive.size)
            if status == 'blocked':
                raise ValueError('这个文件已被下架。')
            if status == 'available':
                return JsonResponse({'sha256': sha, 'created': False})
            blob = SharedModFile.objects.filter(pk=sha).first() or SharedModFile(sha256=sha)
            blob.size, blob.inspection = archive.size, inspection
            archive.seek(0)
            blob.archive.save(f'{sha}-{uuid.uuid4().hex}.zip', archive, save=False)
            stored = (blob.archive.storage, blob.archive.name)
            blob.save()
        return JsonResponse({'sha256': sha, 'created': True}, status=201)
    except (ValueError, TypeError, UnicodeError, signing.BadSignature, RequestDataTooBig, OperationalError) as error:
        if stored:
            stored[0].delete(stored[1])
        return _error(error)
    except Exception:
        if stored:
            stored[0].delete(stored[1])
        raise


@csrf_exempt
@require_http_methods(['GET', 'POST'])
def publish(request):
    if request.method == 'GET':
        return public_catalog(request)
    try:
        manifest = _manifest(request)
        with transaction.atomic():
            _quota(request, 'publish')
            for item in manifest['mods']:
                if _source(item['sha256'], item['size'])[0] != 'available':
                    raise ValueError(f"{item['file_name']} 尚未上传完成或已下架，请重新分享。")
            profile, created = SharedProfile.objects.get_or_create(fingerprint=manifest_key(manifest),
                                                                  defaults={'manifest': manifest})
            if profile.blocked:
                raise ValueError('这份方案已被下架，不能重复发布。')
            if created:
                SharedProfileFile.objects.bulk_create([SharedProfileFile(profile=profile, sha256=sha)
                    for sha in {item['sha256'] for item in manifest['mods']}])
        return JsonResponse({'id': str(profile.pk), 'page_path': reverse('profile_detail', args=[profile.pk]),
                             'created': created}, status=201 if created else 200)
    except (ValueError, TypeError, UnicodeError, RequestDataTooBig, OperationalError) as error:
        return _error(error)


def _availability(profile):
    return [{**item, 'available': _source(item['sha256'], item['size'])[0] == 'available'}
            for item in profile.manifest['mods']]


def _public_profiles(query):
    profiles = SharedProfile.objects.filter(blocked=False).order_by('-created_at', '-id')
    if query:
        profiles = profiles.filter(Q(manifest__name__icontains=query) | Q(manifest__note__icontains=query))
    return profiles


def public_catalog(request):
    """Small paginated summaries; application still rechecks file availability."""
    query = request.GET.get('q', '').strip()[:100]
    page = Paginator(_public_profiles(query), 12).get_page(request.GET.get('page'))
    items = []
    for profile in page:
        manifest = profile.manifest
        items.append({'id': str(profile.pk), 'name': manifest['name'], 'note': manifest['note'],
            'game_version': manifest['game_version'], 'mod_count': len(manifest['mods']),
            'total_size': sum(item['size'] for item in manifest['mods']),
            'created_at': profile.created_at.isoformat(),
            'page_path': reverse('profile_detail', args=[profile.pk])})
    response = JsonResponse({'schema_version': 1, 'items': items, 'page': page.number,
                             'pages': page.paginator.num_pages, 'total': page.paginator.count})
    response['Cache-Control'] = 'private, no-store'
    return response


@require_GET
def public_record(request, profile_id):
    profile = get_object_or_404(SharedProfile, pk=profile_id, blocked=False)
    if not all(item['available'] for item in _availability(profile)):
        return JsonResponse({'error': '方案中有文件已下架或暂不可用，请联系分享者。'}, status=409)
    response = JsonResponse({'id': str(profile.pk), 'manifest': profile.manifest})
    response['Cache-Control'] = 'private, no-store'
    return response


@require_safe
def download_file(request, profile_id, sha):
    profile = get_object_or_404(SharedProfile, pk=profile_id, blocked=False)
    item = next((m for m in profile.manifest['mods'] if m['sha256'] == sha), None)
    if not item:
        raise Http404
    status, archive = _source(sha, item['size'])
    if status != 'available':
        raise Http404
    from .downloads import mod_file_response
    return mod_file_response(request, archive, filename=item['file_name'], size=item['size'], sha256=sha)


@require_GET
def gallery(request):
    query = request.GET.get('q', '').strip()[:100]
    profiles = _public_profiles(query)
    return render(request, 'profiles.html', {'page': Paginator(profiles, 12).get_page(request.GET.get('page')),
                                           'q': query, 'track_visit': True})


@require_GET
def detail(request, profile_id):
    profile = get_object_or_404(SharedProfile, pk=profile_id, blocked=False)
    items = _availability(profile)
    return render(request, 'profile_detail.html', {'profile': profile, 'items': items,
        'available': all(item['available'] for item in items), 'track_visit': True})


@user_passes_test(lambda u: u.is_active and u.is_superuser)
def management(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        if action not in {'block', 'restore'}:
            return JsonResponse({'error': '无效操作'}, status=400)
        if request.POST.get('sha256'):
            target = get_object_or_404(SharedModFile, pk=request.POST['sha256'])
        else:
            target = get_object_or_404(SharedProfile, pk=request.POST.get('id'))
        target.blocked = action == 'block'
        target.save(update_fields=['blocked'])
        audit(request.user, 'profile-' + action, target.pk)
        messages.success(request, '已下架' if target.blocked else '已恢复展示')
        return redirect('profile_management')
    return render(request, 'profile_management.html', {
        'page': Paginator(SharedProfile.objects.all(), 20).get_page(request.GET.get('page')),
        'files': Paginator(SharedModFile.objects.order_by('-created_at'), 20).get_page(request.GET.get('files_page'))})

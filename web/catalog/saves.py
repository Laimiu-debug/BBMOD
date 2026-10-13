"""Publish a campaign only when its pinned MODs and save are all available."""
import hashlib
import io
import json
import uuid
import zipfile

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.core import signing
from django.core.exceptions import RequestDataTooBig
from django.core.paginator import Paginator
from django.db import OperationalError, transaction
from django.db.models import Q, Sum
from django.http import Http404, JsonResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import content_disposition_header
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods, require_POST, require_safe

from app.core.profile_protocol import HASH, MAX_MANIFEST_BYTES
from app.core.save_protocol import MAX_SAVE_BYTES, inspect_save, manifest_key, validate_manifest
from . import profiles
from .downloads import mod_file_response
from .models import SharedSave, SharedSaveFile
from .services import audit

SALT = 'bbmod-campaign-file-v1'


def _native(request):
    if request.headers.get('X-BBMOD-Save-Share') != '1' or request.headers.get('Origin'):
        raise ValueError('请从新版 BBMOD 的「存档分享」发布战役。')


def _manifest(request):
    _native(request)
    if request.content_type != 'application/json' or int(request.META.get('CONTENT_LENGTH') or 0) > MAX_MANIFEST_BYTES:
        raise ValueError('存档清单格式或大小无效。')
    raw = request.body
    if len(raw) > MAX_MANIFEST_BYTES:
        raise ValueError('存档清单过大。')
    return validate_manifest(json.loads(raw))


def _save_source(sha, size):
    blob = SharedSaveFile.objects.filter(pk=sha).first()
    if blob and blob.blocked:
        return 'blocked', None
    if blob and blob.size == size and blob.file and blob.file.storage.exists(blob.file.name):
        return 'available', blob
    return 'missing', None


ERRORS = (ValueError, TypeError, UnicodeError, RequestDataTooBig, OperationalError)


@csrf_exempt
@require_POST
def negotiate(request):
    try:
        manifest = _manifest(request)
        if SharedSave.objects.filter(fingerprint=manifest_key(manifest), blocked=True).exists():
            raise ValueError('这个分享已被下架，不能重复发布。')
        with transaction.atomic():
            profiles._quota(request, 'save-plan')
        files = []
        for item, (status, _) in zip(manifest['mods'], profiles._sources([(m['sha256'], m['size']) for m in manifest['mods']])):
            row = {'sha256': item['sha256'], 'file_name': item['file_name'], 'status': status}
            if status == 'missing':
                row['ticket'] = signing.dumps({'sha256': item['sha256'], 'size': item['size']}, salt=profiles.SALT)
            files.append(row)
        item = manifest['save']
        status, _ = _save_source(item['sha256'], item['size'])
        save = {'sha256': item['sha256'], 'status': status}
        if status == 'missing':
            save['ticket'] = signing.dumps({'sha256': item['sha256'], 'size': item['size']}, salt=SALT)
        return JsonResponse({'schema_version': 1, 'fingerprint': manifest_key(manifest), 'files': files, 'save': save})
    except ERRORS as error:
        return profiles._error(error)


@csrf_exempt
@require_POST
def upload_file(request, sha):
    stored = None
    try:
        _native(request)
        if not HASH.fullmatch(sha) or request.content_type != 'multipart/form-data':
            raise ValueError('存档上传请求无效。')
        if int(request.META.get('CONTENT_LENGTH') or 0) > MAX_SAVE_BYTES + 64 * 1024:
            raise ValueError('单个存档最大 100 MB。')
        ticket = signing.loads(request.POST.get('ticket', ''), salt=SALT, max_age=86400)
        if not isinstance(ticket, dict) or ticket.get('sha256') != sha:
            raise ValueError('存档上传凭据不匹配，请重新分享。')
        file = request.FILES.get('save')
        if not file or len(request.FILES) != 1 or file.size != ticket.get('size'):
            raise ValueError('存档大小与清单不一致。')
        checked = inspect_save(file)
        if checked['sha256'] != sha:
            raise ValueError('存档内容与清单不一致。')
        with transaction.atomic():
            profiles._quota(request, 'save-file', file.size)
            status, blob = _save_source(sha, file.size)
            if status == 'blocked':
                raise ValueError('这个存档文件已被下架。')
            if status == 'available':
                return JsonResponse({'sha256': sha, 'created': False})
            used = SharedSaveFile.objects.aggregate(total=Sum('size'))['total'] or 0
            if used + file.size > settings.SAVE_STORAGE_BYTES:
                raise profiles.QuotaExceeded('网站存档空间不足，请联系管理员。')
            blob = SharedSaveFile.objects.filter(pk=sha).first() or SharedSaveFile(sha256=sha)
            blob.size = file.size
            file.seek(0)
            blob.file.save(f'{sha}-{uuid.uuid4().hex}.sav', file, save=False)
            stored = (blob.file.storage, blob.file.name)
            blob.save()
        return JsonResponse({'sha256': sha, 'created': True}, status=201)
    except (*ERRORS, signing.BadSignature) as error:
        if stored:
            stored[0].delete(stored[1])
        return profiles._error(error)
    except Exception:
        if stored:
            stored[0].delete(stored[1])
        raise


def _availability(record):
    manifest = record.manifest
    status, blob = _save_source(manifest['save']['sha256'], manifest['save']['size'])
    mods = [{**item, 'available': status == 'available'} for item, (status, _) in
            zip(manifest['mods'], profiles._sources([(m['sha256'], m['size']) for m in manifest['mods']]))]
    return blob, mods, status == 'available' and all(m['available'] for m in mods)


def _public(query):
    records = SharedSave.objects.filter(blocked=False).order_by('-created_at', '-id')
    if query:
        records = records.filter(Q(manifest__name__icontains=query) | Q(manifest__note__icontains=query))
    return records


@csrf_exempt
@require_http_methods(['GET', 'POST'])
def publish(request):
    if request.method == 'GET':
        page = Paginator(_public(request.GET.get('q', '').strip()[:100]), 12).get_page(request.GET.get('page'))
        rows = [{'id': str(s.pk), 'name': s.manifest['name'], 'note': s.manifest['note'],
                 'game_version': s.manifest['game_version'], 'dlcs': s.manifest['dlcs'],
                 'mod_count': len(s.manifest['mods']), 'total_size': s.manifest['save']['size'] + sum(m['size'] for m in s.manifest['mods']),
                 'created_at': s.created_at.isoformat(), 'page_path': reverse('save_detail', args=[s.pk])} for s in page]
        response = JsonResponse({'schema_version': 1, 'items': rows, 'page': page.number,
                                 'pages': page.paginator.num_pages, 'total': page.paginator.count})
        response['Cache-Control'] = 'private, no-store'
        return response
    try:
        manifest = _manifest(request)
        with transaction.atomic():
            profiles._quota(request, 'save-publish')
            status, blob = _save_source(manifest['save']['sha256'], manifest['save']['size'])
            if status != 'available' or any(status != 'available' for status, _ in
                    profiles._sources([(m['sha256'], m['size']) for m in manifest['mods']])):
                raise ValueError('存档或配套 MOD 尚未上传完成，或已有文件下架。')
            record, created = SharedSave.objects.get_or_create(fingerprint=manifest_key(manifest),
                defaults={'manifest': manifest, 'save_file': blob})
            if record.blocked:
                raise ValueError('这个分享已被下架，不能重复发布。')
        return JsonResponse({'id': str(record.pk), 'page_path': reverse('save_detail', args=[record.pk]),
                             'created': created}, status=201 if created else 200)
    except ERRORS as error:
        return profiles._error(error)


@require_GET
def public_record(request, save_id):
    record = get_object_or_404(SharedSave, pk=save_id, blocked=False)
    if not _availability(record)[2]:
        return JsonResponse({'error': '存档或配套 MOD 已下架或暂不可用，无法完整恢复。'}, status=409)
    response = JsonResponse({'id': str(record.pk), 'manifest': record.manifest})
    response['Cache-Control'] = 'private, no-store'
    return response


@require_safe
def download_file(request, save_id, sha):
    record = get_object_or_404(SharedSave, pk=save_id, blocked=False)
    blob, mods, available = _availability(record)
    if not available:
        raise Http404
    item = record.manifest['save']
    if item['sha256'] == sha:
        field = blob.file
    else:
        item = next((m for m in mods if m['sha256'] == sha), None)
        if not item:
            raise Http404
        _, field = profiles._source(sha, item['size'])
    response = mod_file_response(request, field, filename=item['file_name'], size=item['size'], sha256=sha)
    if item['file_name'].endswith('.sav'):
        response['Content-Type'] = 'application/octet-stream'
    return response


class _ZipBuffer(io.RawIOBase):
    def __init__(self):
        self.parts = []
    def writable(self):
        return True
    def write(self, data):
        self.parts.append(data)
        return len(data)
    def drain(self):
        parts, self.parts = self.parts, []
        return b''.join(parts)


@require_safe
def bundle(request, save_id):
    record = get_object_or_404(SharedSave, pk=save_id, blocked=False)
    blob, mods, available = _availability(record)
    if not available:
        raise Http404
    files = [('savegames/' + record.manifest['save']['file_name'], record.manifest['save'], blob.file)]
    for item, (_, field) in zip(mods, profiles._sources([(m['sha256'], m['size']) for m in mods])):
        files.append(('data/' + item['file_name'], item, field))

    def chunks():
        buffer = _ZipBuffer()
        with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_STORED, allowZip64=True) as archive:
            archive.writestr('BBMOD_SAVE.json', json.dumps(record.manifest, ensure_ascii=False, indent=2))
            archive.writestr('使用说明.txt', '推荐在 BBMOD 的「存档分享」通过本页链接恢复存档和整套 MOD。\n'
                '手动安装：关闭游戏，核对游戏版本与 DLC，将 data 内 ZIP 放入游戏 data，停用其他 MOD，'
                '将 savegames 内 .sav 放入文档/Battle Brothers/savegames。保留原有存档。\n'
                '本包固定分享时的文件版本；未包含游戏本体、DLC 或 ZIP 外的个人设置。\n')
            yield buffer.drain()
            for name, item, field in files:
                size, digest = 0, hashlib.sha256()
                with field.open('rb') as source, archive.open(name, 'w', force_zip64=True) as target:
                    while block := source.read(128 * 1024):
                        size += len(block)
                        if size > item['size']:
                            raise OSError('分享文件大小已改变。')
                        digest.update(block)
                        target.write(block)
                        yield buffer.drain()
                    if size != item['size'] or digest.hexdigest() != item['sha256']:
                        raise OSError('分享文件校验失败。')
                yield buffer.drain()
        yield buffer.drain()
    response = StreamingHttpResponse(chunks() if request.method != 'HEAD' else iter(()), content_type='application/zip')
    response['Content-Disposition'] = content_disposition_header(True, f'BBMOD-save-{record.pk}.zip')
    response['Cache-Control'] = 'private, no-store'
    return response


@require_GET
def gallery(request):
    query = request.GET.get('q', '').strip()[:100]
    return render(request, 'saves.html', {'page': Paginator(_public(query), 12).get_page(request.GET.get('page')),
                                        'q': query, 'track_visit': True})


@require_GET
def detail(request, save_id):
    record = get_object_or_404(SharedSave, pk=save_id, blocked=False)
    _, mods, available = _availability(record)
    return render(request, 'save_detail.html', {'record': record, 'items': mods, 'available': available, 'track_visit': True})


@user_passes_test(lambda u: u.is_active and u.is_superuser)
def management(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        if action not in {'block', 'restore'}:
            return JsonResponse({'error': '无效操作'}, status=400)
        record = get_object_or_404(SharedSaveFile, pk=request.POST['sha256']) if request.POST.get('sha256') else get_object_or_404(SharedSave, pk=request.POST.get('id'))
        record.blocked = action == 'block'
        record.save(update_fields=['blocked'])
        audit(request.user, 'save-' + action, record.pk)
        messages.success(request, '已下架' if record.blocked else '已恢复')
        return redirect('save_management')
    return render(request, 'save_management.html', {'page': Paginator(SharedSave.objects.all(), 20).get_page(request.GET.get('page'))})

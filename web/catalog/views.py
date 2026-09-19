import hashlib
import hmac
from datetime import timedelta
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm, SetPasswordForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import transaction, IntegrityError
from django.db.models import F, Sum
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import content_disposition_header
from django.views.decorators.http import require_POST, require_GET, require_safe
from .desktop import desktop_available, public_desktop_releases, recommended_desktop, create_desktop_release
from .forms import ModForm, QuickModForm, ReleaseForm, DesktopReleaseForm, CreateAuthorForm
from .models import Mod, Release, DesktopRelease, AuthorProfile, AuditLog, LoginAttempt, CATEGORIES, Suggestion
from .services import public_releases, create_release, can_inspect, audit
from .visitors import traffic_summary
from .community import catalogue_items, requirement_labels

admin_required = user_passes_test(lambda u: u.is_active and u.is_superuser)


def upload_redirect(request, name, **kwargs):
    response = redirect(name, **kwargs)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'redirect': response['Location']})
    return response


def csrf_failure(request, reason=''):
    return render(request, '403.html', status=403)


def latest_releases():
    seen = set()
    result = []
    for rel in public_releases():
        if rel.mod_id not in seen:
            seen.add(rel.mod_id)
            result.append(rel)
    return result


@require_GET
def catalog(request):
    releases = catalogue_items(latest_releases())
    count = len(releases)
    query = request.GET.get('q', '').strip()[:200]
    category = request.GET.get('category', '')
    if query:
        releases = [r for r in releases if query.casefold() in ' '.join(str(r['metadata'].get(k, '')) for k in ['title', 'english_name', 'summary', 'author']).casefold()]
    if category:
        releases = [r for r in releases if r['metadata'].get('category') == category]
    source_kind = request.GET.get('source', '')
    if source_kind in ('hosted', 'original'):
        releases = [r for r in releases if r['source_kind'] == source_kind]
    if request.GET.get('sort') == 'name':
        releases.sort(key=lambda r: r['metadata'].get('title', ''))
    return render(request, 'catalog.html', {'page': Paginator(releases, 12).get_page(request.GET.get('page')), 'count': count,
                                           'q': query, 'category': category, 'source_kind': source_kind,
                                           'categories': CATEGORIES, 'track_visit': True})


@require_GET
def detail(request, mod_id):
    rels = list(public_releases().filter(mod_id=mod_id))
    if not rels:
        raise Http404
    return render(request, 'detail.html', {'release': rels[0], 'history': rels,
                                          'requirements': requirement_labels(rels[0].metadata.get('requires', [])),
                                          'track_visit': True})


@require_GET
def release_file(request, release_id, cover=False):
    release = get_object_or_404(Release.objects.select_related('mod', 'mod__owner'), pk=release_id)
    public = release.status == 'published' and not release.mod.blocked and release.mod.owner.is_active
    if not public and not can_inspect(request.user, release):
        raise Http404
    field = release.cover if cover else release.archive
    if not field:
        raise Http404
    try:
        response = FileResponse(field.open('rb'), content_type='image/webp' if cover else 'application/zip',
                                as_attachment=not cover, filename='cover.webp' if cover else release.mod.install_name)
    except (FileNotFoundError, OSError):
        raise Http404
    # Delisting takes effect on the next request, even for previously public artifacts.
    response['Cache-Control'] = 'private, no-store'
    if not cover:
        response['X-Checksum-SHA256'] = release.sha256
    return response


def _login_keys(request):
    ip = request.META.get('REMOTE_ADDR', '')  # Nginx overwrites X-Real-IP; never trust arbitrary forwarded chains.
    if settings.TRUST_PROXY:
        ip = request.META.get('HTTP_X_REAL_IP', ip)
    name = request.POST.get('username', '').casefold()[:150]
    return [hmac.new(settings.SECRET_KEY.encode(), v.encode(), hashlib.sha256).hexdigest() for v in [ip, ip + ':' + name]]


def sign_in(request):
    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == 'POST':
        now = timezone.now()
        keys = _login_keys(request)
        LoginAttempt.objects.filter(since__lt=now - timedelta(minutes=15)).delete()
        throttled = any(LoginAttempt.objects.filter(key=k, failures__gte=limit).exists() for k, limit in zip(keys, [30, 8]))
        if throttled:
            form.add_error(None, '尝试次数过多，请 15 分钟后再试。')
        elif form.is_valid():
            login(request, form.get_user())
            LoginAttempt.objects.filter(key=keys[1]).delete()
            audit(request.user, '登录', request.user.username)
            return redirect('workshop')
        else:
            for key in keys:
                LoginAttempt.objects.get_or_create(key=key, defaults={'since': now})
                LoginAttempt.objects.filter(key=key).update(failures=F('failures') + 1)
    return render(request, 'form.html', {'form': form, 'title': '进入作者工坊', 'intro': '使用管理员分配的账号登录。浏览和下载 MOD 无需登录。', 'submit': '登录', 'compact': True})


@require_POST
def sign_out(request):
    logout(request)
    return redirect('catalog')


@login_required
def password_change(request):
    form = PasswordChangeForm(request.user, request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        AuthorProfile.objects.update_or_create(user=user, defaults={'must_change_password': False})
        update_session_auth_hash(request, user)
        audit(user, '修改密码', user.username)
        messages.success(request, '密码已修改。')
        return redirect('workshop')
    return render(request, 'form.html', {'form': form, 'title': '修改密码', 'intro': '首次登录或管理员重置密码后，请先设置自己的密码。', 'submit': '保存密码', 'compact': True})


@login_required
def workshop(request):
    mods = Mod.objects.filter(owner=request.user).prefetch_related('releases').order_by('-updated_at')
    used = Release.objects.filter(mod__owner=request.user).aggregate(total=Sum('size'))['total'] or 0
    return render(request, 'workshop.html', {'mods': mods, 'used': used, 'quota': settings.AUTHOR_QUOTA_BYTES})


def owned_mod(request, mod_id):
    query = Mod.objects.all() if request.user.is_superuser else Mod.objects.filter(owner=request.user)
    return get_object_or_404(query, pk=mod_id)


@login_required
def quick_publish(request):
    data = request.POST if request.method == 'POST' else None
    files = request.FILES if request.method == 'POST' else None
    uploaded = request.FILES.get('archive') if files else None
    mod_form = QuickModForm(data=data, instance=Mod(owner=request.user), upload_name=uploaded.name if uploaded else '')
    release_form = ReleaseForm(data, files, initial={'version': '1.0.0', 'publish': True})
    if request.method == 'POST':
        valid_mod, valid_release = mod_form.is_valid(), release_form.is_valid()
        if valid_mod and valid_release:
            try:
                with transaction.atomic():
                    mod = mod_form.save()
                    release = create_release(request.user, mod, release_form)
            except ValidationError as exc:
                release_form.add_error(None, exc)
            except IntegrityError:
                mod_form.add_error('install_name', '该文件名或版本已被使用，请刷新后重试。')
            else:
                messages.success(request, '作品已公开，玩家现在可以下载。' if release.status == 'published' else '作品已保存为草稿。')
                return upload_redirect(request, 'detail' if release.status == 'published' else 'upload', mod_id=mod.pk)
    return render(request, 'quick_publish.html', {'mod_form': mod_form, 'release_form': release_form, 'max_bytes': settings.MAX_MOD_BYTES})


@login_required
def edit_mod(request, mod_id=None):
    mod = owned_mod(request, mod_id) if mod_id else Mod(owner=request.user)
    form = ModForm(request.POST or None, instance=mod)
    if request.method == 'POST' and form.is_valid():
        try:
            with transaction.atomic():
                form.save()
                audit(request.user, '保存作品资料', mod.pk, mod.title)
        except IntegrityError:
            form.add_error('install_name', '该文件名已被使用，请换一个。')
        else:
            messages.success(request, '资料已保存。上传新版本后，新的作品说明会随版本公开。')
            return upload_redirect(request, 'upload', mod_id=mod.pk)
    return render(request, 'form.html', {'form': form, 'title': '编辑作品' if mod_id else '创建作品',
                                        'intro': '填写作品介绍和安装要求。每个版本都会保存当时的说明。', 'submit': '保存并管理版本'})


@login_required
def upload(request, mod_id):
    mod = owned_mod(request, mod_id)
    form = ReleaseForm(request.POST or None, request.FILES or None)
    form.fields['archive'].help_text = f'上传可直接放入游戏 data 目录的单个 ZIP；最大 {settings.MAX_MOD_BYTES // 1024 // 1024} MB。'
    if request.method == 'POST' and form.is_valid():
        try:
            create_release(request.user, mod, form)
        except ValidationError as exc:
            form.add_error(None, exc)
        except IntegrityError:
            form.add_error(None, '版本号已存在或有并发更新，请刷新后重试。')
        else:
            messages.success(request, '新版本已公开。' if form.cleaned_data['publish'] else '新版本已保存，尚未公开。')
            return upload_redirect(request, 'upload', mod_id=mod.pk)
    return render(request, 'upload.html', {'mod': mod, 'form': form, 'history': mod.releases.all(), 'max_bytes': settings.MAX_MOD_BYTES})


@login_required
@require_POST
def release_action(request, release_id):
    release = get_object_or_404(Release.objects.select_related('mod'), pk=release_id)
    owned_mod(request, release.mod_id)
    action = request.POST.get('action')
    with transaction.atomic():
        mod = Mod.objects.select_for_update().get(pk=release.mod_id)
        if action == 'publish' and not mod.blocked:
            release.status = 'published'
            release.published_at = release.published_at or timezone.now()
        elif action == 'withdraw':
            release.status = 'withdrawn'
        else:
            messages.error(request, '此操作不可用；管理员下架的作品不能自行恢复。')
            return redirect('upload', mod_id=release.mod_id)
        release.save(update_fields=['status', 'published_at'])
        audit(request.user, '公开版本' if action == 'publish' else '撤回版本', release.pk)
    return redirect('upload', mod_id=release.mod_id)


@admin_required
def management(request):
    mods = Mod.objects.select_related('owner').order_by('-updated_at')
    return render(request, 'management.html', {'mods': Paginator(mods, 30).get_page(request.GET.get('page')),
                                               'logs': AuditLog.objects.select_related('actor').order_by('-created_at')[:25],
                                               'traffic': traffic_summary(),
                                               'new_suggestions': Suggestion.objects.filter(status=Suggestion.Status.NEW).count()})


@admin_required
@require_POST
def moderate(request, mod_id):
    with transaction.atomic():
        mod = get_object_or_404(Mod.objects.select_for_update(), pk=mod_id)
        action = request.POST.get('action')
        reason = request.POST.get('reason', '').strip()[:500]
        if action not in {'block', 'restore'} or (action == 'block' and not reason):
            messages.error(request, '下架时请填写原因。')
        else:
            mod.blocked = action == 'block'
            mod.block_reason = reason if mod.blocked else ''
            mod.save(update_fields=['blocked', 'block_reason'])
            audit(request.user, '下架作品' if mod.blocked else '恢复作品', mod.pk, reason)
    return redirect('management')


@admin_required
def accounts(request):
    form = CreateAuthorForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            user = form.save()
            AuthorProfile.objects.create(user=user)
            audit(request.user, '创建作者账号', user.username)
        messages.success(request, f'账号 {user.username} 已创建，请私下交付账号和初始密码；首次登录须修改密码。')
        return redirect('accounts')
    return render(request, 'accounts.html', {'form': form, 'accounts': User.objects.all().order_by('-date_joined')})


@admin_required
def account_change(request, user_id):
    user = get_object_or_404(User, pk=user_id, is_superuser=False)
    form = SetPasswordForm(user, request.POST or None)
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'toggle':
            user.is_active = not user.is_active
            user.save(update_fields=['is_active'])
            audit(request.user, '启用账号' if user.is_active else '停用账号', user.username)
            return redirect('accounts')
        if action == 'password' and form.is_valid():
            form.save()
            AuthorProfile.objects.update_or_create(user=user, defaults={'must_change_password': True})
            audit(request.user, '重置作者密码', user.username)
            messages.success(request, '密码已重置，该用户需要重新登录并修改密码。')
            return redirect('accounts')
    return render(request, 'form.html', {'form': form, 'title': f'重置 {user.username} 的密码', 'submit': '重置密码', 'action': 'password', 'compact': True})


@require_GET
def api_catalog(request):
    items = []
    for release in latest_releases():
        items.append({'id': str(release.mod_id), 'release_id': str(release.pk), 'version': release.version,
                      'file_name': release.mod.install_name, 'sha256': release.sha256, 'size': release.size,
                      'published_at': release.published_at.isoformat(), 'notes': release.notes,
                      'metadata': release.metadata, 'inspection': release.inspection,
                      'download_path': reverse('download', args=[release.pk]),
                      'page_path': reverse('detail', args=[release.mod_id])})
    response = JsonResponse({'schema_version': 1, 'site_name': 'BBMOD 军械库', 'mods': items}, json_dumps_params={'ensure_ascii': False})
    response['Cache-Control'] = 'no-store'
    return response


@require_GET
def health(request):
    # Include database readiness, without exposing account or configuration details.
    User.objects.exists()
    return JsonResponse({'status': 'ok'})


@require_GET
def downloads(request):
    channel = request.GET.get('channel', 'all')
    channel = channel if channel in {'all', 'stable', 'preview'} else 'all'
    releases = public_desktop_releases(channel)
    return render(request, 'downloads.html', {'desktop': recommended_desktop(releases), 'releases': releases, 'channel': channel, 'track_visit': True})


@require_safe
def desktop_download(request, release_id=None):
    if release_id:
        release = get_object_or_404(DesktopRelease, pk=release_id)
        if release.status != 'published' and not (request.user.is_active and request.user.is_superuser):
            raise Http404
    else:
        release = recommended_desktop(public_desktop_releases())
    if not release or not desktop_available(release):
        raise Http404
    if settings.DESKTOP_DOWNLOAD_ACCEL:
        # The private Nginx location streams the file and supports Range requests.
        response = HttpResponse(content_type='application/octet-stream')
        response['X-Accel-Redirect'] = '/_desktop/' + release.file.name
    elif request.method == 'HEAD':
        response = HttpResponse(content_type='application/octet-stream')
    else:
        try:
            response = FileResponse(release.file.open('rb'), content_type='application/octet-stream')
        except OSError:
            raise Http404
    response['Content-Disposition'] = content_disposition_header(True, release.filename)
    response['Content-Length'] = release.size
    response['X-Checksum-SHA256'] = release.sha256
    response['Cache-Control'] = 'private, no-store'
    return response


@admin_required
def software_management(request):
    form = DesktopReleaseForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        try:
            create_desktop_release(request.user, form)
        except ValidationError as exc:
            form.add_error(None, exc)
        except IntegrityError:
            form.add_error('version', '该版本已存在，请使用新的版本号。')
        else:
            messages.success(request, '程序版本已公开。' if form.cleaned_data.get('publish') else '程序已保存为草稿。')
            return upload_redirect(request, 'software_management')
    return render(request, 'software_management.html', {'form': form, 'history': DesktopRelease.objects.all(),
                                                       'max_bytes': settings.MAX_DESKTOP_BYTES})


@admin_required
@require_POST
def software_action(request, release_id):
    with transaction.atomic():
        release = get_object_or_404(DesktopRelease.objects.select_for_update(), pk=release_id)
        action = request.POST.get('action')
        if action == 'publish' and desktop_available(release):
            release.status = 'published'
            release.published_at = release.published_at or timezone.now()
        elif action == 'withdraw':
            release.status = 'withdrawn'
        else:
            messages.error(request, '文件尚未就绪或操作无效。')
            return redirect('software_management')
        release.save(update_fields=['status', 'published_at'])
        audit(request.user, '公开程序版本' if action == 'publish' else '撤回程序版本', release.pk, release.version)
    return redirect('software_management')


@require_GET
def api_desktop_releases(request):
    rows = public_desktop_releases()
    recommended = recommended_desktop(rows)
    items = [{'id': str(r.pk), 'version': r.version, 'prerelease': r.prerelease, 'notes': r.notes,
              'filename': r.filename, 'size': r.size, 'sha256': r.sha256,
              'published_at': r.published_at.isoformat() if r.published_at else None,
              'download_path': reverse('desktop_version_download', args=[r.pk])} for r in rows]
    return JsonResponse({'schema_version': 1, 'recommended_version': recommended.version if recommended else None,
                         'releases': items}, json_dumps_params={'ensure_ascii': False})

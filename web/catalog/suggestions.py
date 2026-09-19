"""Private, anonymous feedback with an administrator-only inbox."""
from datetime import timedelta
import hashlib
import hmac
import logging
import json
import secrets
import uuid

from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.core import signing
from django.core.paginator import Paginator
from django.db import OperationalError, transaction
from django.db.models import Count, F, Q
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods

from .models import Suggestion, SuggestionBudget
from .services import audit

TOKEN_SALT = 'bbmod.suggestion.v1'
logger = logging.getLogger(__name__)
admin_required = user_passes_test(lambda user: user.is_active and user.is_superuser)


class SuggestionForm(forms.ModelForm):
    submission = forms.CharField(max_length=500, widget=forms.HiddenInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['kind'].choices = Suggestion.Kind.choices

    class Meta:
        model = Suggestion
        fields = ['kind', 'title', 'details', 'version', 'nickname', 'contact']
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': '例如：希望能按 MOD 名称快速查找'}),
            'details': forms.Textarea(attrs={'rows': 7, 'placeholder': '你在什么场景遇到了问题，或希望增加什么功能？\n如果是问题反馈，请写下操作步骤、实际结果和期望结果。'}),
            'version': forms.TextInput(attrs={'placeholder': '管理器版本号或汉化包版本号', 'autocomplete': 'off'}),
            'nickname': forms.TextInput(attrs={'placeholder': '留个称呼，方便交流', 'autocomplete': 'nickname'}),
            'contact': forms.TextInput(attrs={'placeholder': '邮箱、QQ 或其他方便联系的方式', 'autocomplete': 'off'}),
        }
        help_texts = {'details': '最多 5,000 字。请勿填写密码、密钥或其他敏感信息。',
                      'contact': '选填；仅管理员可见，用于需要时进一步了解情况。'}


class HandlingForm(forms.ModelForm):
    revision = forms.DateTimeField(widget=forms.HiddenInput)

    class Meta:
        model = Suggestion
        fields = ['status', 'internal_notes']
        widgets = {'internal_notes': forms.Textarea(attrs={'rows': 7, 'placeholder': '记录排查结果、后续计划或处理原因'})}
        help_texts = {'internal_notes': '仅管理员可见，保存后不会自动发送给提交者。'}


class QuotaExceeded(Exception):
    pass


def _budget_scopes(request, browser):
    address = request.META.get('REMOTE_ADDR', '')
    if settings.TRUST_PROXY:
        address = request.META.get('HTTP_X_REAL_IP', address)
    # The edge may share an egress address across visitors, so its ceiling is
    # higher than the browser quota. Arbitrary forwarded chains are not trusted.
    return [('browser:' + browser, 5), ('address:' + address, 30), ('global', 300)]


def _save_submission(request, browser, submission_id, data):
    now = timezone.now()
    with transaction.atomic():
        # Start with a write to serialize SQLite writers before checking the
        # receipt. A retry, including simultaneous requests, saves only once.
        SuggestionBudget.objects.filter(since__lt=now - timedelta(days=2)).delete()
        existing = Suggestion.objects.filter(pk=submission_id).first()
        if existing:
            return existing
        for scope, limit in _budget_scopes(request, browser):
            key = hmac.new(settings.SECRET_KEY.encode(),
                           (now.strftime('%Y%m%d%H') + ':' + scope).encode(), hashlib.sha256).hexdigest()
            SuggestionBudget.objects.get_or_create(key=key)
            if not SuggestionBudget.objects.filter(key=key, count__lt=limit).update(count=F('count') + 1):
                raise QuotaExceeded
        return Suggestion.objects.create(id=submission_id,
            **{field: data[field] for field in SuggestionForm.Meta.fields})


@require_http_methods(['GET', 'POST'])
def api_submit(request):
    """Native client uses the same session, CSRF, tickets and inbox as the web."""
    def reply(data, status=200, retry=None):
        response = JsonResponse({'schema_version': 1, **data}, status=status,
                                json_dumps_params={'ensure_ascii': False})
        response['Cache-Control'] = 'private, no-store'
        if retry:
            response['Retry-After'] = str(retry)
        return response

    browser = request.session.get('suggestion_browser')
    if request.method == 'GET':
        if not browser:
            browser = secrets.token_hex(16)
            request.session['suggestion_browser'] = browser
        token = signing.dumps({'id': str(uuid.uuid4()), 'browser': browser}, salt=TOKEN_SALT)
        return reply({'submission': token, 'csrf_token': get_token(request),
                      'kinds': list(Suggestion.Kind.choices)})
    if request.content_type != 'application/json':
        return reply({'error': '请使用 JSON 提交。'}, 415)
    if len(request.body) > 40_000:
        return reply({'error': '填写内容过长。'}, 413)
    try:
        data = json.loads(request.body)
        if not isinstance(data, dict) or any(not isinstance(value, str) for value in data.values()):
            raise ValueError
    except (ValueError, UnicodeError):
        return reply({'error': '无法识别提交内容。'}, 400)
    try:
        token = signing.loads(data.get('submission', '')[:500], salt=TOKEN_SALT, max_age=86400)
        if not browser or not isinstance(token, dict) or token.get('browser') != browser:
            raise ValueError
        submission_id = uuid.UUID(token['id'])
    except (signing.BadSignature, KeyError, ValueError, TypeError, AttributeError):
        return reply({'error': '提交凭据已过期，请重新提交。', 'code': 'ticket_expired'}, 400)
    form = SuggestionForm(data)
    if not form.is_valid():
        return reply({'error': '请检查填写内容。', 'errors': dict(form.errors)}, 400)
    try:
        suggestion = _save_submission(request, browser, submission_id, form.cleaned_data)
    except QuotaExceeded:
        return reply({'error': '提交较频繁，请一小时后再试。'}, 429, 3600)
    except OperationalError:
        logger.warning('Desktop suggestion storage temporarily unavailable')
        return reply({'error': '暂时无法保存建议，请稍后重试。'}, 503, 5)
    return reply({'reference': suggestion.reference, 'message': '建议已送达，管理员会在后台查看。'}, 201)


@require_http_methods(['GET', 'POST'])
def submit(request):
    browser = request.session.get('suggestion_browser')
    if not browser:
        browser = secrets.token_hex(16)
        request.session['suggestion_browser'] = browser
    fresh_token = signing.dumps({'id': str(uuid.uuid4()), 'browser': browser}, salt=TOKEN_SALT)
    data = request.POST if request.method == 'POST' else None
    form = SuggestionForm(data, initial={'kind': Suggestion.Kind.FEATURE, 'submission': fresh_token})
    status = 200
    if request.method == 'POST':
        valid = form.is_valid()
        try:
            token = signing.loads(request.POST.get('submission', '')[:500], salt=TOKEN_SALT, max_age=86400)
            if not isinstance(token, dict) or token.get('browser') != browser:
                raise ValueError
            submission_id = uuid.UUID(token['id'])
        except (signing.BadSignature, KeyError, ValueError, TypeError, AttributeError):
            # Preserve all visible input and renew only the expired form token.
            form.data = form.data.copy()
            form.data['submission'] = fresh_token
            form.errors.pop('submission', None)
            form.add_error(None, '页面已过期或提交凭据无效，填写内容已保留。请检查后再次提交。')
            status = 400
        else:
            if valid:
                try:
                    suggestion = _save_submission(request, browser, submission_id, form.cleaned_data)
                except QuotaExceeded:
                    form.add_error(None, '提交较频繁，请一小时后再试。填写内容已保留。')
                    status = 429
                except OperationalError:
                    logger.warning('Suggestion storage temporarily unavailable')
                    form.add_error(None, '暂时无法保存建议，填写内容已保留。请稍后重试。')
                    status = 503
                else:
                    request.session['last_suggestion'] = str(suggestion.pk)
                    return redirect('suggestion_thanks')
            else:
                status = 400
    response = render(request, 'suggestions.html', {'form': form, 'track_visit': True}, status=status)
    if status in (429, 503):
        response['Retry-After'] = '3600' if status == 429 else '5'
    return response


@require_GET
def thanks(request):
    suggestion_id = request.session.get('last_suggestion')
    suggestion = Suggestion.objects.filter(pk=suggestion_id).first() if suggestion_id else None
    if not suggestion:
        return redirect('suggestions')
    return render(request, 'suggestion_thanks.html', {'reference': suggestion.reference, 'track_visit': True})


@admin_required
@require_GET
def management(request):
    query = Suggestion.objects.all()
    status = request.GET.get('status', '')
    kind = request.GET.get('kind', '')
    search = request.GET.get('q', '').strip()[:100]
    if status not in Suggestion.Status.values:
        status = ''
    if kind not in Suggestion.Kind.values:
        kind = ''
    if status:
        query = query.filter(status=status)
    if kind:
        query = query.filter(kind=kind)
    if search:
        query = query.filter(Q(title__icontains=search) | Q(details__icontains=search) | Q(nickname__icontains=search))
    totals = dict(Suggestion.objects.values_list('status').annotate(total=Count('pk')))
    return render(request, 'suggestion_management.html', {
        'page': Paginator(query, 20).get_page(request.GET.get('page')),
        'status': status, 'kind': kind, 'q': search,
        'statuses': Suggestion.Status.choices, 'kinds': Suggestion.Kind.choices,
        'total': sum(totals.values()), 'new_count': totals.get(Suggestion.Status.NEW, 0),
        'reviewing_count': totals.get(Suggestion.Status.REVIEWING, 0),
    })


@admin_required
@require_http_methods(['GET', 'POST'])
def detail(request, suggestion_id):
    suggestion = get_object_or_404(Suggestion.objects.select_related('handled_by'), pk=suggestion_id)
    form = HandlingForm(request.POST if request.method == 'POST' else None, instance=suggestion,
                        initial={'revision': suggestion.updated_at.isoformat()})
    status = 200
    if request.method == 'POST':
        if form.is_valid():
            with transaction.atomic():
                updated = Suggestion.objects.filter(pk=suggestion.pk, updated_at=form.cleaned_data['revision']).update(
                    status=form.cleaned_data['status'], internal_notes=form.cleaned_data['internal_notes'],
                    handled_by=request.user, updated_at=timezone.now())
                if updated:
                    audit(request.user, '处理建议', suggestion.pk, dict(Suggestion.Status.choices)[form.cleaned_data['status']])
            if updated:
                messages.success(request, '处理记录已保存。')
                return redirect('suggestion_detail', suggestion_id=suggestion.pk)
            form.add_error(None, '这条建议已被其他管理员更新。请重新打开页面查看最新记录，再合并你的备注。')
            status = 409
        else:
            status = 400
        # ModelForm validation mutates its instance; show the actual saved state.
        suggestion.refresh_from_db()
    return render(request, 'suggestion_detail.html', {'suggestion': suggestion, 'form': form}, status=status)

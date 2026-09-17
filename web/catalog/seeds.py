"""Anonymous seed publication and public, server-filtered discovery."""
from dataclasses import asdict
from datetime import timedelta
import hashlib
import hmac
import json

from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import RequestDataTooBig
from django.core.paginator import Paginator
from django.db import transaction, OperationalError
from django.db.models import Count, F, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from app.core.seedgen.config_emitter import ORIGIN_LABELS, DIFFICULTY_LABELS, BUDGET_LABELS
from app.core.seedgen.log_watcher import SeedResult
from app.core.seedgen.presentation import brothers, format_seed, highlights, metric, named_count
from app.core.seedgen.protocol import MAX_SHARE_BYTES, seed_key, validate_share
from app.core.seedgen.traits import traits
from .models import SharedSeed, SharedSeedBrother, SeedUploadBudget
from .services import audit

ORIGINS = [(key, label) for key, label in ORIGIN_LABELS.items() if key != 'common']


class SeedFilters(forms.Form):
    q = forms.CharField(label='种子码 / 介绍', max_length=80, required=False,
                        widget=forms.TextInput(attrs={'placeholder': '输入种子码或路线关键词'}))
    origin = forms.ChoiceField(label='开局起源', choices=[('', '全部起源'), *ORIGINS], required=False)
    combat = forms.ChoiceField(label='战斗难度', choices=[('', '不限'), *DIFFICULTY_LABELS.items()], required=False)
    economic = forms.ChoiceField(label='经济难度', choices=[('', '不限'), *DIFFICULTY_LABELS.items()], required=False)
    budget = forms.ChoiceField(label='初始资金', choices=[('', '不限'), *BUDGET_LABELS.items()], required=False)
    ports = forms.IntegerField(label='港口至少', min_value=0, max_value=100, required=False)
    named = forms.IntegerField(label='红装至少', min_value=0, max_value=500, required=False)
    melee = forms.IntegerField(label='11级近战至少', min_value=0, max_value=200, required=False)
    ranged = forms.IntegerField(label='11级远程至少', min_value=0, max_value=200, required=False)
    defense = forms.IntegerField(label='11级近防至少', min_value=0, max_value=200, required=False)
    people = forms.IntegerField(label='满足条件的兄弟至少', min_value=1, max_value=27, required=False)
    trait = forms.ChoiceField(label='必须具备的特质', required=False)
    exclude = forms.ChoiceField(label='排除的特质', required=False)
    sort = forms.ChoiceField(label='排列方式', choices=[('', '最新分享'), ('ports', '港口最多'),
        ('named', '红装最多'), ('melee', '近战最高')], required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        options = [('', '不限'), *[(t.id, t.name) for t in traits().values()]]
        self.fields['trait'].choices = self.fields['exclude'].choices = options
        for name in ('ports', 'named', 'melee', 'ranged', 'defense', 'people'):
            self.fields[name].widget.attrs['placeholder'] = '不限' if name != 'people' else '1'


def _card(seed):
    result = SeedResult(**seed.record)
    seed.origin_label = ORIGIN_LABELS.get(seed.origin, seed.origin)
    seed.highlights = highlights(result)
    seed.combat_label = DIFFICULTY_LABELS.get(seed.combat_difficulty, '未记录')
    seed.economic_label = DIFFICULTY_LABELS.get(seed.economic_difficulty, '未记录')
    seed.budget_label = BUDGET_LABELS.get(seed.budget_difficulty, '未记录')
    return seed


@require_GET
def gallery(request):
    form = SeedFilters(request.GET)
    query = SharedSeed.objects.filter(blocked=False)
    total = query.count()
    if form.is_valid():
        data = form.cleaned_data
        if data['q']:
            query = query.filter(Q(seed__contains=data['q']) | Q(note__icontains=data['q']))
        if data['origin']:
            query = query.filter(origin=data['origin'])
        for field in ('combat', 'economic', 'budget'):
            if data[field] != '':
                query = query.filter(**{field + '_difficulty': int(data[field])})
        for field in ('ports', 'named'):
            if data[field] is not None:
                query = query.filter(**{field + '__gte': data[field]})
        people = SharedSeedBrother.objects.all()
        has_people_filter = bool(data['trait'] or data['exclude'] or data['people'])
        for field in ('melee', 'ranged', 'defense'):
            if data[field] is not None:
                has_people_filter = True
                people = people.filter(**{field + '__gte': data[field]})
        if data['trait']:
            people = people.filter(traits__contains='|' + data['trait'] + '|')
        if data['exclude']:
            people = people.exclude(traits__contains='|' + data['exclude'] + '|')
        if has_people_filter:
            # All thresholds apply to the same brother, then count matching brothers.
            matched = people.values('seed_id').annotate(n=Count('id')).filter(n__gte=data['people'] or 1)
            query = query.filter(id__in=matched.values('seed_id'))
        if data['sort']:
            query = query.order_by(F(data['sort']).desc(nulls_last=True), '-created_at', '-id')
    else:
        query = query.none()
    page = Paginator(query, 18).get_page(request.GET.get('page'))
    page.object_list = [_card(seed) for seed in page.object_list]
    params = request.GET.copy()
    params.pop('page', None)
    advanced = any(request.GET.get(key) for key in ('combat', 'economic', 'budget', 'melee', 'ranged', 'defense', 'people', 'trait', 'exclude'))
    return render(request, 'seeds.html', {'form': form, 'page': page, 'total': total,
        'params': params.urlencode(), 'advanced': advanced, 'track_visit': True})


@require_GET
def detail(request, seed_id):
    seed = _card(get_object_or_404(SharedSeed, pk=seed_id, blocked=False))
    return render(request, 'seed_detail.html', {'seed': seed,
        'record_text': format_seed(SeedResult(**seed.record), note=seed.note), 'track_visit': True})


def _quota(request):
    now = timezone.now()
    SeedUploadBudget.objects.filter(since__lt=now - timedelta(days=2)).delete()
    ip = request.META.get('REMOTE_ADDR', '')
    if settings.TRUST_PROXY:
        ip = request.META.get('HTTP_X_REAL_IP', ip)
    # Only the reverse proxy's overwritten address is accepted. Vercel visitors
    # may share an egress address, so also keep a separate global hourly ceiling.
    for scope, limit in [('ip:' + ip, 200), ('global', 2000)]:
        key = hmac.new(settings.SECRET_KEY.encode(), (now.strftime('%Y%m%d%H') + scope).encode(), hashlib.sha256).hexdigest()
        SeedUploadBudget.objects.get_or_create(key=key)
        if not SeedUploadBudget.objects.filter(key=key, count__lt=limit).update(count=F('count') + 1):
            raise ValueError('分享次数较多，请一小时后再试。已保存的种子不会丢失。')


@csrf_exempt
@require_POST
def publish(request):
    # Native-only JSON endpoint. Browser forms cannot supply the custom header;
    # reject browser-origin requests as this site has no browser upload flow.
    if request.content_type != 'application/json' or request.headers.get('X-BBMOD-Seed-Share') != '1' or request.headers.get('Origin'):
        return JsonResponse({'error': '请从 BBMOD 管理器点击「分享给兄弟」。'}, status=403)
    try:
        if int(request.META.get('CONTENT_LENGTH') or 0) > MAX_SHARE_BYTES:
            return JsonResponse({'error': '种子档案超过 64 KB'}, status=413)
        raw = request.body
        if len(raw) > MAX_SHARE_BYTES:
            return JsonResponse({'error': '种子档案超过 64 KB'}, status=413)
        record, note = validate_share(json.loads(raw))
    except (ValueError, TypeError, UnicodeError, RequestDataTooBig) as error:
        return JsonResponse({'error': str(error)[:200]}, status=400)
    fingerprint = seed_key(record)
    existing = SharedSeed.objects.filter(fingerprint=fingerprint).first()
    if existing:
        if existing.blocked:
            return JsonResponse({'error': '这条种子已被管理员下架，不能重复发布。'}, status=409)
        return JsonResponse({'page_path': reverse('seed_detail', args=[existing.pk]), 'created': False})
    people = brothers(record)
    try:
        with transaction.atomic():
            _quota(request)
            seed, created = SharedSeed.objects.get_or_create(fingerprint=fingerprint, defaults={
                **{field: getattr(record, field) for field in ('seed', 'origin', 'game_version',
                    'combat_difficulty', 'economic_difficulty', 'budget_difficulty')},
                'record': asdict(record), 'note': note, 'ports': metric(record, 'SettlementInfo:', 'Port'),
                'named': named_count(record),
                'melee': max((b.projected['MeleeSkill'] for b in people if 'MeleeSkill' in b.projected), default=None)})
            if seed.blocked:
                return JsonResponse({'error': '这条种子已下架。'}, status=409)
            if created:
                SharedSeedBrother.objects.bulk_create([SharedSeedBrother(seed=seed,
                    melee=b.projected.get('MeleeSkill'), ranged=b.projected.get('RangedSkill'),
                    defense=b.projected.get('MeleeDefense'), traits='|' + '|'.join(b.traits) + '|') for b in people])
    except ValueError as error:
        response = JsonResponse({'error': str(error)}, status=429)
        response['Retry-After'] = '3600'
        return response
    except OperationalError:
        return JsonResponse({'error': '网站正在处理其他分享，请稍后重试。'}, status=503)
    return JsonResponse({'page_path': reverse('seed_detail', args=[seed.pk]), 'created': created}, status=201 if created else 200)


@user_passes_test(lambda u: u.is_active and u.is_superuser)
def management(request):
    if request.method == 'POST':
        seed = get_object_or_404(SharedSeed, pk=request.POST.get('id'))
        action = request.POST.get('action')
        if action not in ('block', 'restore'):
            return JsonResponse({'error': '无效操作'}, status=400)
        seed.blocked = action == 'block'
        seed.save(update_fields=['blocked'])
        audit(request.user, 'seed-' + action, str(seed.pk), seed.seed)
        messages.success(request, '种子已下架' if seed.blocked else '种子已恢复展示')
        return redirect('seed_management')
    page = Paginator(SharedSeed.objects.all(), 30).get_page(request.GET.get('page'))
    page.object_list = [_card(seed) for seed in page.object_list]
    return render(request, 'seed_management.html', {'page': page})

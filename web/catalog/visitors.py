"""Anonymous, persistent browser visitor numbers and aggregate site traffic."""
from datetime import datetime, time
import hashlib
import logging
import re
import secrets

from django.conf import settings
from django.db import OperationalError, transaction
from django.db.models import Count, F, Min, Q, Sum
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
from .models import SiteVisitor

COOKIE = 'bbmod_visitor'
COOKIE_SALT = 'bbmod.visitor.v1'
COOKIE_AGE = 365 * 24 * 60 * 60
BOT = re.compile(r'bot\b|crawler|spider|slurp|bingpreview|facebookexternalhit|bytespider|uptime|healthcheck|bbmod-check', re.I)
logger = logging.getLogger(__name__)


def record_visit(token, now):
    digest = hashlib.sha256(token.encode('ascii')).hexdigest()
    # Acquire SQLite's write lock before reading. F() prevents lost increments
    # when a browser opens several tabs at once.
    with transaction.atomic():
        updated = SiteVisitor.objects.filter(token_hash=digest).update(page_views=F('page_views') + 1, last_seen=now)
        if updated:
            visitor = SiteVisitor.objects.get(token_hash=digest)
        else:
            visitor = SiteVisitor.objects.create(token_hash=digest, last_seen=now)
    return visitor


@require_POST
def visit(request):
    # Called once by the public-page script. Assets, APIs, errors, downloads and
    # health probes do not execute that script. Keep normal CSRF protection.
    if BOT.search(request.headers.get('User-Agent', '')):
        return HttpResponse(status=204)
    token = request.get_signed_cookie(COOKIE, default='', salt=COOKIE_SALT, max_age=COOKIE_AGE)
    if not re.fullmatch(r'[0-9a-f]{32}', token):
        token = secrets.token_hex(16)
    try:
        visitor = record_visit(token, timezone.now())
        total = SiteVisitor.objects.count()
    except OperationalError:
        # The site remains usable when its counter is temporarily unavailable.
        logger.warning('Visitor counter temporarily unavailable')
        return JsonResponse({'error': '访客统计暂时不可用'}, status=503)
    response = JsonResponse({'visitor_number': visitor.pk, 'total_visitors': total,
        'greeting': f'欢迎你，第{visitor.pk}位好兄弟'})
    response.set_signed_cookie(COOKIE, token, salt=COOKIE_SALT, max_age=COOKIE_AGE,
        httponly=True, secure=request.is_secure(), samesite='Lax', path='/')
    return response


def traffic_summary():
    midnight = timezone.make_aware(datetime.combine(timezone.localdate(), time.min))
    return SiteVisitor.objects.aggregate(total=Count('pk'),
        today=Count('pk', filter=Q(last_seen__gte=midnight)),
        new_today=Count('pk', filter=Q(first_seen__gte=midnight)),
        page_views=Sum('page_views', default=0), since=Min('first_seen'))

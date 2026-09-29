"""Browser downloads can use the same authorized routes at the direct origin."""
from urllib.parse import urlsplit
from django import template
from django.conf import settings
from django.urls import reverse

register = template.Library()


@register.simple_tag
def download_url(name, *args):
    path = reverse(name, args=args)
    base = settings.PUBLIC_DOWNLOAD_BASE
    parts = urlsplit(base)
    if (name in {'download', 'desktop_version_download', 'desktop_download'}
            and parts.scheme == 'https' and parts.hostname and not parts.username
            and not parts.password and not parts.query and not parts.fragment):
        return base + path
    return path

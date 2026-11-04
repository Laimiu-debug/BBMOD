"""Official website address and compatibility for locally saved old links."""
import re
from urllib.parse import urlsplit

SITE_ORIGIN = 'https://bbmod.com'
LEGACY_SITE_ORIGINS = frozenset({'https://bbmod.site', 'https://bbmod.vercel.app'})
OFFICIAL_SITE_ORIGINS = LEGACY_SITE_ORIGINS | {SITE_ORIGIN}
DIRECT_DOWNLOAD_BASE = 'https://dl.gongpro.app/bbmod'
_ID = r'[a-f0-9]{8}-(?:[a-f0-9]{4}-){3}[a-f0-9]{12}'
PUBLIC_READ_PATH = re.compile(
    rf'(?:/downloads/windows/(?:{_ID}/)?|/files/{_ID}/download/|/mods/{_ID}/'
    rf'|/api/v1/(?:desktop/releases/|catalog/|(?:profiles|saves)/{_ID}/(?:files/[a-f0-9]{{64}}/)?))')


def canonical_public_read_url(value):
    """Recognize an exact relay route while preserving the site's identity."""
    if isinstance(value, str) and value.startswith(DIRECT_DOWNLOAD_BASE + '/'):
        path = value[len(DIRECT_DOWNLOAD_BASE):]
        if PUBLIC_READ_PATH.fullmatch(path):
            return SITE_ORIGIN + path
    return canonical_site_url(value)


def public_read_urls(value):
    """Independent HTTPS transport for exact public GET/HEAD routes only.

    Keep saved identities on bbmod.com. Never forward custom sites, credentials,
    query strings, uploads or account routes to the download relay.
    """
    canonical = canonical_public_read_url(value)
    try:
        parts = urlsplit(canonical)
    except ValueError:
        return (value,)
    if (parts.scheme + '://' + parts.netloc.lower() == SITE_ORIGIN
            and not parts.query and not parts.fragment and PUBLIC_READ_PATH.fullmatch(parts.path)):
        return (DIRECT_DOWNLOAD_BASE + parts.path, canonical)
    return (canonical,)


def canonical_site_origin(value):
    """Map exact official roots to the current site, preserving custom sources."""
    if not isinstance(value, str):
        return value
    try:
        parts = urlsplit(value.strip())
    except ValueError:
        return value
    origin = parts.scheme + '://' + parts.netloc.lower()
    if (origin in OFFICIAL_SITE_ORIGINS and parts.path in {'', '/'}
            and not parts.query and not parts.fragment):
        return SITE_ORIGIN
    return value


def same_site(left, right):
    return bool(left and right and canonical_site_origin(left) == canonical_site_origin(right))


def canonical_site_url(value):
    """Rewrite trusted old URLs without changing paths, IDs or custom links."""
    if not isinstance(value, str):
        return value
    try:
        parts = urlsplit(value)
    except ValueError:
        return value
    origin = parts.scheme + '://' + parts.netloc.lower()
    if (origin in LEGACY_SITE_ORIGINS and parts.path.startswith('/')
            and not parts.path.startswith('//') and not parts.query and not parts.fragment):
        return SITE_ORIGIN + parts.path
    return value

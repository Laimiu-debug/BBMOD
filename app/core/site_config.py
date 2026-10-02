"""Official website address and compatibility for locally saved old links."""
from urllib.parse import urlsplit

SITE_ORIGIN = 'https://bbmod.com'
LEGACY_SITE_ORIGINS = frozenset({'https://bbmod.site', 'https://bbmod.vercel.app'})
OFFICIAL_SITE_ORIGINS = LEGACY_SITE_ORIGINS | {SITE_ORIGIN}


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

"""Identify manual installs from public release history without downloading ZIPs."""
import html
import re
import time
from urllib.parse import urlsplit
from urllib.request import Request, build_opener

from .online_catalog import NoRedirect, _request, site_origin


def public_release_links(document, origin):
    """Only the site's version-history section and same-site download paths."""
    origin = site_origin(origin)
    history = re.search(r'<section\b[^>]*class=["\'][^"\']*\bhistory\b[^"\']*["\'][^>]*>(.*?)</section>', document, re.S)
    if not history:
        return []
    result = []
    for match in re.finditer(r'<h3>\s*v([^<]{1,40})</h3>(.*?)(?=<h3>|$)', history[1], re.S):
        version = html.unescape(match[1]).strip()
        if not version or any(ord(c) < 32 for c in version):
            continue
        for link in re.findall(r'href=["\']([^"\']+)["\']', match[2]):
            try:
                parts = urlsplit(html.unescape(link))
            except ValueError:
                continue
            if parts.query or parts.fragment or parts.username or parts.password:
                continue
            if parts.scheme not in {'', 'http', 'https'}:
                continue
            if parts.netloc:
                try:
                    link_origin = site_origin((parts.scheme or urlsplit(origin).scheme) + '://' + parts.netloc)
                except ValueError:
                    continue
                if link_origin != origin:
                    continue
            if re.fullmatch(r'/files/[a-f0-9]{8}-(?:[a-f0-9]{4}-){3}[a-f0-9]{12}/download/', parts.path):
                result.append((version, origin + parts.path))
                break
    return result


def identify_release_versions(origin, item, current_sha256, known=None, *, max_headers=8, max_seconds=12):
    origin = site_origin(origin)
    versions = dict(known or {})
    versions[item['sha256']] = item['version']
    if current_sha256 in versions:
        return versions
    started = time.monotonic()
    blocks, size = [], 0
    with _request(origin + item['page_path']) as response:
        while block := response.read1(64 * 1024):
            size += len(block)
            if size > 1024 * 1024 or time.monotonic() - started > max_seconds:
                raise ValueError('版本历史读取超过限制')
            blocks.append(block)
    links = public_release_links(b''.join(blocks).decode('utf-8', errors='replace'), origin)
    for version, url in links[:max_headers]:
        if time.monotonic() - started >= max_seconds:
            break
        if version in versions.values():
            continue
        with build_opener(NoRedirect()).open(Request(url, method='HEAD', headers={'User-Agent': 'BBMOD-Catalog/1'}),
                                            timeout=min(8, max_seconds)) as response:
            sha256 = response.headers.get('X-Checksum-SHA256', '')
            if response.status == 200 and re.fullmatch('[a-f0-9]{64}', sha256):
                versions[sha256] = version
                if sha256 == current_sha256:
                    break
    return versions

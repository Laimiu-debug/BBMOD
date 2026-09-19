"""Check the public gateway after deployment; platform READY is insufficient."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import re
from urllib.parse import urlparse
from urllib.request import Request, urlopen


def check(base, path):
    request = Request(base + path, headers={'User-Agent': 'BBMOD-gateway-check/1'})
    # urllib also honors Windows system proxy settings and HTTPS_PROXY.
    with urlopen(request, timeout=30) as response:
        assert response.status == 200, (path, response.status)
        assert response.url == base + path, (path, 'Unexpected redirect', response.url)
        if not path.startswith('/static/'):
            assert 'no-store' in response.headers.get('Cache-Control', ''), (path, 'Shared caching must be disabled')
        body = response.read().decode('utf-8')
        if path == '/':
            assert '<title>BBMOD' in body, 'The public domain is serving the wrong site'
        elif path == '/health/':
            assert json.loads(body)['status'] == 'ok'
        elif path == '/api/v1/catalog/':
            assert isinstance(json.loads(body)['mods'], list)
        elif path == '/login/':
            assert 'csrfmiddlewaretoken' in body
        elif path == '/suggestions/':
            assert 'csrfmiddlewaretoken' in body and '提交建议' in body and '仅管理员可见' in body
        elif path == '/wiki/':
            assert '战场兄弟百科' in body and '/wiki/search/' in body
        elif path == '/api/v1/wiki/search/':
            assert json.loads(body)['schema_version'] == 1 and json.loads(body)['total'] > 0
        elif path == '/downloads/':
            assert 'BBMOD 桌面管理器' in body
            if '直接下载 Windows 版' in body:
                assert re.search(r'href="/downloads/windows/[a-f0-9-]+/" download="BBMOD-[^"]+\.exe"', body)
        elif path == '/api/v1/desktop/releases/':
            assert json.loads(body)['schema_version'] == 1
        elif path.endswith('.css'):
            assert 'text/css' in response.headers.get('Content-Type', '')
        return {'path': path, 'status': response.status}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('url', nargs='?', default='https://bbmod.vercel.app')
    args = parser.parse_args()
    parsed = urlparse(args.url)
    local = parsed.scheme == 'http' and parsed.hostname in {'127.0.0.1', 'localhost', '::1'}
    if ((parsed.scheme != 'https' and not local) or not parsed.hostname or parsed.username or parsed.password
            or parsed.path not in {'', '/'} or parsed.query or parsed.fragment):
        parser.error('请输入 HTTPS 网站地址，不含账号、路径或查询参数。')
    base = args.url.rstrip('/')
    paths = ['/', '/health/', '/api/v1/catalog/', '/login/', '/static/site.css', '/downloads/', '/api/v1/desktop/releases/', '/suggestions/', '/static/suggestions.css', '/wiki/', '/api/v1/wiki/search/', '/static/wiki.css']
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(lambda path: check(base, path), paths))
    print(json.dumps({'url': base, 'status': 'passed', 'checks': results}, indent=2))


if __name__ == '__main__':
    main()

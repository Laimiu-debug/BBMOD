"""Resumable, read-only acquisition of the Battle Brothers Wiki public API.

Raw source is deliberately separate from deployable application code and data.
Two workers and a shared request interval bound load on the upstream wiki.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API = 'https://battlebrothers.fandom.com/api.php'
USER_AGENT = 'BBMOD-Wiki-Migration/1.0 (https://bbmod.site/; public encyclopedia mirror)'
NAMESPACES = (0, 10, 14, 828, 6)
_lock = threading.Lock()
_next_request = 0.0


def now():
    return datetime.now(timezone.utc).isoformat()


def atomic_json(path, data, compressed=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    blob = json.dumps(data, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    if compressed:
        blob = gzip.compress(blob, mtime=0)
    tmp = path.with_suffix(path.suffix + '.part')
    tmp.write_bytes(blob)
    tmp.replace(path)


def load_json(path):
    path = Path(path)
    data = path.read_bytes()
    if path.suffix == '.gz':
        data = gzip.decompress(data)
    return json.loads(data)


def api(**params):
    global _next_request
    params.update(format='json', formatversion=2, maxlag=5)
    url = API + '?' + urlencode(params)
    for attempt in range(5):
        with _lock:
            wait = max(0, _next_request - time.monotonic())
            _next_request = time.monotonic() + wait + 0.4
        if wait:
            time.sleep(wait)
        try:
            req = Request(url, headers={'User-Agent': USER_AGENT, 'Accept-Encoding': 'gzip'})
            with urlopen(req, timeout=45) as response:
                raw = response.read(24 * 1024 * 1024 + 1)
                if len(raw) > 24 * 1024 * 1024:
                    raise ValueError('API response exceeds size limit')
                if response.headers.get('Content-Encoding') == 'gzip':
                    raw = gzip.decompress(raw)
                if len(raw) > 48 * 1024 * 1024:
                    raise ValueError('Decoded API response exceeds size limit')
                data = json.loads(raw)
            if 'error' in data:
                code = data['error'].get('code', 'unknown')
                if code not in ('maxlag', 'ratelimited', 'readonly'):
                    raise ValueError('Wiki API: ' + str(data['error']))
                raise URLError(code)
            return data
        except (HTTPError, URLError, TimeoutError, ConnectionError) as exc:
            if isinstance(exc, HTTPError) and exc.code in (401, 403, 404):
                raise
            if attempt == 4:
                raise
            delay = min(30, 2 ** (attempt + 1))
            if isinstance(exc, HTTPError):
                try:
                    delay = min(60, max(delay, int(exc.headers.get('Retry-After', 0))))
                except ValueError:
                    pass
            time.sleep(delay)


def inventory(root, refresh=False):
    path = root / 'inventory.json'
    if path.exists() and not refresh:
        return load_json(path)
    site = api(action='query', meta='siteinfo', siprop='general|statistics|rightsinfo|namespaces')
    atomic_json(root / 'siteinfo.json', site)
    pages = []
    for namespace in NAMESPACES:
        continuation = {}
        while True:
            result = api(action='query', generator='allpages', gapnamespace=namespace,
                         gaplimit=500, prop='info', **continuation)
            pages.extend(result.get('query', {}).get('pages', []))
            continuation = result.get('continue')
            if not continuation:
                break
        print(f'inventory namespace={namespace} total={len(pages)}', flush=True)
    data = {'schema_version': 1, 'source': API, 'retrieved_at': now(),
            'statistics': site['query']['statistics'], 'rights': site['query']['rightsinfo'],
            'namespaces': NAMESPACES, 'pages': sorted(pages, key=lambda r: r['pageid'])}
    atomic_json(path, data)
    return data


def fetch_page(root, row, refresh=False):
    pid = row['pageid']
    path = root / 'pages' / f'{pid}.json.gz'
    if path.exists() and not refresh:
        previous = load_json(path)
        if previous.get('requested_revision') == row.get('lastrevid'):
            return 'cached'
    if row['ns'] in (0, 14):
        data = api(action='parse', oldid=row['lastrevid'],
                   prop='text|wikitext|revid|images|links|categories|sections|templates|parsewarnings',
                   disableeditsection=1, disablelimitreport=1)
    else:
        data = api(action='query', prop='revisions', revids=row['lastrevid'],
                   rvprop='ids|timestamp|content', rvslots='main')
    document = {'schema_version': 1, 'source': API, 'retrieved_at': now(),
                'page': row, 'requested_revision': row.get('lastrevid'), 'response': data}
    atomic_json(path, document, compressed=True)
    return 'fetched'


def fetch_image_metadata(root, pages, refresh=False):
    files = [r for r in pages if r['ns'] == 6]
    for start in range(0, len(files), 50):
        group = files[start:start + 50]
        missing = [r for r in group if refresh or not (root / 'files' / f"{r['pageid']}.json").exists()]
        if not missing:
            continue
        data = api(action='query', prop='imageinfo',
                   pageids='|'.join(str(r['pageid']) for r in missing),
                   iiprop='url|size|mime|sha1|timestamp|user|extmetadata')
        for row in data.get('query', {}).get('pages', []):
            atomic_json(root / 'files' / f"{row['pageid']}.json", row)
        if start % 500 == 0:
            print(f'file metadata {min(start+50,len(files))}/{len(files)}', flush=True)


def fetch_dependencies(root, pages):
    rows = [r for r in pages if r['ns'] not in (0, 14)]
    pending = []
    for row in rows:
        path = root / 'pages' / f"{row['pageid']}.json.gz"
        if not path.exists() or load_json(path).get('requested_revision') != row.get('lastrevid'):
            pending.append(row)
    for start in range(0, len(pending), 50):
        group = pending[start:start+50]
        result = api(action='query', prop='revisions',
                     revids='|'.join(str(r['lastrevid']) for r in group),
                     rvprop='ids|timestamp|content', rvslots='main')
        returned = {r['pageid']: r for r in result.get('query', {}).get('pages', [])}
        for row in group:
            source = returned.get(row['pageid'])
            if not source or not source.get('revisions'):
                raise ValueError(f'Missing dependency revision: {row["title"]}')
            document = {'schema_version': 1, 'source': API, 'retrieved_at': now(),
                        'page': row, 'requested_revision': row['lastrevid'],
                        'response': {'query': {'pages': [source]}}}
            atomic_json(root / 'pages' / f"{row['pageid']}.json.gz", document, compressed=True)
        if start % 500 == 0:
            print(f'source dependencies {min(start+50,len(pending))}/{len(pending)}', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--refresh-inventory', action='store_true')
    parser.add_argument('--metadata-only', action='store_true')
    parser.add_argument('--workers', type=int, choices=(1, 2), default=2)
    args = parser.parse_args()
    root = args.output.resolve()
    root.mkdir(parents=True, exist_ok=True)
    data = inventory(root, args.refresh_inventory)
    fetch_image_metadata(root, data['pages'], args.refresh_inventory)
    if args.metadata_only:
        return
    fetch_dependencies(root, data['pages'])
    rows = sorted((r for r in data['pages'] if r['ns'] in (0,14)), key=lambda r: (r['ns'], r['pageid']))
    failures = []
    completed = 0
    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(fetch_page, root, row, args.refresh_inventory): row for row in rows}
        for future in as_completed(futures):
            row = futures[future]
            try:
                future.result()
            except Exception as exc:
                failures.append({'pageid': row['pageid'], 'title': row['title'], 'error': str(exc)[:600]})
            completed += 1
            if completed % 100 == 0 or completed == len(rows):
                status = {'completed': completed, 'total': len(rows), 'failures': failures,
                          'elapsed_seconds': round(time.monotonic()-started), 'updated_at': now()}
                atomic_json(root / 'fetch-status.json', status)
                print(json.dumps({k:v for k,v in status.items() if k!='failures'}) + f' errors={len(failures)}', flush=True)
    if failures:
        raise SystemExit(f'{len(failures)} sources failed; rerun resumes only missing revisions.')
    used=set()
    for row in rows:
        parsed=load_json(root/'pages'/f"{row['pageid']}.json.gz")['response'].get('parse',{})
        used.update(name.replace('_',' ').casefold() for name in parsed.get('images',[]))
    atomic_json(root/'used-images.json',sorted(used))


if __name__ == '__main__':
    main()

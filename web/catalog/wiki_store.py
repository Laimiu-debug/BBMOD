"""Read-only, versioned encyclopedia snapshots independent of community records."""
from contextlib import contextmanager
import json
from pathlib import Path
import re
import sqlite3
from urllib.parse import quote, urlencode

from django.conf import settings

SOURCE = 'https://battlebrothers.fandom.com'
LICENSE_URL = 'https://creativecommons.org/licenses/by-sa/3.0/'
SNAPSHOT_PATTERN = re.compile(r'[0-9]{8}T[0-9]{6}Z-[a-f0-9]{12}')
ASSET_PATTERN = re.compile(r'[a-f0-9]{64}\.(?:png|jpg|gif|webp|svg)')


def title_key(title):
    return ' '.join(str(title).replace('_', ' ').split()).casefold()


def page_url(title, fragment='', lang=None):
    result = '/wiki/read/' + quote(str(title).replace(' ', '_'), safe="/():',-") + '/'
    if lang in ('zh', 'en', 'bi'):
        result += '?' + urlencode({'lang': lang})
    if fragment:
        result += '#' + quote(fragment, safe=':._-')
    return result


def source_url(title):
    return SOURCE + '/wiki/' + quote(str(title).replace(' ', '_'), safe="/():',-")


def chinese_tokens(text):
    tokens = []
    for part in re.findall(r'[\u3400-\u9fff]+', text):
        if len(part) == 1:
            tokens.append(part)
        else:
            tokens.extend(part)
            tokens.extend(part[i:i+2] for i in range(len(part)-1))
    return ' '.join(tokens)


def search_expression(query):
    words = re.findall(r'[\w]+', query, flags=re.UNICODE)[:10]
    terms = []
    for word in words:
        if re.search(r'[\u3400-\u9fff]', word):
            terms.extend(chinese_tokens(word).split())
        else:
            terms.append(word)
    return ' AND '.join('"' + word.replace('"', '""') + '"*' for word in terms)


def current_release():
    root = Path(settings.WIKI_ROOT)
    try:
        info = json.loads((root / 'current.json').read_text(encoding='utf-8'))
        edition = info['snapshot']
        if not isinstance(edition, str) or not SNAPSHOT_PATTERN.fullmatch(edition):
            return None
        path = root / 'releases' / edition
        if not (path / 'wiki.sqlite3').is_file():
            return None
        return path
    except (OSError, ValueError, KeyError, TypeError):
        return None


@contextmanager
def open_store():
    release = current_release()
    if release is None:
        yield None
        return
    connection = sqlite3.connect((release / 'wiki.sqlite3').as_uri() + '?mode=ro&immutable=1', uri=True)
    connection.row_factory = sqlite3.Row
    try:
        yield WikiStore(connection, release)
    finally:
        connection.close()


class WikiStore:
    def __init__(self, connection, release):
        self.db = connection
        self.release = release
        self.page_columns = {row[1] for row in self.db.execute('PRAGMA table_info(pages)')}

    def listing_columns(self, prefix=''):
        fields = ['id', 'title', 'title_zh', 'namespace', 'revision', 'summary']
        fields += [name for name in ('summary_zh', 'translation_json') if name in self.page_columns]
        return ','.join(prefix + name for name in fields)

    @staticmethod
    def normalize(row):
        if row is None:
            return None
        result = dict(row)
        for name in ('html_zh', 'summary_zh'):
            result.setdefault(name, '')
        result.setdefault('translation_json', '{}')
        return result

    def report(self):
        row = self.db.execute("SELECT value FROM metadata WHERE key='report'").fetchone()
        return json.loads(row['value'])

    def page(self, title=None, page_id=None, summary_only=False):
        columns = self.listing_columns() if summary_only else '*'
        if page_id is not None:
            row = self.db.execute(f'SELECT {columns} FROM pages WHERE id=?', (page_id,)).fetchone()
        else:
            normalized=' '.join(str(title).replace('_',' ').split())
            row = self.db.execute(f'SELECT {columns} FROM pages WHERE title=?', (normalized,)).fetchone()
            if row is None:
                row = self.db.execute(f'SELECT {columns} FROM pages WHERE title_key=? ORDER BY (redirect="") DESC,title LIMIT 1', (title_key(title),)).fetchone()
        return self.normalize(row)

    def members(self, category, limit=100, offset=0, lang='zh'):
        params = (title_key(category.removeprefix('Category:')),)
        count = self.db.execute('SELECT COUNT(*) FROM categories WHERE category_key=?', params).fetchone()[0]
        order = 'p.title' if lang == 'en' else 'COALESCE(NULLIF(p.title_zh,\'\'),p.title)'
        rows = self.db.execute(f'''SELECT {self.listing_columns('p.')}
            FROM categories c JOIN pages p ON p.id=c.page_id WHERE c.category_key=?
            ORDER BY p.namespace DESC,{order} COLLATE NOCASE,p.title LIMIT ? OFFSET ?''', (*params,limit,offset)).fetchall()
        return count, [self.normalize(r) for r in rows]

    def search(self, query='', limit=24, offset=0, namespace=0, lang='zh'):
        query = query.strip()[:100]
        expression = search_expression(query)
        if not expression:
            count = self.db.execute('SELECT COUNT(*) FROM pages WHERE namespace=? AND redirect=""', (namespace,)).fetchone()[0]
            order = 'title' if lang == 'en' else "COALESCE(NULLIF(title_zh,''),title)"
            rows = self.db.execute(f'''SELECT {self.listing_columns()} FROM pages WHERE namespace=? AND redirect=""
                ORDER BY {order} COLLATE NOCASE,title LIMIT ? OFFSET ?''', (namespace,limit,offset)).fetchall()
        else:
            params = (expression,namespace)
            count = self.db.execute('''SELECT COUNT(*) FROM page_search s JOIN pages p ON p.id=s.rowid
                WHERE page_search MATCH ? AND p.namespace=? AND p.redirect=""''', params).fetchone()[0]
            rows = self.db.execute(f'''SELECT {self.listing_columns('p.')} FROM page_search s JOIN pages p ON p.id=s.rowid
                WHERE page_search MATCH ? AND p.namespace=? AND p.redirect=""
                ORDER BY CASE WHEN p.title_key=? OR p.title_zh=? THEN 0 ELSE 1 END,
                bm25(page_search,12.0,12.0,5.0,1.0,3.0),p.title LIMIT ? OFFSET ?''',
                (*params,title_key(query),query,limit,offset)).fetchall()
        return count, [self.normalize(r) for r in rows]

    def translation_counts(self):
        counts = {'total': 0, 'translated': 0, 'complete': 0, 'reviewed': 0,
                  'retained_english': 0, 'no_translatable_text': 0}
        for row in self.db.execute(f'''SELECT {self.listing_columns()} FROM pages
                                      WHERE namespace=0 AND redirect=""'''):
            info = translation_info(dict(row))
            if info.get('retained_english'):
                counts['retained_english'] += 1
                continue
            if info['no_translatable_text']:
                counts['no_translatable_text'] += 1
                continue
            counts['total'] += 1
            counts['translated'] += info['status'] in ('complete', 'partial')
            counts['complete'] += info['status'] == 'complete'
            counts['reviewed'] += info['reviewed'] and info['status'] == 'complete'
        return counts

    def asset(self, name):
        row = self.db.execute('SELECT * FROM assets WHERE local_name=?', (name,)).fetchone()
        return dict(row) if row else None

    def glossary(self, page_id):
        rows = self.db.execute('''SELECT en,zh FROM page_terms WHERE page_id=? ORDER BY en COLLATE NOCASE LIMIT 80''', (page_id,)).fetchall()
        return [dict(r) for r in rows]


def translation_info(row):
    """Coverage and review are independent; old snapshots imply neither."""
    try:
        info = json.loads(row.get('translation_json') or '{}')
    except (ValueError, TypeError):
        info = {}
    if not isinstance(info, dict):
        info = {}
    info = dict(info)
    no_text = (info.get('no_translatable_text') is True
               and type(info.get('total_blocks')) is int and info['total_blocks'] == 0)
    status = info.get('status', 'untranslated')
    if no_text:
        status = 'not_applicable'
    if status in ('translated', 'reviewed'):
        status = 'complete'
    if status not in ('complete', 'partial', 'untranslated', 'not_applicable'):
        status = 'partial' if row.get('html_zh') else 'untranslated'
    # Full page reads can verify that the body exists; search rows omit large HTML.
    if 'html' in row and status in ('complete', 'partial') and not row.get('html_zh'):
        status = 'untranslated'
    if row.get('html_zh') and status == 'untranslated':
        status = 'partial'
    stale = info.get('source_revision') not in (None, row.get('revision'))
    reviewed = (status == 'complete' and not stale and info.get('review_complete') is not False and
                (info.get('review_status') == 'reviewed' or info.get('status') == 'reviewed'))
    info.update(status=status, reviewed=reviewed, stale=stale, source=info.get('source', ''),
                no_translatable_text=no_text,
                review_status='not_applicable' if no_text else 'reviewed' if reviewed else info.get('review_status', 'unreviewed'))
    return info

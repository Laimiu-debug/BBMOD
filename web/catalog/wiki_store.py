"""Read-only, versioned encyclopedia snapshots independent of community records."""
from contextlib import contextmanager
import json
from pathlib import Path
import re
import sqlite3
from urllib.parse import quote

from django.conf import settings

SOURCE = 'https://battlebrothers.fandom.com'
LICENSE_URL = 'https://creativecommons.org/licenses/by-sa/3.0/'
SNAPSHOT_PATTERN = re.compile(r'[0-9]{8}T[0-9]{6}Z-[a-f0-9]{12}')
ASSET_PATTERN = re.compile(r'[a-f0-9]{64}\.(?:png|jpg|gif|webp|svg)')


def title_key(title):
    return ' '.join(str(title).replace('_', ' ').split()).casefold()


def page_url(title, fragment=''):
    result = '/wiki/read/' + quote(str(title).replace(' ', '_'), safe="/():',-") + '/'
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

    def report(self):
        row = self.db.execute("SELECT value FROM metadata WHERE key='report'").fetchone()
        return json.loads(row['value'])

    def page(self, title=None, page_id=None):
        if page_id is not None:
            row = self.db.execute('SELECT * FROM pages WHERE id=?', (page_id,)).fetchone()
        else:
            normalized=' '.join(str(title).replace('_',' ').split())
            row = self.db.execute('SELECT * FROM pages WHERE title=?', (normalized,)).fetchone()
            if row is None:
                row = self.db.execute('SELECT * FROM pages WHERE title_key=? ORDER BY (redirect="") DESC,title LIMIT 1', (title_key(title),)).fetchone()
        return dict(row) if row else None

    def members(self, category, limit=100, offset=0):
        params = (title_key(category.removeprefix('Category:')),)
        count = self.db.execute('SELECT COUNT(*) FROM categories WHERE category_key=?', params).fetchone()[0]
        rows = self.db.execute('''SELECT p.id,p.title,p.title_zh,p.namespace,p.summary
            FROM categories c JOIN pages p ON p.id=c.page_id WHERE c.category_key=?
            ORDER BY p.namespace DESC,p.title COLLATE NOCASE LIMIT ? OFFSET ?''', (*params,limit,offset)).fetchall()
        return count, [dict(r) for r in rows]

    def search(self, query='', limit=24, offset=0, namespace=0):
        query = query.strip()[:100]
        expression = search_expression(query)
        if not expression:
            count = self.db.execute('SELECT COUNT(*) FROM pages WHERE namespace=? AND redirect=""', (namespace,)).fetchone()[0]
            rows = self.db.execute('''SELECT id,title,title_zh,summary FROM pages WHERE namespace=? AND redirect=""
                ORDER BY title COLLATE NOCASE LIMIT ? OFFSET ?''', (namespace,limit,offset)).fetchall()
        else:
            params = (expression,namespace)
            count = self.db.execute('''SELECT COUNT(*) FROM page_search s JOIN pages p ON p.id=s.rowid
                WHERE page_search MATCH ? AND p.namespace=? AND p.redirect=""''', params).fetchone()[0]
            rows = self.db.execute('''SELECT p.id,p.title,p.title_zh,p.summary FROM page_search s JOIN pages p ON p.id=s.rowid
                WHERE page_search MATCH ? AND p.namespace=? AND p.redirect=""
                ORDER BY CASE WHEN p.title_key=? OR p.title_zh=? THEN 0 ELSE 1 END,
                bm25(page_search,12.0,12.0,5.0,1.0,3.0),p.title LIMIT ? OFFSET ?''',
                (*params,title_key(query),query,limit,offset)).fetchall()
        return count, [dict(r) for r in rows]

    def asset(self, name):
        row = self.db.execute('SELECT * FROM assets WHERE local_name=?', (name,)).fetchone()
        return dict(row) if row else None

    def glossary(self, page_id):
        rows = self.db.execute('''SELECT en,zh FROM page_terms WHERE page_id=? ORDER BY en COLLATE NOCASE LIMIT 80''', (page_id,)).fetchall()
        return [dict(r) for r in rows]

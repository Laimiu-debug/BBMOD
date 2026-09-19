"""Whole-unit wiki translation with revision locks and protected inline markup.

Translation files contain prose, never HTML. Original HTML/source are not edited.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from dataclasses import dataclass, field
import hashlib
import html
import json
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit, urlunsplit, parse_qsl, urlencode

from bs4 import BeautifulSoup, NavigableString, Tag

VERSION = 1
BLOCKS = set('p li td th caption dt dd h1 h2 h3 h4 h5 h6 figcaption summary blockquote div ul ol dl table tbody thead tfoot tr figure details'.split())
ATOMIC = {'img', 'br', 'hr', 'math', 'code', 'pre', 'kbd'}
TOKEN = re.compile(r'\{#(\d+)(/?)\}|\{/#(\d+)\}')
WORDS = re.compile(r"[A-Za-z]+(?:['’\-][A-Za-z]+)*")
VARIABLE = re.compile(r'%[A-Za-z0-9_]+%')
_NUMBER_BODY = r'\d+(?:,\d{3})*(?:\.\d+)?(?:\s*%)?'
NUMBER = re.compile(r'[+\-\u2212]\s*' + _NUMBER_BODY + r'|(?<![A-Za-z_\d])' + _NUMBER_BODY)


class TranslationError(ValueError):
    pass


def normalize(text):
    return re.sub(r'\s+', ' ', str(text)).strip()


def unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise TranslationError('Duplicate JSON key: ' + str(key))
        result[key] = value
    return result


def prose_text(template):
    return TOKEN.sub('', template)


def canonical_href(value):
    """Keep the destination's meaning, independent of local language selection."""
    parts = urlsplit(str(value))
    if not parts.scheme and not parts.netloc:
        path = unquote(parts.path)
        if path.startswith('/wiki/read/'):
            query = urlencode([(key, val) for key, val in parse_qsl(parts.query, keep_blank_values=True)
                               if key != 'lang'])
            return urlunsplit(('', '', path, query, unquote(parts.fragment)))
        if not path:
            return '#' + unquote(parts.fragment)
    return str(value)


def source_digest(source, inline):
    shape = [(int(key), value['tag'], value['kind'], canonical_href(value.get('href', ''))
              if value['tag'] == 'a' else '', value.get('alt', '') if value['tag'] == 'img' else '')
             for key, value in inline.items()]
    payload = json.dumps([VERSION, source, shape], ensure_ascii=False, separators=(',', ':'))
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()


@dataclass
class Unit:
    source: str
    inline: dict
    nodes: list = field(repr=False)
    originals: dict = field(repr=False)
    ordinal: int = 0
    anchor: str = ''
    kind: str = ''

    @property
    def source_sha256(self):
        return source_digest(self.source, self.inline)

    @property
    def id(self):
        return 'u-' + self.source_sha256[:24]

    @property
    def words(self):
        return len(WORDS.findall(prose_text(self.source)))

    def record(self):
        return {'id': self.id, 'source_sha256': self.source_sha256, 'source': self.source,
                'plain': normalize(prose_text(self.source)), 'inline': self.inline,
                'words': self.words, 'kind': self.kind,
                'source_anomaly': bool(re.search(r'</?[A-Za-z][^>]*>', self.source))}


def english_soup(body):
    """Remove the old bilingual term decorations, retaining their English text."""
    soup = BeautifulSoup(body, 'html.parser')
    for term in list(soup.select('.w-term')):
        original = term.select_one('.w-term-en')
        if original is not None:
            term.replace_with(NavigableString(original.get_text()))
    return soup


def extract_units(body):
    soup = english_soup(body)
    units = []

    def add(nodes, parent):
        inline, originals = {}, {}

        def encode(node):
            if isinstance(node, NavigableString):
                return str(node)
            if not isinstance(node, Tag):
                return ''
            key = str(len(inline) + 1)
            atomic = node.name in ATOMIC
            inline[key] = {'tag': node.name, 'kind': 'atomic' if atomic else 'pair'}
            if node.name == 'a':
                inline[key]['href'] = node.get('href', '')
            if node.name == 'img':
                inline[key]['alt'] = node.get('alt', '')
            originals[key] = node
            if atomic:
                return '{#' + key + '/}'
            return '{#' + key + '}' + ''.join(encode(child) for child in node.children) + '{/#' + key + '}'

        source = normalize(''.join(encode(node) for node in nodes))
        # Numbers, mathematical expressions, whitespace and images need no prose translation.
        if not WORDS.search(prose_text(source)):
            return
        unit = Unit(source, inline, list(nodes), originals, len(units),
                    parent.get('id', '') if isinstance(parent, Tag) else '',
                    parent.name or 'root')
        units.append(unit)

    def walk(parent):
        pending = []
        for node in list(parent.children):
            structural = isinstance(node, Tag) and (node.name in BLOCKS or node.find(list(BLOCKS)) is not None)
            if structural:
                if pending:
                    add(pending, parent)
                    pending = []
                if node.name not in ATOMIC:
                    walk(node)
            else:
                pending.append(node)
        if pending:
            add(pending, parent)

    walk(soup)
    return soup, units


def validate_unit(unit, record):
    if record.get('id') != unit.id or record.get('source_sha256') != unit.source_sha256 or record.get('source') != unit.source:
        raise TranslationError('Source changed or wrong unit hash: ' + unit.id)
    if record.get('status') not in ('translated', 'reviewed'):
        raise TranslationError('Invalid translation status: ' + unit.id)
    value = record.get('zh')
    if not isinstance(value, str) or not value.strip():
        raise TranslationError('Empty translation: ' + unit.id)
    if re.search(r'[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff]', value):
        raise TranslationError('Invalid translation characters: ' + unit.id)
    if re.search(r'</?[A-Za-z][^>]*>', value):
        raise TranslationError('Translation must not contain HTML: ' + unit.id)
    if Counter(TOKEN.findall(value)) != Counter(TOKEN.findall(unit.source)):
        raise TranslationError('Missing, repeated or unknown inline placeholder: ' + unit.id)
    if re.search(r'\{/?#', TOKEN.sub('', value)):
        raise TranslationError('Malformed inline placeholder: ' + unit.id)

    def parents(text):
        stack, result = [], {}
        for match in TOKEN.finditer(text):
            start, atomic, end = match.groups()
            if end:
                if not stack or stack.pop() != end:
                    raise TranslationError('Crossed or unbalanced inline tags: ' + unit.id)
            else:
                result[start] = tuple(stack)
                if not atomic:
                    stack.append(start)
        if stack:
            raise TranslationError('Unclosed inline tags: ' + unit.id)
        return result

    if parents(value) != parents(unit.source):
        raise TranslationError('Inline hierarchy changed: ' + unit.id)
    # Markup boundaries must not join an English label to a following signed
    # modifier (e.g. Minstrel<br>+1). Spaces inside a signed number or before its
    # percent suffix are formatting only and are normalized below.
    def talent_probability(match):
        icon = unit.inline.get(match.group(1), {})
        if icon.get('tag') == 'img' and re.fullmatch(r'[123] Star Talent', icon.get('alt', '')):
            return '{#' + match.group(1) + '/}' + match.group(2) + ' ' + match.group(3) + '% chance'
        return match.group()

    # The Wiki's illustrated talent legend uses "star icon - 60% chance";
    # that hyphen separates a label from a probability and is not a penalty.
    # Require the actual protected talent icon, range 0..100 and exact wording.
    numeric_source = re.sub(r'\{#(\d+)/\}((?:\{/#\d+\})*) - (0|[1-9]\d?|100)% chance\b',
                            talent_probability, unit.source)
    source_plain, translated_plain = TOKEN.sub(' ', numeric_source), TOKEN.sub(' ', value)
    exception = record.get('source_exception')
    if exception is not None:
        if (not isinstance(exception, dict) or exception.get('kind') != 'escaped_image_markup'
                or record['status'] != 'reviewed' or not isinstance(exception.get('reason'), str)
                or not exception['reason'].strip()):
            raise TranslationError('Invalid reviewed source exception: ' + unit.id)
        fragment = exception.get('source')
        if (not isinstance(fragment, str) or not fragment or source_plain.count(fragment) != 1
                or TOKEN.search(fragment)):
            raise TranslationError('Source exception does not match exactly once: ' + unit.id)
        markup = BeautifulSoup(fragment, 'html.parser')
        images = markup.find_all('img')
        if (not fragment.lstrip().startswith('<') or markup.get_text(strip=True)
                or len(images) != 1 or any(node.name not in ('a', 'img') for node in markup.find_all(True))
                or not images[0].get('src')
                or not any(node.name == 'img' and node.get('src') == images[0]['src']
                           for node in unit.originals.values())):
            raise TranslationError('Source exception must be duplicate markup for a protected image: ' + unit.id)
        # This removes only the audited duplicate image serialization. Its URL,
        # hash, dimensions and percent-encoded URL bytes are not prose variables
        # or numbers; the protected original image and its attributes remain.
        source_plain = source_plain.replace(fragment, '', 1)
    if Counter(VARIABLE.findall(source_plain)) != Counter(VARIABLE.findall(translated_plain)):
        raise TranslationError('Game variable changed: ' + unit.id)
    clean_source = VARIABLE.sub('', source_plain)
    clean_target = VARIABLE.sub('', translated_plain)
    # A compact level label is a quantity; generic identifiers such as
    # Brother1 remain identifiers and must not gain numeric requirements.
    clean_source = re.sub(r'\blvl(\d+)\b', r'lvl \1', clean_source, flags=re.I)
    clean_target = re.sub(r'\blvl(\d+)\b', r'lvl \1', clean_target, flags=re.I)
    # In an explicit level-11 label, the hyphen joins the noun and level.
    # An isolated -11 or any other hyphenated quantity keeps its sign.
    clean_source = re.sub(r'\blevel-(\d+)\b', r'level \1', clean_source, flags=re.I)
    clean_target = re.sub(r'\blevel-(\d+)\b', r'level \1', clean_target, flags=re.I)
    # "mid-200s" is an approximate positive band, not a negative modifier.
    # Require the complete English band label and plural numeric suffix.
    band = r'\b(?:low|mid|high)(?:/(?:low|mid|high))*-(\d+)s\b'
    clean_source = re.sub(band, r'\1s', clean_source, flags=re.I)
    clean_target = re.sub(band, r'\1s', clean_target, flags=re.I)
    # Map dimensions such as 140x140 contain two quantities. The second is not
    # a name suffix (unlike Brother1), even though it follows the letter x.
    clean_source = re.sub(r'(?<=\d)[xX](?=\d)', '×', clean_source)
    clean_target = re.sub(r'(?<=\d)[xX](?=\d)', '×', clean_target)
    # A compact duel size (1vs1) also contains two quantities, not a name
    # suffix. Both sides must survive even when Chinese supplies the separator.
    clean_source = re.sub(r'\b(\d+)vs(\d+)\b', r'\1 vs \2', clean_source, flags=re.I)
    clean_target = re.sub(r'\b(\d+)vs(\d+)\b', r'\1 vs \2', clean_target, flags=re.I)
    # Weapon handedness is a term, not a changed quantity. Consume only the
    # explicitly corresponding Chinese term; every other number stays exact.
    compound_en = r'\b1-\s+and\s+2-handed\b'
    compound_zh = r'单手\s*[与和、]\s*双手'
    compound_count = min(len(re.findall(compound_en, clean_source, re.I)),
                         len(re.findall(compound_zh, clean_target)))
    if compound_count:
        # Consume both sides so this same Chinese pair cannot also discharge
        # a separate numeric handedness term elsewhere in the sentence.
        clean_source = re.sub(compound_en, 'HAND_PAIR', clean_source, count=compound_count, flags=re.I)
        clean_target = re.sub(compound_zh, 'HAND_PAIR', clean_target, count=compound_count)
    for digit, term in (('1', '单手'), ('2', '双手')):
        # Some equipment source tables use lower-case "Companion (1h)".
        # This is a background variant only in that exact labelled context;
        # a bare "1h" can mean one hour and must remain a checked quantity.
        companion_en = r'\bCompanion\s*\(\s*' + digit + r'h\s*\)'
        companion_zh = r'老战友\s*(?:（\s*' + term + r'\s*）|\(\s*' + term + r'\s*\))'
        companion_count = min(len(re.findall(companion_en, clean_source)),
                              len(re.findall(companion_zh, clean_target)))
        if companion_count:
            clean_source = re.sub(companion_en, 'COMPANION_HAND', clean_source, count=companion_count)
            clean_target = re.sub(companion_zh, 'COMPANION_HAND', clean_target, count=companion_count)
        sword_en = r'\b' + digit + r'h\s+swords?\b'
        sword_zh = term + '剑'
        sword_count = min(len(re.findall(sword_en, clean_source)), clean_target.count(sword_zh))
        if sword_count:
            clean_source = re.sub(sword_en, 'HANDED_SWORD', clean_source, count=sword_count)
            clean_target = clean_target.replace(sword_zh, 'HANDED_SWORD', sword_count)
        # The background table also names the two Companion variants exactly
        # "(1Hand)" / "(2Hand)". These are the same weapon-category terms.
        pattern = r'\b' + digit + r'(?:[ -]?handed|-?handers?|Hand|(?-i:H))\b'
        count = min(len(re.findall(pattern, clean_source, re.I)), clean_target.count(term))
        clean_source = re.sub(pattern, term, clean_source, count=count, flags=re.I) if count else clean_source
    if (Counter(re.sub(r'\s+', '', number).replace('\u2212', '-') for number in NUMBER.findall(clean_source))
            != Counter(re.sub(r'\s+', '', number).replace('\u2212', '-') for number in NUMBER.findall(clean_target))):
        raise TranslationError('Numbers changed: ' + unit.id)
    return value


def translated_nodes(soup, unit, value):
    holder = soup.new_tag('span')
    stack, cursor = [holder], 0
    for match in TOKEN.finditer(value):
        stack[-1].append(NavigableString(value[cursor:match.start()]))
        start, atomic, end = match.groups()
        if end:
            stack.pop()
        elif atomic:
            stack[-1].append(deepcopy(unit.originals[start]))
        else:
            original = unit.originals[start]
            node = soup.new_tag(original.name, attrs=deepcopy(original.attrs))
            stack[-1].append(node)
            stack.append(node)
        cursor = match.end()
    stack[-1].append(NavigableString(value[cursor:]))
    return list(holder.contents)


class TranslationCatalog:
    def __init__(self, directory=None):
        self.pages, self.records, self.titles, self.files = {}, {}, {}, []
        self.retained_english = {}
        self.entries = []
        if directory is not None and not Path(directory).is_dir():
            raise TranslationError('Wiki translation directory does not exist or is not a directory: ' + str(directory))
        for path in sorted(Path(directory).glob('*.json')) if directory is not None else []:
            raw = path.read_bytes()
            document = json.loads(raw.decode('utf-8'), object_pairs_hook=unique_keys)
            if not isinstance(document, dict) or document.get('schema_version') != VERSION:
                raise TranslationError('Unknown wiki translation format: ' + str(path))
            self.files.append({'file': path.name, 'sha256': hashlib.sha256(raw).hexdigest()})
            if document.get('kind') == 'wiki_translation_scope':
                policy = document.get('retained_english')
                if (not isinstance(policy, dict) or not isinstance(policy.get('source_category'), str)
                        or not policy['source_category'].strip() or not isinstance(policy.get('reason'), str)
                        or not policy['reason'].strip() or not isinstance(policy.get('pages'), list)
                        or not policy['pages']):
                    raise TranslationError('Invalid retained-English scope: ' + str(path))
                seen = set()
                for page in policy['pages']:
                    if (not isinstance(page, dict) or type(page.get('id')) is not int or page['id'] <= 0
                            or type(page.get('revision')) is not int or page['revision'] <= 0
                            or not isinstance(page.get('title'), str) or not page['title'].strip()
                            or page['id'] in seen):
                        raise TranslationError('Invalid retained-English page identity: ' + str(path))
                    seen.add(page['id'])
                    entry = {**page, 'category': policy['source_category'], 'reason': policy['reason']}
                    old = self.retained_english.get(page['id'])
                    if old is not None and old != entry:
                        raise TranslationError('Conflicting retained-English page: ' + str(page['id']))
                    if page['id'] in self.pages and self.pages[page['id']] != page['revision']:
                        raise TranslationError('Conflicting page revision: ' + str(page['id']))
                    self.retained_english[page['id']] = entry
                    self.pages[page['id']] = page['revision']
                continue
            if 'titles' in document:
                if not isinstance(document['titles'], dict):
                    raise TranslationError('Invalid title dictionary: ' + str(path))
                for en, zh in document['titles'].items():
                    if not isinstance(zh, str) or '<' in zh or '>' in zh:
                        raise TranslationError('Invalid title translation: ' + en)
                    if en in self.titles and self.titles[en] != zh:
                        raise TranslationError('Conflicting title translation: ' + en)
                    self.titles[en] = zh
                continue
            if document.get('kind') != 'wiki_units' or document.get('schema_version') != VERSION:
                raise TranslationError('Unknown wiki translation format: ' + str(path))
            revisions = document.get('page_revisions')
            if not isinstance(revisions, dict) or not revisions:
                raise TranslationError('Missing page revision constraints: ' + str(path))
            for page, revision in revisions.items():
                if not str(page).isdigit() or int(page) <= 0 or type(revision) is not int or revision <= 0:
                    raise TranslationError('Invalid page revision: ' + str(path))
                page = int(page)
                if page in self.pages and self.pages[page] != revision:
                    raise TranslationError('Conflicting page revision: ' + str(page))
                self.pages[page] = revision
            if not isinstance(document.get('units'), list):
                raise TranslationError('Invalid translation unit list: ' + str(path))
            for record in document['units']:
                if not isinstance(record, dict):
                    raise TranslationError('Invalid translation unit: ' + str(path))
                identity = record.get('id')
                if (not isinstance(identity, str) or not re.fullmatch(r'u-[a-f0-9]{24}', identity)
                        or not isinstance(record.get('source'), str)
                        or not isinstance(record.get('source_sha256'), str)
                        or not re.fullmatch(r'[a-f0-9]{64}', record['source_sha256'])
                        or record.get('status') not in ('translated', 'reviewed')
                        or not isinstance(record.get('zh'), str) or not record['zh'].strip()):
                    raise TranslationError('Invalid unit record: ' + str(path))
                page_ids = record.get('page_ids', list(map(int, revisions)))
                if (not isinstance(page_ids, list) or not page_ids
                        or any(type(page) is not int or str(page) not in revisions for page in page_ids)):
                    raise TranslationError('Unit scope is outside revision-locked pages: ' + identity)
                scope = set(page_ids)
                for entry in self.records.get(identity, []):
                    old = entry['record']
                    if scope & entry['pages'] and any(old.get(k) != record.get(k)
                            for k in ('source', 'source_sha256', 'zh', 'source_exception')):
                        raise TranslationError('Conflicting duplicate unit on the same page: ' + identity)
                entry = {'record': record, 'pages': scope, 'key': len(self.entries),
                         'origin': path.name + ':' + identity}
                self.records.setdefault(identity, []).append(entry)
                self.entries.append(entry)
        self.used = set()

    def validate_revisions(self, rows):
        revisions = {int(row.get('pageid', row.get('id'))): int(row.get('lastrevid', row.get('revision'))) for row in rows}
        for page, revision in self.pages.items():
            if revisions.get(page) != revision:
                raise TranslationError(f'Page {page} revision changed: expected {revision}, actual {revisions.get(page)}')

    def validate_retention_sources(self, rows):
        """A checked-in category scope is explicit, complete and source-bound.

        Category membership alone never activates retention. A changed title,
        revision or membership requires reviewing the policy file again.
        """
        if not self.retained_english:
            return
        sources = {}
        for row in rows:
            identity = int(row.get('pageid', row.get('id')))
            categories = row.get('categories')
            if categories is None:
                categories = json.loads(row.get('categories_json', '[]'))
            sources[identity] = {**row, 'categories': categories}
        for identity, policy in self.retained_english.items():
            row = sources.get(identity, {})
            if (row.get('title') != policy['title'] or row.get('ns', row.get('namespace')) != 0
                    or row.get('redirect') or policy['category'] not in row.get('categories', [])):
                raise TranslationError('Retained-English source identity/category changed: ' + str(identity))
        for category in {policy['category'] for policy in self.retained_english.values()}:
            expected = {identity for identity, policy in self.retained_english.items() if policy['category'] == category}
            actual = {identity for identity, row in sources.items()
                      if row.get('ns', row.get('namespace')) == 0 and not row.get('redirect')
                      and category in row['categories']}
            if actual != expected:
                raise TranslationError('Retained-English category membership changed: ' + category)

    @property
    def suppressed_translation_records(self):
        return sum(entry['pages'] <= self.retained_english.keys() for entry in self.entries)

    def apply(self, page_id, revision, body, sections=(), applicable=True):
        from .wiki_render import CLEANER
        soup, units = extract_units(body)
        total_words = sum(unit.words for unit in units)
        translated, reviewed, translated_words, reviewed_words = 0, 0, 0, 0
        headings, translated_plain_fragments, untranslated = {}, [], []
        if page_id in self.pages and self.pages[page_id] != revision:
            raise TranslationError('Page revision changed: ' + str(page_id))
        if page_id in self.retained_english:
            policy = self.retained_english[page_id]
            info = {'schema_version': VERSION, 'source': 'BBMOD explicit translation scope',
                    'source_revision': revision, 'status': 'not_applicable', 'retained_english': True,
                    'retention_reason': policy['reason'], 'retention_category': policy['category'],
                    'total_blocks': len(units), 'source_words': total_words,
                    'translated_blocks': 0, 'reviewed_blocks': 0, 'untranslated_blocks': 0,
                    'excluded_blocks': len(units), 'translated_words': 0, 'reviewed_words': 0,
                    'review_complete': False, 'review_status': 'not_applicable'}
            return {'html_zh': '', 'summary_zh': '', 'plain_zh': '', 'translation': info,
                    'sections': [{key: value for key, value in section.items() if key != 'title_zh'}
                                 for section in sections]}
        for unit in units:
            entries = [entry for entry in self.records.get(unit.id, []) if page_id in entry['pages']]
            if not entries:
                untranslated.append(unit)
                continue
            record = next((entry['record'] for entry in entries if entry['record']['status'] == 'reviewed'), entries[0]['record'])
            value = validate_unit(unit, record)
            self.used.update(entry['key'] for entry in entries)
            fragments = translated_nodes(soup, unit, value)
            translated_plain_fragments.append(BeautifulSoup(''.join(str(fragment) for fragment in fragments), 'html.parser').get_text(' ', strip=True))
            for fragment in fragments:
                unit.nodes[0].insert_before(fragment)
            for node in unit.nodes:
                node.extract()
            translated += 1
            translated_words += unit.words
            if record['status'] == 'reviewed':
                reviewed += 1
                reviewed_words += unit.words
            if unit.kind.startswith('h') and len(unit.kind) == 2:
                headings[normalize(prose_text(unit.source))] = normalize(prose_text(value))
        info = {'schema_version': VERSION, 'source': 'BBMOD independent wiki review', 'source_revision': revision,
                'status': 'not_applicable' if not units else 'complete' if translated == len(units) else 'partial' if translated else 'untranslated' if applicable else 'not_applicable',
                'no_translatable_text': not units,
                'total_blocks': len(units), 'translated_blocks': translated, 'reviewed_blocks': reviewed,
                'untranslated_blocks': len(units) - translated, 'source_words': total_words,
                'translated_words': translated_words, 'reviewed_words': reviewed_words,
                'review_complete': bool(units) and reviewed == len(units),
                'review_status': 'not_applicable' if not units else 'reviewed' if reviewed == len(units) else 'partial' if reviewed else 'unreviewed'}
        sections = [dict(section) for section in sections]
        for section in sections:
            if normalize(section.get('title', '')) in headings:
                section['title_zh'] = headings[normalize(section['title'])]
        if translated:
            for node in soup.find_all(lang=True):
                if node['lang'].lower() in ('en', 'en-us', 'en-gb'):
                    node['lang'] = 'zh-Hans'
            for unit in untranslated:
                marker = soup.new_tag('span', lang='en')
                unit.nodes[0].insert_before(marker)
                for node in unit.nodes:
                    marker.append(node.extract())
            root = soup.new_tag('div', lang='zh-Hans')
            for node in list(soup.contents):
                root.append(node.extract())
            soup.append(root)
        result_html = CLEANER.clean(str(soup)) if translated else ''
        translated_plain = BeautifulSoup(result_html, 'html.parser').get_text(' ', strip=True) if result_html else ''
        return {'html_zh': result_html, 'summary_zh': normalize(' '.join(translated_plain_fragments))[:260],
                'plain_zh': translated_plain, 'sections': sections, 'translation': info}

    def assert_used(self):
        # A record scoped solely to explicitly retained pages is suppressed by
        # policy. Mixed scopes must still match at least one translatable page.
        unused = [entry['origin'] for entry in self.entries if entry['key'] not in self.used
                  and not entry['pages'] <= self.retained_english.keys()]
        if unused:
            raise TranslationError(f'{len(unused)} translation records did not match their revision-locked page scope: {sorted(unused)[:5]}')

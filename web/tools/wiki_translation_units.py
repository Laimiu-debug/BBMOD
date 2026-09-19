"""Extract, validate and report complete wiki translation units."""
from __future__ import annotations

import argparse
from collections import Counter
import gzip
import json
from pathlib import Path
import re
import sqlite3
import sys

WEB = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WEB))
from catalog.wiki_translation import TranslationCatalog, TranslationError, Unit, TOKEN, extract_units, normalize, validate_unit


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    staged = path.with_suffix(path.suffix + '.tmp')
    staged.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    staged.replace(path)


def game_plain(value):
    """Normalize display markup only. Real %variables% and prose stay intact."""
    value = value.replace('\\r\\n', '\n').replace('\\n', '\n').replace('\r\n', '\n')
    value = re.sub(r'\[img\].*?\[/img\]', '', value, flags=re.S | re.I)
    # Original scripts/events/event.nut assigns these two macros only an
    # [img]...[/img] string (or ""). They are display pictures, not names or
    # terrain descriptions. Keep every real prose variable, including %terrain%.
    value = value.replace('%terrainImage%', '').replace('%townImage%', '')
    value = re.sub(r'\[/?(?:b|i|u|s|color|font|size|url|align)(?:=[^\]]*)?\]', '', value, flags=re.I)
    # These two engine tokens delimit displayed speech; they are not character
    # substitutions. Apart from the two audited image macros above, do not
    # remove any other percent-delimited variable.
    return value.replace('%SPEECH_ON%', '"').replace('%SPEECH_OFF%', '"')


def match_key(value):
    return normalize(value.translate(str.maketrans({'“': '"', '”': '"', '‘': "'", '’': "'"})))


def game_matches(path):
    document = json.loads(path.read_text(encoding='utf-8'))
    result = {}
    for identity, entry in document['entries'].items():
        if entry.get('status') != 'reviewed' or not entry.get('translation'):
            continue
        source, translation = game_plain(entry['source']), game_plain(entry['translation'])
        if source.strip():
            result.setdefault(match_key(source), []).append({'entry_id': identity,
                'translation': normalize(translation), 'match_kind': 'whole_entry'})
        source_parts = re.split(r'\n\s*\n', source.strip())
        target_parts = re.split(r'\n\s*\n', translation.strip())
        if len(source_parts) > 1 and len(source_parts) == len(target_parts):
            for index, (en, zh) in enumerate(zip(source_parts, target_parts)):
                if en.strip() and zh.strip():
                    result.setdefault(match_key(en), []).append({'entry_id': identity,
                        'translation': normalize(zh), 'match_kind': 'aligned_paragraph',
                        'paragraph_index': index, 'paragraph_count': len(source_parts)})
        # The engine displays SPEECH_ON/OFF as its own speech blocks. Wiki prose
        # often keeps those block boundaries even when the catalog has no newline.
        # Split both languages by the same explicit delimiters, never punctuation.
        raw_source = re.split(r'(%SPEECH_ON%.*?%SPEECH_OFF%)', entry['source'], flags=re.S)
        raw_target = re.split(r'(%SPEECH_ON%.*?%SPEECH_OFF%)', entry['translation'], flags=re.S)
        if len(raw_source) > 1 and len(raw_source) == len(raw_target):
            for segment, (en_block, zh_block) in enumerate(zip(raw_source, raw_target)):
                en_parts = re.split(r'\n\s*\n', game_plain(en_block).strip())
                zh_parts = re.split(r'\n\s*\n', game_plain(zh_block).strip())
                if len(en_parts) != len(zh_parts):
                    continue
                for paragraph, (en, zh) in enumerate(zip(en_parts, zh_parts)):
                    if en.strip() and zh.strip():
                        candidate = {'entry_id': identity, 'translation': normalize(zh),
                            'match_kind': 'aligned_speech_segment', 'speech_segment_index': segment,
                            'speech_segment_count': len(raw_source), 'paragraph_index': paragraph,
                            'paragraph_count': len(en_parts)}
                        result.setdefault(match_key(en), []).append(candidate)
    return result


def extract(database, output, catalog, page_ids=None, source=None):
    connection = sqlite3.connect(database.as_uri() + '?mode=ro', uri=True)
    connection.row_factory = sqlite3.Row
    units, pages, by_namespace = {}, {}, Counter()
    matches = game_matches(catalog)
    for row in connection.execute('SELECT id,title,namespace,revision,html FROM pages WHERE redirect="" AND namespace IN (0,14) AND id>0 ORDER BY id'):
        if page_ids and row['id'] not in page_ids:
            continue
        if source:
            saved = json.loads(gzip.decompress((source / 'pages' / f"{row['id']}.json.gz").read_bytes()))
            if (saved['requested_revision'] != row['revision']
                    or saved.get('response', {}).get('parse', {}).get('revid', row['revision']) != row['revision']):
                raise ValueError('SQLite/source revision mismatch: ' + row['title'])
        _, extracted = extract_units(row['html'])
        page = {'id': row['id'], 'title': row['title'], 'revision': row['revision'], 'namespace': row['namespace'],
                'unit_ids': [unit.id for unit in extracted], 'words': sum(unit.words for unit in extracted)}
        pages[str(row['id'])] = page
        by_namespace[row['namespace']] += 1
        for unit in extracted:
            if unit.id not in units:
                record = unit.record()
                record['page_ids'] = []
                record['occurrences'] = 0
                candidates = matches.get(match_key(record['plain']), [])
                if candidates:
                    record['game_matches'] = candidates
                units[unit.id] = record
            record = units[unit.id]
            record['occurrences'] += 1
            if row['id'] not in record['page_ids']:
                record['page_ids'].append(row['id'])
        if len(pages) % 100 == 0:
            print(f'extract {len(pages)} pages / {len(units)} unique units', flush=True)
    connection.close()
    unique = list(units.values())
    matched = [unit for unit in unique if unit.get('game_matches')]
    report = {'schema_version': 1, 'pages': len(pages), 'namespace_counts': dict(by_namespace),
              'total_units': sum(len(page['unit_ids']) for page in pages.values()), 'unique_units': len(unique),
              'total_words': sum(page['words'] for page in pages.values()), 'unique_words': sum(unit['words'] for unit in unique),
              'exact_game_match_unique_units': len(matched), 'exact_game_match_unique_words': sum(unit['words'] for unit in matched),
              'exact_game_match_occurrences': sum(unit['occurrences'] for unit in matched),
              'source_anomaly_units': sum(unit['source_anomaly'] for unit in unique),
              'source_database': str(database), 'word_count_method': 'English lexical words in complete units; excludes protected images/math/code and markup tokens',
              'match_method': 'Exact case-sensitive text after removing complete game image markup, audited terrainImage/townImage display macros, known BBCode, normalizing whitespace/literal newlines and quote glyphs; SPEECH_ON/OFF become quotes. Real variables remain. Whole entries and equal-count aligned paragraphs/explicit speech blocks only; no fuzzy matching'}
    unambiguous = [unit for unit in matched if len({candidate['translation'] for candidate in unit['game_matches']}) == 1]
    report['exact_game_match_unambiguous_units'] = len(unambiguous)
    report['exact_game_match_unambiguous_words'] = sum(unit['words'] for unit in unambiguous)
    report['exact_game_match_no_inline_units'] = sum(not unit['inline'] for unit in unambiguous)
    report['exact_game_match_no_inline_words'] = sum(unit['words'] for unit in unambiguous if not unit['inline'])
    report['exact_game_match_unique_unit_ratio'] = len(matched) / max(1, len(unique))
    report['exact_game_match_unique_word_ratio'] = report['exact_game_match_unique_words'] / max(1, report['unique_words'])
    dump(output / 'corpus.json', {'schema_version': 1, 'units': unique})
    dump(output / 'pages.json', {'schema_version': 1, 'pages': pages})
    dump(output / 'report.json', report)
    print(json.dumps(report, ensure_ascii=False))
    return report


def validate(database, directory, output):
    connection = sqlite3.connect(database.as_uri() + '?mode=ro', uri=True)
    connection.row_factory = sqlite3.Row
    rows = [dict(row) for row in connection.execute('SELECT * FROM pages WHERE id>0')]
    translations = TranslationCatalog(directory)
    translations.validate_revisions(rows)
    translations.validate_retention_sources(rows)
    totals = Counter()
    pages = []
    for row in rows:
        result = translations.apply(row['id'], row['revision'], row['html'], json.loads(row['sections_json']),
                                    row['namespace'] in (0,14) and not row['redirect'])
        info = result['translation']
        if row['namespace'] in (0,14) and not row['redirect']:
            if info.get('retained_english'):
                totals['retained_english_pages'] += 1
                totals['retained_english_blocks'] += info['total_blocks']
                totals['retained_english_source_words'] += info['source_words']
            else:
                totals[info['status']] += 1
                for key in ('total_blocks','translated_blocks','reviewed_blocks','untranslated_blocks','source_words','translated_words','reviewed_words'):
                    totals[key] += info[key]
            pages.append({'id': row['id'], 'title': row['title'], **info})
    translations.assert_used()
    connection.close()
    report = {'schema_version': 1, 'status': 'valid', 'totals': dict(totals), 'files': translations.files,
              'suppressed_translation_records': translations.suppressed_translation_records, 'pages': pages}
    if output:
        dump(output, report)
    print(json.dumps({'status': 'valid', 'totals': dict(totals)}, ensure_ascii=False))
    return report


def exact_reuse_record(unit, candidates):
    """Reuse a complete reviewed sentence only when its markup can stay whole.

    Markup inside the prose needs a translator to choose its Chinese position.
    A whole-unit wrapper or leading/trailing icon is safe to preserve verbatim.
    No token-template substitution is performed by this function.
    """
    values = {candidate['translation'] for candidate in candidates}
    if len(values) != 1:
        raise TranslationError('Ambiguous reviewed game translations')
    source = unit['source']
    edge = r'(?:\s|' + TOKEN.pattern + r')*'
    prefix = re.match(edge, source).group()
    suffix = re.search(edge + r'$', source).group()
    middle_end = len(source) - len(suffix) if suffix else len(source)
    if TOKEN.search(source[len(prefix):middle_end]):
        raise TranslationError('Inline prose needs reviewed positioning')
    record = {'id': unit['id'], 'source_sha256': unit['source_sha256'], 'source': source,
              'zh': prefix + next(iter(values)) + suffix, 'status': 'reviewed',
              'page_ids': unit['page_ids'], 'provenance': {'method': 'exact_reviewed_game_prose',
                  'game_matches': candidates}}
    validate_unit(Unit(source, unit['inline'], [], {}), record)
    return record


def export_game_reuse(corpus_directory, catalog, output, excluded=(), minimum_words=8):
    corpus = json.loads((corpus_directory / 'corpus.json').read_text(encoding='utf-8'))
    pages = json.loads((corpus_directory / 'pages.json').read_text(encoding='utf-8'))['pages']
    matches = game_matches(catalog)
    records, rejected, scopes = [], Counter(), set()
    words = 0
    excluded = set(excluded)
    for unit in corpus['units']:
        scope = [page for page in unit['page_ids'] if page not in excluded]
        if not scope or unit['words'] < minimum_words or unit['source_anomaly']:
            continue
        candidates = matches.get(match_key(unit['plain']), [])
        if not candidates:
            continue
        try:
            record = exact_reuse_record({**unit, 'page_ids': scope}, candidates)
        except TranslationError as error:
            rejected[str(error).split(': u-')[0]] += 1
            continue
        records.append(record)
        scopes.update(scope)
        words += unit['words']
    document = {'schema_version': 1, 'kind': 'wiki_units',
        'page_revisions': {str(page): pages[str(page)]['revision'] for page in sorted(scopes)},
        'provenance': {'source': 'BBMOD independent reviewed game catalog',
                       'method': 'Exact complete text only, with explicit paired paragraph/speech boundaries. No variable inference or internal markup positioning.'},
        'units': records}
    report = {'schema_version': 1, 'status': 'validated_candidates', 'units': len(records),
              'unique_words': words, 'scoped_pages': len(scopes), 'excluded_pages': sorted(excluded),
              'minimum_words': minimum_words, 'rejected': dict(rejected)}
    dump(output, document)
    dump(output.with_name(output.stem + '-report.json'), report)
    print(json.dumps(report, ensure_ascii=False))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('extract','validate','report','reuse'))
    parser.add_argument('--database', type=Path)
    parser.add_argument('--source', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--catalog', type=Path, default=WEB.parent / 'app/localization/full_catalog.json')
    parser.add_argument('--translations', type=Path, default=WEB / 'content/wiki-zh')
    parser.add_argument('--pages', type=int, nargs='*')
    parser.add_argument('--corpus', type=Path, default=WEB.parent / 'output/wiki-translation')
    parser.add_argument('--exclude-pages', type=int, nargs='*', default=[])
    parser.add_argument('--minimum-words', type=int, default=8)
    args = parser.parse_args()
    if args.command != 'reuse' and not args.database:
        parser.error('--database is required for extract, validate and report')
    if args.command == 'reuse':
        export_game_reuse(args.corpus.resolve(), args.catalog.resolve(),
            (args.output or args.corpus / 'game-reuse-candidates.json').resolve(), args.exclude_pages, args.minimum_words)
        return
    if args.command == 'extract':
        extract(args.database.resolve(), (args.output or WEB.parent / 'output/wiki-translation').resolve(),
                args.catalog.resolve(), set(args.pages or []), args.source.resolve() if args.source else None)
    else:
        validate(args.database.resolve(), args.translations.resolve(), args.output)


if __name__ == '__main__':
    main()

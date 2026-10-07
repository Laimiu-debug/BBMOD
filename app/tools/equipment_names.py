"""Resolve reviewed equipment types separately from random in-game names."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def naming_sources():
    translations = ROOT / 'localization/full_catalog.json'
    names = ROOT / 'data/item_inspector/names.json'
    terms = {entry['source']: entry['translation']
             for entry in json.loads(translations.read_text('utf-8'))['entries'].values()
             if entry['status'] == 'reviewed'}
    return (json.loads(names.read_text('utf-8'))['items'], terms,
            hashlib.sha256(translations.read_bytes()).hexdigest(),
            hashlib.sha256(names.read_bytes()).hexdigest())


def naming_fields(identifier, source, names, terms):
    record = names[identifier]
    if source != record['source']:
        raise ValueError(f'Equipment naming source changed: {identifier}: {source}')
    # Fail on missing name components instead of mixing English into a Chinese
    # game-name search. The reviewed source list is keyed by ID, never file order.
    pool = [{'en': name, 'zh': terms[name]} for name in record['names']]
    return {'en': record['type_en'], 'zh': terms.get(record['type_en'], record['type_zh']),
            'name_mode': 'random', 'name_pool': pool}


def refresh_named_names(document):
    names, terms, translation_hash, naming_hash = naming_sources()
    if set(document['items']) != set(names):
        raise ValueError('The reviewed naming table does not cover the named equipment catalog')
    for identifier, item in document['items'].items():
        item.update(naming_fields(identifier, item['source'], names, terms))
    document['translation_sha256'] = translation_hash
    document['naming_sha256'] = naming_hash
    return document

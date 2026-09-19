"""Extract equipment facts from local original scripts without executing game code.

Descriptions and game code are not distributed. Names use BBMOD's reviewed terms;
the separately verified named-item catalog remains the authority for random rolls.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.item_inspector import FIELDS

NUMERIC = (*FIELDS, 'Vision', 'RangeMin', 'RangeMax')
TEXT = ('ID', 'Name', 'Categories')
TRACKED = {*NUMERIC, *TEXT, 'ItemType', 'IsDroppedAsLoot'}
FOLDERS = {'weapons': 'weapon', 'armor': 'armor', 'helmets': 'helmet', 'shields': 'shield'}


def build(source: Path, output: Path):
    terms_path = ROOT / 'localization/full_catalog.json'
    terms = {entry['source']: entry['translation']
             for entry in json.loads(terms_path.read_text('utf-8'))['entries'].values()
             if entry['status'] == 'reviewed'}
    named_path = ROOT / 'data/item_inspector/catalog.json'
    named = json.loads(named_path.read_text('utf-8'))['items']
    named_sources = {entry['source']: (identifier, entry) for identifier, entry in named.items()}
    hashes, cache = {}, {}

    def layers(relative):
        if relative in cache:
            return cache[relative]
        path = source / relative
        text = path.read_text('utf-8')
        hashes[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
        parent = re.search(r'this\.inherit\("([^"]+)"', text)
        defaults, creates = layers(parent[1] + '.nut') if parent else ([], [])
        # Only member declarations and the create function are inspected. No
        # tooltip, attachment, actor-skill or on-equip adjustments enter the data.
        members = text.split('\n\tfunction ', 1)[0]
        own_defaults = re.findall(r'^\t\t(\w+)\s*=\s*(.*?)(?:,)?\r?$', members, re.MULTILINE)
        create = re.search(r'\bfunction create\(\)\s*\{(.*?)(?=\n\tfunction |\n\}\);|\n\};)', text, re.DOTALL)
        body = create[1].split('this.randomizeValues();')[0] if create else ''
        own_creates = re.findall(r'this\.m\.(\w+)\s*=\s*([^;]+);', body)
        # Reject branch-dependent stat writes instead of silently choosing one.
        seen = set()
        for key, _ in own_creates:
            if key in TRACKED:
                if key in seen:
                    raise ValueError(f'Ambiguous field: {relative}: {key}')
                seen.add(key)
        result = (defaults + own_defaults, creates + own_creates)
        cache[relative] = result
        return result

    def facts(relative):
        values = dict.fromkeys(NUMERIC, 0)
        values.update(ConditionMax=1, ArmorDamageMult=1, ID='', Name='', Categories='',
                      ItemType='', IsDroppedAsLoot=False)
        defaults, creates = layers(relative)
        for key, value in defaults + creates:
            if key not in TRACKED:
                continue
            value = value.strip().rstrip(',')
            if key in NUMERIC:
                if not re.fullmatch(r'-?\d+(?:\.\d+)?', value):
                    raise ValueError(f'Nonliteral stat: {relative}: {key} = {value}')
                values[key] = float(value) if '.' in value else int(value)
            elif key in TEXT:
                if not re.fullmatch(r'"(?:\\.|[^"\\])*"', value):
                    raise ValueError(f'Nonliteral name: {relative}: {key}')
                values[key] = value[1:-1].replace("\\'", "'").replace('\\"', '"').replace('\\\\', '\\')
            elif key == 'IsDroppedAsLoot':
                if value not in ('true', 'false'):
                    raise ValueError(f'Nonliteral loot setting: {relative}')
                values[key] = value == 'true'
            else:
                values[key] = value.replace('this.m.ItemType', values[key])
        return values

    items, excluded = {}, []
    for folder, kind in FOLDERS.items():
        for path in sorted((source / 'scripts/items' / folder).rglob('*.nut')):
            relative = path.relative_to(source).as_posix()
            if path.stem == kind or path.stem == 'named_' + kind:
                continue
            values = facts(relative)
            known = named_sources.get(relative)
            if known:
                identifier, entry = known
                for key in FIELDS:
                    if values[key] != entry['base'][key]:
                        raise ValueError(f'Named baseline drift: {relative}: {key}')
                english, chinese, rarity = entry['en'], entry['zh'], 'named'
                assert identifier == values['ID']
            else:
                english = values['Name']
                if not english or not values['ID']:
                    excluded.append({'source': relative, 'reason': 'No visible name or item ID'})
                    continue
                chinese = terms.get(english, english)
                rarity = ('legendary' if 'ItemType.Legendary' in values['ItemType'] else
                          'regular' if values['IsDroppedAsLoot'] else 'special')
            ranged = 'ItemType.RangedWeapon' in values['ItemType']
            group = ('ranged' if ranged else 'two_handed' if 'ItemType.TwoHanded' in values['ItemType']
                     else 'one_handed') if kind == 'weapon' else kind
            items[relative] = {
                'id': values['ID'], 'en': english, 'zh': chinese, 'kind': kind,
                'group': group, 'rarity': rarity, 'ranged': ranged,
                'category': terms.get(values['Categories'], values['Categories']),
                'loot': values['IsDroppedAsLoot'],
                'base': {key: values[key] for key in NUMERIC},
            }
    assert sum(item['rarity'] == 'named' for item in items.values()) == len(named) == 94
    document = {
        'schema': 1, 'game_version': '1.5.2.3',
        'provenance': 'Original local game scripts; BBMOD independently reviewed Chinese terminology.',
        'translation_sha256': hashlib.sha256(terms_path.read_bytes()).hexdigest(),
        'named_catalog_sha256': hashlib.sha256(named_path.read_bytes()).hexdigest(),
        'source_sha256': dict(sorted(hashes.items())), 'excluded': excluded, 'items': items,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(document, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Built {len(items)} equipment entries; {len(excluded)} unnamed internal entries excluded: {output}')
    return document


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / 'build/full-l10n/decompiled')
    parser.add_argument('--output', type=Path, default=ROOT / 'data/equipment_catalog.json')
    args = parser.parse_args()
    build(args.source, args.output)

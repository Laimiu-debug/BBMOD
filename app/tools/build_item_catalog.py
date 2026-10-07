"""Build verified numeric baselines from local original 1.5.2.3 scripts.

Only literals before randomizeValues are accepted; game code is never executed.
The generated artifact contains factual stats, reviewed type labels and game-name components.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.equipment_names import naming_fields, naming_sources, refresh_named_names
FIELDS = ('ConditionMax StaminaModifier RegularDamage RegularDamageMax ArmorDamageMult DirectDamageMult '
          'DirectDamageAdd ChanceToHitHead ShieldDamage AmmoMax AdditionalAccuracy FatigueOnSkillUse '
          'MeleeDefense RangedDefense').split()


def build(source, output):
    names, terms, translation_hash, naming_hash = naming_sources()
    items, hashes = {}, {}
    for folder, category, base in [('weapons', 'weapon', 'named_weapon'),
            ('armor', 'armor', 'named_armor'), ('helmets', 'helmet', 'named_helmet'),
            ('shields', 'shield', 'named_shield')]:
        directory = source / 'scripts/items' / folder / 'named'
        parent = directory / (base + '.nut')
        hashes[parent.relative_to(source).as_posix()] = hashlib.sha256(parent.read_bytes()).hexdigest()
        children = [p for p in sorted(directory.glob('*.nut')) if p.stem != base]
        defaults = dict.fromkeys(FIELDS, 0)
        defaults.update(ConditionMax=1, ArmorDamageMult=1)
        for path in children:
            text = path.read_text('utf-8')
            assert f'inherit("scripts/items/{folder}/named/{base}"' in text
            assert 'function randomizeValues' not in text
            before = text.split('this.randomizeValues();')[0]
            assert before != text
            values = dict(defaults)
            for key, value in re.findall(r'this\.m\.(\w+)\s*=\s*([^;]+);', before):
                if key in FIELDS:
                    assert re.fullmatch(r'-?\d+(?:\.\d+)?', value), (path, key, value)
                    values[key] = float(value) if '.' in value else int(value)
            identifier = re.search(r'this\.m\.ID = "([^"]+)"', before).group(1)
            relative = path.relative_to(source).as_posix()
            hashes[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
            assert identifier not in items
            items[identifier] = {**naming_fields(identifier, relative, names, terms), 'kind': category,
                'ranged': 'ItemType.RangedWeapon' in before, 'base': values, 'source': relative}
    assert set(items) == set(names) and len(items) == 94
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({'schema': 1, 'game_version': '1.5.2.3',
        'provenance': 'Original local game scripts; BBMOD independently authored Chinese terminology.',
        'translation_sha256': translation_hash, 'naming_sha256': naming_hash,
        'source_sha256': hashes, 'items': items}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Built {len(items)} named equipment baselines: {output}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / 'build/full-l10n/decompiled')
    parser.add_argument('--output', type=Path, default=ROOT / 'data/item_inspector/catalog.json')
    parser.add_argument('--refresh-names', action='store_true',
                        help='Refresh names in the output catalog without changing verified numeric facts')
    args = parser.parse_args()
    if args.refresh_names:
        document = refresh_named_names(json.loads(args.output.read_text('utf-8')))
        args.output.write_text(json.dumps(document, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(f'Refreshed names for {len(document["items"])} equipment types: {args.output}')
    else:
        build(args.source, args.output)

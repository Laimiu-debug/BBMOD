"""Build verified numeric baselines from local original 1.5.2.3 scripts.

Only literals before randomizeValues are accepted; game code is never executed.
The generated artifact contains factual stats and BBMOD's independently authored names.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
FIELDS = ('ConditionMax StaminaModifier RegularDamage RegularDamageMax ArmorDamageMult DirectDamageMult '
          'DirectDamageAdd ChanceToHitHead ShieldDamage AmmoMax AdditionalAccuracy FatigueOnSkillUse '
          'MeleeDefense RangedDefense').split()
ENGLISH = {'warbow': 'War Bow', 'handgonne': 'Handgonne', 'exesword': "Executioner's Sword",
    'battle_whip': 'Battle Whip', 'warscythe': 'Warscythe', 'polemace': 'Polemace',
    'goblin_heavy_bow': 'Goblin Heavy Bow'}
ARMOR_ZH = ['黑金甲','黑皮甲','蓝色铆钉锁甲','棕色板片甲','金色鳞甲','绿色板片甲','纹章锁甲','豹皮甲',
    '林德蠕龙甲','青铜甲','金色札甲','贵族锁甲','覆甲毛皮甲','佣兵甲','骷髅锁甲']
HELMET_ZH = ['金羽盔','黑金缠头盔','纹章锁甲盔','林德蠕龙盔','面甲锥形盔','金属牛角盔','金属犀角盔',
    '金属骷髅盔','封闭锁甲北地盔','草原锁甲盔','羽饰护鼻盔','北欧盔','红金头带盔','绿色萨莱特盔','狼盔']
SHIELD_ZH = ['强盗熨斗形盾','强盗鸢形盾','小圆盾','龙纹盾','全金属熨斗形盾','金色圆盾','林德蠕龙盾',
    '兽人重盾','红白盾','骑士纹章盾','西帕尔圆盾','亡灵熨斗形盾','亡灵鸢形盾','翼纹盾']


def build(source, output):
    original = ROOT / 'localization/full_catalog.json'
    terms = {v['source']: v['translation'] for v in json.loads(original.read_text('utf-8'))['entries'].values()
             if v['status'] == 'reviewed'}
    items, hashes = {}, {}
    for folder, category, base, names in [('weapons', 'weapon', 'named_weapon', None),
            ('armor', 'armor', 'named_armor', ARMOR_ZH), ('helmets', 'helmet', 'named_helmet', HELMET_ZH),
            ('shields', 'shield', 'named_shield', SHIELD_ZH)]:
        directory = source / 'scripts/items' / folder / 'named'
        parent = directory / (base + '.nut')
        hashes[parent.relative_to(source).as_posix()] = hashlib.sha256(parent.read_bytes()).hexdigest()
        children = [p for p in sorted(directory.glob('*.nut')) if p.stem != base]
        if names is not None:
            assert len(children) == len(names), (folder, len(children))
        defaults = dict.fromkeys(FIELDS, 0)
        defaults.update(ConditionMax=1, ArmorDamageMult=1)
        for index, path in enumerate(children):
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
            stem = path.stem.removeprefix('named_')
            english = ENGLISH.get(stem, stem.replace('_', ' ').title().replace(' And ', ' and ').replace(' With ', ' with '))
            if category == 'weapon':
                # Prefer the game's visible name of the corresponding regular base.
                normal = source / 'scripts/items/weapons' / (stem + '.nut')
                if normal.exists():
                    match = re.search(r'this\.m\.Name = "([^"]+)"', normal.read_text('utf-8'))
                    if match:
                        english = match.group(1).replace("\\'", "'")
                chinese = terms.get(english)
                if not chinese:
                    import sys
                    sys.path.insert(0, str(ROOT))
                    from core.seedgen.weapons import NAMED_WEAPONS
                    chinese = NAMED_WEAPONS[identifier].removeprefix('红')
            else:
                chinese = terms.get(english, names[index])
            relative = path.relative_to(source).as_posix()
            hashes[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
            assert identifier not in items
            items[identifier] = {'en': 'Named ' + english, 'zh': '红' + chinese, 'kind': category,
                'ranged': 'ItemType.RangedWeapon' in before, 'base': values, 'source': relative}
    assert len(items) == 94
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({'schema': 1, 'game_version': '1.5.2.3',
        'provenance': 'Original local game scripts; BBMOD independently authored Chinese terminology.',
        'translation_sha256': hashlib.sha256(original.read_bytes()).hexdigest(),
        'source_sha256': hashes, 'items': items}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Built {len(items)} named equipment baselines: {output}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / 'build/full-l10n/decompiled')
    parser.add_argument('--output', type=Path, default=ROOT / 'data/item_inspector/catalog.json')
    args = parser.parse_args()
    build(args.source, args.output)

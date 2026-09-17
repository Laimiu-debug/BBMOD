"""Build selectable starting traits from official scripts and our reviewed text."""
from pathlib import Path
import argparse
import json
import re

ROOT = Path(__file__).resolve().parents[1]
STRING = r'"(?:\\.|[^"\\])*"'

def decode(value):
    return json.loads(value.replace("\\'", "'"))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT/'build/full-l10n/decompiled')
    args = parser.parse_args()
    catalog = json.loads((ROOT/'localization/full_catalog.json').read_text(encoding='utf-8'))
    translations = {entry['source']: entry['translation'] for entry in catalog['entries'].values()}
    source = (args.source/'scripts/config/character_traits.nut').read_text(encoding='utf-8-sig')
    pairs = re.findall(r'"(trait\.[a-z_]+)"\s*,\s*"(scripts/skills/traits/[a-z_]+)"', source)
    entries = []
    for trait_id, path in dict(pairs).items():
        text = (args.source/(path+'.nut')).read_text(encoding='utf-8-sig')
        def field(name):
            return decode(re.search(r'this\.m\.'+name+r'\s*=\s*('+STRING+r')', text)[1])
        assert field('ID') == trait_id
        english, description = field('Name'), field('Description')
        excluded = re.search(r'this\.m\.Excluded\s*=\s*\[(.*?)\];', text, re.S)
        entries.append({'id': trait_id, 'name': translations[english], 'english': english,
                        'description': translations[description],
                        'incompatible': re.findall(r'"(trait\.[a-z_]+)"', excluded[1]) if excluded else []})
    assert len(entries) > 40 and len(entries) == len({entry['id'] for entry in entries})
    output = ROOT/'data/seed_traits.json'
    output.write_text(json.dumps({'schema_version':1, 'source':'Official 1.5.2.3 CharacterTraits; BBMOD independent reviewed translations',
                                  'traits':entries},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'{len(entries)} starting traits -> {output}')

if __name__ == '__main__':
    main()

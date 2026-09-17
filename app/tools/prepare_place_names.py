"""Identify geographic names from the verified English sources, offline only.

The decompilation is used to classify literal positions, never to rebuild game
functions. Only the two independent name-pool assignments are compiled.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.cnut import Cnut
from tools.prepare_full_catalog import contexts, QUOTED, unescape

WORK = ROOT / 'build/full-l10n'
TARGET = ROOT / 'localization/place_names.json'
POOL_SCRIPT = ROOT / 'localization/place_name_pools.cnut'


def geographic_context(file: str, contexts_: list[str]) -> bool:
    if file == 'scripts/config/world_location_names.cnut':
        return any(c.startswith('@array:gt.Const.World.LocationNames.') for c in contexts_)
    if file == 'scripts/config/strings.cnut':
        return any(c.startswith('@array:gt.Const.Strings.TerrainRegionNames@') for c in contexts_)
    if file.startswith('scripts/entity/world/settlements/') and file.count('/') == 4:
        return any(c.startswith('@array:Names@') for c in contexts_)
    if file.startswith('scripts/entity/world/locations/'):
        return any(re.search(r'(?:this\.m\.Name\s*=|this\.world_entity\.setName\()\s*$', c)
                   for c in contexts_)
    return False


def name_pool(name: str) -> list[str]:
    code = (WORK / 'decompiled/scripts/config/character_names.nut').read_text(encoding='utf-8')
    match = re.search(r'gt\.Const\.Strings\.' + re.escape(name) + r'\s*<-\s*\[([\s\S]*?)\];', code)
    if not match:
        raise ValueError(f'Missing original name pool: {name}')
    # Retain order and repetitions: both affect seeded world generation.
    return [unescape(m.group(1)) for m in QUOTED.finditer(match.group(1))]


def main():
    catalog = json.loads((ROOT / 'localization/full_catalog.json').read_text(encoding='utf-8'))
    entries, sites = catalog['entries'], []
    keys = set()
    for file, spec in catalog['files'].items():
        if not file.startswith(('scripts/config/', 'scripts/entity/world/')):
            continue
        code = (WORK / 'decompiled' / file).with_suffix('.nut')
        if not code.is_file():
            continue
        ctx = contexts(code.read_text(encoding='utf-8'))
        for start, end, key in spec['patches']:
            source = entries[key]['source']
            if geographic_context(file, ctx.get(source, [])):
                sites.append({'file': file, 'start': start, 'end': end, 'key': key})
                keys.add(key)
    if not keys:
        raise ValueError('No geographic names found')
    pools = {name: name_pool(name) for name in ('CharacterNames', 'KnightNames')}
    # Independent data script. Original game functions are not recompiled.
    script = '// BBMOD: original English owners for geographic name templates only.\n'
    for name, values in pools.items():
        script += 'getroottable().Const.Strings.BBMODPlace' + name + ' <- ' + json.dumps(values, ensure_ascii=True) + ';\n'
    temporary = WORK / 'place-name-analysis/place_name_pools.nut'
    temporary.parent.mkdir(parents=True, exist_ok=True)
    temporary.write_text(script, encoding='ascii')
    subprocess.run([str(WORK / 'tools/bin/sq.exe'), '-o', str(POOL_SCRIPT), '-c', str(temporary)],
                   capture_output=True, check=True)
    subprocess.run([str(WORK / 'tools/bin/bbsq.exe'), '-e', str(POOL_SCRIPT)], capture_output=True, check=True)
    Cnut(POOL_SCRIPT.read_bytes(), encrypted=True)
    result = {
        'schema_version': 1,
        'policy': 'original_english',
        'scope': 'settlements, terrain regions, camps and named locations; map and dialogue share original names',
        'source': 'verified official English script literals; no third-party localization',
        'name_keys': sorted(keys),
        'sites': sites,
        'source_files': {file: catalog['files'][file]['sha256'] for file in sorted({s['file'] for s in sites})},
        'owner_pools': pools,
        'owner_script_sha256': hashlib.sha256(POOL_SCRIPT.read_bytes()).hexdigest(),
        'inline_mentions': json.loads((ROOT / 'localization/place_name_mentions.json').read_text(encoding='utf-8')),
    }
    TARGET.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'names': len(keys), 'sites': len(sites), 'files': len(result['source_files']),
                      'owner_pools': {k: len(v) for k, v in pools.items()}}, ensure_ascii=False))


if __name__ == '__main__':
    main()

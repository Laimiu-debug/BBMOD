"""Assemble shared character, map and camp filters for the independent host."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULES = ('define_common', 'define_role', 'define_score', 'define_lair',
           'function_brother_output_check', 'function_generate_brother',
           'function_role_score', 'function_print_info')
SEARCH_MODULES = ('config_weapon_rating', 'function_weapon_filter', 'function_named_attr',
                  'function_map_output_check', 'function_generate_settlement',
                  'function_lair_output_check', 'function_generate_lair')


def prepare(output: Path) -> dict:
    payload = ROOT/'seedgen/payload/seed_generator'
    parts = ['// Generated from the shared BBMOD character rules.\n::SeedGenerator <- {};']
    hashes = {}
    for name in MODULES:
        path = payload/(name+'.nut')
        source = path.read_text('utf-8')
        hashes[path.name] = hashlib.sha256(source.encode()).hexdigest()
        source = '\n'.join(line for line in source.splitlines()
                           if not line.strip().startswith('::include('))
        parts.append('{\n'+source+'\n}')
    main = (payload/'function_main_loop.nut').read_text('utf-8')
    hashes['function_main_loop.nut'] = hashlib.sha256(main.encode()).hexdigest()
    # Use the very same role allocation and condition evaluator as game searches.
    declarations = main[:main.index('gt.SeedGenerator.map_output_type')]
    sort = main[main.index('local broScoreSortByDescend'):main.index('local startNewCampaign')]
    start = main.index('\t\t\tlocal bros_len = bros.len();')
    end = main.index('\n\n\t\t\tif(DebugConfig.DebugMode)', start)
    evaluate = main[start:end]
    parts.append('dofile(::WORLD_MAP_SEED);\n{\n'+declarations+sort+'''
gt.SeedGenerator.evaluateBrothers <- function(bros, world_state) {
    local roster=null, origin=world_state.m.CampaignSettings.StartingScenario.getID();
'''+evaluate+'''
    team_score_avg_ = team_score_sum_ / bros_len;
    local match=gt.SeedGenerator.broOutputCheck(world_state,bros_sort_entries,bros_entries,team_score_avg_);
    return {entries=bros_entries,roles=role_array,score=team_score_avg_,match=match};
};
}
''')
    output.mkdir(parents=True, exist_ok=True)
    source = '\n'.join(parts)+'\n'
    (output/'brothers.nut').write_text(source, encoding='utf-8')
    # Templates travel with the component; runtime never reads a game install.
    for name in ('config_role_condition.nut', 'config_map_condition.nut', 'config_lair_condition.nut'):
        (output/name).write_bytes((payload/name).read_bytes())
    record = dict(schema=1, sources=hashes, sha256=hashlib.sha256(source.encode()).hexdigest())
    (output/'brothers-manifest.json').write_text(json.dumps(record, indent=2), encoding='utf-8')
    search_parts, search_hashes = [], {}
    for name in SEARCH_MODULES:
        path = payload/(name+'.nut')
        content = path.read_text('utf-8')
        search_hashes[path.name] = hashlib.sha256(content.encode()).hexdigest()
        content = '\n'.join(line for line in content.splitlines()
                            if not line.strip().startswith('::include('))
        search_parts.append('{\n'+content+'\n}')
    search_source = '\n'.join(search_parts)+'\n'
    (output/'search.nut').write_text(search_source, encoding='utf-8')
    (output/'search-manifest.json').write_text(json.dumps(dict(schema=1,
        sources=search_hashes, sha256=hashlib.sha256(search_source.encode()).hexdigest()), indent=2), encoding='utf-8')
    return record


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'build/offline-map/rules')
    print(json.dumps(prepare(parser.parse_args().output)))

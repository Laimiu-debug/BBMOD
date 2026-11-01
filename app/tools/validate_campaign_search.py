"""Compare parameterized independent searches with small original-game batches."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import copy
import gzip
import hashlib
import itertools
import json
import re
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.seedgen.config_emitter import BroCondition, CampaignConfig, CommonConfig, OriginConfig, SeedGenConfig
from core.seedgen.offline import OfflineSeedSearch, ORIGINS, fingerprint
from core.worldmap.model import Campaign, CAMP_PROFILE, CAMPAIGN_PROFILE


def search(config, seed):
    cfg = SeedGenConfig(common=CommonConfig.preset('all'), campaign=config,
        origins={config.origin: OriginConfig(conditions=[BroCondition('TeamScore', [-100])])},
        map_conditions=[['SettlementNum', 1]], lair_conditions=[['NamedNumber', 0]])
    job = OfflineSeedSearch(seeds=[seed], return_all=True)
    job.prepare(cfg)
    began = time.monotonic()
    try:
        job.launch()
        while not job.stop_reason:
            job.poll()
            if time.monotonic()-began > 95: raise TimeoutError((config, seed))
            time.sleep(.005)
    finally:
        job.stop_and_restore()
    if job.script_error or len(job.records) != 1 or len(job.results) != 1:
        raise RuntimeError(job.script_error or f'Incomplete search: {config}, {seed}')
    return job.records[0], time.monotonic()-began


def reference_cases(folder):
    report = json.loads((folder/'capture.json').read_text('utf-8'))
    if not all(report.get(k) for k in ('finished', 'restored', 'camps')):
        raise ValueError(f'Incomplete or unrestored original-game capture: {folder}')
    raw = (folder/'reference.jsonl').read_bytes()
    rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
    for environment in (row for row in rows if row['kind'] == 'environment'):
        index = environment.get('case', 0)
        config = CampaignConfig(environment['origin'], *(environment[k] for k in ('combat', 'economic', 'budget')))
        if environment['dlc'] != 342: raise ValueError('Original capture must include every official DLC')
        for seed in report['seeds']:
            selected = [row for row in rows if row.get('case', 0) == index and row.get('seed') == seed]
            camps = [{k:v for k,v in row.items() if k not in ('kind', 'seed', 'case', 'hidden')}
                     for row in selected if row['kind'] == 'camp']
            towns = [row['name'] for row in selected if row['kind'] == 'campaign-town']
            end = next(row for row in selected if row['kind'] == 'seed-end')
            if len(camps) != end['camps'] or sum(len(camp['items']) for camp in camps) != end['items']:
                raise ValueError('Original camp records are incomplete')
            player = next(row['xy'] for row in selected if row['kind'] == 'phase' and row['name'] == 'player')
            profile = CAMP_PROFILE if (config.origin,config.combat_difficulty,config.economic_difficulty,config.budget_difficulty) == ('scenario.militia',2,2,2) else CAMPAIGN_PROFILE
            expected = dict(profile=profile, seed=seed, origin=config.origin,
                combat=config.combat_difficulty, economic=config.economic_difficulty, budget=config.budget_difficulty,
                camps=camps, settlement_names=towns, player_xy=player)
            members = next(row['members'] for row in selected if row['kind'] == 'brothers')
            provenance = dict(capture_sha256=hashlib.sha256(raw).hexdigest(), restored=True,
                exe_sha256=report['exe_sha256'], probe_sha256=report['reference_probe_sha256'])
            yield config, expected, members, provenance


def name_key(name):
    # This exact original crypt template uses the non-campaign text RNG.
    found = re.fullmatch(r'Tomb of (.+) the (Great|Cruel|Tyrant)', name)
    return 'Tomb of '+found[1] if found else None


def comparison(actual, expected, allowed_names=()):
    checked, variants = copy.deepcopy(actual), []
    for index, (left, right) in enumerate(zip(checked['camps'], expected['camps'], strict=True)):
        key = name_key(left['name'])
        if left['name'] != right['name'] and key in allowed_names and name_key(right['name']) == key:
            variants.append(dict(camp=index, xy=left['xy'], offline=left['name'], original=right['name']))
            left['name'] = right['name']
    return checked == expected, variants


def name_variance_proof(folder):
    captures = list(reference_cases(folder))
    if len(captures) < 3: raise ValueError('At least three identical original-game campaigns are required')
    config, expected, members, provenance = captures[0]
    names = {}
    for other_config, other, other_members, _ in captures:
        if other_config != config or other['seed'] != expected['seed']:
            raise ValueError('Name-variance controls must use the same seed and campaign settings')
        for camp in other['camps']:
            key = name_key(camp['name'])
            if key: names.setdefault(key, set()).add(camp['name'])
        equal, _ = comparison(other, expected, tuple(names))
        if not equal: raise ValueError('The repeated game controls also differ in gameplay data')
        for original, repeated in zip(members, other_members, strict=True):
            if any(original[key] != repeated[key] for key in ('attr','talents','traits','growth')):
                raise ValueError('The repeated controls have different starting characters')
    variants = {key: sorted(value) for key,value in names.items() if len(value) > 1}
    if not variants: raise ValueError('The game controls did not demonstrate cosmetic name variance')
    return dict(capture=str(folder), repetitions=len(captures), seed=expected['seed'], origin=config.origin,
        gameplay_differences=0, variants=variants, provenance=provenance)


def validate(folder, allowed_names=(), workers=1):
    cases, fixture = [], []
    captured = list(reference_cases(folder))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        solved = list(pool.map(lambda case: search(case[0], case[1]['seed']), captured))
    for (config, expected, members, provenance), (record, seconds) in zip(captured, solved, strict=True):
        actual = Campaign.from_dict(record['campaign'], expected['seed'], 140, 170, len(expected['settlement_names'])).to_dict()
        equal, variants = comparison(actual, expected, allowed_names)
        if not equal:
            mismatches = [(i, a['xy'], b['xy']) for i,(a,b) in enumerate(zip(actual['camps'],expected['camps'])) if a != b]
            (folder/'mismatch.json').write_text(json.dumps(dict(expected=expected, actual=actual),ensure_ascii=False), 'utf-8')
            raise AssertionError((config, 'campaign mismatch', mismatches[:3]))
        for member, brother in zip(members, record['raw'], strict=True):
            assert member['attr'] == brother['Attr'], (config, 'attributes')
            assert member['talents'] == brother['Talents'], (config, 'talents')
            assert sorted(member['traits']) == sorted(brother['Traits']), (config, 'traits')
            assert [sum(values) for values in member['growth']] == brother['Level11TalentsAdd'], (config, 'growth')
        case = dict(origin=config.origin, combat=config.combat_difficulty, economic=config.economic_difficulty,
            budget=config.budget_difficulty, seed=expected['seed'], camps=len(expected['camps']),
            items=sum(len(c['items']) for c in expected['camps']), members=len(members), differences=0,
            cosmetic_name_variants=variants, seconds=seconds, provenance=provenance)
        cases.append(case)
        fixture.append(dict(campaign=expected, members=members, provenance=provenance))
        print(json.dumps(case, ensure_ascii=False), flush=True)
    return cases, fixture


def matrix():
    result = [CampaignConfig(origin, value, value, value) for origin in sorted(ORIGINS) for value in range(3)]
    result += [CampaignConfig('scenario.early_access', *values) for values in itertools.product(range(3), repeat=3)
               if len(set(values)) != 1]
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-game', action='store_true')
    parser.add_argument('--game', type=Path)
    parser.add_argument('--home', type=Path, default=ROOT/'build/offline-map/campaign-search')
    parser.add_argument('--capture', type=Path, action='append', default=[])
    parser.add_argument('--output', type=Path, default=ROOT/'build/offline-map/campaign-search-validation.json')
    parser.add_argument('--fixture', type=Path)
    parser.add_argument('--name-variance-capture', type=Path,
                        help='Repeated identical original-game campaigns proving cosmetic title variance')
    parser.add_argument('--workers', type=int, choices=range(1, 5), default=1,
                        help='Independent validation processes; timing is not a performance benchmark')
    args = parser.parse_args()
    initial = fingerprint()
    folders = args.capture
    if args.run_game:
        if not args.game: parser.error('--game is required with --run-game')
        from capture_worldmap_reference import capture
        from core.game import _inspect_game
        game = _inspect_game(args.game)
        if not game or not game.version_ok: parser.error('Original 1.5.2.3 required')
        configs = matrix()
        for start in range(0, len(configs), 6):
            folder = args.home/f'batch-{start//6:02d}'
            desired = [dict(origin=c.origin,combat=c.combat_difficulty,economic=c.economic_difficulty,
                            budget=c.budget_difficulty) for c in configs[start:start+6]]
            report = json.loads((folder/'capture.json').read_text('utf-8')) if (folder/'capture.json').is_file() else {}
            if not (report.get('restored') and report.get('finished') and report.get('campaigns') == desired):
                capture(game, folder, ['AbCdEfGhIj'], timeout=180, camps=True,
                        checkpoints=False, campaigns=configs[start:start+6], via_steam=True)
            folders.append(folder)
    proof = name_variance_proof(args.name_variance_capture) if args.name_variance_capture else None
    cases, fixture = [], []
    for folder in folders:
        verified, captured = validate(folder, tuple(proof['variants']) if proof else (), args.workers)
        cases.extend(verified); fixture.extend(captured)
    if fingerprint() != initial: raise RuntimeError('The solver changed during validation; run again')
    origins = {case['origin'] for case in cases}
    difficulties = {(case['combat'],case['economic'],case['budget']) for case in cases}
    success = origins == ORIGINS and len(difficulties) == 27 and not any(case['differences'] for case in cases)
    report = dict(schema=1, success=success, fingerprint=initial, origins=sorted(origins),
        difficulty_combinations=len(difficulties), cases=cases, captured=time.time(), name_variance_proof=proof,
        cosmetic_name_variants=sum(len(case['cosmetic_name_variants']) for case in cases))
    report['validation_workers'] = args.workers
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2), 'utf-8')
    if success and args.fixture:
        args.fixture.parent.mkdir(parents=True, exist_ok=True)
        args.fixture.write_bytes(gzip.compress(json.dumps(fixture,ensure_ascii=False,separators=(',',':')).encode(),mtime=0))
    print(json.dumps(dict(success=success, cases=len(cases), origins=len(origins), difficulties=len(difficulties))),flush=True)
    return 0 if success else 1


if __name__ == '__main__': raise SystemExit(main())

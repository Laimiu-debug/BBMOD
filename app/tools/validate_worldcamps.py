"""Compare offline campaign camps, loot, rolls and names to original-game captures."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.worldmap.engine import MapSolver
from core.worldmap.loot import item_appraisal, item_rating
from core.worldmap.model import CAMP_PROFILE


def references(folder):
    report = json.loads((folder/'capture.json').read_text('utf-8'))
    if not report.get('finished') or not report.get('restored') or not report.get('camps'):
        raise ValueError('需要已完成并恢复游戏目录的完整营地参照。')
    raw = (folder/'reference.jsonl').read_bytes()
    rows = [json.loads(line) for line in raw.splitlines()]
    environment = next(r for r in rows if r['kind'] == 'environment')
    if (environment['dlc'] != 342 or environment['origin'] != 'scenario.militia'
            or any(environment[k] != 2 for k in ('combat', 'economic', 'budget'))):
        raise ValueError('游戏参照配置不匹配。')
    provenance = dict(game_version=report['game_version'], exe_sha256=report['exe_sha256'],
        probe_sha256=report['reference_probe_sha256'], capture_sha256=hashlib.sha256(raw).hexdigest(), restored=True)
    for seed in report['seeds']:
        towns = [r for r in rows if r['kind'] == 'campaign-town' and r['seed'] == seed]
        camps = [{k: v for k, v in r.items() if k not in ('seed', 'kind', 'hidden', 'case')}
                 for r in rows if r['kind'] == 'camp' and r['seed'] == seed]
        end = next(r for r in rows if r['kind'] == 'seed-end' and r['seed'] == seed)
        phases = [r for r in rows if r['kind'] == 'phase' and r['seed'] == seed]
        if len(camps) != end['camps'] or sum(len(c['items']) for c in camps) != end['items']:
            raise ValueError('参照记录不完整。')
        player = next(r['xy'] for r in phases if r['name'] == 'player')
        campaign = dict(profile=CAMP_PROFILE, seed=seed, origin='scenario.militia', combat=2, economic=2, budget=2,
                        camps=camps, settlement_names=[t['name'] for t in towns], player_xy=player)
        yield campaign, sum(r.get('seconds', 0) for r in phases), provenance


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', type=Path, required=True)
    parser.add_argument('--repeats', type=int, default=3)
    parser.add_argument('--write-fixtures', action='store_true')
    parser.add_argument('--output', type=Path, default=ROOT/'build/offline-map/camp-validation.json')
    args = parser.parse_args()
    if not 1 <= args.repeats <= 10:
        parser.error('--repeats must be 1..10')
    solver, cases = MapSolver(), []
    for expected, native_seconds, provenance in references(args.capture):
        samples = []
        for _ in range(args.repeats):
            result = solver.solve(expected['seed'], use_cache=False, include_camps=True)
            actual = result.world.campaign.to_dict()
            if actual != expected:
                mismatch = [(i, a['xy'], b['xy']) for i, (a, b) in enumerate(zip(actual['camps'], expected['camps'])) if a != b]
                raise AssertionError((expected['seed'], 'campaign mismatch', mismatch[:5]))
            for camp in result.world.campaign.camps:
                for item in camp.items:
                    appraisal = item_appraisal(item)
                    if not appraisal.get('valid') or (item.kind == 'weapon' and item_rating(item) is None):
                        raise AssertionError((expected['seed'], item.identifier, 'appraisal/trace mismatch'))
            samples.append(result.elapsed)
        case = dict(seed=expected['seed'], camps=len(expected['camps']),
            named_items=sum(len(c['items']) for c in expected['camps']),
            differences=0, offline_wall_seconds=samples, median_seconds=statistics.median(samples),
            native_instrumented_seconds=native_seconds, provenance=provenance)
        cases.append(case)
        if args.write_fixtures:
            dest = ROOT/'tests/fixtures/worldmap'/('camp-'+hashlib.sha256(expected['seed'].encode()).hexdigest()[:16]+'.json.gz')
            dest.write_bytes(gzip.compress(json.dumps(dict(campaign=expected, provenance=provenance),
                ensure_ascii=False, separators=(',', ':')).encode('utf-8'), mtime=0))
        print(json.dumps(case, ensure_ascii=False), flush=True)
    report = dict(schema=1, profile=CAMP_PROFILE, fingerprint=solver.components.fingerprint(), success=True,
        timestamp=time.time(), cases=cases, offline_median_seconds=statistics.median(s for c in cases for s in c['offline_wall_seconds']))
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()

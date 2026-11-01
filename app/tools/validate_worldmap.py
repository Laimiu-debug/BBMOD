"""Compare complete independent maps against captured native-game evidence."""
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
from core.worldmap.model import PROFILE, WorldMap


def references(folder: Path):
    report = json.loads((folder/'capture.json').read_text('utf-8'))
    if not report.get('finished') or not report.get('restored') or report.get('checkpoints', True):
        raise ValueError('需要已完成、已恢复且关闭中间快照的原版采样。')
    raw = (folder/'reference.jsonl').read_bytes()
    phases, maps = {}, {}
    for line in raw.splitlines():
        row = json.loads(line)
        kind = row['kind']
        if kind == 'phase':
            phases[row['step']] = row
            if row['name'] == 'complete':
                maps[row['seed']] = dict(seed=row['seed'], width=row['width'], height=row['height'],
                                         rows=[], settlements=[], regions=[])
        elif kind == 'row' and phases[row['step']]['name'] == 'complete':
            maps[phases[row['step']]['seed']]['rows'].append(row['tiles'])
        elif kind in ('settlement', 'region'):
            maps[row['seed']]['settlements' if kind == 'settlement' else 'regions'].append(row)
        elif kind == 'seed-end':
            maps[row['seed']]['native_seconds'] = row['seconds_instrumented']
    provenance = dict(game_version=report['game_version'], exe_sha256=report['exe_sha256'],
                      probe_sha256=report['reference_probe_sha256'], capture_sha256=hashlib.sha256(raw).hexdigest(),
                      checkpoint_logging=False, restored=True)
    for seed, value in maps.items():
        yield WorldMap.from_dict(value), value['native_seconds'], provenance


def compare(expected: WorldMap, actual: WorldMap):
    fields = ('terrain', 'tactical_terrain', 'subregion', 'region', 'road_directions')
    differences = {name: sum(a[i] != b[i] for ra, rb in zip(expected.rows, actual.rows)
                             for a, b in zip(ra, rb)) for i, name in enumerate(fields)}
    differences['settlements'] = sum(a.to_dict() != b.to_dict() for a, b in
                                     zip(expected.settlements, actual.settlements)) + abs(len(expected.settlements)-len(actual.settlements))
    differences['regions'] = sum(a != b for a, b in zip(expected.regions, actual.regions)) + abs(len(expected.regions)-len(actual.regions))
    return differences


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', type=Path, action='append', required=True)
    parser.add_argument('--repeats', type=int, default=3)
    parser.add_argument('--write-fixtures', action='store_true')
    parser.add_argument('--output', type=Path, default=ROOT/'build/offline-map/validation.json')
    args = parser.parse_args()
    if not 1 <= args.repeats <= 10:
        parser.error('--repeats must be 1..10')
    solver = MapSolver()
    cases = []
    for folder in args.capture:
        for expected, native_seconds, provenance in references(folder):
            samples, compute = [], []
            differences = None
            for _ in range(args.repeats):
                result = solver.solve(expected.seed, use_cache=False)
                differences = compare(expected, result.world)
                if any(differences.values()):
                    raise AssertionError((expected.seed, differences))
                samples.append(result.elapsed)
                compute.append(result.generation_seconds)
            case = dict(seed=expected.seed, tiles=expected.width*expected.height,
                        settlements=len(expected.settlements), regions=len(expected.regions),
                        differences=differences, native_seconds=native_seconds,
                        offline_wall_seconds=samples, offline_compute_seconds=compute,
                        median_seconds=statistics.median(samples),
                        speedup=native_seconds/statistics.median(samples), provenance=provenance)
            cases.append(case)
            if args.write_fixtures:
                fixture = ROOT/'tests/fixtures/worldmap'/('map-'+hashlib.sha256(expected.seed.encode('ascii')).hexdigest()[:16]+'.json.gz')
                payload = dict(provenance=provenance, native_seconds=native_seconds, map=expected.to_dict())
                fixture.write_bytes(gzip.compress(json.dumps(payload, ensure_ascii=False,
                    separators=(',', ':')).encode('utf-8'), mtime=0))
            print(json.dumps(case, ensure_ascii=False), flush=True)
    report = dict(schema=1, profile=PROFILE, fingerprint=solver.components.fingerprint(),
                  success=True, timestamp=time.time(), cases=cases,
                  native_median_seconds=statistics.median(c['native_seconds'] for c in cases),
                  offline_median_seconds=statistics.median(s for c in cases for s in c['offline_wall_seconds']))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(args.output)


if __name__ == '__main__':
    main()

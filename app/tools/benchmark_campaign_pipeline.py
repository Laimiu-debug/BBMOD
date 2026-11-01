"""Compare fixed combined searches with the saved 0.9.0 pipeline, without a game."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.seedgen.config_emitter import (BroCondition, CampaignConfig, CommonConfig, OriginConfig,
                                        SeedGenConfig, brother_condition)
from core.seedgen.offline import OfflineSeedSearch, fingerprint
from core.worldmap.engine import Components


def run(implementation, components, cfg, seeds):
    search = implementation(components=components, seeds=seeds)
    search.prepare(cfg)
    started = time.perf_counter()
    try:
        search.launch()
        while not search.stop_reason:
            search.poll()
            if time.perf_counter()-started > 600:
                raise TimeoutError('Combined search benchmark')
            time.sleep(.002)
    finally:
        search.stop_and_restore()
    if search.script_error:
        raise RuntimeError(search.script_error)
    assert search.progress.loop_idx == len(seeds)
    archives = [asdict(result) for result in search.results]
    return dict(seconds=time.perf_counter()-started, seeds=len(seeds), hits=len(archives),
                campaign_candidates=getattr(search, 'campaign_candidates', search.progress.loop_idx),
                prefilter_rejected=getattr(search, 'prefilter_rejected', 0)), archives


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--repeats', type=int, choices=range(1, 5), default=2)
    parser.add_argument('--steady-count', type=int, default=1024)
    args = parser.parse_args()
    module_spec = importlib.util.spec_from_file_location('core.seedgen.offline_v090', args.baseline/'offline.py')
    baseline = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(baseline)
    components = Components.locate()
    previous = Components(components.binary, args.baseline/'native/runtime.nut', components.rules)
    refs = [r for line in gzip.decompress((ROOT/'tests/fixtures/worldmap/brothers.json.gz').read_bytes()).splitlines()
            if (r := json.loads(line)).get('kind') == 'brothers' and r['origin'] == 'scenario.militia']
    seeds = list(dict.fromkeys(ref['seed'] for ref in refs))
    assert len(seeds) >= 4
    trait = next(t for member in refs[0]['members'] for t in member['traits']
                 if not any(t in other['traits'] for other in refs[1]['members']))
    cases = [('strict', brother_condition(1, {}, required=['trait.iron_lungs', 'trait.sure_footing'],
                                          total_min=9, star_ranges={'MeleeSkill': (3,3)}), (seeds*2)[:8]),
             ('mixed', brother_condition(1, {}, required=[trait]), seeds[:4]),
             ('loose', BroCondition('TeamScore', [-100]), seeds[:2])]
    report = dict(schema=1, baseline_version='0.9.0', fingerprint=fingerprint(),
                  game_started=False, repeats=args.repeats, measurement='sequential alternating runs; same fixed seeds and settings',
                  cases=[])
    evidence = []
    for name, condition, values in cases:
        cfg = SeedGenConfig(common=CommonConfig.preset('all'), campaign=CampaignConfig('scenario.militia',2,2,2),
                            map_conditions=[['SettlementNum',1]], lair_conditions=[['NamedNumber',0]])
        cfg.origins = {cfg.campaign.origin: OriginConfig(conditions=[condition])}
        rounds = []
        for repeat in range(args.repeats):
            outputs = {}
            for label in (('before','after') if repeat % 2 == 0 else ('after','before')):
                implementation, component = (baseline.OfflineSeedSearch, previous) if label == 'before' else (OfflineSeedSearch, components)
                stats, archives = run(implementation, component, cfg, values)
                outputs[label] = stats, archives
                print(json.dumps(dict(case=name, repeat=repeat, implementation=label, **stats)), flush=True)
            before, after = outputs['before'], outputs['after']
            evidence.append(dict(case=name, repeat=repeat, before=before[1], after=after[1]))
            assert before[1] == after[1], 'Matching archives changed: '+name
            rounds.append(dict(before=before[0], after=after[0], archive_equivalence=True))
        before = statistics.median(r['before']['seconds'] for r in rounds)
        after = statistics.median(r['after']['seconds'] for r in rounds)
        report['cases'].append(dict(name=name, config=asdict(cfg), seeds=values, rounds=rounds,
            before_seconds=before, after_seconds=after, before_seeds_per_second=len(values)/before,
            after_seeds_per_second=len(values)/after, speedup=before/after, archive_equivalence=True))
    strict = SeedGenConfig(common=CommonConfig.preset('all'), campaign=CampaignConfig('scenario.militia',2,2,2),
                           map_conditions=[['SettlementNum',1]], lair_conditions=[['NamedNumber',0]])
    strict.origins = {strict.campaign.origin: OriginConfig(conditions=[cases[0][1]])}
    steady, _ = run(OfflineSeedSearch, components, strict, (seeds*(args.steady_count//len(seeds)+1))[:args.steady_count])
    steady['seeds_per_second'] = steady['seeds']/steady['seconds']
    report['steady_strict'] = steady
    report['success'] = True
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    args.output.with_suffix('.archives.json.gz').write_bytes(gzip.compress(
        json.dumps(evidence, ensure_ascii=False).encode(), mtime=0))
    print(json.dumps(dict(success=True, cases=[{k:c[k] for k in ('name','before_seeds_per_second','after_seeds_per_second','speedup')} for c in report['cases']],
                         steady_strict=steady)), flush=True)


if __name__ == '__main__':
    main()

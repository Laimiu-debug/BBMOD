"""Compare complete character results before and after host/output optimizations."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import gzip
import hashlib
import json
from pathlib import Path
import random
import sys
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.seedgen.config_emitter import (CampaignConfig, CommonConfig, OriginConfig,
    SeedGenConfig, brother_condition, score_condition)
from core.seedgen.offline import OfflineSeedSearch, FAST_ORIGINS, fingerprint


def cases():
    rng = random.Random(20261022)
    seeds = ['46U2HMOORH', 'AbCdEfGhIj', 'ABCDEFGHIJ', 'aaaaaaaaaa',
             'ZZZZZZZZZZ', '0123456789', 'bB7Aa12QxP']
    seeds += [''.join(rng.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz', k=10))
              for _ in range(32)]
    for origin in sorted(FAST_ORIGINS):
        for real in (True, False):
            cfg = SeedGenConfig(common=CommonConfig.preset('bro_only'),
                campaign=CampaignConfig(origin=origin, combat_difficulty=2,
                    economic_difficulty=2, budget_difficulty=2),
                origins={origin: OriginConfig(conditions=[
                    brother_condition(1, {}, required=['trait.iron_lungs', 'trait.sure_footing'],
                        match='any', total_min=7, star_ranges={'MeleeSkill': (2, 3)}),
                    brother_condition(1, {'MeleeSkill': 90}, excluded=['trait.fat'],
                        total_min=6, star_ranges={'RangedDefense': (0, 0)}),
                    score_condition('TeamScore', .65, 1, 'RoleMelee')])})
            cfg.common.UseBrotherLevel11RealAttr = real
            yield f'{origin}/{"real" if real else "average"}/fixed', cfg, seeds, 0, True
            # Also compare the entire sequential random-seed stream. GC and
            # serialization must never consume a game RNG draw.
            cfg.common.EnableLowercaseSeed = not real
            cfg.origins[origin].conditions = [score_condition('TeamScore', -100, 1, 'RoleMelee')]
            yield f'{origin}/{"real" if real else "average"}/stream', cfg, [], 100, False


def capture():
    records = []
    for name, cfg, seeds, count, raw in cases():
        search = OfflineSeedSearch(seeds=seeds, count=count, return_all=raw)
        with patch('core.seedgen.offline.secrets.choice', return_value='A'):
            search.prepare(cfg)
        started = time.monotonic()
        try:
            search.launch()
            while not search.stop_reason:
                added, _ = search.poll()
                if time.monotonic()-started > 30:
                    raise TimeoutError(name)
                if not added:
                    time.sleep(.001)
        finally:
            search.stop_and_restore()
        if search.script_error:
            raise RuntimeError(search.script_error)
        records.append(dict(case=name, records=search.records,
            results=[asdict(result) for result in search.results],
            loops=search.progress.loop_idx, hits=search.progress.hits,
            best=search.progress.best_team_score))
    return dict(schema=1, fingerprint=fingerprint(), cases=records)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', type=Path, required=True)
    parser.add_argument('--compare', type=Path)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    actual = capture()
    data = json.dumps(actual, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    args.snapshot.parent.mkdir(parents=True, exist_ok=True)
    args.snapshot.write_bytes(gzip.compress(data, mtime=0))
    if args.compare:
        expected = json.loads(gzip.decompress(args.compare.read_bytes()))
        differences = [old['case'] for old, new in zip(expected['cases'], actual['cases'], strict=True)
                       if old != new]
        report = dict(schema=1, success=not differences, cases=len(actual['cases']),
            seeds=sum(case['loops'] for case in actual['cases']),
            fixed_raw_records=sum(len(case['records']) for case in actual['cases']),
            matched_results=sum(len(case['results']) for case in actual['cases']),
            differences=differences, before_fingerprint=expected['fingerprint'],
            after_fingerprint=actual['fingerprint'],
            before_sha256=hashlib.sha256(args.compare.read_bytes()).hexdigest(),
            after_sha256=hashlib.sha256(args.snapshot.read_bytes()).hexdigest())
        if args.report:
            args.report.write_text(json.dumps(report, indent=2), encoding='utf-8')
        print(json.dumps(report), flush=True)
        return int(bool(differences))
    print(json.dumps(dict(snapshot=str(args.snapshot), cases=len(actual['cases']),
        seeds=sum(case['loops'] for case in actual['cases']))), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

"""Time independent character searches without stdout/result or disk bottlenecks."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.seedgen.config_emitter import CampaignConfig, CommonConfig, OriginConfig, SeedGenConfig, brother_condition
from core.seedgen.offline import OfflineSeedSearch, FAST_ORIGINS, fingerprint


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--count', type=int, default=1000)
    parser.add_argument('--output', type=Path, default=ROOT/'build/offline-map/brother-benchmark.json')
    args = parser.parse_args()
    if not 100 <= args.count <= 100000:
        parser.error('--count must be 100..100000')
    cases = []
    for origin in sorted(FAST_ORIGINS):
        cfg = SeedGenConfig(common=CommonConfig.preset('bro_only'), campaign=CampaignConfig(origin=origin),
            origins={origin: OriginConfig(conditions=[brother_condition(1, {}, total_min=9,
                required=['trait.iron_lungs', 'trait.sure_footing'], star_ranges={'MeleeSkill': (3, 3)})])})
        search = OfflineSeedSearch(count=args.count)
        search.prepare(cfg)
        started = time.perf_counter()
        ready, measured = None, None
        try:
            search.launch()
            while not search.stop_reason:
                search.poll()
                now = time.perf_counter()
                if search.startup.stage == 'generating' and ready is None:
                    ready = now-started
                if now-started > 180:
                    raise TimeoutError(origin)
                time.sleep(.002)
            measured = time.perf_counter()-started
        finally:
            search.stop_and_restore()
        if search.script_error:
            raise RuntimeError(search.script_error)
        case = dict(origin=origin, seeds=search.progress.loop_idx, wall_seconds=measured,
                    startup_seconds=ready, seeds_per_second=search.progress.loop_idx/measured,
                    hits=len(search.results), real_level11=True)
        cases.append(case)
        print(json.dumps(case), flush=True)
    args.output.write_text(json.dumps(dict(schema=1, fingerprint=fingerprint(), cases=cases), indent=2), encoding='utf-8')

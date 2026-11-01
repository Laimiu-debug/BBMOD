"""Prove the character prefilter agrees with original campaign rosters."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.seedgen.config_emitter import (SeedGenConfig, CommonConfig, CampaignConfig,
                                        OriginConfig, BroCondition)
from core.seedgen.offline import OfflineSeedSearch, FAST_ORIGINS, fingerprint


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture', type=Path, default=ROOT/'tests/fixtures/seed_campaigns.json.gz')
    parser.add_argument('--output', type=Path, default=ROOT/'build/offline-map/prefilter-validation.json')
    args = parser.parse_args()
    initial = fingerprint()
    references = json.loads(gzip.decompress(args.fixture.read_bytes()))
    cases, differences = [], []
    for ref in references:
        campaign = ref['campaign']
        origin = campaign['origin']
        if origin not in FAST_ORIGINS:
            continue
        assert ref['provenance']['restored']
        levels = [campaign[k] for k in ('combat','economic','budget')]
        cfg = SeedGenConfig(common=CommonConfig.preset('bro_only'),
            campaign=CampaignConfig(origin, *levels),
            origins={origin: OriginConfig(conditions=[BroCondition('TeamScore',[-100])])})
        search = OfflineSeedSearch(seeds=[campaign['seed']], return_all=True)
        search.prepare(cfg)
        started = time.monotonic()
        try:
            search.launch()
            while not search.stop_reason:
                search.poll()
                if time.monotonic()-started > 15:
                    raise TimeoutError(origin)
                time.sleep(.002)
        finally:
            search.stop_and_restore()
        if search.script_error:
            raise RuntimeError(search.script_error)
        before = len(differences)
        for index, (actual, original) in enumerate(zip(search.records[0]['raw'], ref['members'], strict=True)):
            checks = dict(attributes=(actual['Attr'], original['attr']), talents=(actual['Talents'], original['talents']),
                traits=(sorted(actual['Traits']), sorted(original['traits'])),
                growth=(actual['Level11TalentsAdd'], [sum(v) for v in original['growth']]))
            for field, (value, expected) in checks.items():
                if value != expected:
                    differences.append(dict(origin=origin, levels=levels, seed=campaign['seed'],
                                            member=index, field=field, actual=value, expected=expected))
        cases.append(dict(origin=origin, levels=levels, seed=campaign['seed'],
                          members=len(ref['members']), differences=len(differences)-before))
    assert fingerprint() == initial
    origins = {case['origin'] for case in cases}
    levels = {tuple(case['levels']) for case in cases}
    success = origins == FAST_ORIGINS and len(levels) == 27 and not differences
    report = dict(schema=1, success=success, fingerprint=initial,
                  fixture_sha256=hashlib.sha256(args.fixture.read_bytes()).hexdigest(),
                  origins=sorted(origins), difficulty_combinations=len(levels), cases=cases, differences=differences)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(dict(success=success, cases=len(cases), origins=len(origins),
                         difficulties=len(levels), differences=len(differences))))
    return 0 if success else 1


if __name__ == '__main__':
    raise SystemExit(main())

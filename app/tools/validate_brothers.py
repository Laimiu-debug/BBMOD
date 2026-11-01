"""Compare independent rosters to captured original actors, including real growth."""
from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.seedgen.config_emitter import BroCondition, CampaignConfig, CommonConfig, OriginConfig, SeedGenConfig
from core.seedgen.offline import OfflineSeedSearch, FAST_ORIGINS, fingerprint


def validate(references):
    refs = [json.loads(line) for reference in references for line in reference.read_text('utf-8').splitlines()
            if json.loads(line)['kind'] == 'brothers']
    differences, cases = [], []
    if {ref['origin'] for ref in refs} != FAST_ORIGINS:
        raise ValueError('人物快速对照必须覆盖全部快速起源；逃兵由完整开局对照覆盖。')
    for origin in sorted({ref['origin'] for ref in refs}):
        cfg = SeedGenConfig(common=CommonConfig.preset('bro_only'), campaign=CampaignConfig(origin=origin))
        cfg.origins = {origin: OriginConfig(conditions=[BroCondition('TeamScore', [-100])])}
        expected = [ref for ref in refs if ref['origin'] == origin]
        search = OfflineSeedSearch(seeds=[ref['seed'] for ref in expected], return_all=True)
        search.prepare(cfg)
        started = time.perf_counter()
        try:
            search.launch()
            while not search.stop_reason:
                search.poll()
                if time.perf_counter()-started > 60:
                    raise TimeoutError(origin)
                time.sleep(.002)
        finally:
            search.stop_and_restore()
        if search.script_error:
            raise RuntimeError(search.script_error)
        for ref, actual in zip(expected, search.records, strict=True):
            previous = len(differences)
            for index, (member, raw) in enumerate(zip(ref['members'], actual['raw'], strict=True)):
                checks = dict(attr=(member['attr'], raw['Attr']), talents=(member['talents'], raw['Talents']),
                    traits=(sorted(member['traits']), sorted(raw['Traits'])),
                    growth=([sum(values) for values in member['growth']], raw['Level11TalentsAdd']))
                for field, (before, after) in checks.items():
                    if before != after:
                        differences.append(dict(origin=origin, seed=ref['seed'], member=index,
                                                field=field, expected=before, actual=after))
            cases.append(dict(origin=origin, seed=ref['seed'], members=len(ref['members']),
                              differences=len(differences)-previous))
        print(origin+': '+str(sum(case['differences'] for case in cases if case['origin'] == origin)), flush=True)
    captures = [json.loads(reference.with_name('capture.json').read_text('utf-8')) for reference in references]
    if any(not capture.get('restored') or not capture.get('finished') for capture in captures):
        raise ValueError('原版采集未完成或游戏文件恢复校验未通过。')
    return dict(schema=1, success=bool(cases) and not differences,
        profile='bb-1.5.2.3-all-dlc-v1', fingerprint=fingerprint(),
        sources=[str(reference) for reference in references], captures=captures, cases=cases, differences=differences)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', type=Path, required=True, action='append')
    parser.add_argument('--output', type=Path, default=ROOT/'build/offline-map/brother-validation.json')
    parser.add_argument('--fixture', type=Path)
    args = parser.parse_args()
    result = validate(args.reference)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    if args.fixture and result['success']:
        args.fixture.parent.mkdir(parents=True, exist_ok=True)
        args.fixture.write_bytes(gzip.compress(b'\n'.join(reference.read_bytes().strip()
            for reference in args.reference)+b'\n', mtime=0))
    print(json.dumps(dict(success=result['success'], cases=len(result['cases']),
                         members=sum(case['members'] for case in result['cases']), differences=len(result['differences']))))
    sys.exit(0 if result['success'] else 1)

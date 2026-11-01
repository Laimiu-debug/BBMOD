"""Compare a Linux native host to captured original-game fixtures, without a game."""
import argparse
import gzip
import json
from pathlib import Path
import statistics
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from app.core.worldmap.engine import Components,MapSolver
from app.core.worldmap.model import WorldMap
from app.core.worldmap.atlas import atlas_data


def difference(actual,expected,path='root'):
    if type(actual) is not type(expected):return f'{path}: types {type(actual).__name__}/{type(expected).__name__}'
    if isinstance(actual,dict):
        if actual.keys()!=expected.keys():return f'{path}: keys differ'
        for key in actual:
            found=difference(actual[key],expected[key],f'{path}.{key}')
            if found:return found
    elif isinstance(actual,(list,tuple)):
        if len(actual)!=len(expected):return f'{path}: length {len(actual)}/{len(expected)}'
        for i,(a,b) in enumerate(zip(actual,expected)):
            found=difference(a,b,f'{path}[{i}]')
            if found:return found
    elif actual!=expected:return f'{path}: {actual!r} != {expected!r}'
    return None


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home',type=Path,default=Path('/srv/worldmap'))
    parser.add_argument('--report',type=Path,default=Path('/tmp/atlas-validation.json'))
    args=parser.parse_args(); fixtures=ROOT/'app/tests/fixtures/worldmap';results=[]
    components=Components(args.home/'worldmap',args.home/'runtime.nut',args.home/'rules')
    with tempfile.TemporaryDirectory(prefix='atlas-validation-') as temporary:
        solver=MapSolver(components,Path(temporary))
        for path in sorted(fixtures.glob('*.json.gz')):
            case=json.loads(gzip.decompress(path.read_bytes()));campaign=case.get('campaign');seed=campaign['seed'] if campaign else case['map']['seed']
            result=solver.solve(seed,include_camps=bool(campaign),use_cache=False,timeout=75)
            actual=result.world.campaign.to_dict() if campaign else result.world.to_dict()
            expected=campaign if campaign else WorldMap.from_dict(case['map']).to_dict()
            diff=difference(actual,expected)
            if diff:raise RuntimeError(f'{seed}: {diff}')
            if campaign:
                data=atlas_data(result.world)
                if any(t['name']=='未收录地名' for t in data['towns']) or any(c['name']=='未收录地名' for c in data['camps']):
                    raise RuntimeError('Compiled translations are incomplete')
            record=dict(seed=seed,campaign=bool(campaign),seconds=result.elapsed,success=True)
            results.append(record);print(json.dumps(record),flush=True)
        solver.solve('46U2HMOORH',include_camps=True)
        cached=solver.solve('46U2HMOORH',include_camps=True)
        report=dict(success=True,platform=sys.platform,fingerprint=components.fingerprint(),references=results,
            campaign_median_seconds=statistics.median(r['seconds'] for r in results if r['campaign']),cached_seconds=cached.elapsed)
        args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps(report,indent=2),'utf-8')
        print(json.dumps({k:v for k,v in report.items() if k!='references'}),flush=True)


if __name__=='__main__':main()

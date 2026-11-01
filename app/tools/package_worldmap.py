"""Prepare a validated independent component and prove detached execution."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.worldmap.engine import Components, MapSolver
from core.seedgen.offline import fingerprint as brother_fingerprint


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--detached-check', action='store_true')
    args = parser.parse_args()
    components = Components.locate()
    build = ROOT/'build/offline-map'
    validation = json.loads((build/'validation.json').read_text('utf-8'))
    camp_validation = json.loads((build/'camp-validation.json').read_text('utf-8'))
    brother_validation = json.loads((build/'brother-validation.json').read_text('utf-8'))
    search_validation = json.loads((build/'campaign-search-validation.json').read_text('utf-8'))
    prefilter_validation = json.loads((build/'prefilter-validation.json').read_text('utf-8'))
    if (not validation.get('success') or not camp_validation.get('success')
            or validation['fingerprint'] != components.fingerprint()
            or camp_validation['fingerprint'] != components.fingerprint()):
        parser.error('组件尚未通过当前版本的原版地图对照。')
    if not brother_validation.get('success') or brother_validation['fingerprint'] != brother_fingerprint(components):
        parser.error('组件尚未通过当前版本的原版人物对照。')
    if (not search_validation.get('success') or search_validation['fingerprint'] != brother_fingerprint(components)
            or len(search_validation.get('origins', [])) != 14 or search_validation.get('difficulty_combinations') != 27):
        parser.error('组件尚未通过当前版本的全部官方起源与难度组合搜索对照。')
    if (not prefilter_validation.get('success') or prefilter_validation['fingerprint'] != brother_fingerprint(components)
            or len(prefilter_validation.get('origins', [])) != 13 or prefilter_validation.get('difficulty_combinations') != 27):
        parser.error('组件尚未通过当前版本的人物预筛与原版完整开局对照。')
    package = build/'package'
    package.mkdir(exist_ok=True)
    for source, dest in [(components.binary, package/'worldmap.exe'),
                         (components.bootstrap, package/'runtime.nut'),
                         (components.bootstrap.with_name('camps.nut'), package/'camps.nut'),
                         (components.bootstrap.with_name('brothers.nut'), package/'brothers.nut'),
                         (components.bootstrap.with_name('actors.nut'), package/'actors.nut'),
                         (components.bootstrap.with_name('search.nut'), package/'search.nut'),
                         (build/'vendor/COPYRIGHT', package/'SQUIRREL-COPYRIGHT')]:
        shutil.copyfile(source, dest)
    shutil.copytree(components.rules, package/'rules', dirs_exist_ok=True)
    shutil.copyfile(build/'validation.json', package/'validation.json')
    shutil.copyfile(build/'camp-validation.json', package/'camp-validation.json')
    shutil.copyfile(build/'brother-validation.json', package/'brother-validation.json')
    shutil.copyfile(build/'campaign-search-validation.json', package/'campaign-search-validation.json')
    shutil.copyfile(build/'prefilter-validation.json', package/'prefilter-validation.json')
    files = {p.relative_to(package).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in package.rglob('*') if p.is_file() and p.name != 'pack.json'}
    packed = Components(package/'worldmap.exe', package/'runtime.nut', package/'rules')
    report = dict(schema=1, profile=validation['profile'], fingerprint=packed.fingerprint(), files=files,
                  validated_seeds=[c['seed'] for c in validation['cases']],
                  camp_profile=camp_validation['profile'], validated_camp_seeds=[c['seed'] for c in camp_validation['cases']], detached=None)
    report['brother_fingerprint'] = brother_fingerprint(packed)
    report['validated_brother_cases'] = len(brother_validation['cases'])
    report['validated_campaign_cases'] = len(search_validation['cases'])
    report['campaign_origins'] = search_validation['origins']
    report['difficulty_combinations'] = search_validation['difficulty_combinations']
    report['validated_prefilter_cases'] = len(prefilter_validation['cases'])
    if report['fingerprint'] != validation['fingerprint']:
        raise ValueError('打包后组件校验不一致。')
    if args.detached_check:
        temporary_root = Path('H:/codex/tmp').resolve()
        temporary_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='bbmod-worldmap-', dir=temporary_root) as directory:
            detached = Path(directory).resolve()
            if not detached.is_relative_to(temporary_root): raise ValueError('临时目录越界。')
            shutil.copytree(package, detached/'component')
            component = detached/'component'
            solver = MapSolver(Components(component/'worldmap.exe', component/'runtime.nut', component/'rules'), cache=detached/'cache')
            result = solver.solve('46U2HMOORH', include_camps=True)
            replay = solver.solve('46U2HMOORH', include_camps=True)
            expected = MapSolver().solve('46U2HMOORH', use_cache=False, include_camps=True)
            assert result.world.to_dict() == expected.world.to_dict() and replay.cached
            from core.seedgen.offline import OfflineSeedSearch
            from core.seedgen.config_emitter import BroCondition, CampaignConfig, CommonConfig, OriginConfig, SeedGenConfig
            cfg = SeedGenConfig(common=CommonConfig.preset('bro_only'),
                campaign=CampaignConfig(origin='scenario.militia'),
                origins={'scenario.militia': OriginConfig(conditions=[BroCondition('TeamScore', [-100])])})
            characters = OfflineSeedSearch(components=solver.components, seeds=['AbCdEfGhIj'])
            characters.prepare(cfg)
            started = time.monotonic()
            try:
                characters.launch()
                while not characters.stop_reason and time.monotonic()-started < 15:
                    characters.poll()
                    time.sleep(.005)
            finally:
                characters.stop_and_restore()
            assert not characters.script_error and len(characters.results) == 1
            assert len(characters.results[0].brothers) == 12
            combined_config = SeedGenConfig(common=CommonConfig.preset('all'),
                campaign=CampaignConfig('scenario.deserters', 0, 1, 2),
                origins={'scenario.deserters': OriginConfig(conditions=[BroCondition('TeamScore', [-100])])},
                map_conditions=[['SettlementNum', 1]], lair_conditions=[['NamedNumber', 0]])
            combined = OfflineSeedSearch(components=solver.components, seeds=['46U2HMOORH'])
            combined.prepare(combined_config)
            started = time.monotonic()
            try:
                combined.launch()
                while not combined.stop_reason and time.monotonic()-started < 20:
                    combined.poll(); time.sleep(.005)
            finally:
                combined.stop_and_restore()
            assert not combined.script_error and len(combined.results) == 1
            assert len(combined.results[0].brothers) == 3 and combined.results[0].named_items
            assert combined.results[0].combat_difficulty == 0 and combined.results[0].economic_difficulty == 1
            prefilter_cfg = SeedGenConfig(common=CommonConfig.preset('all'),
                campaign=CampaignConfig(origin='scenario.militia'),
                origins={'scenario.militia': OriginConfig(conditions=[BroCondition('TeamScore', [100])])})
            prefiltered = OfflineSeedSearch(components=solver.components, seeds=['46U2HMOORH', 'ABCDEFGHIJ'])
            prefiltered.prepare(prefilter_cfg)
            started = time.monotonic()
            try:
                prefiltered.launch()
                while not prefiltered.stop_reason and time.monotonic()-started < 15:
                    prefiltered.poll(); time.sleep(.005)
            finally:
                prefiltered.stop_and_restore()
            assert not prefiltered.script_error and prefiltered.prefilter_rejected == 2
            assert prefiltered.progress.loop_idx == 2 and prefiltered.campaign_candidates == 0
            import pefile
            binary = pefile.PE(str(component/'worldmap.exe'))
            try:
                imports = [entry.dll.decode('ascii') for entry in binary.DIRECTORY_ENTRY_IMPORT]
            finally:
                binary.close()  # Release the Windows mapping before deleting QA files.
            assert {name.lower() for name in imports} <= {'kernel32.dll', 'msvcrt.dll'}
            report['detached'] = dict(success=True, binary_imports=imports,
                original_game_directory_used=False, wall_seconds=result.elapsed, cached_seconds=replay.elapsed,
                camps=len(result.world.campaign.camps), named_items=sum(len(c.items) for c in result.world.campaign.camps),
                starting_brothers=len(characters.results[0].brothers),
                combined_search=True, combined_origin=combined.results[0].origin,
                prefilter_search=True, prefilter_rejected=prefiltered.prefilter_rejected,
                temporary_directory_removed_on_exit=True)
    (package/'pack.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    (build/'detached-check.json').write_text(json.dumps(report['detached'], indent=2), encoding='utf-8')
    print(json.dumps(dict(package=str(package), files=len(files), detached=report['detached']), ensure_ascii=False))


if __name__ == '__main__': main()

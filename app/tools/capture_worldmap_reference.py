"""Opt-in original-game oracle for the standalone world-map implementation.

Only this development tool imports game/session modules. The offline solver must
not. Captures the unmodified native generation stages, restores all temporary
files, and records provenance. No campaign is saved.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import time
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core import game as game_mod
from core.gamelog import IncrementalLogReader
from core.paths import resource_path
from core.seedgen.config_emitter import CampaignConfig, emit_campaign
from core.seedgen.session import FileSession


def signature(data: Path) -> dict[str, str]:
    return {p.relative_to(data).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in data.rglob('*') if p.is_file() and p.suffix.lower() != '.dat'}


def capture(game, output: Path, seeds: list[str], timeout: float = 240, *, api_only=False, checkpoints=True, with_api=False,
            camps=False, trace_rng=False, brothers=False, campaigns=None, via_steam=False) -> dict:
    if game_mod.probe_game_running():
        raise RuntimeError('请先关闭正在运行的游戏；不会中断现有游戏。')
    session = FileSession(game.root)
    if session.active:
        raise RuntimeError('存在未恢复的种子会话，请先通过 BBMOD 恢复。')
    output.mkdir(parents=True, exist_ok=True)
    session_id = uuid.uuid4().hex
    source = Path(__file__).with_name('brother_reference.nut' if brothers else
        'worldcamp_reference.nut' if camps else 'worldmap_reference.nut').read_text('utf-8')
    source = source.replace('__SEEDS__', json.dumps(seeds))
    source = source.replace('__API_ONLY__', 'true' if api_only else 'false')
    source = source.replace('__CHECKPOINTS__', 'true' if checkpoints else 'false')
    source = source.replace('__WITH_API__', 'true' if with_api else 'false')
    source = source.replace('__TRACE_RNG__', 'true' if trace_rng else 'false')
    campaigns = campaigns or [CampaignConfig(origin='scenario.militia', combat_difficulty=2,
        economic_difficulty=2, budget_difficulty=2)]
    for campaign in campaigns: campaign.validate()
    source = source.replace('__CAMPAIGNS__', '['+','.join('{origin='+json.dumps(c.origin)+
        f',combat={c.combat_difficulty},economic={c.economic_difficulty},budget={c.budget_difficulty}'+'}'
        for c in campaigns)+']')
    payload = {
        'mod_hooks.zip': resource_path('seedgen/payload/mod_hooks.zip').read_bytes(),
        'seed_generator/config_campaign.nut': emit_campaign(
            campaigns[0]
            if camps else CampaignConfig(), session_id).encode(),
        'seed_generator/function_auto_start.nut': resource_path('seedgen/payload/seed_generator/function_auto_start.nut').read_bytes(),
        'bbmod_worldmap_reference.nut': source.encode(),
        'scripts/!mods_preload/mod_bbmod_worldmap_reference.nut': b'''::SeedGenerator <- {ID="mod_bbmod_worldmap_reference",Name="BBMOD Map Reference",Version=1};
::mods_registerMod(::SeedGenerator.ID,::SeedGenerator.Version,::SeedGenerator.Name);
::include("seed_generator/config_campaign");
::mods_queue(::SeedGenerator.ID,"",function(){
    ::include("seed_generator/function_auto_start");
    ::include("bbmod_worldmap_reference");
});
''',
    }
    before = signature(game.data_dir)
    readers = {folder/'log.html': IncrementalLogReader(folder/'log.html')
               for folder in game_mod.find_log_write_paths()}
    # Establish byte offsets before launch. Never consume old reference records.
    for reader in readers.values():
        reader.read_new()
    observed = set()
    changed = set()
    records = []
    finished = False
    launched = False
    began = time.perf_counter()
    report = {'schema': 1, 'game_version': game.version, 'seeds': seeds, 'session_id':session_id, 'api_only':api_only,
              'checkpoints':checkpoints, 'with_api':with_api, 'camps':camps, 'trace_rng':trace_rng, 'brothers':brothers,
              'exe_sha256': hashlib.sha256(game.exe.read_bytes()).hexdigest(),
              'reference_probe_sha256': hashlib.sha256(source.encode()).hexdigest()}
    if camps:
        report['campaigns'] = [dict(origin=c.origin, combat=c.combat_difficulty,
            economic=c.economic_difficulty, budget=c.budget_difficulty) for c in campaigns]
    try:
        session.begin(payload)
        if via_steam:
            game_mod.launch_game(game, via_steam=True)
        else:
            game_mod.launch_executable(game)
        launched = True
        with (output/'reference.jsonl').open('w', encoding='utf-8') as stream:
            while time.perf_counter()-began < timeout:
                for path, reader in readers.items():
                    for row in reader.read_new():
                        changed.add(path)
                        text = row.text.strip()
                        if text.startswith('Failed to execute script file') and 'mod_bbmod_worldmap_reference' in text:
                            raise RuntimeError(text)
                        if text == 'BBMODSeedSession: '+session_id:
                            observed.add(path)
                        if path not in observed:
                            continue
                        if not finished and getattr(row, 'level', '') in ('error', 'critical'):
                            raise RuntimeError('原版采集脚本执行失败：'+text)
                        if text.startswith('BBMODMapReference: '):
                            kind, raw = text.removeprefix('BBMODMapReference: ').split(' ', 1)
                            value = {'kind': kind, **json.loads(raw)}
                            stream.write(json.dumps(value, ensure_ascii=False)+'\n')
                            records.append(value)
                            if kind in ('environment','phase','seed-end','done'):
                                print(json.dumps({k:v for k,v in value.items() if k not in ('items','traits','trace')}, ensure_ascii=False), flush=True)
                            if kind == 'done':
                                finished = True
                                break
                        elif ('generation-failed' in text or 'Script Error' in text or
                              text.startswith('BBMODSeedStart: error')):
                            print(text, flush=True)
                stream.flush()
                if finished:
                    break
                time.sleep(0.15)
        if not finished:
            raise RuntimeError(f'地图参照采集超时，已采集 {len(records)} 条记录。')
    finally:
        if launched and game_mod.probe_game_running() and not game_mod.kill_game():
            raise RuntimeError('测试进程无法停止，已保留恢复会话；请关闭测试游戏后恢复。')
        for path in changed:
            if path.is_file():
                shutil.copy2(path, output/'game-log.html')
        session.restore()
        report['restored'] = signature(game.data_dir) == before
        report['finished'] = finished
        report['wall_seconds'] = time.perf_counter()-began
        report['records'] = len(records)
        (output/'capture.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        if not report['restored']:
            raise RuntimeError('游戏目录恢复校验未通过，请检查本次会话。')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-game', action='store_true')
    parser.add_argument('--game', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seed', action='append', default=[])
    parser.add_argument('--timeout', type=float, default=240)
    parser.add_argument('--api-only', action='store_true')
    parser.add_argument('--no-checkpoints', action='store_true')
    parser.add_argument('--with-api', action='store_true')
    parser.add_argument('--camps', action='store_true', help='Capture full original campaign initialization and camp loot')
    parser.add_argument('--trace-rng', action='store_true', help='Development diagnosis only: record full campaign RNG calls')
    parser.add_argument('--brothers', action='store_true', help='Observe original starting rosters for every official origin')
    parser.add_argument('--via-steam', action='store_true', help='Use the registered Steam launch path for the original oracle')
    args = parser.parse_args()
    if not args.run_game:
        parser.error('--run-game is required to start the original game for validation')
    seeds = args.seed or ['AbCdEfGhIj', 'ABCDEFGHIJ']
    if any(len(s) != 10 or not s.isascii() or not s.isalnum() for s in seeds):
        parser.error('种子必须为区分大小写的十位英文字母或数字')
    game = game_mod._inspect_game(args.game)
    if not game or not game.version_ok:
        parser.error('需要原版 1.5.2.3 游戏目录')
    print(json.dumps(capture(game, args.output, seeds, args.timeout, api_only=args.api_only,
                            checkpoints=not args.no_checkpoints,with_api=args.with_api,camps=args.camps,trace_rng=args.trace_rng,
                            brothers=args.brothers,via_steam=args.via_steam), ensure_ascii=False))


if __name__ == '__main__':
    main()

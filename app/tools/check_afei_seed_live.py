"""Opt-in real-game check: A/B/A batch versus independent native campaigns.

Uses BBMOD's recoverable session in the Steam-registered installation. Never
publishes fixture seeds. Refuses to run alongside an existing game process.
"""
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core import game as game_mod
from core.gamelog import IncrementalLogReader
from core.paths import resource_path
from core.seedgen.config_emitter import CampaignConfig, CommonConfig, SeedGenConfig
from core.seedgen.mod_origins import AFEI_ORIGIN
from core.seedgen.orchestrator import SeedGenOrchestrator


SNAPSHOT = r'''
::SeedGenerator.probeWorld <- function(seed, round) {
    ::logInfo("BBMODSeedProbeBegin: " + round + " " + seed);
    foreach (town in ::World.EntityManager.getSettlements()) {
        local tile = town.getTile();
        ::logInfo("BBMODSeedProbe: Town|" + town.getName() + "|" + tile.SquareCoords.X + "|" + tile.SquareCoords.Y);
    }
    foreach (camp in ::World.EntityManager.getLocations()) {
        if (camp.isLocationType(::Const.World.LocationType.Unique)) continue;
        local tile = camp.getTile();
        foreach (item in camp.getLoot().getItems()) {
            if (!item.isItemType(::Const.Items.ItemType.Named)) continue;
            local value = "Item|" + camp.getName() + "|" + tile.SquareCoords.X + "|" + tile.SquareCoords.Y + "|" + item.getID();
            foreach (field in ["RegularDamage", "RegularDamageMax", "ArmorDamageMult", "DirectDamageMult", "DirectDamageAdd",
                "ChanceToHitHead", "StaminaModifier", "ShieldDamage", "AmmoMax", "AdditionalAccuracy",
                "FatigueOnSkillUse", "MeleeDefense", "RangedDefense", "ConditionMax"])
                if (field in item.m) value += "|" + field + ":" + item.m[field];
            ::logInfo("BBMODSeedProbe: " + value);
        }
    }
    local count = 0;
    foreach (bro in ::World.getPlayerRoster().getAll()) {
        count++;
        local value = "Brother|" + bro.getName();
        foreach (field in ["Hitpoints", "Stamina", "Bravery", "Initiative", "MeleeSkill", "RangedSkill", "MeleeDefense", "RangedDefense"])
            value += "|" + field + ":" + bro.getBaseProperties()[field];
        ::logInfo("BBMODSeedProbe: " + value);
    }
    ::logInfo("BBMODSeedProbe: Brothers:" + count);
    ::logInfo("BBMODSeedProbeEnd");
};
'''

NATIVE_PROBE = r'''
::SeedGenerator.CurrentLoop <- 0;
::SeedGenerator.CurrentHits <- 0;
::SeedGenerator.reportProgress <- function(phase) {};
::mods_hookClass("states/world_state", function(o) {
    local nativeStart = ::mods_getMember(o, "startNewCampaign");
    ::mods_override(o, "startNewCampaign", function() {
        local S = ::SeedGenerator;
        local seed = S.DebugConfig.DebugSeed[0];
        ::AfeixExpedition.openLedger = function() { return false; };
        this.m.CampaignSettings.Seed = seed;
        nativeStart.bindenv(this)();
        ::Time.clearEvents();
        this.m.IsRunningUpdatesWhilePaused = false;
        this.setPause(true);
        S.probeWorld(seed, 0);
        S.CurrentLoop = 0;
        S.CurrentHits = 0;
        S.generateSettlement(seed, this, true);
        ::logInfo("Seed: " + seed + " LoopIdx:0 Origin:scenario.afeix_expedition");
        S.printSettlementInfo();
        ::logInfo("CRLF");
    });
});
'''


def file_signature(data):
    return {path.relative_to(data).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in data.rglob('*') if path.is_file() and path.suffix.lower() != '.dat'}


def run_case(game, output, name, seeds, native=False, timeout=180):
    before = file_signature(game.data_dir)
    case = output / name
    case.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='payload-', dir=case) as temporary:
        payload = Path(temporary)
        shutil.copytree(resource_path('seedgen/payload'), payload, dirs_exist_ok=True)
        custom = payload / 'seed_generator/function_mod_origin.nut'
        text = custom.read_text('utf-8')
        text = SNAPSHOT + text.replace('nativeStart.bindenv(state)();',
                                      'nativeStart.bindenv(state)();\n        this.probeWorld(seed, this.CurrentLoop);')
        custom.write_text(text, encoding='utf-8')
        if native:
            # Independent reference: no custom campaign reset/loop and no
            # generator replacements for native named-item randomization.
            (payload / 'seed_generator/function_named_attr.nut').write_text(
                '::include("seed_generator/define_lair");\n::SeedGenerator.NamedIndex <- 0;\n::SeedGenerator.NamedIndexDict <- {};\n', encoding='utf-8')
            (payload / 'seed_generator/function_main_loop.nut').write_text(NATIVE_PROBE, encoding='utf-8')
        cfg = SeedGenConfig(campaign=CampaignConfig(origin=AFEI_ORIGIN),
                            common=CommonConfig.preset('map_lair'),
                            map_conditions=[['SettlementNum', 0]], lair_conditions=[['NamedNumber', 0]])
        cfg.common.debug_mode = True
        cfg.common.debug_seeds = seeds
        session = SeedGenOrchestrator(game, payload)
        probes, current = [], None
        readers = {folder / 'log.html': IncrementalLogReader(folder / 'log.html')
                   for folder in game_mod.find_log_write_paths()}
        seen_marker = set()
        restored = False
        launched = False
        try:
            session.prepare(cfg)
            game_mod.launch_executable(game)
            launched = True
            started = time.monotonic()
            while time.monotonic() - started < timeout:
                session.poll()
                for path, reader in readers.items():
                    for row in reader.read_new():
                        text = row.text.strip()
                        if text.startswith('BBMODSeedSession: '):
                            if text == 'BBMODSeedSession: ' + session._session_id:
                                seen_marker.add(path)
                            else:
                                seen_marker.discard(path)
                        if path not in seen_marker:
                            continue
                        if text.startswith('BBMODSeedProbeBegin: '):
                            current = {'header': text, 'lines': []}
                        elif text.startswith('BBMODSeedProbe: ') and current is not None:
                            current['lines'].append(text.removeprefix('BBMODSeedProbe: '))
                        elif text == 'BBMODSeedProbeEnd' and current is not None:
                            probes.append(current); current = None
                if session.startup.stage == 'error':
                    raise RuntimeError(session.startup.detail)
                if len(session.results) >= len(seeds) and len(probes) >= len(seeds):
                    break
                time.sleep(0.5)
            else:
                raise RuntimeError(f'{name} timed out: {session.startup}, {session.progress}, results={len(session.results)}')
            (case / 'records.json').write_text(json.dumps([asdict(r) for r in session.results], ensure_ascii=False, indent=2), encoding='utf-8')
            (case / 'probes.json').write_text(json.dumps(probes, ensure_ascii=False, indent=2), encoding='utf-8')
        finally:
            if launched and game_mod.probe_game_running() and not game_mod.kill_game():
                raise RuntimeError('Could not stop the test game; the protected session is retained')
            for path in readers:
                if path.is_file() and path in seen_marker:
                    shutil.copy2(path, case / 'game-log.html')
            session.stop_and_restore()
            restored = file_signature(game.data_dir) == before
            (case / 'restored.json').write_text(json.dumps({'restored': restored}), encoding='utf-8')
            if not restored:
                raise RuntimeError('Game MOD/loose files differ after recovery')
        return probes, session.results, restored


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-game', action='store_true', help='Explicitly run and stop test campaigns in the registered game')
    parser.add_argument('--game', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=resource_path('build/afei-seed-live'))
    args = parser.parse_args()
    if not args.run_game:
        parser.error('--run-game is required; this check starts the actual game')
    if game_mod.probe_game_running():
        raise RuntimeError('Close the existing game before testing')
    game = game_mod._inspect_game(args.game)
    if game is None:
        raise RuntimeError('Invalid game installation')
    args.output.mkdir(parents=True, exist_ok=True)
    seeds = ['AbCdEfGhIj', 'ABCDEFGHIJ', 'AbCdEfGhIj']
    batch, results, restored = run_case(game, args.output, 'batch', seeds)
    assert batch[0]['lines'] == batch[2]['lines'], 'A/B/A world differs: campaign state leaked'
    assert all('Brothers:3' in item['lines'] for item in batch), 'Starting roster is not exactly three'
    for index, seed in enumerate(seeds[:2]):
        native, native_results, native_restored = run_case(game, args.output, f'native-{index}', [seed], native=True)
        assert native[0]['lines'] == batch[index]['lines'], f'{seed}: map/named attributes differ from native new campaign'
        assert native_results[0].lines == [line for line in results[index].lines
                                         if line.startswith(('SettlementInfo:', 'BuildInfo:', 'AttachedInfo:'))]
        restored = restored and native_restored
    report = {'game_version': game.version, 'origin': AFEI_ORIGIN, 'seeds': seeds,
              'batch_rounds': len(results), 'native_campaigns': 2, 'starting_brothers': 3,
              'same_seed_after_other_seed': True, 'native_map_and_named_attributes_match': True,
              'restored_original_files': restored, 'mods': results[0].mods, 'dlc_mask': results[0].dlc_mask}
    (args.output / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()

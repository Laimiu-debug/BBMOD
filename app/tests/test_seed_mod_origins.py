"""Origin sessions, fixed-roster UI, reproduction metadata, and native sequencing."""
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace
from unittest.mock import patch
import zipfile

import pytest
from PySide6.QtWidgets import QApplication

from core.game import GameInfo
from core.gamelog import LogRow
from core.paths import resource_path
from core.seedgen.config_emitter import CampaignConfig, CommonConfig, SeedGenConfig
from core.seedgen.log_watcher import SeedLogParser, SeedResult
from core.seedgen.mod_origins import AFEI_MOD, AFEI_ORIGIN, AFEI_SCENARIO
from core.seedgen.orchestrator import SeedGenOrchestrator
from core.seedgen.presentation import format_seed
from core.seedgen.protocol import seed_key, share_payload, validate_share
from core.settings import Settings
from ui.seedgen_page import SeedGenPage


def mod_at(path):
    with zipfile.ZipFile(path, 'w') as archive:
        archive.writestr('scripts/!mods_preload/mod_afeix_expedition.nut',
                        '::mods_registerMod("mod_afeix_expedition", 62, "阿飞远征团");')
        archive.writestr(AFEI_SCENARIO, '// fixture origin')
    return path


def signature(directory):
    return {p.relative_to(directory).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in directory.rglob('*') if p.is_file()}


@pytest.fixture
def game(tmp_path):
    data = tmp_path / 'game/data'
    data.mkdir(parents=True)
    (data / 'data_001.dat').write_bytes(b'official untouched')
    mod_at(data / 'afei-renamed.zip')
    (data / 'unrelated.zip').write_bytes(b'unrelated untouched')
    with patch('core.seedgen.orchestrator.game_mod.is_game_running', return_value=False), \
         patch('core.seedgen.orchestrator.game_mod.check_base_archive', return_value=None):
        yield GameInfo(data.parent, data.parent / 'win32/BattleBrothers.exe', '1.5.2.3', data)


def config(mode='map_lair'):
    return SeedGenConfig(campaign=CampaignConfig(origin=AFEI_ORIGIN), common=CommonConfig.preset(mode))


def test_origin_session_keeps_exact_main_package_and_restores_every_original(game):
    before = signature(game.data_dir)
    session = SeedGenOrchestrator(game, resource_path('seedgen/payload'))
    session.prepare(config())
    during = signature(game.data_dir)
    assert during['afei-renamed.zip'] == before['afei-renamed.zip']
    assert 'unrelated.zip' not in during and during['data_001.dat'] == before['data_001.dat']
    assert 'scripts/!mods_preload/mod_breditor.nut' not in during
    assert session._mods[0]['id'] == AFEI_MOD and session._mods[0]['version'] == '62'
    assert session._mods[0]['sha256'] == before['afei-renamed.zip']
    parsed = SeedLogParser(session._session_id)
    result, _ = parsed.feed([LogRow('info', '', 'SQ', text) for text in [
        'BBMODSeedEnvironment: DLC:99', 'BBMODSeedSession: ' + session._session_id,
        'BBMODSeedEnvironment: DLC:31', 'Seed: ABCDEFGHIJ LoopIdx:2 Origin:' + AFEI_ORIGIN,
        'SettlementInfo: Port:3', 'CRLF']])
    result = session._collect(result)[0]
    assert result.dlc_mask == 31 and result.game_version == '1.5.2.3'
    assert result.mods == session._mods
    result.mods[0]['version'] = 'changed'
    assert session._mods[0]['version'] == '62'
    session.stop_and_restore()
    assert signature(game.data_dir) == before


@pytest.mark.parametrize('problem', ['missing', 'duplicate', 'brother-mode'])
def test_invalid_mod_origin_fails_before_mutation(game, problem):
    if problem == 'missing':
        (game.data_dir / 'afei-renamed.zip').unlink()
    elif problem == 'duplicate':
        mod_at(game.data_dir / 'second.zip')
    before = signature(game.data_dir)
    session = SeedGenOrchestrator(game, resource_path('seedgen/payload'))
    with pytest.raises(ValueError):
        session.prepare(config('all' if problem == 'brother-mode' else 'map_lair'))
    assert signature(game.data_dir) == before and not session.files.active


def test_afei_ui_only_offers_map_camp_modes_and_remembers_origin(tmp_path):
    app = QApplication.instance() or QApplication([])
    settings = Settings.__new__(Settings)
    settings.path, settings.data = tmp_path / 'settings.json', {}
    context = SimpleNamespace(game=None, settings=settings)
    page = SeedGenPage(context)
    page.origin_combo.setCurrentIndex(page.origin_combo.findData(AFEI_ORIGIN))
    assert page.mode_combo.currentText() == '地图 + 红装'
    for label, tabs in [('只找地图', (False, True, False)), ('只找红装', (False, False, True)),
                        ('地图 + 红装', (False, True, True))]:
        page.mode_combo.setCurrentText(label)
        assert tuple(page.filter_tabs.isTabEnabled(i) for i in range(3)) == tabs
        cfg = page._current_config()
        assert not cfg.common.GenerateBrotherMode and not cfg.origins
        assert (cfg.map_conditions is not None, cfg.lair_conditions is not None) == tabs[1:]
    for label in ['人物 + 地图', '只找开局兄弟（快）', '人物 + 红装', '人物 + 地图 + 红装']:
        assert not page.mode_combo.model().item(page.mode_combo.findText(label)).isEnabled()
    page._save_campaign()
    reopened = SeedGenPage(context)
    assert reopened.origin_combo.currentData() == AFEI_ORIGIN
    assert reopened.mode_combo.currentText() == '地图 + 红装'
    page.origin_combo.setCurrentIndex(page.origin_combo.findData('scenario.militia'))
    assert all(page.mode_combo.model().item(i).isEnabled() for i in range(page.mode_combo.count()))
    page.close(); reopened.close()


def environment_result():
    return SeedResult('ABCDEFGHIJ', 0, origin=AFEI_ORIGIN, done=True, dlc_mask=342,
                      game_version='1.5.2.3', combat_difficulty=1, economic_difficulty=1, budget_difficulty=1,
                      lines=['SettlementInfo: Port:3'], mods=[
                          {'id': AFEI_MOD, 'name': '阿飞远征团', 'version': '0.28.12', 'sha256': 'a' * 64},
                          {'id': 'mod_hooks', 'name': 'Legacy Hooks', 'version': '21.1', 'sha256': 'b' * 64}])


def test_environment_identity_sharing_and_legacy_compatibility():
    old = SeedResult('ABCDEFGHIJ', 0, origin='scenario.militia', done=True, lines=['SettlementInfo: Port:3'])
    legacy = [old.seed, old.origin, old.game_version, old.combat_difficulty, old.economic_difficulty, old.budget_difficulty]
    assert seed_key(old) == hashlib.sha256(json.dumps(legacy, ensure_ascii=True).encode()).hexdigest()
    value = share_payload(old)
    assert value['schema_version'] == 1 and 'mods' not in value['record']
    assert validate_share(value)[0] == old
    result = environment_result()
    value = share_payload(result)
    assert value['schema_version'] == 2 and validate_share(value)[0] == result
    assert seed_key(replace(result, dlc_mask=15)) != seed_key(result)
    changed = replace(result, mods=[{**result.mods[0], 'sha256': 'c' * 64}, result.mods[1]])
    assert seed_key(changed) != seed_key(result)
    assert seed_key(replace(result, mods=list(reversed(result.mods)))) == seed_key(result)
    assert '0.28.12' in format_seed(result) and 'a' * 64 in format_seed(result)
    for replacement in [replace(result, mods=[]), replace(result, dlc_mask=None),
                        replace(result, game_version=''), replace(result, combat_difficulty=None),
                        replace(result, dlc_mask=True), replace(result, mods=result.mods * 2),
                        replace(result, mods=[{**result.mods[0], 'sha256': 'C:/private'}, result.mods[1]])]:
        with pytest.raises(ValueError):
            share_payload(replacement)


def test_historical_log_import_keeps_environment_without_leaking_across_sessions():
    result = environment_result()
    parser = SeedLogParser()
    messages = ['BBMODSeedSession: first', 'BBMODSeedEnvironment: DLC:342',
                'BBMODSeedEnvironment: Mods:' + json.dumps(result.mods, ensure_ascii=False),
                'BBMODSeedEnvironment: Difficulty:1,1,1', 'BBMODSeedEnvironment: Game:1.5.2.3',
                'Seed: ABCDEFGHIJ LoopIdx:0 Origin:' + AFEI_ORIGIN, 'SettlementInfo: Port:3', 'CRLF',
                'BBMODSeedSession: second', 'Seed: ABCDEFGHIJ LoopIdx:1 Origin:scenario.militia',
                'SettlementInfo: Port:4', 'CRLF']
    records, _ = parser.feed([LogRow('info', '', 'SQ', text) for text in messages])
    assert records[0] == result
    assert share_payload(records[0])['schema_version'] == 2
    assert records[1].mods == [] and records[1].dlc_mask is None and records[1].game_version == ''


def test_log_import_keeps_same_seed_with_different_mod_packages():
    result = environment_result()
    parser = SeedLogParser()
    messages = []
    for sha in ['a', 'c', 'c']:
        mods = [{**result.mods[0], 'sha256': sha * 64}, result.mods[1]]
        messages += ['BBMODSeedSession: ' + sha, 'BBMODSeedEnvironment: DLC:342',
                     'BBMODSeedEnvironment: Mods:' + json.dumps(mods),
                     'Seed: ABCDEFGHIJ LoopIdx:0 Origin:' + AFEI_ORIGIN,
                     'SettlementInfo: Port:3', 'CRLF']
    records, _ = parser.feed([LogRow('info', '', 'SQ', text) for text in messages])
    assert len(records) == 2
    assert [record.mods[0]['sha256'] for record in records] == ['a' * 64, 'c' * 64]


def test_changed_squirrel_sources_compile(tmp_path):
    sq = resource_path('build/fox-audit/tools/sq.exe')
    if not sq.is_file():
        pytest.skip('Local Squirrel VM required')
    paths = [resource_path('seedgen/payload') / name for name in (
        'scripts/!mods_preload/mod_seed_generator.nut', 'seed_generator/function_mod_origin.nut',
        'seed_generator/function_generate_settlement.nut', 'seed_generator/function_main_loop.nut',
        'seed_generator/function_auto_start.nut')]
    script = tmp_path / 'compile.nut'
    script.write_text('\n'.join('loadfile(' + json.dumps(p.as_posix()) + ');' for p in paths)
                      + '\nprint("ORIGIN_COMPILE_PASS\\n");', encoding='utf-8')
    run = subprocess.run([str(sq), str(script)], capture_output=True, timeout=15)
    assert run.returncode == 0 and not run.stderr and b'ORIGIN_COMPILE_PASS' in run.stdout, (run.stdout + run.stderr)


def test_native_campaign_loop_resets_flags_preserves_rolls_and_intersects_filters(tmp_path):
    sq = resource_path('build/fox-audit/tools/sq.exe')
    native = resource_path('build/full-l10n/decompiled/scripts/states/world_state.nut')
    tags = resource_path('build/full-l10n/decompiled/scripts/tools/tag_collection.nut')
    if not all(path.is_file() for path in (sq, native, tags)):
        pytest.skip('Locally extracted native campaign/tag source required')
    source = r'''
::inherit <- function(basePath, object) { return object; };
::log <- []; ::currentSeed <- ""; ::clock <- 0;
::logInfo <- function(value) { ::log.push(value); };
::Math <- {seedRandomString=function(seed){::currentSeed=seed;}, seedRandom=function(seed){}};
::Time <- {clearEvents=function(){},setVirtualTime=function(t){}, getRealTime=function(){return 1;}};
::Root <- {setBackgroundTaskCallback=function(fn){}};
::Const <- {DLC={Unhold=true,Wildmen=true,Desert=true}};
local manager={clear=function(){}};
::roster <- {count=0,clear=function(){this.count=0;}};
::World <- {Combat=clone manager, Events=clone manager, Ambitions=clone manager, Crafting=clone manager,
 Retinue=clone manager, Contracts=clone manager, Statistics=clone manager,
 Flags=null, Assets=null, getPlayerRoster=function(){return ::roster;}, clearScene=function(){},
 resizeScene=function(x,y){}, uncoverFogOfWar=function(pos,size){},
 EntityManager={clear=function(){},buildRoadAmbushSpots=function(){}},
 FactionManager={clear=function(){},createFactions=function(){},uncoverSettlements=function(mode){},
 runSimulation=function(){
   assert(::roster.count==3 && ::World.Flags.get("captains-created"));
   ::SeedGenerator.NamedIndexDict[0] <- ["native roll",::currentSeed];
 }}};
::MapGen <- {get=function(name){return {getMinX=function(){return 1;},getMinY=function(){return 1;},fill=function(bounds,none){}};}};
::AfeixExpedition <- {openLedger=function(){throw "ledger opened during search";}};
::spawnCalls <- 0; ::initCalls <- 0;
::assets <- {m={Origin=null},init=function(){},clear=function(){},setCampaignSettings=function(settings){
   assert(!::World.Flags.has("captains-created"));
   ::World.Flags.set("captains-created",true);
   ::roster.count=3;
   this.m.Origin=settings.StartingScenario;
 }};
::World.Assets=::assets;
::new <- function(path) {
  if(path=="scripts/tools/tag_collection") {local tags=clone ::tag_collection; tags.m={}; return tags;}
  assert(path=="scripts/scenarios/world/afeix_expedition_scenario");
  return {getID=function(){return "scenario.afeix_expedition";},
    onSpawnPlayer=function(){::spawnCalls++;},onInit=function(){::initCalls++;}};
};
::SeedGenerator <- {
 CommonConfig={GenerateSettlementMode=true,GenerateBrotherMode=false,OnlyPrintMatchingSettlement=true,
   PrintLairInfo=true,OnlyPrintMatchingLair=true,EnableLowercaseSeed=false},
 DebugConfig={DebugMode=true,DebugSeed=["AAAAAAAAAA","BBBBBBBBBB","AAAAAAAAAA","CCCCCCCCCC"]},
 NamedIndex=0,NamedIndexDict={},CurrentLoop=0,CurrentHits=0,map_output_type=-1,lair_output_type=-1,
 reportProgress=function(phase){},
 generateSettlement=function(seed,state,read_existing){
   assert(read_existing && ::spawnCalls==this.CurrentLoop+1 && ::initCalls==this.CurrentLoop+1);
   assert(state.m.CampaignSettings==null && this.NamedIndexDict[0][1]==seed);
   return this.CurrentLoop==1 ? -1 : 0;
 },
 generateLairInfo=function(){return this.CurrentLoop==3 ? -1 : 0;},
 printSettlementInfo=function(){::logInfo("SettlementInfo: Port:3");},
 printLairInfo=function(){::logInfo("NamedInfo: Sum:1");}
};
'''
    source += 'dofile(' + json.dumps(tags.as_posix()) + ');\n'
    source += 'dofile(' + json.dumps(native.as_posix()) + ');\n'
    source += 'dofile(' + json.dumps(resource_path('seedgen/payload/seed_generator/function_mod_origin.nut').as_posix()) + ');\n'
    source += r'''
local state=::world_state;
state.setdelegate(getroottable());
state.m.Assets=::assets;
state.m.CampaignSettings={Seed="AAAAAAAAAA",StartingScenario=::new("scripts/scenarios/world/afeix_expedition_scenario"),ExplorationMode=false};
state.setAutoPause=function(value){}; state.setPause=function(value){};
state.getPlayer=function(){return {getTile=function(){return {Pos={X=0,Y=0}};}};};
state.setupWeather=function(){};
::SeedGenerator.searchModOrigin(state,state.startNewCampaign);
local heads=[]; foreach(line in ::log) if(line.find("Seed: ")==0) heads.push(line);
assert(heads.len()==2 && heads[0].find("LoopIdx:0")!=null && heads[1].find("LoopIdx:2")!=null);
assert(::spawnCalls==4 && ::initCalls==4 && ::SeedGenerator.CurrentHits==2);
assert(::World.Flags.get("captains-created") && ::World.Flags.get("IsDesertCampaign"));
print("NATIVE_ORIGIN_LOOP_PASS 4 campaigns 2 matched\n");
'''
    script = tmp_path / 'native_loop.nut'
    script.write_text(source, encoding='utf-8')
    run = subprocess.run([str(sq), str(script)], capture_output=True, timeout=15)
    assert run.returncode == 0 and not run.stderr and b'NATIVE_ORIGIN_LOOP_PASS' in run.stdout, (run.stdout + run.stderr)

import re
import subprocess
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from core.paths import resource_path
from core import game as game_mod
from core.seedgen.config_emitter import CommonConfig, SeedGenConfig, render_lair_row, write_configs
from core.seedgen.log_watcher import SeedResult
from core.seedgen.presentation import format_seed
from core.seedgen.weapons import NAMED_WEAPONS, WEAPON_CHOICES, weapon_condition
from core.settings import Settings
from ui.seedgen_page import SeedGenPage


def test_weapon_catalog_matches_the_actual_game_scripts():
    directory = resource_path('build/full-l10n/decompiled/scripts/items/weapons/named')
    if not directory.is_dir():
        pytest.skip('Official decompiled scripts unavailable')
    actual = set()
    for path in directory.glob('*.nut'):
        match = re.search(r'this\.m\.ID = "([^"]+)"', path.read_text('utf-8-sig'))
        if match:
            actual.add(match[1])
    assert set(NAMED_WEAPONS) == actual
    assert len(NAMED_WEAPONS) == len(set(NAMED_WEAPONS.values())) == 50


@pytest.mark.parametrize('args', [
    ('weapon.fake', 1), ('weapon.named_javelin"], print(1)', 1),
    ('weapon', 0), ('weapon', 201), ('weapon', True),
    ('weapon', 1, -1), ('weapon', 1, 101), ('weapon', 1, True), ('weapon', 1, None, 1.5),
])
def test_invalid_weapon_criteria_are_rejected(args):
    with pytest.raises(ValueError):
        weapon_condition(*args)


def test_actual_squirrel_checker_filters_types_quantities_and_same_item_affixes(tmp_path):
    sq = resource_path('build/full-l10n/tools/bin/sq.exe')
    if not sq.is_file():
        pytest.skip('Offline Squirrel interpreter unavailable')
    payload = resource_path('seedgen/payload')
    cfg = SeedGenConfig(common=CommonConfig.preset('lair_only'),
                        lair_conditions=[weapon_condition('weapon.named_javelin', 2, 75, 75)])
    write_configs(payload, tmp_path, cfg)
    rows = {
        'plain': weapon_condition('weapon.named_javelin'),
        'damage': weapon_condition('weapon.named_javelin', 1, 75),
        'zero': weapon_condition('weapon.named_javelin', 1, 0),
        'range': weapon_condition('range', 2),
        'allWeapons': weapon_condition('weapon', 2),
        'twoHanded': weapon_condition('two_hand', 1),
        'penetration': weapon_condition('weapon.named_javelin', 1, None, 75),
    }
    source = r'''
::SeedGenerator <- {};
::include <- function(path) { dofile(path + ".nut"); };
include("seed_generator/config_common");
include("seed_generator/config_lair_condition");
include("seed_generator/function_lair_output_check");
local S = ::SeedGenerator;
local LairOutput = S.LairOutput; local NamedAttr = S.NamedAttr;
assert(S.CommonConfig.GenerateSettlementMode && !S.CommonConfig.GenerateBrotherMode);
assert(S.CommonConfig.PrintLairInfo && S.CommonConfig.PrintLairNamedDetail && S.CommonConfig.OnlyPrintMatchingLair);
assert(!S.CommonConfig.OnlyPrintMatchingSettlement);
S.Const <- {Items={ItemType={Helmet=1,Armor=2,Shield=4,MeleeWeapon=8,TwoHanded=16,OneHanded=32,RangedWeapon=64}}};
S.Math <- {round=function(n){return floor(n+0.5);}};
S.NamedIndexDict <- {};
S.named_total_num <- 0;
S.lair_info_list <- [];
S.logError <- function(e){throw e;};
local cases=0;
function item(id, first, roll1, second, roll2, flags=64) {
    local index=::SeedGenerator.NamedIndexDict.len();
    ::SeedGenerator.NamedIndexDict[index] <- [first,roll1,0,100,second,roll2,0,100];
    return {m={ID=id,NamedInitIndex=index},Flags=flags,
        isItemType=function(flag){return (this.Flags & flag)!=0;}};
}
function run(rule, items, expected) {
    local S=::SeedGenerator;
    local lair=array(S.LairInfoEntryNum,0);
    lair[S.LairInfoEntry.NamedItemsList]=items;
    S.LairOutputConditionArray=[rule]; S.lair_info_list=[lair]; S.named_total_num=items.len();
    assert(S.lairOutoutCheck()==expected); cases++;
}
local configured=S.LairOutputConditionArray[0];
local D=S.NamedAttr.RegularDamage; local P=S.NamedAttr.DirectDamageAdd; local A=S.NamedAttr.AmmoMax;
local good=item("weapon.named_javelin",D,75,P,75);
local best=item("weapon.named_javelin",P,100,D,100);
local weak=item("weapon.named_javelin",D,74,P,100);
local damageOnly=item("weapon.named_javelin",D,100,A,100);
local penetrationOnly=item("weapon.named_javelin",P,100,A,100);
local axe=item("weapon.named_throwing_axe",D,100,P,100);
run(configured,[good,best],0);
run(configured,[good],-1);
run(configured,[good,weak],-1);
run(configured,[damageOnly,penetrationOnly],-1);
run(configured,[good,axe],-1);
run(configured,[],-1);
'''
    source += '\n'.join(f'local {key}={render_lair_row(row).rstrip(",")};' for key, row in rows.items())
    source += r'''
run(plain,[penetrationOnly],0);
run(plain,[axe],-1);
run(damage,[damageOnly],0);
run(damage,[penetrationOnly],-1);
run(zero,[penetrationOnly],-1);
run(zero,[item("weapon.named_javelin",D,0,A,0)],0);
run(penetration,[penetrationOnly],0);
run(penetration,[damageOnly],-1);
run(range,[good,axe],0);
local sword=item("weapon.named_greatsword",D,100,P,100,8|16);
run(range,[good,sword],-1);
run(allWeapons,[good,sword],0);
run(twoHanded,[sword],0);
run(twoHanded,[good],-1);
run([S.LairOutput.NamedNumber,2],[good,axe],0);
print("WEAPON_FILTER_PASS cases="+cases+"\n");
'''
    script = tmp_path / 'weapons.nut'
    script.write_text(source, encoding='utf-8')
    result = subprocess.run([str(sq), str(script)], cwd=tmp_path, capture_output=True, timeout=15)
    assert result.returncode == 0 and not result.stderr and b'WEAPON_FILTER_PASS cases=20' in result.stdout, (result.stdout + result.stderr).decode(errors='replace')


def test_ui_selection_reaches_all_red_loot_modes_and_survives_reopen(tmp_path):
    app = QApplication.instance() or QApplication([])
    settings = Settings.__new__(Settings)
    settings.path, settings.data = tmp_path / 'settings.json', {}
    context = SimpleNamespace(game=None, settings=settings)
    page = SeedGenPage(context)
    page.resize(840, 620)
    page.show()
    page.mode_combo.setCurrentText('只找红装')
    page.rule_mode.setCurrentIndex(page.rule_mode.findData('traits'))  # Empty inactive trait rule must not block loot.
    assert not page.filter_tabs.isTabEnabled(0) and not page.filter_tabs.isTabEnabled(1)
    filt = page.weapon_filter
    filt.kind.setFocus()
    QTest.keyClick(filt.kind, Qt.Key_Down)
    assert filt.kind.currentData() == 'weapon' and filt.stack.currentIndex() == 1
    filt.weapon.setCurrentIndex(filt.weapon.findData('weapon.named_javelin'))
    filt.count.setValue(2)
    filt.damage.setValue(75)
    filt.penetration.setValue(75)
    cfg = page._current_config()
    assert cfg.lair_conditions == [weapon_condition('weapon.named_javelin', 2, 75, 75)]
    assert cfg.origins == {} and cfg.map_conditions is None
    page.rule_mode.setCurrentIndex(page.rule_mode.findData('attributes'))
    for label in ('人物 + 红装', '人物 + 地图 + 红装'):
        page.mode_combo.setCurrentText(label)
        assert page._current_config().lair_conditions == cfg.lair_conditions
        assert page._current_config().origins
    for label in ('只找地图', '人物 + 地图', '只找开局兄弟（快）'):
        page.mode_combo.setCurrentText(label)
        assert page._current_config().lair_conditions is None
    reopened = SeedGenPage(context)
    reopened.mode_combo.setCurrentText('只找红装')
    assert reopened._current_config().lair_conditions == cfg.lair_conditions
    reopened.weapon_filter.kind.setCurrentIndex(0)
    reopened.named_min.setValue(28)
    assert reopened._current_config().lair_conditions == [['NamedNumber', 28]]
    reopened.weapon_filter.kind.setCurrentIndex(1)
    assert reopened._current_config().lair_conditions == cfg.lair_conditions  # No OR with total count.
    reopened.close()
    page.close()
    app.processEvents()


def test_unknown_saved_values_fall_back_without_emitting_custom_script(tmp_path):
    app = QApplication.instance() or QApplication([])
    settings = Settings.__new__(Settings)
    settings.path = tmp_path / 'settings.json'
    settings.data = {'seed_lair_filter': {'kind':'weapon','weapon':'unknown','count':-5,'damage':'bad','penetration':True}}
    page = SeedGenPage(SimpleNamespace(game=None, settings=settings))
    page.mode_combo.setCurrentText('只找红装')
    assert page._current_config().lair_conditions == [weapon_condition('weapon')]
    page.close()


def test_result_names_and_affix_rolls_are_kept_separate_from_final_weapon_stats():
    seed = SeedResult('REDJAVELIN', 1, done=True, lines=[
        'ItemInfo(RangedWeapon): weapon.named_javelin(RegularDamage:75%|DirectDamageAdd:100%) MinDamage:40 MaxDamage:60 DirectDamage:0.45 AmmoMax:5',
        'ItemInfo(Armor): armor.named_coat(StaminaModifier:50%|Condition:75%) Armor:250',
        'ItemInfo(OneHanded): weapon.unknown MinDamage:30',
    ])
    text = format_seed(seed)
    assert '红标枪：伤害品质 75%；穿甲品质 100%' in text
    assert '最低伤害 40' in text and '无视护甲比例 45%' in text
    assert '红甲：' in text and '护甲 250' in text
    assert '单手红武：最低伤害 30' in text


def test_seed_launch_uses_normal_desktop_path_and_keeps_copy_guard(tmp_path):
    root = tmp_path / 'game'
    game = SimpleNamespace(root=root, exe=root / 'win32/BattleBrothers.exe')
    with patch('core.game.find_steam_root', return_value=None), \
         patch('core.game.os.startfile', create=True) as desktop, \
         patch('core.game.subprocess.Popen') as child:
        assert game_mod.launch_game(game, via_steam=False)
        desktop.assert_called_once_with(str(game.exe), cwd=str(game.exe.parent))
        child.assert_not_called()
        desktop.side_effect = OSError('launch unavailable')
        assert not game_mod.launch_game(game, via_steam=False)
    steam = tmp_path / 'steam'
    (steam / 'steamapps/common/Battle Brothers').mkdir(parents=True)
    (steam / 'steamapps/appmanifest_365360.acf').write_text('"installdir" "Battle Brothers"')
    with patch('core.game.find_steam_root', return_value=steam), \
         patch('core.game.list_steam_libraries', return_value=[steam]), \
         patch('core.game.os.startfile', create=True) as desktop:
        with pytest.raises(RuntimeError, match='隔离测试'):
            game_mod.launch_game(game, via_steam=False)
        desktop.assert_not_called()


def test_actual_main_loop_loot_only_ignores_map_and_character_filters(tmp_path):
    sq = resource_path('build/full-l10n/tools/bin/sq.exe')
    if not sq.is_file():
        pytest.skip('Offline Squirrel interpreter unavailable')
    source = r'''
::Time <- {setVirtualTime=function(n){},getExactTime=function(){return 0.0;}};
::Math <- {seedRandomString=function(s){},rand=function(a,b){return a;}};
::outputs <- 0; ::aligned <- 0; ::named <- 0;
::logInfo <- function(s) {};
::SeedGenerator <- {LowestScore=0,Attr={},AttrNum=0,Role={},RoleName=["Melee"],RoleNum=1,
BroOutput={},BroOutputConditionArray=[],MaxRoleArray={},BroSortEntry={},BroScoreEntry={},BroSortEntryNum=0,BroEntryNum=0,
LoopPrintInterval=10000,DebugConfig={DebugMode=false},EndlessLoopFlag=false,
CommonConfig={GenerateSettlementMode=true,GenerateBrotherMode=false,PrintLairInfo=true,
PrintLairNamedDetail=true,OnlyPrintMatchingLair=true,OnlyPrintMatchingSettlement=false,EnableLowercaseSeed=false},
generateSettlement=function(seed,world){if(this.CurrentLoop==6) throw "finished"; return -1;},
generateBrother=function(seed,world,align){assert(align);::aligned++;},
generateLairInfo=function(){return this.CurrentLoop%2==0?0:-1;},
printLairInfo=function(){::named++;},printSettlementInfo=function(){::outputs++;}};
::World <- {Assets={getStash=function(){return {clear=function(){},resize=function(n){}};}},
clearScene=function(){},EntityManager={clear=function(){}},FactionManager={clear=function(){},runSimulation=function(){}}};
::world <- {setAutoPause=function(n){},setPause=function(n){},Time=::Time,Math=::Math,World=::World,logInfo=::logInfo,
m={IsRunningUpdatesWhilePaused=false,CampaignSettings={Seed="AAAAAAAAAA",StartingScenario={getID=function(){return "scenario.cultists";},onSpawnPlayer=function(){}}}}};
::mods_hookClass <- function(path, callback){callback(::world);};
::mods_override <- function(o, name, fn){o[name] <- fn;};
'''
    source += f'dofile("{resource_path("seedgen/payload/seed_generator/function_main_loop.nut").as_posix()}");\n'
    source += r'''
local ended=false;
try { ::world.startNewCampaign(); } catch(error) {if(error!="finished") throw error; ended=true;}
assert(ended && ::aligned==6 && ::outputs==3 && ::named==3);
print("LOOT_ONLY_LOOP_PASS\n");
'''
    path = tmp_path / 'loot_loop.nut'
    path.write_text(source, encoding='utf-8')
    result = subprocess.run([str(sq), str(path)], capture_output=True, timeout=15)
    assert result.returncode == 0 and not result.stderr and b'LOOT_ONLY_LOOP_PASS' in result.stdout, (result.stdout + result.stderr).decode(errors='replace')

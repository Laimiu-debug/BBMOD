"""Offline checks of the actual installed star/rating MOD and our current package.

Reads that gameplay MOD only. Never reads any third-party localization content,
launches the game, or writes to the Steam installation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from unittest.mock import patch
import zipfile

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
from core.l10n import conflicting_ui_mods
from core.full_l10n import load_full_catalog
from core.cnut import Cnut
from core.l10n_compat import DISPLAY_ONLY_FILES, hooks_assets
from core.localization_profiles import LocalizationProfiles, NAME_HINT, DISABLED_DIR

MOD_SCRIPT = 'scripts/!mods_preload/mod_sr_alternative_standard.nut'
HIRE = next(iter(DISPLAY_ONLY_FILES))
EXPECTED_MOD = 'a993de21b58f6132f0339ecdf7141e56c0086a3f0c12d3f83e4b202749af4279'
WORK = APP / 'build/review/star-rating-compatibility'

HARNESS = r'''
::logInfo <- function(s) {};
::inherit <- function(baseName, members) { return members; };
::objects <- {};
::new <- function(name) { return ::objects[name]; };
::Time <- {getRealTimeF = function() { return 1.0; }};
::Tactical <- {spawnEntity = function(name) {}, getCasualtyRoster = function() { return null; }};
::World <- {spawnEntity = function(name) {}, spawnLocation = function(name) {}, getPlayerEntity = function() { return null; },
 getGuestRoster = function() { return null; }, getPlayerRoster = function() { return null; },
 getTemporaryRoster = function() { return null; }, getRoster = function(id) { return null; }};
dofile("redirect.nut");
assert(::mods_getRegisteredMod("mod_hooks").Version == 21.1);
dofile("mod_sr_alternative_standard.nut");
dofile("finalize.nut");
::Const <- {Attributes = {Hitpoints=0, Fatigue=1, Initiative=2, Bravery=3, MeleeSkill=4, RangedSkill=5, MeleeDefense=6, RangedDefense=7},
 SkillType = {Trait=1}, UI = {Color = {DamageValue="#aa0000", PositiveValue="#00aa00"}}};
local zero = {Hitpoints=[0,0],Stamina=[0,0],Initiative=[0,0],Bravery=[0,0],MeleeSkill=[0,0],RangedSkill=[0,0],MeleeDefense=[0,0],RangedDefense=[0,0]};
local background = {getDescription = function() {return "独立汉化人物背景。";}, onChangeAttributes = function() {return zero;}, getIconColored=function(){return "background.png";}};
local props = {Hitpoints=60,Stamina=100,Initiative=100,Bravery=40,MeleeSkill=67,RangedSkill=42,MeleeDefense=5,RangedDefense=5};
local entity = {getBackground=function(){return background;}, getBaseProperties=function(){return props;},
 getTalents=function(){return [0,1,2,3,3,2,1,0];}, m={Skills={m={Skills=[]}}, Attributes=[]},
 getID=function(){return 42;}, getName=function(){return "阿尔内";}, getLevel=function(){return 1;},
 getHiringCost=function(){return 4510;}, getDailyCost=function(){return 34;}, getDailyFood=function(){return 2;},
 getTryoutCost=function(){return 476;}, getImagePath=function(){return "brother.png";},
 getImageOffsetX=function(){return 0;}, getImageOffsetY=function(){return 0;}};
for(local i=0;i<8;i++) entity.m.Attributes.append(array(10,3));
local target = {Const=::Const, queryHireInformation=function(){}, onTryoutRosterEntry=function(id){}, onHireRosterEntry=function(id){return "original hire";}};
local name = "scripts/ui/screens/world/modules/world_town_screen/town_hire_dialog_module";
::objects[name] <- target;
local hooked = ::new(name);
assert(hooked == target);
assert("onDismissRosterEntry" in target);
local data = target.convertEntityHireInformationToUIDataAltered(entity);
assert(data.ID==42 && data.InitialMoneyCost==4510 && data.TryoutCost==476 && data.DailyMoneyCost==34);
assert(data.meleeSkill==67 && data.meleeSkillTalent==3 && data.hitpointsMax==60 && data.hitpointsTalent==0);
assert(data.BackgroundText.find("67/57 (97)")!=null);
assert(data.BackgroundText.find("talent_3.png")!=null);
assert(data.BackgroundText.find("加点建议")!=null);
assert(data.BackgroundText.find("独立汉化人物背景。")!=null);
// Calling new again must not wrap the one-time hook twice.
local hire = target.onHireRosterEntry;
::new(name);
assert(target.onHireRosterEntry==hire);
// A new campaign re-arms these hooks, as the actual framework promises.
::mods_callHook("beforeCampaignLoad");
::new(name);
assert(target.onHireRosterEntry!=hire);
print("BBMOD_STAR_RATING_PASSED\n");
'''


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--mod', type=Path, required=True)
    ap.add_argument('--package', type=Path, default=APP/'build/full-l10n/preview-package/mod_bbmod_zhcn.zip')
    ap.add_argument('--installed-data', type=Path, help='Opaque copies only; switching is tested in a temporary directory.')
    args = ap.parse_args()
    before = sha(args.mod)
    assert before == EXPECTED_MOD, 'Different MOD revision: review its behavior before accepting this fixture.'
    WORK.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.mod) as z:
        (WORK/'mod_sr_alternative_standard.nut').write_bytes(z.read(MOD_SCRIPT))
        (WORK/'world_town_screen_hire_dialog_module.js').write_bytes(z.read(HIRE))
    assets = hooks_assets()
    with zipfile.ZipFile(args.package) as z:
        assert HIRE not in z.namelist()
        assert MOD_SCRIPT not in z.namelist()
        manifest = json.loads(z.read('BBMOD_L10N.json'))
        for name, raw in assets.items():
            assert z.read(name) == raw
        html = z.read('ui/main.html').decode('utf-8-sig')
        assert html.index('screens/menu/main_menu_screen.js') < html.index('src="mod_hooks.js"') < html.index('</head>')
        for name in ('dictionary.js','runtime.js'):
            (WORK/name).write_bytes(z.read('ui/mods/bbmod_l10n/'+name))
        # The untouched original screen remains the fallback when the gameplay
        # MOD is absent. Check the actual official file against catalog origin.
        catalog = load_full_catalog()
        original_ui = (APP/'build/full-l10n/original'/HIRE).read_bytes()
        assert hashlib.sha256(original_ui).hexdigest() == catalog['files'][HIRE]['sha256']
        (WORK/'original_hire.js').write_bytes(original_ui)
        helper = 'scripts/ui/global/data_helper.cnut'
        original_helper = Cnut((APP/'build/full-l10n/plain'/helper).read_bytes())
        translated_helper = Cnut(z.read(helper), encrypted=True)
        def recruit_function(parsed):
            return next(f for f in parsed.functions if f['name']=='convertEntityHireInformationToUIData')
        original_recruit, translated_recruit = map(recruit_function, (original_helper,translated_helper))
        assert original_recruit['instructions']==translated_recruit['instructions']
        assert original_recruit['literals']==translated_recruit['literals']
    (WORK/'redirect.nut').write_bytes(assets['scripts/!mods_preload/!!redirect.nut'])
    (WORK/'finalize.nut').write_bytes(assets['scripts/!mods_preload/~~finalize.nut'])
    (WORK/'harness.nut').write_text(HARNESS, encoding='utf-8')
    result = subprocess.run([str(APP/'build/full-l10n/tools/bin/sq.exe'), 'harness.nut'], cwd=WORK, capture_output=True, timeout=30)
    output = (result.stdout+result.stderr).decode('utf-8', errors='replace')
    assert result.returncode==0 and 'BBMOD_STAR_RATING_PASSED' in output, output
    ui = subprocess.run(['node',str(APP/'tools/check_star_rating_ui.cjs'),str(WORK)], capture_output=True, timeout=30)
    assert ui.returncode==0, (ui.stdout+ui.stderr).decode('utf-8',errors='replace')
    ui_result = json.loads(ui.stdout.decode('utf-8').strip().splitlines()[-1])
    vanilla = subprocess.run(['node',str(APP/'tools/check_star_rating_ui.cjs'),str(WORK),'vanilla'], capture_output=True, timeout=30)
    assert vanilla.returncode==0, (vanilla.stdout+vanilla.stderr).decode('utf-8',errors='replace')
    vanilla_result = json.loads(vanilla.stdout.decode('utf-8').strip().splitlines()[-1])
    with tempfile.TemporaryDirectory(prefix='bbmod-star-') as temp:
        root = Path(temp)/'game'
        (root/'data').mkdir(parents=True)
        installed = root/'data'/args.mod.name
        shutil.copy2(args.mod, installed)
        manager = LocalizationProfiles(root)
        with patch('core.game.is_game_running', return_value=False):
            key = manager.register('独立汉化', [args.package], builtin=True)
            plan = manager.plan(key)
            assert args.mod.name not in plan.disable and not plan.conflicts
            manager.apply(plan)
            assert sha(installed)==before
            assert not conflicting_ui_mods(root/'data', args.package)
    installed_profile = None
    if args.installed_data:
        originals = {p.name: p for p in sorted(args.installed_data.glob('*.zip'))}
        original_hashes = {n: sha(p) for n,p in originals.items()}
        language_names = sorted(n for n in originals if NAME_HINT.search(n))
        assert language_names, 'No existing localization identified for switch-back validation.'
        with tempfile.TemporaryDirectory(prefix='bbmod-star-installed-') as temp:
            root = Path(temp)/'game'
            (root/'data').mkdir(parents=True)
            for name, path in originals.items(): shutil.copy2(path, root/'data'/name)
            manager = LocalizationProfiles(root)
            with patch('core.game.is_game_running', return_value=False):
                previous = manager.register('原有汉化', [root/'data'/n for n in language_names])
                selected = manager.register('独立汉化', [args.package], builtin=True)
                plan = manager.plan(selected)
                assert sorted(plan.disable) == language_names and not plan.conflicts, plan
                manager.apply(plan)
                kept = [n for n in originals if n not in language_names]
                assert args.mod.name in kept
                assert all(sha(root/'data'/n)==original_hashes[n] for n in kept)
                assert not conflicting_ui_mods(root/'data', args.package)
                back = manager.plan(previous)
                # The old third-party pack still owns the hire screen. That
                # real overlap must remain visible; this fix changes only our
                # package and does not rewrite or whitelist the old one.
                assert args.mod.name in back.conflicts
                manager.apply(back)
                assert all(any((folder/n).exists() and sha(folder/n)==expected
                               for folder in (root/'data', root/DISABLED_DIR))
                           for n,expected in original_hashes.items())
                installed_profile = {'source_hashes':original_hashes, 'disabled_localizations':language_names,
                                     'gameplay_mods_preserved':kept, 'switch_back_files_preserved':True,
                                     'switch_back_conflicts_reported':back.conflicts,
                                     'third_party_translation_contents_read':False, 'conflicts':[]}
        assert {n:sha(p) for n,p in originals.items()} == original_hashes
    assert sha(args.mod)==before
    report = {'package_sha256':sha(args.package),'full_catalog_sha256':manifest['full_catalog_sha256'],
              'game_started':False,'steam_installation_modified':False,'mod_sha256':before,'mod_unchanged':True,
              'profile_preserves_star_mod':True,'file_overlaps':[], 'legacy_hooks':'21.1 included unchanged',
              'native_hook_registration_and_rearming':'passed', 'native_stats_stars_ratings':'passed', 'ui':ui_result,
              'without_star_mod':{'original_recruit_data_function_unchanged':True, 'no_star_script_bundled':True,'ui':vanilla_result},
              'installed_profile_simulation':installed_profile}
    (WORK/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))


if __name__=='__main__': main()

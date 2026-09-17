"""Check the packaged place-display session offline. Never start the game."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from core.place_display import read_packaged_display, BRIDGE_ENTRY, DATA_ENTRY, JS_ENTRY


def main():
    package=ROOT/'build/full-l10n/preview-package/mod_bbmod_zhcn.zip'
    target=ROOT/'build/session-place-names/validation'; target.mkdir(parents=True,exist_ok=True)
    raw=read_packaged_display(package)
    (target/'place_names.tsv').write_bytes(raw)
    with zipfile.ZipFile(package) as archive:
        manifest=json.loads(archive.read('BBMOD_L10N.json'))
        for file in ['dictionary.js','runtime.js','place_names.js']:
            (target/file).write_bytes(archive.read('ui/mods/bbmod_l10n/'+file))
        for entry, file in [('ui/mod_hooks.js','mod_hooks.js'),(BRIDGE_ENTRY,'bridge.nut'),
                            ('scripts/!mods_preload/!!redirect.nut','hooks.nut')]:
            (target/file).write_bytes(archive.read(entry))
        html=archive.read('ui/main.html').decode('utf-8')
        positions=[html.index(part) for part in ['screens/menu/main_menu_screen.js','src="mod_hooks.js"',
                    'mods/bbmod_l10n/dictionary.js','mods/bbmod_l10n/place_names.js','mods/bbmod_l10n/runtime.js','</head>']]
        assert positions==sorted(positions)
    browser=subprocess.run(['node',str(ROOT/'tests/place_display.test.cjs'),str(ROOT/'build/browser-check/node_modules/jsdom'),str(target)],
                           capture_output=True,timeout=45)
    (target/'ui-output.txt').write_bytes(browser.stdout+browser.stderr)
    if browser.returncode:
        raise RuntimeError((browser.stdout+browser.stderr).decode(errors='replace'))
    ui=json.loads(browser.stdout.decode().splitlines()[-1])
    def quote(path):return json.dumps(str(path.resolve()).replace('\\','/'))
    # Real packaged Modding Script Hooks plus minimal stand-ins for engine
    # functions. This executes the bridge in the Squirrel interpreter itself.
    harness='''
::logInfo <- function(value) {};
::Time <- { getRealTimeF = function() { return 1.0; } };
::inherit <- function(baseName, members) { return members; };
::new <- function(script) { return { OriginalField = "untouched" }; };
::empty <- function(...) { return {}; };
::Tactical <- { spawnEntity = empty, getCasualtyRoster = empty };
::World <- { spawnEntity = empty, spawnLocation = empty, getPlayerEntity = empty,
             getGuestRoster = empty, getPlayerRoster = empty, getTemporaryRoster = empty, getRoster = empty };
'''
    harness+='dofile('+quote(target/'hooks.nut')+');\ndofile('+quote(target/'bridge.nut')+');\n'
    harness+='''
local menu = new("scripts/ui/screens/menu/main_menu_screen");
assert(menu.OriginalField == "untouched");
assert("getRegisteredCSSHooks" in menu && "getRegisteredJSHooks" in menu);
assert(menu.getRegisteredCSSHooks().len() == 0);
assert(menu.getRegisteredJSHooks().len() == 0);
assert(menu.bbmodGetPlaceNameSession() == "");
::BBMODPlaceDisplaySession <- "zh-CN:offline-test";
assert(menu.bbmodGetPlaceNameSession(null) == "zh-CN:offline-test");
local other = new("scripts/ui/screens/menu/ingame_menu_screen");
assert(!("bbmodGetPlaceNameSession" in other));
local another = new("scripts/ui/screens/menu/main_menu_screen");
assert(another.bbmodGetPlaceNameSession() == "zh-CN:offline-test");
delete ::BBMODPlaceDisplaySession;
assert(menu.bbmodGetPlaceNameSession() == "");
assert(another.OriginalField == "untouched");
print("BBMOD_PLACE_BRIDGE_PASS\\n");
'''
    file=target/'check-bridge.nut';file.write_text(harness,encoding='ascii')
    bridge=subprocess.run([str(ROOT/'build/full-l10n/tools/bin/sq.exe'),str(file)],capture_output=True,timeout=15)
    (target/'squirrel-output.txt').write_bytes(bridge.stdout+bridge.stderr)
    if bridge.returncode or bridge.stderr or b'BBMOD_PLACE_BRIDGE_PASS' not in bridge.stdout:
        raise RuntimeError((bridge.stdout+bridge.stderr).decode(errors='replace'))
    native=subprocess.run(['cmd','/c',str(ROOT/'native/test_places.cmd'),str(target/'place_names.tsv')],
                          cwd=ROOT,capture_output=True,timeout=55)
    (target/'native-output.txt').write_bytes(native.stdout+native.stderr)
    if native.returncode or b'BBMOD_NATIVE_PLACE_PASS' not in native.stdout:
        raise RuntimeError((native.stdout+native.stderr).decode(errors='replace'))
    report={'package_sha256':hashlib.sha256(package.read_bytes()).hexdigest(),'version':manifest['version'],
            'place_name_display':manifest['place_name_display'],'reviewed_geographic_entries':manifest['reviewed_place_entries'],
            'expanded_place_names':manifest['expanded_place_names'],'dictionary_sha256':hashlib.sha256(raw).hexdigest(),
            'reviewed_places_sha256':hashlib.sha256((ROOT/'localization/reviewed_place_names.json').read_bytes()).hexdigest(),
            'native_map_dictionary_all_entries':'passed','native_vm_abi_10000_calls':'passed',
            'actual_native_render_proxy':'passed','native_dictionary_hash_check':'passed',
            'pinned_game_code_signatures':'passed','actual_game_process_executed':False,
            'squirrel_bridge_with_packaged_framework':'passed','ui':ui,'input_and_backend_names_unchanged':True,
            'new_bridge_entry':BRIDGE_ENTRY,'bridge_sha256':hashlib.sha256((target/'bridge.nut').read_bytes()).hexdigest(),
            'game_visual_acceptance':'pending'}
    (target/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))


if __name__=='__main__':main()

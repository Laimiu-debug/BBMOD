"""Exercise the bridge and roll arithmetic in an isolated original-game main menu.

No campaign is opened and no save routine is called. The temporary test mod is
never bundled. Existing user configs/logs are snapshotted and restored.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.game import GameInfo, locate_game, is_game_running, find_log_write_paths, OFFICIAL_ARCHIVES
from core.inspector_mod import change
from core.item_inspector import appraise, catalog, MARKER
from core.gamelog import load_log


def main():
    if is_game_running(): raise RuntimeError('Exit the game before isolated validation')
    source = locate_game()
    assert source and source.version_ok
    folder = ROOT / 'build/inspector-game'
    out = ROOT / 'build/review/inspector-engine'; out.mkdir(parents=True, exist_ok=True)
    (folder / 'data').mkdir(parents=True, exist_ok=True)
    if not (folder / 'win32').exists(): shutil.copytree(source.root / 'win32', folder / 'win32')
    for filename in OFFICIAL_ARCHIVES:
        target = folder / 'data' / filename
        if (source.data_dir / filename).exists() and not target.exists():
            try: os.link(source.data_dir / filename, target)
            except OSError: shutil.copy2(source.data_dir / filename, target)
    game = GameInfo(folder, folder / 'win32/BattleBrothers.exe', source.version, folder / 'data')
    # Steam's documented local development marker prevents relaunch into the
    # user's registered installation. It does not grant a Steam license.
    (game.exe.parent / 'steam_appid.txt').write_text('365360', encoding='ascii')
    change(game)
    scripts = [x['source'].removesuffix('.nut') for x in catalog().values()]
    bootstrap = '''::mods_hookExactClass("states/main_menu_state", function(o) {
        local original = o.onInit;
        o.onInit = function() {
            original();
            try {
                ::logInfo("BBMOD_ROUND " + ::Math.round(-7.5) + " " + ::Math.round(7.5));
                local paths = PATHS;
                foreach(path in paths) {
                    for(local i = 0; i < 20; i++) {
                        local item = this.new(path);
                        // Exercise the actual hooked tooltip helper without needing a campaign.
                        local probe = {m = item.m,
                            getTooltip = function() { return [{id=1,type="title",text="engine-test"}]; },
                            isChangeableInBattle = function() { return false; },
                            isItemType = function(t) { return (this.m.ItemType & t) != 0; }};
                        local sequence = ::BBMODItemInspector.Sequence;
                        local tooltip = this.new("scripts/ui/screens/tooltip/modules/tooltip");
                        tooltip.setOnQueryUIItemTooltipDataListener(function(a,b,c) {
                            return ::TooltipEvents.tactical_helper_addHintsToTooltip(null,null,probe,"stash");
                        });
                        local result = tooltip.bbmodInspectorQuery([null,1,"stash",sequence + 1]);
                        if (::BBMODItemInspector.Sequence != sequence + 1 || result[0].text != "engine-test")
                            throw "The real tooltip bridge did not run";
                    }
                }
                ::logInfo("BBMOD_INSPECTOR_ENGINE_PASS");
            } catch(error) { ::logError("BBMOD_INSPECTOR_ENGINE_FAIL " + error); }
            this.finish();
        };
    });'''.replace('PATHS', json.dumps(scripts))
    test_mod = folder / 'data/mod_zz_bbmod_inspector_test.zip'
    with zipfile.ZipFile(test_mod, 'w') as archive:
        archive.writestr('scripts/!mods_preload/zz_bbmod_inspector_test.nut', bootstrap)
    originals = {}
    logs = []
    for directory in find_log_write_paths():
        if not directory.exists(): continue
        logs.append(directory / 'log.html')
        for path in directory.iterdir():
            if path.is_file() and (path.name.startswith('log') or path.name.startswith('config')):
                originals[path] = path.read_bytes()
                (out / (str(len(originals)) + '-' + path.name)).write_bytes(originals[path])
    process = None
    try:
        startup = subprocess.STARTUPINFO(); startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW; startup.wShowWindow = 0
        process = subprocess.Popen([str(game.exe)], cwd=game.exe.parent, startupinfo=startup,
                                   creationflags=subprocess.CREATE_NO_WINDOW)
        deadline = time.monotonic() + 50
        while process.poll() is None and time.monotonic() < deadline: time.sleep(.25)
        if process.poll() is None: raise TimeoutError('Isolated engine did not finish in 50 seconds')
        print('isolated_process_exit', process.returncode, flush=True)
        all_rows = []
        for i, path in enumerate(logs):
            if path.exists() and path.read_bytes() != originals.get(path):
                shutil.copy2(path, out / f'engine-{i}.html')
                all_rows += [str(row.text) for row in load_log(path)]
        assert any('BBMOD_INSPECTOR_ENGINE_PASS' in row for row in all_rows), '\n'.join(all_rows[-25:])
        events = [json.loads(row.split(MARKER, 1)[1]) for row in all_rows if MARKER in row]
        invalid = []
        for event in events:
            result = appraise(event)
            if not result.get('valid'):
                invalid.append({'event': event, 'result': result})
        report = {'events': len(events), 'types': len({x['id'] for x in events}), 'invalid': invalid,
                  'rounding': [row for row in all_rows if 'BBMOD_ROUND' in row], 'no_campaign_loaded': True}
        (out / 'result.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps({k: v if k != 'invalid' else len(v) for k,v in report.items()}, ensure_ascii=False))
        assert len(events) == 1880 and not invalid
    finally:
        if process and process.poll() is None:
            process.terminate(); process.wait(timeout=10)
        test_mod.unlink(missing_ok=True)
        (game.exe.parent / 'steam_appid.txt').unlink(missing_ok=True)
        if not is_game_running():
            for path, raw in originals.items(): path.write_bytes(raw)


if __name__ == '__main__': main()

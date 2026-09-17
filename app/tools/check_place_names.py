"""Exercise packaged name generation in the offline Squirrel interpreter.

Only the original and patched bytecode functions run with small engine stubs;
BattleBrothers.exe is never started and no save is read or written.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.full_l10n import load_full_catalog
from core.place_names import load_policy, POOL_ENTRY, original_names
from core.l10n import UI_ROOT

WORK = ROOT / 'build/full-l10n'


def main():
    package = WORK / 'preview-package/mod_bbmod_zhcn.zip'
    policy = load_policy(load_full_catalog())
    target = WORK / 'place-name-validation'
    target.mkdir(exist_ok=True)
    original = WORK / 'plain'
    patched = WORK / 'preview-validation'
    def quote(path):
        return json.dumps(str(path.resolve()).replace('\\', '/'))
    harness = '''
::Const <- { Strings = {}, World = {} };
::Time <- { getVirtualTimeF = function() { return 0.0; } };
::rng <- 1; ::calls <- 0;
::Math <- { rand = function(lo, hi) { ::calls++; ::rng = (::rng * 31 + 7) % 1000003; return lo + ::rng % (hi-lo+1); } };
::replaceAll <- function(value, from, to) {
    local start = 0; local pos;
    while ((pos = value.find(from, start)) != null) {
        value = value.slice(0,pos) + to + value.slice(pos+from.len()); start = pos+to.len();
    }
    return value;
};
::buildTextFromTemplate <- function(value, vars) {
    foreach (pair in vars) value = replaceAll(value, "%" + pair[0] + "%", pair[1]);
    return value;
};
'''
    harness += 'dofile(' + quote(original / 'scripts/config/character_names.cnut') + ');\n'
    harness += 'local originalCharacters = clone Const.Strings.CharacterNames; local originalKnights = clone Const.Strings.KnightNames;\n'
    harness += 'dofile(' + quote(original / 'scripts/config/world_location_names.cnut') + ');\n'
    harness += 'dofile(' + quote(original / 'scripts/entity/world/entity_manager.cnut') + ');\n'
    harness += 'local baseline = entity_manager; baseline.setdelegate(getroottable());\n'
    harness += 'dofile(' + quote(patched / 'scripts/config/character_names.cnut') + ');\n'
    harness += 'local localizedCharacters = Const.Strings.CharacterNames; local localizedKnights = Const.Strings.KnightNames;\n'
    harness += 'dofile(' + quote(patched / POOL_ENTRY) + ');\n'
    harness += '''
assert(Const.Strings.CharacterNames[0] != originalCharacters[0]);
assert(Const.Strings.BBMODPlaceCharacterNames.len() == originalCharacters.len());
assert(Const.Strings.BBMODPlaceKnightNames.len() == originalKnights.len());
foreach (i, n in originalCharacters) assert(Const.Strings.BBMODPlaceCharacterNames[i] == n);
foreach (i, n in originalKnights) assert(Const.Strings.BBMODPlaceKnightNames[i] == n);
'''
    harness += 'dofile(' + quote(patched / 'scripts/entity/world/entity_manager.cnut') + ');\n'
    harness += 'local modified = entity_manager; modified.setdelegate(getroottable());\n'
    harness += '''
local tested = 0;
foreach (pool in Const.World.LocationNames) {
    foreach (template in pool) {
        for (local seed = 1; seed <= 5; seed++) {
            Const.Strings.CharacterNames = originalCharacters; Const.Strings.KnightNames = originalKnights;
            ::rng = seed; ::calls = 0;
            local expected = baseline.getUniqueLocationName([template]);
            local expectedCalls = ::calls;
            Const.Strings.CharacterNames = localizedCharacters; Const.Strings.KnightNames = localizedKnights;
            ::rng = seed; ::calls = 0;
            local actual = modified.getUniqueLocationName([template]);
            assert(actual == expected); assert(::calls == expectedCalls);
            assert(buildTextFromTemplate("Travel to %destination%.", [["destination",actual]]) == "Travel to " + expected + ".");
            tested++;
        }
    }
}
assert(Const.Strings.CharacterNames == localizedCharacters);
assert(Const.Strings.KnightNames == localizedKnights);
print("BBMOD_NAMES_PASS " + tested + "\\n");
'''
    file = target / 'check.nut'
    file.write_text(harness, encoding='ascii')
    result = subprocess.run([str(WORK / 'tools/bin/sq.exe'), str(file)], capture_output=True, timeout=30)
    if result.returncode or b'BBMOD_NAMES_PASS ' not in result.stdout or result.stderr:
        raise RuntimeError((result.stdout + result.stderr).decode(errors='replace'))
    tested = int(result.stdout.split(b'BBMOD_NAMES_PASS ')[1].split()[0])
    with zipfile.ZipFile(package) as z:
        dictionary = json.loads(z.read(UI_ROOT + 'dictionary.js').decode().partition(' = ')[2].rstrip(';\n'))
        names = original_names(load_full_catalog(), policy)
        assert all(dictionary[name.strip()] == name.strip() for name in names)
        assert dictionary['New Campaign'] != 'New Campaign'
        # Use the packaged UI code to exercise rendered contract text without a
        # browser or a running BBMOD process. It must keep names in prose too.
        (target / 'dictionary.js').write_bytes(z.read(UI_ROOT + 'dictionary.js'))
        (target / 'runtime.js').write_bytes(z.read(UI_ROOT + 'runtime.js'))
    checker = target / 'check.cjs'
    checker.write_text('''const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const sandbox={window:{}};vm.createContext(sandbox);
for(const name of ['dictionary.js','runtime.js']) vm.runInContext(fs.readFileSync(__dirname+'/'+name,'utf8'),sandbox);
const t=sandbox.window.BBMODL10N.translate;
for(const name of ['Wiesendorf','Stormy Sea','Icy Cave','Black Monolith']) {
 assert.equal(t(name),name);assert.equal(t('护送商队前往'+name+'，随后返回。'),'护送商队前往'+name+'，随后返回。');
 assert.equal(t('前往 [color=#ffffff]'+name+'[/color]'),'前往 [color=#ffffff]'+name+'[/color]');
}
assert.notEqual(t('New Campaign'),'New Campaign');console.log('BBMOD_UI_NAMES_PASS');
''', encoding='utf-8')
    ui = subprocess.run(['node', str(checker)], capture_output=True, timeout=15, check=True)
    assert b'BBMOD_UI_NAMES_PASS' in ui.stdout
    report = {'package_sha256': hashlib.sha256(package.read_bytes()).hexdigest(),
              'place_name_policy_sha256': hashlib.sha256((ROOT / 'localization/place_names.json').read_bytes()).hexdigest(),
              'place_name_policy': 'original_english', 'geographic_entries': len(names),
              'original_name_generation_cases': tested, 'random_call_counts_unchanged': True,
              'character_names_remain_localized': True, 'packaged_ui_name_preservation': 'passed',
              'game_started': False, 'existing_save_migration': False, 'game_acceptance': 'pending'}
    (target / 'validation.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()

"""Execute real packaged battle-result bytecode and then its display assets."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
from core.cnut import Cnut

WORK = APP / 'build/full-l10n'
FILE = 'scripts/states/tactical_state.cnut'

HARNESS = r'''
::fixture <- {round=1, outcome=0};
::Const <- {Combat={MiasmaTimeout=3.0,FireTimeout=2.0,SmokeTimeout=2.0},
    Tactical={CombatResult={EnemyDestroyed=0,EnemyRetreated=1,PlayerDestroyed=2,PlayerRetreated=3}}};
::Tactical <- {
    TurnSequenceBar={getCurrentRound=function(){return ::fixture.round;}},
    Entities={getCombatResult=function(){return ::fixture.outcome;}}
};
::inherit <- function(parent,members){members.setdelegate(getroottable());return members;};
::emit <- function(key,text){
    local raw=""; foreach(byte in text) raw+=format("%02x",byte & 255);
    print(key+"|"+raw+"\n");
};
'''


def run(script, target, label):
    quoted = json.dumps(str(script.resolve()).replace('\\', '/'))
    code = HARNESS + f'dofile({quoted});\n' + r'''
tactical_state.m.Scenario = {}; // Offline scenario: do not touch achievements.
for(local outcome=0; outcome<4; outcome++) {
    fixture.outcome=outcome;
    foreach(round in [1,2,15]) {
        fixture.round=round;
        local result=tactical_state.tactical_combat_result_screen_onQueryCombatInformation();
        local key=outcome+"."+round;
        emit(key+".title",result.title); emit(key+".subtitle",result.subTitle);
        emit(key+".flags",result.result+"/"+result.loot+"/"+result.arena);
    }
}
print("BBMOD_DYNAMIC_PASS\n");
'''
    harness = target / (label + '.nut')
    harness.write_text(code, encoding='utf-8')
    result = subprocess.run([str(WORK / 'tools/bin/sq.exe'), str(harness)], capture_output=True, timeout=30)
    output = (result.stdout + result.stderr).decode('utf-8', errors='replace')
    assert result.returncode == 0 and 'BBMOD_DYNAMIC_PASS' in output and not result.stderr, output[-3000:]
    return {key: bytes.fromhex(raw).decode('utf-8') for key, raw in
            (line.split('|', 1) for line in output.splitlines() if '|' in line)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    patched = args.output / 'tactical_state.cnut'
    ui = args.output / 'ui'
    ui.mkdir(exist_ok=True)
    with zipfile.ZipFile(args.package) as archive:
        patched.write_bytes(archive.read(FILE))
        for name in ['dictionary.js', 'runtime.js', 'place_names.js', 'name_forms.js']:
            (ui / name).write_bytes(archive.read('ui/mods/bbmod_l10n/' + name))
    subprocess.run([str(WORK / 'tools/bin/bbsq.exe'), '-d', str(patched)], capture_output=True, check=True, timeout=30)
    original = run(WORK / 'plain' / FILE, args.output, 'original')
    current = run(patched, args.output, 'translated')
    labels = ['敌军被歼灭，历时', '敌军撤退，历时', '战斗失败，历时', '我方撤退，历时']
    for outcome, prefix in enumerate(labels):
        for round in [1, 2, 15]:
            key = f'{outcome}.{round}'
            assert original[key + '.subtitle'].endswith('round' + ('s' if round > 1 else ''))
            assert current[key + '.subtitle'] == prefix + str(round) + ' 回合'
            assert current[key + '.flags'] == original[key + '.flags']
    # The other literal "s" is a banner-size identifier and must survive.
    with zipfile.ZipFile(args.package) as archive:
        contract = Cnut(archive.read('scripts/contracts/contract.cnut'), encrypted=True)
    assert 's' in next(f['literals'] for f in contract.functions if f['name'] == 'getBanner')
    result = subprocess.run(['node', str(APP / 'tests/dynamic_text.test.cjs'), str(ui)], capture_output=True, timeout=45)
    output = (result.stdout + result.stderr).decode('utf-8', errors='replace')
    assert result.returncode == 0, output[-4000:]
    report = {'package_sha256': hashlib.sha256(args.package.read_bytes()).hexdigest(),
              'battle_result_cases': 12, 'outcomes_and_loot_flags': 'unchanged',
              'banner_size_key': 'unchanged', 'native_execution': 'passed',
              'browser_dom': output, 'game_started': False, 'game_visual_acceptance': 'pending',
              'texts': {key: {'source': original[key], 'translation': current[key]} for key in original}}
    (args.output / 'validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k != 'texts'}, ensure_ascii=False))


if __name__ == '__main__':
    main()

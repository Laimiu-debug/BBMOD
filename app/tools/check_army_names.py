"""Verify packaged army-name changes against official archives and execute the pools."""
import argparse
from contextlib import ExitStack
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
from core.cnut import Cnut
from core.cnut_semantics import protected_literals
from core.place_names import allowed_pool_change


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('package', 'game', 'modkit', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    counts = {'scripts': 0, 'functions': 0, 'protected_literals': 0}
    noble_sites = 0
    with ExitStack() as stack:
        package = stack.enter_context(zipfile.ZipFile(args.package))
        assert package.testzip() is None
        archives = {}
        for row in json.loads(package.read('BBMOD_TEXT_SOURCES.json')):
            file = row['file']
            if not file.endswith('.cnut'):
                continue
            if row['archive'] not in archives:
                archives[row['archive']] = stack.enter_context(zipfile.ZipFile(args.game / 'data' / row['archive']))
            source = archives[row['archive']].read(file)
            assert hashlib.sha256(source).hexdigest() == row['source_sha256']
            old, new = Cnut(source, encrypted=True), Cnut(package.read(file), encrypted=True)
            assert len(old.functions) == len(new.functions)
            for a, b in zip(old.functions, new.functions):
                assert all(a[k] == b[k] for k in ('path', 'source', 'name', 'instructions'))
                assert len(a['literals']) == len(b['literals'])
                for index, value in enumerate(a['literals']):
                    target = b['literals'][index]
                    if not isinstance(value, str):
                        assert value == target
                    if value == ' Company':
                        assert target == ' 军队', (file, target)
                        noble_sites += 1
                for index in protected_literals(a):
                    x, y = a['literals'][index], b['literals'][index]
                    assert x == y or allowed_pool_change(file, a['name'], x, y)
                    counts['protected_literals'] += 1
                counts['functions'] += 1
            counts['scripts'] += 1
        assert noble_sites >= 14
        file = 'scripts/config/strings.cnut'
        pool_results = {}
        for label, raw in [('original', archives['data_001.dat'].read(file)), ('packaged', package.read(file))]:
            target = args.output / (label + '.cnut')
            target.write_bytes(raw)
            subprocess.run([str(args.modkit / 'bbsq.exe'), '-d', str(target)], check=True, capture_output=True)
            # Color constants only support unrelated perk descriptions in the
            # same actual config script; no army names are supplied by the stub.
            code = '::Const <- { UI = { Color = { PositiveValue="a", NegativeValue="b", DamageValue="c" } } };\ndofile(' + json.dumps(target.resolve().as_posix()) + ');\n'
            code += '''function emit(kind, name) {
                local hex=""; foreach(b in name) hex += format("%02x", b & 255);
                print(kind+"|"+hex+"\\n");
            }
            foreach(name in Const.Strings.MercenaryCompanyNames) emit("company", name);
            foreach(pool in Const.Strings.TerrainRegionNames) foreach(name in pool) emit("terrain", name);
            print("ARMY_NAMES_PASS\\n");
            '''
            runner = args.output / (label + '.nut')
            runner.write_text(code, 'utf-8')
            result = subprocess.run([str(args.modkit / 'sq.exe'), str(runner)], capture_output=True, timeout=30)
            stdout = result.stdout.decode('utf-8')
            assert result.returncode == 0 and not result.stderr and 'ARMY_NAMES_PASS' in stdout, (stdout[-2000:], result.stderr)
            pool_results[label] = {'company': [], 'terrain': []}
            for line in stdout.splitlines():
                if '|' in line:
                    kind, encoded = line.split('|', 1)
                    pool_results[label][kind].append(bytes.fromhex(encoded).decode('utf-8'))
        assert len(pool_results['original']['company']) == len(pool_results['packaged']['company']) == 57
        assert pool_results['original']['terrain'] == pool_results['packaged']['terrain']
        (args.output / 'pools.json').write_text(json.dumps(pool_results, ensure_ascii=False, indent=2), 'utf-8')
        ui = args.output / 'ui'; ui.mkdir(exist_ok=True)
        for name in ('dictionary.js', 'place_names.js', 'name_forms.js', 'runtime.js', 'map_labels.js'):
            (ui / name).write_bytes(package.read('ui/mods/bbmod_l10n/' + name))
    report = {**counts, 'noble_name_sites': noble_sites,
              'package_sha256': hashlib.sha256(args.package.read_bytes()).hexdigest(),
              'instruction_and_program_literals_check': 'passed', 'native_pool_execution': 'passed',
              'mercenary_pool_count': 57, 'canonical_terrain_names_unchanged': True,
              'game_installation_modified': False, 'game_visual_acceptance': 'not_run'}
    (args.output / 'native-validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), 'utf-8')
    print(json.dumps(report))


if __name__ == '__main__':
    main()

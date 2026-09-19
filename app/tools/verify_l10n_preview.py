"""Check exactly the scripts in the current preview, including protected keys."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.cnut import Cnut
from core.cnut_semantics import protected_literals
from core.place_names import POOL_ENTRY, POOL_FILE, allowed_pool_change, load_policy
from core.full_l10n import load_full_catalog
from core.l10n_compat import hooks_assets, DISPLAY_ONLY_FILES
from tools.translate_full_catalog import WORK


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', type=Path, default=WORK/'preview-package/mod_bbmod_zhcn.zip')
    parser.add_argument('--output', type=Path, default=WORK/'preview-validation')
    args = parser.parse_args()
    package, target = args.package, args.output
    target.mkdir(parents=True, exist_ok=True)
    scripts, javascript = [], []
    vendor = hooks_assets()
    with zipfile.ZipFile(package) as z:
        assert not (set(z.namelist()) & DISPLAY_ONLY_FILES)
        for name, expected in vendor.items():
            assert z.read(name) == expected, name
        for name in z.namelist():
            if not name.startswith(('scripts/', 'ui/')) or not name.endswith(('.cnut', '.js')): continue
            p = target / name
            assert p.resolve().is_relative_to(target.resolve())
            p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(z.read(name))
            (scripts if name.endswith('.cnut') else javascript).append(p)
    for start in range(0, len(scripts), 40):
        subprocess.run([str(WORK / 'tools/bin/bbsq.exe'), '-d', *map(str, scripts[start:start + 40])],
                       capture_output=True, check=True, timeout=60)
        if start % 400 == 0: print(f'Native reader: {start}/{len(scripts)}', flush=True)
    functions = changes = keys = 0
    pool_changes = []
    for p in scripts:
        relative = p.relative_to(target).as_posix()
        if relative in vendor:
            # Framework logic is third-party, checked byte-for-byte above. It
            # must not be described as an unchanged original game function.
            Cnut(p.read_bytes())
            continue
        if relative == POOL_ENTRY:
            expected = Cnut(POOL_FILE.read_bytes(), encrypted=True)
            actual = Cnut(p.read_bytes())
            assert len(actual.functions) == len(expected.functions) == 1
            assert all(a['literals'] == b['literals'] and a['instructions'] == b['instructions']
                       for a, b in zip(actual.functions, expected.functions))
            continue
        original = Cnut((WORK / 'plain' / p.relative_to(target)).read_bytes())
        translated = Cnut(p.read_bytes())
        assert len(original.functions) == len(translated.functions)
        for a, b in zip(original.functions, translated.functions):
            assert all(a[k] == b[k] for k in ['path', 'source', 'name', 'instructions'])
            assert len(a['literals']) == len(b['literals'])
            for index in protected_literals(a):
                x, y = a['literals'][index], b['literals'][index]
                if x != y:
                    assert allowed_pool_change(relative, a['name'], x, y), (p, a['name'], x, y)
                    pool_changes.append({'file': relative, 'function': a['name'], 'source': x, 'target': y})
                keys += 1
            for x, y in zip(a['literals'], b['literals']):
                if not isinstance(x, str): assert x == y
                elif x != y: changes += 1
            functions += 1
    assert len(pool_changes) == 2, pool_changes
    catalog = load_full_catalog()
    policy = load_policy(catalog)
    retained = 0
    for name in policy['source_files']:
        original = Cnut((WORK / 'plain' / name).read_bytes())
        translated = Cnut((target / name).read_bytes())
        positions = {lit.start: lit for lit in original.literals}
        translations = {(lit.function, lit.index): lit.text for lit in translated.literals}
        for site in (s for s in policy['sites'] if s['file'] == name):
            lit = positions[site['start']]
            assert translations[lit.function, lit.index] == lit.text
            retained += 1
    inputs = target / 'js-paths.json'; inputs.write_text(json.dumps(list(map(str, javascript))), encoding='utf-8')
    checker = target / 'check-js.cjs'
    checker.write_text('const fs=require("node:fs"),vm=require("node:vm");for(const p of JSON.parse(fs.readFileSync(process.argv[2],"utf8")))new vm.Script(fs.readFileSync(p,"utf8"),{filename:p});', encoding='utf-8')
    subprocess.run(['node', str(checker), str(inputs)], check=True, capture_output=True)
    report = {'package_sha256': hashlib.sha256(package.read_bytes()).hexdigest(), 'scripts': len(scripts),
              'functions': functions, 'changed_literals': changes, 'protected_literals': keys,
              'javascript_files': len(javascript), 'native_squirrel_reader': 'passed',
              'instructions_unchanged': True, 'program_literals_unchanged': not pool_changes,
              'program_literals_validated': True, 'intentional_place_owner_lookups': pool_changes,
              'independent_data_scripts': [POOL_ENTRY], 'place_name_literals_preserved': retained,
              'framework_files_verified': {name: hashlib.sha256(raw).hexdigest() for name, raw in vendor.items()},
              'runtime_translated_screens': sorted(DISPLAY_ONLY_FILES),
              'place_name_policy': 'original_english',
              'javascript_parse': 'passed', 'game_visual_acceptance': 'pending'}
    (package.parent / 'validation.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report), flush=True)


if __name__ == '__main__': main()

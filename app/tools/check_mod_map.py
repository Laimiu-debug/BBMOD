"""Validate the ordinary MOD map renderer offline; never launch the game."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.place_display import read_packaged_display


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=ROOT/'build/mod-map-check')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    read_packaged_display(args.package)
    with zipfile.ZipFile(args.package) as archive:
        manifest = json.loads(archive.read('BBMOD_L10N.json'))
        assert not manifest.get('requires_bbmod_launcher') and not manifest.get('uses_bbmod_map_font')
        assert not any(name.lower().endswith(('.exe', '.dll')) for name in archive.namelist())
        for name in ('dictionary.js', 'place_names.js', 'name_forms.js', 'runtime.js', 'map_labels.js'):
            (args.output/name).write_bytes(archive.read('ui/mods/bbmod_l10n/' + name))
        (args.output/'mod_hooks.js').write_bytes(archive.read('ui/mod_hooks.js'))
        (args.output/'map_labels.nut').write_bytes(archive.read('scripts/!mods_preload/bbmod_map_labels.nut'))
        html = archive.read('ui/main.html').decode('utf-8')
        order = [html.index(name) for name in ('screens/world/world_screen.js', 'mod_hooks.js',
                 'mods/bbmod_l10n/dictionary.js', 'mods/bbmod_l10n/name_forms.js', 'mods/bbmod_l10n/place_names.js',
                 'mods/bbmod_l10n/runtime.js', 'mods/bbmod_l10n/map_labels.js', '</head>')]
        assert order == sorted(order)
    checks = {}
    for name in ('place_display', 'map_labels'):
        result = subprocess.run(['node', str(ROOT/'tests'/f'{name}.test.cjs'),
            str(ROOT/'build/browser-check/node_modules/jsdom'), str(args.output)], capture_output=True, timeout=45)
        (args.output/f'{name}.log').write_bytes(result.stdout + result.stderr)
        if result.returncode:
            raise RuntimeError((result.stdout + result.stderr).decode(errors='replace'))
        checks[name] = json.loads(result.stdout.decode().splitlines()[-1])
    result = subprocess.run([str(ROOT/'build/full-l10n/tools/bin/sq.exe'),
        str(ROOT/'tests/map_labels_harness.nut'), str((args.output/'map_labels.nut').resolve())],
        capture_output=True, timeout=20)
    (args.output/'squirrel.log').write_bytes(result.stdout + result.stderr)
    if result.returncode or result.stderr or b'BBMOD_MOD_MAP_PASS' not in result.stdout:
        raise RuntimeError((result.stdout + result.stderr).decode(errors='replace'))
    report = {'package_sha256': hashlib.sha256(args.package.read_bytes()).hexdigest(),
        'checks': checks, 'squirrel_render_and_restore': 'passed', 'native_components_included': False,
        'game_started': False, 'game_acceptance': 'pending', 'defender_behavior_acceptance': 'pending'}
    (args.output/'validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()

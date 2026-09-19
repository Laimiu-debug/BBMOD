"""Audit every catalog entry through the packaged display adapter, offline.

Checks format/variables and residual English after geographic/name conversion.
This does not replace editorial review or playthroughs of composed game scenes.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
from core.full_l10n import FULL_CATALOG_FILE, load_full_catalog
from core.l10n import translated_catalog
from core.l10n_tokens import ALLOWED_UI_WORDS, validate_translation
from core.place_names import load_policy, preserve_inline_names


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.package) as archive:
        manifest = json.loads(archive.read('BBMOD_L10N.json'))
        assert manifest['full_catalog_sha256'] == hashlib.sha256(FULL_CATALOG_FILE.read_bytes()).hexdigest()
        assert manifest['overrides_applied'] == 0, 'Audit custom overrides separately.'
        for name in ['dictionary.js', 'place_names.js', 'name_forms.js', 'runtime.js']:
            (args.output / name).write_bytes(archive.read('ui/mods/bbmod_l10n/' + name))
    catalog = load_full_catalog()
    dictionary = translated_catalog()
    entries = preserve_inline_names({key: {**entry, 'translation': dictionary[entry['source']]}
                                    for key, entry in catalog['entries'].items()}, load_policy(catalog))
    inputs, format_issues, categories = [], [], Counter()
    for key, entry in entries.items():
        categories[entry['category']] += 1
        issues = validate_translation(entry['source'], entry['translation'])
        if issues:
            format_issues.append({'id': key, 'issues': issues})
        credited = entry.get('preserved_attribution') or any(
            c['file'] == 'scripts/config/credits.cnut' for c in entry['contexts'])
        inputs.append({'id': key, 'text': entry['translation'], 'credit': bool(credited)})
    (args.output / 'inputs.json').write_text(json.dumps({
        'entries': inputs, 'allowed': sorted(ALLOWED_UI_WORDS | {'End'})}, ensure_ascii=True), encoding='utf-8')
    result = subprocess.run(['node', str(APP / 'tests/catalog_display.test.cjs'), str(args.output.resolve())],
                            capture_output=True, timeout=60)
    output = (result.stdout + result.stderr).decode('utf-8', errors='replace')
    (args.output / 'browser.log').write_text(output, encoding='utf-8')
    assert result.returncode == 0, output[-3500:]
    display = json.loads((args.output / 'display.json').read_text(encoding='utf-8'))
    report = {'package_sha256': hashlib.sha256(args.package.read_bytes()).hexdigest(),
              'entries': len(entries), 'categories': categories, 'format_issues': format_issues,
              **display, 'game_started': False, 'full_editorial_review': False,
              'scope': 'Static catalog text rendered through packaged UI; dynamic variables and scene branches require separate checks.'}
    (args.output / 'validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k != 'findings'}, ensure_ascii=False))
    assert not format_issues and not report['findings'], report['findings']


if __name__ == '__main__':
    main()

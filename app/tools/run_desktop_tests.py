"""Run each pytest module in a separate process so Qt lifetimes cannot cross suites."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--all', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    names = ['test_mod_file_safety.py', 'test_io_util.py', 'test_profiles_page.py', 'test_online_catalog.py', 'test_localization_profiles.py',
             'test_localization_manager_ui.py', 'test_seed_session.py', 'test_app_updates.py', 'test_update_notice.py']
    paths = sorted((root / 'tests').glob('test_*.py')) if args.all else [root / 'tests' / name for name in names]
    results = []
    for path in paths:
        result = subprocess.run([sys.executable, '-X', 'utf8', '-m', 'pytest', str(path), '-q'],
                                cwd=root, capture_output=True, text=True, encoding='utf-8', errors='replace')
        print(path.name + ': ' + result.stdout.strip().split('\n')[-1], flush=True)
        if result.returncode:
            print(result.stdout + result.stderr, flush=True)
        results.append({'module': path.name, 'exit_code': result.returncode,
                        'passed': sum(map(int, re.findall(r'(\d+) passed', result.stdout))),
                        'skipped': sum(map(int, re.findall(r'(\d+) skipped', result.stdout)))})
    output = root / 'build' / 'desktop-tests.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(results, indent=2), encoding='utf-8')
    print(f"Total: {sum(r['passed'] for r in results)} passed; {sum(r['skipped'] for r in results)} skipped; {sum(bool(r['exit_code']) for r in results)} failed modules")
    return int(any(r['exit_code'] for r in results))


if __name__ == '__main__':
    raise SystemExit(main())

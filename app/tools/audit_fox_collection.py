"""Offline compile/bytecode and optional manager lifecycle checks of prepared MODs.

Use the author's sq.exe and bbsq.exe from https://www.adammil.net/files/133/bbros.zip.
MOD functions are compiled/read, never executed. All file operations use a
temporary game directory; this tool never launches Battle Brothers.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.cnut import Cnut
from core.local_mod_archive import staged_packages
from core.modmanager import ModManager
from core.paths import resource_path


def audit(collection, sq, bbsq, *, node='node', lifecycle=False, only=None):
    manifest = json.loads((collection / '适配清单.json').read_text(encoding='utf-8'))
    results = []
    frameworks = [resource_path('seedgen/payload/mod_hooks.zip')]
    for row in manifest['packages']:
        if any(reg['mod_id'] in {'mod_modern_hooks', 'mod_msu'} for reg in row['registrations']):
            frameworks.append(collection / row['path'])
    for number, row in enumerate(manifest['packages'], 1):
        if only and Path(row['path']).name not in only:
            continue
        source = (collection / row['path']).resolve()
        if not source.is_relative_to(collection.resolve()):
            raise ValueError('适配清单路径越界')
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        if digest != row['sha256']:
            raise ValueError(f'适配包已改变：{source.name}')
        checks = []
        with tempfile.TemporaryDirectory(prefix='bbmod-fox-audit-') as directory:
            temporary = Path(directory)
            validated = temporary / 'validated'; validated.mkdir()
            staged_packages(source, validated)
            commands = []
            with zipfile.ZipFile(source) as archive:
                for name in archive.namelist():
                    suffix = Path(name).suffix.lower()
                    if suffix not in {'.nut', '.cnut', '.js'}:
                        continue
                    raw = archive.read(name)
                    path = temporary / (str(len(checks)) + suffix)
                    path.write_bytes(raw)
                    check = {'entry': name, 'kind': suffix, 'syntax': 'not_run'}
                    if suffix == '.cnut':
                        Cnut(raw, encrypted=True)
                        subprocess.run([str(bbsq), '-d', str(path)], check=True, capture_output=True, timeout=30)
                        check['bytecode'] = 'passed'
                    if suffix == '.js':
                        result = subprocess.run([node, '--check', str(path)], capture_output=True, timeout=30)
                        check['syntax'] = 'passed' if result.returncode == 0 else result.stderr.decode(errors='replace')
                    else:
                        commands.append('try { loadfile(' + json.dumps(path.as_posix()) + '); print("PASS ' +
                            str(len(checks)) + '\\n"); } catch(e) { print("FAIL ' + str(len(checks)) + ' "+e+"\\n"); }')
                    checks.append(check)
            harness = temporary / 'compile.nut'; harness.write_text('\n'.join(commands), encoding='utf-8')
            result = subprocess.run([str(sq), str(harness)], capture_output=True, timeout=60)
            for line in result.stdout.decode(errors='replace').splitlines():
                parts = line.split(' ', 2)
                if len(parts) > 1 and parts[1].isdigit() and parts[0] in {'PASS', 'FAIL'}:
                    checks[int(parts[1])]['syntax'] = 'passed' if parts[0] == 'PASS' else parts[2]
            if any(c['syntax'] != 'passed' for c in checks):
                raise ValueError(f'脚本验证失败：{source.name} {checks}')
            if lifecycle:
                game = temporary / 'game'; (game / 'data').mkdir(parents=True)
                manager = ModManager(game)
                deps = [p for p in frameworks if p.name != source.name]
                if source.name == 'data_fox_zhcn.zip':
                    deps = deps[1:]
                paths = manager.install_many(deps + [source])
                installed = game / 'data' / source.name
                assert hashlib.sha256(installed.read_bytes()).hexdigest() == digest
                manager.save_profile('checked')
                manager.set_enabled_many([p.name for p in paths], False)
                assert not installed.exists()
                manager.apply_profile('checked')
                assert hashlib.sha256(installed.read_bytes()).hexdigest() == digest
                if source in frameworks or source.name == 'data_fox_zhcn.zip':
                    manager.set_enabled_many([p.name for p in paths], False)
                    manager.uninstall(source.name, from_disabled=True)
                else:
                    manager.uninstall(source.name)
                assert not installed.exists()
                assert hashlib.sha256(source.read_bytes()).hexdigest() == digest
            results.append({'name': row['name_cn'], 'package': row['path'], 'sha256': digest,
                            'archive_crc': 'passed', 'scripts': checks,
                            'lifecycle': 'passed' if lifecycle else 'not_run', 'game_tested': False})
        print(f'{number}/{len(manifest["packages"])} PASS {row["name_cn"]}', flush=True)
    return {'packages': results, 'game_tested': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--collection', type=Path, required=True)
    parser.add_argument('--sq', type=Path, required=True)
    parser.add_argument('--bbsq', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--lifecycle', action='store_true')
    parser.add_argument('--package', action='append', help='只复查指定 ZIP，可重复传入')
    args = parser.parse_args()
    result = audit(args.collection, args.sq.resolve(), args.bbsq.resolve(), lifecycle=args.lifecycle, only=args.package)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()

"""Prepare a separate, reproducible local collection; never modify the originals.

python tools/prepare_fox_collection.py --source <folder> --output <new-folder>
The reviewed input hashes are bundled with the application. This is a local
adaptation tool, not a third-party MOD redistribution or gameplay certification.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.modinfo import analyze_zip
from core.modstore import load_index
from core.paths import resource_path


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def zip_bytes(files):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, raw in sorted(files.items()):
            entry = zipfile.ZipInfo(name, (2026, 9, 27, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, raw)
    return stream.getvalue()


def prepare(source, output, seven_zip):
    source, output = source.resolve(), output.resolve()
    if output == source or output.is_relative_to(source) or source.is_relative_to(output):
        raise ValueError('适配输出必须在原合集之外，原包始终保留。')
    reviewed = json.loads(resource_path('data/fox_collection.json').read_text(encoding='utf-8'))
    inputs = sorted(p for p in source.rglob('*') if p.suffix.lower() in {'.zip', '.rar'})
    expected = {row['source_name']: row for row in reviewed}
    if {p.name for p in inputs} != set(expected) or len(inputs) != len(expected):
        raise ValueError('合集文件与已审查清单不一致，请重新审核后再生成。')
    for path in inputs:
        if sha(path.read_bytes()) != expected[path.name]['source_sha256']:
            raise ValueError(f'原包已变化，停止自动适配：{path.name}')
    output.mkdir(parents=True, exist_ok=True)
    rows, index = [], load_index()
    for path in inputs:
        recipe = expected[path.name]
        if path.suffix.lower() == '.rar':
            member = 'scripts/!mods_preload/mod_davkul_hotkey.nut'
            result = subprocess.run([str(seven_zip), 'x', '-so', str(path), member],
                                    capture_output=True, check=True, timeout=30)
            if len(result.stdout) != 3938 or sha(result.stdout) != recipe['member_sha256']:
                raise ValueError('RAR 内部脚本与审核版本不一致。')
            files = {member: result.stdout}
        else:
            with zipfile.ZipFile(path) as archive:
                bad = archive.testzip()
                if bad:
                    raise ValueError(f'CRC 校验失败：{path.name}/{bad}')
                files = {entry.filename: archive.read(entry) for entry in archive.infolist() if not entry.is_dir()}
        nested = [(name, raw) for name, raw in files.items() if name.lower().endswith('.zip')]
        for name, raw in nested:
            del files[name]
            if recipe.get('split_quickswap'):
                with zipfile.ZipFile(io.BytesIO(raw)) as child:
                    child_files = {e.filename: child.read(e) for e in child.infolist() if not e.is_dir()}
                child_recipe = {'install_name': 'mod_fox_quickly_swap_items.zip',
                    'name_cn': '快速切换道具（兼容控制宠物）', 'category': '基础功能',
                    'note': '从 EIMO 内层包分离，可单独启停和卸载。', 'tags': [],
                    'source_name': path.name + ' / ' + name, 'source_sha256': sha(raw)}
                rows.append(write_package(output, child_files, child_recipe, index))
        if recipe.get('normalize_tabard_version'):
            name = 'scripts/!mods_preload/!mod_sarisofoi_company_tabards.nut'
            old = b'1.5.2024'
            if files[name].count(old) != 1:
                raise ValueError('军团外套版本标记不匹配。')
            # The shipped Squirrel 3 compiler reads 1.5.2024 as float 1.5.
            # Spell the same effective value explicitly; do not change behavior.
            files[name] = files[name].replace(old, b'1.5')
        # A source script shadows its compiled twin. Keep only the source that
        # was actually effective, so preload enumeration cannot load both.
        for name in list(files):
            if name.endswith('.cnut') and name[:-5] + '.nut' in files:
                del files[name]
        if recipe.get('arena_source_compat'):
            # The old compiled override loses to Fox's arena_contract.nut.
            # Apply its seven cooldown removals to the matching reviewed Fox
            # script. All other source bytes, including translations, remain.
            fox = next(p for p in inputs if expected[p.name]['category'] == '汉化')
            with zipfile.ZipFile(fox) as archive:
                name = 'scripts/contracts/contracts/arena_contract.nut'
                text = archive.read(name)
            calls = [b'this.Contract.getHome().getBuilding("building.arena").refreshCooldown();',
                     b'this.m.Home.getBuilding("building.arena").refreshCooldown();']
            if [text.count(call) for call in calls] != [6, 1]:
                raise ValueError('竞技场冷却逻辑与已审查版本不一致。')
            for call in calls:
                text = text.replace(call, b'')
            files.pop('scripts/contracts/contracts/arena_contract.cnut')
            files[name] = text
        rows.append(write_package(output, files, recipe, index))
    manifest = {'schema': 1, 'source': str(source), 'source_count': len(inputs),
                'package_count': len(rows), 'game_tested': False, 'packages': rows}
    (output / '适配清单.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    return manifest, index


def write_package(output, files, recipe, index):
    files['BBMOD_COLLECTION.json'] = json.dumps({
        'schema': 1, 'source_name': recipe['source_name'], 'source_sha256': recipe['source_sha256'],
        'name_cn': recipe['name_cn'], 'note': recipe['note'], 'game_tested': False,
    }, ensure_ascii=False, indent=2).encode('utf-8')
    folder = {'框架': '框架', '汉化': '汉化二选一', '作弊': '可选作弊', '基础功能': '基础功能'}[recipe['category']]
    path = output / folder / recipe['install_name']
    raw = zip_bytes(files)
    if path.exists() and path.read_bytes() != raw:
        raise FileExistsError(f'输出已被修改，未覆盖：{path}')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    info = analyze_zip(path)
    meta = {key: recipe[key] for key in ('name_cn', 'category', 'note', 'tags')}
    index[path.name] = meta
    index.setdefault(recipe['source_name'], {}).update(meta)
    return {**recipe, 'path': str(path.relative_to(output)), 'sha256': sha(raw),
            'scripts': info.nut_count + info.cnut_count, 'registrations': [vars(r) for r in info.registrations],
            'requirements': info.requirements, 'analysis_errors': info.analysis_errors}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seven-zip', type=Path, default=Path(r'C:\Program Files\7-Zip\7z.exe'))
    parser.add_argument('--write-index', action='store_true')
    args = parser.parse_args()
    manifest, index = prepare(args.source, args.output, args.seven_zip)
    if args.write_index:
        resource_path('data/mod_index.json').write_text(json.dumps(index, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f"{manifest['source_count']} 个原包 → {manifest['package_count']} 个可管理 ZIP；原包未改动。")


if __name__ == '__main__':
    main()

"""Build and verify the single authoritative desktop version without renumbering it."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.version import VERSION, release_filename


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def sources():
    paths = [ROOT / name for name in ('main.py', 'BBMOD.spec', 'requirements.txt', 'requirements-dev.txt')]
    for name in ('core', 'ui', 'data', 'seedgen', 'assets', 'localization'):
        paths.extend(path for path in (ROOT / name).rglob('*')
                     if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc')
    component = ROOT/'build/offline-map/package'
    if (component/'pack.json').is_file():
        paths.extend(path for path in component.rglob('*') if path.is_file())
    return {path.relative_to(ROOT).as_posix(): digest(path) for path in sorted(paths)}


def verify_worldmap_component():
    component = (ROOT/'build/offline-map/package').resolve()
    manifest_path = component/'pack.json'
    if not manifest_path.is_file():
        raise RuntimeError('缺少离线地图组件，请先运行 tools/package_worldmap.py。')
    manifest = json.loads(manifest_path.read_text('utf-8'))
    validation = json.loads((component/'validation.json').read_text('utf-8'))
    camp_validation = json.loads((component/'camp-validation.json').read_text('utf-8'))
    brother_validation = json.loads((component/'brother-validation.json').read_text('utf-8'))
    search_validation = json.loads((component/'campaign-search-validation.json').read_text('utf-8'))
    prefilter_validation = json.loads((component/'prefilter-validation.json').read_text('utf-8'))
    from core.worldmap.engine import Components
    actual = Components(component/'worldmap.exe', component/'runtime.nut', component/'rules').fingerprint()
    if (not validation.get('success') or not camp_validation.get('success')
            or actual != manifest['fingerprint'] or actual != validation['fingerprint']
            or actual != camp_validation['fingerprint']):
        raise RuntimeError('离线地图组件未通过当前版本的原版对照。')
    from core.seedgen.offline import fingerprint as brother_fingerprint
    current_brothers = brother_fingerprint(Components(component/'worldmap.exe', component/'runtime.nut', component/'rules'))
    if (not brother_validation.get('success') or current_brothers != brother_validation['fingerprint']
            or current_brothers != manifest['brother_fingerprint']):
        raise RuntimeError('独立人物解算组件未通过当前版本的原版对照。')
    if (not search_validation.get('success') or current_brothers != search_validation['fingerprint']
            or len(search_validation.get('origins', [])) != 14 or search_validation.get('difficulty_combinations') != 27):
        raise RuntimeError('独立组合搜索组件未通过当前版本的原版起源与难度对照。')
    if (not prefilter_validation.get('success') or current_brothers != prefilter_validation['fingerprint']
            or len(prefilter_validation.get('origins', [])) != 13 or prefilter_validation.get('difficulty_combinations') != 27):
        raise RuntimeError('人物预筛组件未通过当前版本的原版完整开局对照。')
    for name, expected in manifest['files'].items():
        path = (component/name).resolve()
        if not path.is_relative_to(component) or not path.is_file() or digest(path) != expected:
            raise RuntimeError('离线地图组件文件校验失败：'+name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'dist')
    args = parser.parse_args()
    verify_worldmap_component()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    target = output / release_filename()
    manifest_path = output / (target.stem + '.manifest.json')
    inputs = sources()
    if target.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
            if manifest['sources'] == inputs and manifest['sha256'] == digest(target):
                print(json.dumps({'version': VERSION, 'exe': str(target), 'reused': True}))
                return 0
        except (OSError, ValueError, KeyError):
            pass
        parser.error('同版本成品已存在且源码或校验值不同；请为新发布明确升级 VERSION，不覆盖旧文件。')
    work = ROOT / 'build' / 'desktop' / VERSION
    stage = work / 'staged'
    stage.mkdir(parents=True, exist_ok=True)
    lock = work / 'build.lock'
    with lock.open('x', encoding='utf-8') as stream:
        stream.write(VERSION)
    try:
        commands = [
            ('build.log', [sys.executable, '-X', 'utf8', '-m', 'PyInstaller', '--noconfirm', '--clean',
                           '--distpath', str(stage), '--workpath', str(work / 'pyinstaller'), str(ROOT / 'BBMOD.spec')]),
            ('package-check.log', [sys.executable, '-X', 'utf8', str(ROOT / 'tools/package_check.py'),
                                   '--exe', str(stage / target.name), '--report', str(work / 'package-check.json')]),
        ]
        for log_name, command in commands:
            print(f'{log_name}: {work / log_name}', flush=True)
            with (work / log_name).open('wb') as log:
                result = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
            if result.returncode:
                print((work / log_name).read_text(encoding='utf-8', errors='replace')[-6000:])
                return result.returncode
        if sources() != inputs:
            raise RuntimeError('构建期间源码发生变化，请重新验证后打包。')
        built = stage / target.name
        with target.open('xb') as destination, built.open('rb') as source:
            try:
                shutil.copyfileobj(source, destination)
            except BaseException:
                destination.close()
                target.unlink()
                raise
        manifest = {'version': VERSION, 'filename': target.name, 'sha256': digest(target),
                    'size': target.stat().st_size, 'sources': inputs,
                    'package_check': str(work / 'package-check.json')}
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps({'version': VERSION, 'exe': str(target), 'sha256': manifest['sha256'],
                          'manifest': str(manifest_path)}, ensure_ascii=False))
        return 0
    finally:
        lock.unlink()


if __name__ == '__main__':
    raise SystemExit(main())

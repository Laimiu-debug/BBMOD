"""Create an allowlisted server source package. Never includes credentials or uploads."""
import argparse
import hashlib
import io
import json
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VERSION = '0.3.4'
PREFIX = f'BBMOD-Hub-{VERSION}'
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', type=Path, default=ROOT / 'app/build/hub' / VERSION)
args = parser.parse_args()
OUT = args.output.resolve()
OUT.mkdir(parents=True, exist_ok=True)
target = OUT / f'{PREFIX}.tar.gz'
files = [ROOT / '.dockerignore', ROOT / 'app/core/archive_safety.py']
files += [ROOT / 'app' / name for name in ['core/paths.py', 'core/gamelog.py',
    'core/seedgen/config_emitter.py', 'core/seedgen/log_watcher.py', 'core/seedgen/presentation.py',
    'core/seedgen/protocol.py', 'core/seedgen/traits.py', 'core/seedgen/weapons.py', 'data/seed_traits.json']]
web = ROOT / 'web'
for name in ['manage.py', 'requirements.txt', 'requirements.lock', 'requirements-wiki.txt', 'Dockerfile', 'compose.yml', 'compose.https.yml', 'compose.gateway.yml', '.env.example', 'README.md']:
    files.append(web / name)
for folder in ['hub', 'catalog', 'templates', 'static', 'deploy', 'tools', 'vercel', 'content', 'docs']:
    for path in (web / folder).rglob('*'):
        if (path.is_file() and not any(p in {'__pycache__', '.vercel'} for p in path.parts)
                and path.suffix != '.pyc' and path.name != 'seed_preview.py'
                and not path.name.startswith('.env')):
            files.append(path)
manifest = {}
with tarfile.open(target, 'w:gz') as archive:
    for path in sorted(files):
        relative = path.relative_to(ROOT).as_posix()
        data = path.read_bytes()
        manifest[relative] = hashlib.sha256(data).hexdigest()
        info = tarfile.TarInfo(PREFIX + '/' + relative)
        info.size = len(data); info.mode = 0o644
        archive.addfile(info, io.BytesIO(data))
    data = json.dumps({'version': VERSION, 'files': manifest}, indent=2).encode()
    info = tarfile.TarInfo(PREFIX + '/MANIFEST.json'); info.size = len(data)
    archive.addfile(info, io.BytesIO(data))
with tarfile.open(target) as archive:
    for member in archive.getmembers():
        relative = member.name[len(PREFIX) + 1:]
        if relative in manifest:
            assert hashlib.sha256(archive.extractfile(member).read()).hexdigest() == manifest[relative]
        assert not any(p in {'.env', '.preview', '.venv', 'var', 'certs', 'db.sqlite3'} for p in Path(relative).parts)
print(json.dumps({'package': str(target), 'files': len(files), 'sha256': hashlib.sha256(target.read_bytes()).hexdigest()}, ensure_ascii=False))

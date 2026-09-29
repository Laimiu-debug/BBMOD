"""Build a disposable union of active resource manifests in the same transaction."""
from pathlib import Path
import zipfile

FILENAME = 'zzzz_bbmod_preload.zip'
MARKER = 'BBMOD_PRELOAD_MERGE.txt'


def plan(data, changes, staging):
    data = Path(data)
    target = data / FILENAME
    if target.exists():
        try:
            with zipfile.ZipFile(target) as archive:
                owned = archive.read(MARKER) == b'BBMOD generated preload union v1\n'
        except (OSError, KeyError, zipfile.BadZipFile):
            owned = False
        if not owned:
            raise ValueError(f'{FILENAME} 不是本软件生成的文件，请先移出或重命名。')
    packages = {p: p for p in data.glob('*.zip') if p.name != FILENAME}
    for destination, source in changes.items():
        if destination.parent == data and destination.name != FILENAME:
            if source is None:
                packages.pop(destination, None)
            else:
                packages[destination] = source
    manifests = {}
    holders = set()
    # Official resources are retained when a MOD supplies a partial manifest.
    for source in [*sorted(data.glob('data_*.dat')), *packages.values()]:
        try:
            with zipfile.ZipFile(source) as archive:
                for name in archive.namelist():
                    if not name.startswith('preload/') or not name.endswith('.txt'):
                        continue
                    if archive.getinfo(name).file_size > 2 * 1024 * 1024:
                        raise ValueError(f'预载清单过大：{source.name}/{name}')
                    lines = archive.read(name).decode('utf-8-sig').splitlines()
                    manifests.setdefault(name, set()).update(line.strip() for line in lines if line.strip())
                    if Path(source).suffix.lower() != '.dat':
                        holders.add(str(source))
        except zipfile.BadZipFile:
            # Invalid archives are surfaced by MOD validation; they are not manifests.
            continue
    if holders:
        output = Path(staging) / FILENAME
        with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
            for name, lines in sorted(manifests.items()):
                archive.writestr(name, '\n'.join(sorted(lines)) + '\n')
            archive.writestr(MARKER, b'BBMOD generated preload union v1\n')
        changes[target] = output
    elif target.exists():
        changes[target] = None

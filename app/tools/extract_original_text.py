"""Read only official game archives; keep working copies outside the game.

The mod-kit is a compiler tool, never a source of translated game text.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.game import OFFICIAL_ARCHIVES


def main():
    root = Path(sys.argv[1]).resolve()
    out = Path(sys.argv[2]).resolve()
    if out.is_relative_to(root):
        raise ValueError('Working copies must be outside the game')
    out.mkdir(parents=True, exist_ok=True)
    entries = {}
    for archive_name in sorted(OFFICIAL_ARCHIVES):
        archive = root / 'data' / archive_name
        if not archive.is_file():
            continue
        with zipfile.ZipFile(archive) as zf:
            for info in zf.infolist():
                path = Path(info.filename)
                if path.suffix.lower() not in {'.cnut', '.js', '.html', '.css', '.fnt', '.txt'}:
                    continue
                if path.is_absolute() or '..' in path.parts:
                    raise ValueError(info.filename)
                raw = zf.read(info)
                dest = (out / 'original' / path).resolve()
                if not dest.is_relative_to(out):
                    raise ValueError(info.filename)
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(raw)
                entries[info.filename] = {'archive': archive_name, 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}
    (out / 'sources.json').write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding='utf-8')
    compiler = out / 'tools' / 'bin' / 'bbsq.exe'
    files = []
    for name in entries:
        if name.endswith('.cnut'):
            dest = out / 'plain' / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes((out / 'original' / name).read_bytes())
            files.append(dest)
    for i in range(0, len(files), 40):
        subprocess.run([str(compiler), '-d', *map(str, files[i:i + 40])], check=True, capture_output=True, timeout=60)
    print(json.dumps({'files': len(entries), 'scripts': len(files), 'bytes': sum(e['bytes'] for e in entries.values())}))


if __name__ == '__main__':
    main()

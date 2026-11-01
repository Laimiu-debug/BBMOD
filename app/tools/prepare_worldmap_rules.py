"""Development-only extraction of a self-contained, pinned original rule pack.

The runtime reads this pack, never an installed game. This tool is not a
runtime dependency and extracted proprietary scripts stay in ignored build/.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.cnut import Cnut, cipher_block
from core.game import OFFICIAL_ARCHIVES, _inspect_game


def prepare_origin_alignment(output: Path) -> dict:
    """Assemble owned RNG helpers; no installation lookup at solver runtime."""
    payload = Path(__file__).resolve().parents[1]/'seedgen/payload/seed_generator'
    common = (payload/'define_common.nut').read_text('utf-8')
    generate = (payload/'function_generate_brother.nut').read_text('utf-8')
    generate = '\n'.join(line for line in generate.splitlines() if not line.strip().startswith('::include('))
    # The normal payload scopes each module separately; keep those local names.
    source = ('// Generated from BBMOD seedgen helpers. Do not edit.\n::SeedGenerator <- {};\n{\n'
              + common + '\n}\n{\n' + generate
              + '\ngt.SeedGenerator.alignMilitia <- generateMilitiaBrotherFast;\n}\n')
    path = output/'origin_alignment.nut'
    path.write_text(source, encoding='utf-8')
    return dict(sha256=hashlib.sha256(source.encode('utf-8')).hexdigest(), poacher_ammo_draws=True,
                sources=['seedgen/payload/seed_generator/define_common.nut',
                         'seedgen/payload/seed_generator/function_generate_brother.nut'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    game = _inspect_game(args.game)
    if not game or not game.version_ok:
        parser.error('Original 1.5.2.3 installation required for rule extraction')
    missing = [name for name in OFFICIAL_ARCHIVES if not (game.data_dir/name).is_file()]
    if missing:
        parser.error('The pinned all-DLC profile requires: '+', '.join(missing))
    output = args.output.resolve()
    if output.is_relative_to(game.root.resolve()):
        parser.error('Rule pack must be built outside the game')
    files = {}
    for archive_name in sorted(OFFICIAL_ARCHIVES):
        archive = game.data_dir/archive_name
        if not archive.is_file():
            continue
        with zipfile.ZipFile(archive) as z:
            for item in z.infolist():
                name = item.filename
                if not name.endswith('.cnut') or not name.startswith('scripts/'):
                    continue
                dest = (output/name).resolve()
                if not dest.is_relative_to(output):
                    raise ValueError('Archive path escapes pack')
                raw = z.read(item)
                script = Cnut(raw, encrypted=True)
                plain = bytearray(raw)
                for start, length in script.blocks:
                    plain[start:start+length] = cipher_block(raw[start:start+length], decrypt=True)
                Cnut(bytes(plain))
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(plain)
                files[name] = {'archive': archive_name, 'sha256': hashlib.sha256(raw).hexdigest(),
                               'plain_sha256': hashlib.sha256(plain).hexdigest()}
    manifest = {'schema': 1, 'game_version': game.version, 'profile': 'bb-1.5.2.3-all-dlc-v1',
                'dlc_mask': 342, 'files': files, 'origin_alignment': prepare_origin_alignment(output)}
    (output/'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    tiles = sorted(n.removesuffix('.cnut') for n in files if n.startswith('scripts/mapgen/templates/world/tiles/'))
    (output/'index.nut').write_text('::WORLD_MAP_TEMPLATES <- '+json.dumps(tiles)+';\n', encoding='utf-8')
    from prepare_brother_rules import prepare as prepare_brothers
    prepare_brothers(output)
    print(json.dumps({'scripts': len(files), 'tile_templates': len(tiles), 'output': str(output)}))


if __name__ == '__main__':
    main()

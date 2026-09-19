"""Bundle the original artwork referenced by each equipment script.

Statically resolves literal paths and the first original visual variant. No game
code is executed, no game files are written, and no artwork is synthesized.
"""
import argparse
from contextlib import ExitStack
import hashlib
import io
import json
from pathlib import Path
import re
import sys
import zipfile

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.game import OFFICIAL_ARCHIVES


def function(text, name):
    match = re.search(r'\bfunction ' + name + r'\(\)\s*\{(.*?)(?=\n\tfunction |\n\}\);|\n\};)', text, re.S)
    return match[1] if match else ''


def resolve_icons(source, relative):
    texts = []
    while relative:
        text = (source / relative).read_text('utf-8')
        texts.insert(0, text)
        parent = re.search(r'this\.inherit\("([^"]+)"', text)
        relative = parent[1] + '.nut' if parent else ''
    values = {'Variant': 0, 'Faction': 1, 'VariantString': '', 'Icon': '', 'IconLarge': ''}
    classes = {re.search(r'this\.(\w+)\s*<-', text)[1]: index for index, text in enumerate(texts)}

    def expression(raw, body):
        raw = raw.strip()
        if raw.isdigit(): return int(raw)
        random = re.fullmatch(r'this\.Math\.rand\((\d+), (\d+)\)', raw)
        if random: return int(random[1])
        if raw == 'variants[this.Math.rand(0, variants.len() - 1)]':
            return int(re.search(r'local variants = \[\s*(\d+)', body)[1])
        # All supported local aliases are the game's zero-padded variant/faction.
        aliases = {key.lower(): str(values[key]).zfill(2) for key in ('Variant', 'Faction')}
        parts = re.split(r'\s*\+\s*', raw)
        result = ''
        for part in parts:
            if re.fullmatch(r'"[^"\\]*"', part): result += part[1:-1]
            elif part.startswith('this.m.') and part[7:] in values: result += str(values[part[7:]])
            elif part in aliases: result += aliases[part]
            else: raise ValueError('Unsupported icon expression: ' + raw)
        return result

    def update_variant(index):
        implementation = next((i for i in range(index, -1, -1) if function(texts[i], 'updateVariant')), None)
        if implementation is None: return
        body = function(texts[implementation], 'updateVariant')
        operations = r'this\.m\.(Icon|IconLarge)\s*=\s*([^;]+);|this\.(\w+)\.updateVariant\(\);'
        for match in re.finditer(operations, body):
            key, raw, parent = match.groups()
            if key: values[key] = expression(raw, body)
            elif parent in classes and classes[parent] < implementation: update_variant(classes[parent])
            else: raise ValueError('Unsupported icon inheritance: ' + parent)

    for text in texts:
        members = text.split('\n\tfunction ', 1)[0]
        for key, raw in re.findall(r'^\t\t(Variant|VariantString|Faction) = ([^\r\n]+?)(?:,)?\r?$', members, re.M):
            values[key] = expression(raw.rstrip(','), members)
    operations = r'this\.m\.(Variant|VariantString|Faction|Icon|IconLarge)\s*=\s*([^;]+);|this\.updateVariant\(\);'
    for text in texts:
        body = function(text, 'create')
        for match in re.finditer(operations, body):
            key, raw = match.groups()
            if key:
                values[key] = expression(raw, body)
            else:
                update_variant(len(texts) - 1)
    return values['Icon'], values['IconLarge'] or values['Icon']


def build(source, data, output):
    catalog_path = ROOT / 'data/equipment_catalog.json'
    catalog = json.loads(catalog_path.read_text('utf-8'))
    items, files = {}, {}
    output.mkdir(parents=True, exist_ok=True)
    with ExitStack() as stack:
        archives = [(name, stack.enter_context(zipfile.ZipFile(data / name)))
                    for name in sorted(OFFICIAL_ARCHIVES) if (data / name).is_file()]
        resources = {name: (filename, archive) for filename, archive in archives
                     for name in archive.namelist() if name.startswith('gfx/ui/items/') and name.endswith('.png')}

        def extract(relative):
            name = 'gfx/ui/items/' + relative
            if name not in resources:
                raise ValueError('Missing original icon: ' + name)
            archive_name, archive = resources[name]
            raw = archive.read(name)
            digest = hashlib.sha256(raw).hexdigest()
            filename = digest + '.png'
            with Image.open(io.BytesIO(raw)) as picture:
                picture.load()
                size = list(picture.size)
            if filename not in files:
                (output / filename).write_bytes(raw)
                files[filename] = {'archive': archive_name, 'source': name, 'sha256': digest, 'size': size}
            return filename

        errors = []
        for relative, item in catalog['items'].items():
            try:
                small, large = resolve_icons(source, relative)
                if 'gfx/ui/items/' + small not in resources and 'gfx/ui/items/' + large in resources: small = large
                if 'gfx/ui/items/' + large not in resources and 'gfx/ui/items/' + small in resources: large = small
                if not item['loot'] and item['rarity'] == 'special' and 'gfx/ui/items/' + small not in resources:
                    items[relative] = {'small': None, 'large': None, 'reason': '原版未提供此特殊条目的物品图标'}
                    continue
                items[relative] = {'small': extract(small), 'large': extract(large)}
            except (ValueError, TypeError) as error:
                errors.append(f'{relative}: {error}')
        if errors: raise ValueError('\n'.join(errors))
    manifest = {'schema': 1, 'game_version': catalog['game_version'],
                'catalog_sha256': hashlib.sha256(catalog_path.read_bytes()).hexdigest(),
                'copyright': 'Game artwork copyright Overhype Studios. BBMOD is an unofficial community tool.',
                'visual_variant': 'First original variant; individual named items may have another appearance.',
                'items': items, 'files': files}
    (output / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    illustrated = sum(bool(item['small']) for item in items.values())
    print(f'Bundled original icons for {illustrated}/{len(items)} entries ({len(files)} unique PNG files); remaining special entries explicitly marked.')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / 'build/full-l10n/decompiled')
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=ROOT / 'assets/equipment')
    args = parser.parse_args()
    build(args.source, args.data, args.output)

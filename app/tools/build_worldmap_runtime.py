"""Build the independent host with reproducible upstream Squirrel sources.

Generated sources and binaries stay under app/build. The host uses a 64-bit
process with 32-bit Squirrel integers/floats, matching original map rules.
"""
from __future__ import annotations
import argparse
import hashlib
import io
from pathlib import Path
import shutil
import subprocess
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE_URL = 'https://codeload.github.com/albertodemichelis/squirrel/zip/refs/tags/v3.1'
SOURCE_SHA256 = '12b9955ff1b108b1ef181954a22bea11d90299906fa03c0099c771dd169e2496'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--compiler', default=shutil.which('g++'))
    args = parser.parse_args()
    if not args.compiler:
        parser.error('g++ compiler required')
    output = ROOT/'build/offline-map'
    vendor = output/'vendor'
    archive = output/'squirrel-3.1.zip'
    if not archive.exists():
        archive.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(SOURCE_URL, timeout=45) as response:
            archive.write_bytes(response.read())
    raw = archive.read_bytes()
    if hashlib.sha256(raw).hexdigest() != SOURCE_SHA256:
        raise RuntimeError('Squirrel source checksum mismatch')
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        prefix = z.namelist()[0]
        for item in z.infolist():
            if item.is_dir():
                continue
            dest = vendor/item.filename.removeprefix(prefix)
            if not dest.resolve().is_relative_to(vendor.resolve()):
                raise ValueError('Source archive path escapes vendor directory')
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(z.read(item))
    # Preserve pointer-sized hashes/object storage while keeping script arithmetic
    # and the on-disk original bytecode ABI at 32 bits. No game code is patched.
    header = vendor/'include/squirrel.h'
    header.write_text(header.read_text().replace(
        '#if (defined(_WIN64) || defined(_LP64))',
        '#if (defined(_WIN64) || defined(_LP64)) && !defined(BBMOD_SQ32)'), encoding='utf-8')
    config = vendor/'include/sqconfig.h'
    text = config.read_text()
    text = text.replace('typedef unsigned int SQHash;', 'typedef unsigned long long SQHash;')
    text = text.replace('typedef SQUnsignedInteger SQRawObjectVal;', 'typedef unsigned long long SQRawObjectVal;')
    text = text.replace('#define SQ_OBJECT_RAWINIT()\n', '#define SQ_OBJECT_RAWINIT() { _unVal.raw = 0; }\n')
    config.write_text(text, encoding='utf-8')
    binary = output/'bin/worldmap.exe'
    binary.parent.mkdir(parents=True, exist_ok=True)
    command = [args.compiler, '-std=c++17', '-O2', '-DNDEBUG', '-DBBMOD_SQ32',
               '-DSQ_ALIGNMENT=8', '-fpermissive', '-Wno-cast-function-type',
               '-static', '-I'+str(vendor/'include'), '-I'+str(vendor/'squirrel'),
               str(ROOT/'native/worldmap/runtime.cpp'),
               *map(str, sorted((vendor/'squirrel').glob('*.cpp'))),
               *map(str, sorted((vendor/'sqstdlib').glob('*.cpp'))), '-o', str(binary)]
    result = subprocess.run(command, capture_output=True, text=True)
    (output/'build-runtime.log').write_text(result.stdout+result.stderr, encoding='utf-8')
    if result.returncode:
        raise RuntimeError(result.stderr[-6000:])
    print(binary)


if __name__ == '__main__':
    main()

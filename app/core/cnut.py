"""Bounded reader for the game's 32-bit Squirrel 3 bytecode.

Only literal strings may be replaced. Instructions, keys, source/debug names,
numeric constants, and function structure remain byte-for-byte unchanged.
"""
from __future__ import annotations

from dataclasses import dataclass
import struct

_MASK = 0xffffffff
_DELTA = 0x9e3779b9
_KEY = (238473842, 20047425, 14005, 978629342)


def cipher_block(data: bytes, *, decrypt: bool = False) -> bytes:
    """The public BB bytecode format applies XXTEA to each reader block.

    Partial trailing words are intentionally left alone, matching the game.
    These fixed values describe a file format, not user credentials.
    """
    n = len(data) // 4
    if n < 2:
        return data
    words = list(struct.unpack(f'<{n}I', data[:n * 4]))
    rounds = 6 + 52 // n
    def mix(z, y, total, p, e):
        return (((z >> 5 ^ y << 2) + (y >> 3 ^ z << 4)) ^ ((total ^ y) + (_KEY[(p & 3) ^ e] ^ z))) & _MASK
    if decrypt:
        total = rounds * _DELTA & _MASK
        y = words[0]
        for _ in range(rounds):
            e = total >> 2 & 3
            for p in range(n - 1, 0, -1):
                z = words[p - 1]
                words[p] = (words[p] - mix(z, y, total, p, e)) & _MASK
                y = words[p]
            z = words[-1]
            words[0] = (words[0] - mix(z, y, total, 0, e)) & _MASK
            y = words[0]
            total = (total - _DELTA) & _MASK
    else:
        total = 0
        z = words[-1]
        for _ in range(rounds):
            total = (total + _DELTA) & _MASK
            e = total >> 2 & 3
            for p in range(n - 1):
                y = words[p + 1]
                words[p] = (words[p] + mix(z, y, total, p, e)) & _MASK
                z = words[p]
            y = words[0]
            words[-1] = (words[-1] + mix(z, y, total, n - 1, e)) & _MASK
            z = words[-1]
    return struct.pack(f'<{n}I', *words) + data[n * 4:]


def patch_literals(encrypted: bytes, patches: list, entries: dict) -> bytes:
    """Patch checked string spans without recompiling any game instruction."""
    chunks = []
    cursor = 0
    for start, end, key in sorted(patches):
        if start < cursor or end > len(encrypted) or end < start + 4:
            raise ValueError('汉化文本位置重叠或越界')
        entry = entries[key]
        source = entry['source'].encode('utf-8')
        if struct.unpack('<i', encrypted[start:start + 4])[0] != len(source):
            raise ValueError('原版文本长度不匹配')
        if cipher_block(encrypted[start + 4:end], decrypt=True) != source:
            raise ValueError('原版文本校验失败')
        value = entry['translation'].encode('utf-8')
        chunks.extend([encrypted[cursor:start], struct.pack('<i', len(value)), cipher_block(value)])
        cursor = end
    chunks.append(encrypted[cursor:])
    return b''.join(chunks)


@dataclass(frozen=True)
class Literal:
    function: str
    index: int
    start: int
    end: int
    text: str


class Cnut:
    def __init__(self, data: bytes, *, encrypted: bool = False):
        self.data = data
        self.encrypted = encrypted
        self.pos = 0
        self.literals: list[Literal] = []
        self.functions: list[dict] = []
        self.blocks: list[tuple[int, int]] = []
        if self.read(2) != b'\xfa\xfa' or self.read(4) != b'RIQS':
            raise ValueError('Unsupported Squirrel header')
        if [self.integer() for _ in range(3)] != [1, 4, 4]:
            raise ValueError('Only 32-bit Squirrel bytecode is supported')
        self.function('0')
        self.tag(b'LIAT')
        if self.pos != len(data):
            raise ValueError('Unexpected trailing bytecode')

    def read(self, count: int) -> bytes:
        if count < 0 or self.pos + count > len(self.data):
            raise ValueError('Truncated or invalid bytecode')
        start = self.pos
        self.pos += count
        if count >= 8:
            self.blocks.append((start, count))
        value = self.data[start:self.pos]
        return cipher_block(value, decrypt=True) if self.encrypted and count >= 8 else value

    def integer(self) -> int:
        return struct.unpack('<i', self.read(4))[0]

    def tag(self, expected: bytes = b'TRAP'):
        if self.read(4) != expected:
            raise ValueError(f'Invalid bytecode section at {self.pos - 4}')

    def obj(self, function: str = '', index: int = -1):
        kind = self.integer()
        if kind == 0x08000010:
            start = self.pos
            size = self.integer()
            raw = self.read(size)
            # Some original scripts carry non-text byte strings. Preserve them
            # losslessly; they are never admitted to the translation catalog.
            text = raw.decode('utf-8', errors='surrogateescape')
            if index >= 0:
                self.literals.append(Literal(function, index, start, self.pos, text))
            return text
        if kind in (0x05000002, 0x05000004, 0x01000008):
            return self.read(4)
        if kind == 0x01000001:
            return None
        raise ValueError(f'Invalid Squirrel object {kind:x} at {self.pos - 4}')

    def function(self, path: str):
        if path.count('.') > 80:
            raise ValueError('Excessive function nesting')
        self.tag()
        source, name = self.obj(), self.obj()
        self.tag()
        counts = [self.integer() for _ in range(8)]
        if any(n < 0 or n > len(self.data) for n in counts):
            raise ValueError('Invalid section size')
        nl, np, no, nv, nn, nd, ni, nf = counts
        self.tag()
        literals = [self.obj(path, i) for i in range(nl)]
        self.tag()
        for _ in range(np):
            self.obj()
        self.tag()
        for _ in range(no):
            self.integer()
            self.obj()
            self.obj()
        self.tag()
        for _ in range(nv):
            self.obj()
            for _ in range(3):
                self.integer()
        self.tag()
        self.read(nn * 8)
        self.tag()
        self.read(nd * 4)
        self.tag()
        instructions_start = self.pos
        instructions = list(struct.iter_unpack('<iBBBB', self.read(ni * 8)))
        self.functions.append({'path': path, 'source': source, 'name': name, 'literals': literals, 'instructions': instructions,
                               'instructions_start': instructions_start})
        self.tag()
        for i in range(nf):
            self.function(f'{path}.{i}')
        self.integer()
        self.read(1)
        self.integer()

    def replace(self, replacements: dict[tuple[str, int], str]) -> bytes:
        known = {(lit.function, lit.index) for lit in self.literals}
        if replacements.keys() - known:
            raise ValueError('Unknown literal replacement')
        chunks = []
        cursor = 0
        for lit in self.literals:
            key = (lit.function, lit.index)
            if key not in replacements:
                continue
            value = replacements[key].encode('utf-8')
            chunks.extend([self.data[cursor:lit.start], struct.pack('<i', len(value)), value])
            cursor = lit.end
        chunks.append(self.data[cursor:])
        result = b''.join(chunks)
        # A second parse validates the rewritten lengths and structure.
        Cnut(result)
        return result

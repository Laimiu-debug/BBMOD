"""Deterministic RNG used by the supported 1.5.2.3 map generator.

The string hash is SDBM with 64-bit wraparound. Map Math.rand(a,b) uses
MT19937-64 and the MSVC rejection/modulo integer distribution. The zero-argument
Math.rand overload is a different generator and is deliberately not substituted
for this stream.
"""
from __future__ import annotations

MASK64 = (1 << 64) - 1


def seed_hash(seed: str) -> int:
    """Case-sensitive hash of the game's ASCII seed string."""
    if not isinstance(seed, str) or not seed.isascii():
        raise ValueError('地图种子必须是 ASCII 字符串')
    value = 0
    for char in seed:
        value = (value * 65599 + ord(char)) & MASK64
    return value


class MapRandom:
    """MT19937-64 with the game's inclusive integer-range draw semantics."""

    def __init__(self, seed: int | str):
        self.seed(seed)

    def seed(self, seed: int | str) -> None:
        if isinstance(seed, str):
            seed = seed_hash(seed)
        if type(seed) is not int:
            raise TypeError('seed must be an integer or ASCII string')
        state = [seed & MASK64]
        for i in range(1, 312):
            previous = state[-1]
            state.append((6364136223846793005 * (previous ^ (previous >> 62)) + i) & MASK64)
        self._state = state
        self._index = 312
        self.draws = 0

    def _twist(self) -> None:
        state = self._state
        # In-place ordering matters for the second half and the final word.
        for i in range(312):
            value = (state[i] & 0xFFFFFFFF80000000) | (state[(i+1) % 312] & 0x7FFFFFFF)
            state[i] = state[(i+156) % 312] ^ (value >> 1) ^ (0xB5026F5AA96619E9 if value & 1 else 0)
        self._index = 0

    def next_u64(self) -> int:
        if self._index == 312:
            self._twist()
        value = self._state[self._index]
        self._index += 1
        self.draws += 1
        value ^= (value >> 29) & 0x5555555555555555
        value ^= (value << 17) & 0x71D67FFFEDA60000
        value ^= (value << 37) & 0xFFF7EEE000000000
        value ^= value >> 43
        return value & MASK64

    def rand(self, low: int, high: int) -> int:
        """Inclusive signed-32-bit range; degenerate ranges do not draw."""
        if type(low) is not int or type(high) is not int:
            raise TypeError('Math.rand bounds must be integers')
        if not -(1 << 31) <= low < 1 << 31 or not -(1 << 31) <= high < 1 << 31:
            raise ValueError('Math.rand bounds exceed signed 32-bit range')
        if high <= low:
            return low
        size = high-low+1
        limit = (1 << 64) - ((1 << 64) % size)
        while True:
            value = self.next_u64()
            if value < limit:
                return low + value % size

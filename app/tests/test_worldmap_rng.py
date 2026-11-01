"""Independent standard vectors and original-game oracle checks for map RNG."""
import json
from pathlib import Path

import pytest

from core.worldmap.rng import MapRandom, seed_hash


def test_mt19937_64_reference_vector():
    # Public mt19937-64 reference implementation, default seed 5489.
    expected = [14514284786278117030, 4620546740167642908, 13109570281517897720,
                17462938647148434322, 355488278567739596]
    rng = MapRandom(5489)
    assert [rng.next_u64() for _ in expected] == expected


def test_case_sensitive_seed_and_fresh_reproduction():
    first = MapRandom('AbCdEfGhIj')
    replay = MapRandom('AbCdEfGhIj')
    other = MapRandom('ABCDEFGHIJ')
    a = [first.next_u64() for _ in range(1000)]
    assert a == [replay.next_u64() for _ in a]
    assert a != [other.next_u64() for _ in a]
    assert seed_hash('AbCdEfGhIj') != seed_hash('ABCDEFGHIJ')


def test_degenerate_range_preserves_state():
    rng = MapRandom('ABCDEFGHIJ')
    assert rng.rand(7, 7) == 7
    assert rng.rand(9, -2) == 9
    assert rng.draws == 0
    assert rng.next_u64() == MapRandom('ABCDEFGHIJ').next_u64()


def test_rejection_does_not_bias_partial_last_bucket():
    rng = MapRandom(1)
    draws = iter([(1 << 64)-1, 17])
    rng.next_u64 = lambda: next(draws)
    assert rng.rand(1, 100) == 18


def test_invalid_input_is_rejected():
    with pytest.raises(ValueError):
        seed_hash('地图')
    with pytest.raises(ValueError):
        MapRandom(1).rand(0, 1 << 31)


def test_original_game_rng_oracle():
    path = Path(__file__).with_name('fixtures')/'worldmap/rng-geometry-1.5.2.3.json'
    fixture = json.loads(path.read_text('utf-8'))
    assert fixture['provenance']['finished'] is True
    assert fixture['provenance']['restored'] is True
    cases = fixture['rng']
    assert len(cases) == 16
    for case in cases:
        rng = MapRandom(case['seed'])
        actual = [rng.rand(case['min'], case['max']) for _ in case['values']]
        assert actual == case['values'], case

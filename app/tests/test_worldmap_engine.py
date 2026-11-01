"""Real native-map fixtures, cache corruption, cancellation and seed case."""
import gzip
import json
from pathlib import Path
import threading

import pytest

from core.worldmap.engine import MapSolver, SolveCancelled
from core.worldmap.model import WorldMap, validate_seed

FIXTURES = Path(__file__).with_name('fixtures')/'worldmap'


def fixture_maps():
    return [json.loads(gzip.decompress(p.read_bytes())) for p in sorted(FIXTURES.glob('map-*.json.gz'))]


def test_all_five_complete_maps_match_native_engine(tmp_path):
    cases = fixture_maps()
    assert len(cases) == 5
    assert {c['map']['seed'] for c in cases} == {'AbCdEfGhIj', 'ABCDEFGHIJ', '46U2HMOORH', 'aaaaaaaaaa', 'ZZZZZZZZZZ'}
    solver = MapSolver(cache=tmp_path)
    if not solver.components.binary.is_file():
        pytest.skip('Build the independent runtime and extract a rule pack first')
    for case in cases:
        expected = WorldMap.from_dict(case['map'])
        result = solver.solve(expected.seed, use_cache=False)
        assert result.world.to_dict() == expected.to_dict()
        assert not result.cached
        assert case['provenance']['restored'] is True


def test_case_sensitive_cache_and_corrupt_cache_recovery(tmp_path):
    solver = MapSolver(cache=tmp_path)
    if not solver.components.binary.is_file():
        pytest.skip('Independent runtime unavailable')
    a = solver.solve('AbCdEfGhIj')
    b = solver.solve('ABCDEFGHIJ')
    assert a.world.rows != b.world.rows
    assert solver.solve('AbCdEfGhIj').cached
    assert solver.solve('ABCDEFGHIJ').cached
    assert len(list(tmp_path.rglob('*.json.gz'))) == 2
    for path in tmp_path.rglob('*.json.gz'):
        path.write_bytes(b'corrupt')
    recovered = solver.solve('AbCdEfGhIj')
    assert not recovered.cached and recovered.world == a.world


def test_invalid_seed_and_pre_cancel_never_start_a_process(tmp_path, monkeypatch):
    from unittest.mock import Mock
    popen = Mock(side_effect=AssertionError('must not start'))
    monkeypatch.setattr('core.worldmap.engine.subprocess.Popen', popen)
    for value in ('short', '../outside', '中文中文中文中文中文', 'A'*11):
        with pytest.raises(ValueError): validate_seed(value)
    event = threading.Event(); event.set()
    solver = MapSolver(cache=tmp_path)
    if not solver.components.binary.is_file(): pytest.skip('Independent runtime unavailable')
    with pytest.raises(SolveCancelled): solver.solve('ABCDEFGHIJ', cancelled=event)
    popen.assert_not_called()


def test_damaged_map_is_rejected():
    value = fixture_maps()[0]['map']
    value['rows'][0][0][0] = 99
    with pytest.raises(ValueError, match='地块'): WorldMap.from_dict(value)


def test_cancel_running_solver_reaps_the_child_and_writes_no_cache(tmp_path, monkeypatch):
    import subprocess
    original = subprocess.Popen
    children = []
    def record(*args, **kwargs):
        child = original(*args, **kwargs); children.append(child); return child
    monkeypatch.setattr('core.worldmap.engine.subprocess.Popen', record)
    solver = MapSolver(cache=tmp_path)
    if not solver.components.binary.is_file(): pytest.skip('Independent runtime unavailable')
    event = threading.Event()
    timer = threading.Timer(.15, event.set); timer.start()
    try:
        with pytest.raises(SolveCancelled): solver.solve('ABCDEFGHIJ', cancelled=event)
    finally:
        timer.cancel()
    assert children and all(child.poll() is not None for child in children)
    assert not list(tmp_path.rglob('*.json.gz'))

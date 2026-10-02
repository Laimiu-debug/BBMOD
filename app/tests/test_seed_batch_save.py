from dataclasses import replace
from unittest.mock import patch

import pytest

from core.seedgen.library import SeedLibrary
from core.seedgen.log_watcher import SeedResult
from core.seedgen.protocol import seed_key


def record(seed='AbCdEfGhIj', **values):
    return SeedResult(seed, 123, origin='scenario.militia', done=True,
                      lines=['CharInfo: 0 Melee:0.8'], **values)


def test_batch_uses_one_connection_and_matches_consecutive_saves(tmp_path):
    library = SeedLibrary(tmp_path / 'batch.sqlite3')
    single = SeedLibrary(tmp_path / 'single.sqlite3')
    first, second = record(), record('ABCDEFGHIJ')
    richer = replace(first, lines=first.lines + ['Trait: trait.tough'])
    inputs = [replace(first, done=False, lines=[]), second, first, richer,
              replace(first, loop_idx=999, done=False, lines=['partial'])]
    expected = [(single.save(result), False) for result in inputs]

    with patch.object(library, '_connect', wraps=library._connect) as connect:
        assert library.save_many(iter(inputs)) == expected
        connect.assert_called_once_with()
    assert library.all() == single.all() == [richer, second]


def test_batch_retains_trash_public_link_and_creation_order(tmp_path):
    library = SeedLibrary(tmp_path / 'seeds.sqlite3')
    first, second, third = record(), record('ABCDEFGHIJ'), record('abcdefghij')
    library.save_many([first, second])
    library.mark_shared(first, 'https://bbmod.site/seeds/kept/')
    library.delete([seed_key(first)])
    richer = replace(first, lines=first.lines + ['SettlementInfo: Port:8'])

    assert library.save_many([richer, third, first]) == [
        (richer, True), (third, False), (richer, True)]
    assert library.all() == [second, third]
    assert library.all(deleted=True) == [richer]
    assert library.shared_url(first).endswith('/kept/')
    library.restore([seed_key(first)])
    assert library.all() == [richer, second, third]


def test_failed_batch_rolls_back_earlier_records(tmp_path):
    library = SeedLibrary(tmp_path / 'seeds.sqlite3')
    first = record()
    library.save(first)
    richer = replace(first, lines=first.lines + ['Trait: trait.tough'])
    broken = record('ABCDEFGHIJ', mods=[{'bad': 'missing-id'}])

    with pytest.raises(KeyError):
        library.save_many([richer, record('abcdefghij'), broken])
    assert SeedLibrary(library.path).all() == [first]


def test_empty_batch_does_not_open_database(tmp_path):
    library = SeedLibrary(tmp_path / 'seeds.sqlite3')
    with patch.object(library, '_connect') as connect:
        assert library.save_many([]) == []
        connect.assert_not_called()

"""Original roster agreement and independent searches without a game install."""
import gzip
import json
from pathlib import Path
import time

import pytest

from core.seedgen.config_emitter import (BroCondition, CampaignConfig, CommonConfig,
                                        OriginConfig, SeedGenConfig, brother_condition)
from core.seedgen.offline import OfflineSeedSearch, FAST_ORIGINS, supports
from core.seedgen.traits import trait_label
from core.seedgen.orchestrator import StopLimits
from core.worldmap.engine import Components

FIXTURE = Path(__file__).with_name('fixtures')/'worldmap/brothers.json.gz'


def references():
    return [record for line in gzip.decompress(FIXTURE.read_bytes()).splitlines()
            if line.strip() and (record := json.loads(line))['kind'] == 'brothers']


def config(origin='scenario.militia', condition=None):
    return SeedGenConfig(common=CommonConfig.preset('bro_only'), campaign=CampaignConfig(origin=origin),
        origins={origin: OriginConfig(conditions=[condition or BroCondition('TeamScore', [-100])])})


def run(search, cfg):
    search.prepare(cfg)
    started = time.monotonic()
    try:
        search.launch()
        while not search.stop_reason:
            search.poll()
            assert time.monotonic()-started < 12
            time.sleep(.002)
    finally:
        search.stop_and_restore()
    assert not search.script_error
    return search


@pytest.fixture(autouse=True)
def available():
    if not Components.locate().binary.is_file():
        pytest.skip('Build the independent solver and its rule pack first')


@pytest.mark.parametrize('origin', sorted(FAST_ORIGINS))
def test_original_actors_traits_stars_and_growth(origin):
    refs = [ref for ref in references() if ref['origin'] == origin]
    search = run(OfflineSeedSearch(seeds=[ref['seed'] for ref in refs], return_all=True), config(origin))
    assert len(refs) >= 3
    for ref, actual in zip(refs, search.records, strict=True):
        for member, raw in zip(ref['members'], actual['raw'], strict=True):
            assert raw['Attr'] == member['attr']
            assert raw['Talents'] == member['talents']
            assert set(raw['Traits']) == set(member['traits'])
            assert raw['Level11TalentsAdd'] == [sum(values) for values in member['growth']]


@pytest.mark.parametrize('count,total,required,excluded,match,stars', [
    (1, 8, (), (), 'all', {}), (2, 7, (), (), 'all', {}),
    (1, 0, (), (), 'all', {'MeleeSkill': (3, 3), 'Stamina': (2, 3)}),
    (1, 0, ('trait.fat',), (), 'all', {}),
    (1, 4, ('trait.fat', 'trait.drunkard'), (), 'any', {}),
    (2, 3, (), ('trait.fat', 'trait.drunkard'), 'all', {}),
])
def test_filters_match_distinct_original_brothers(count, total, required, excluded, match, stars):
    refs = [ref for ref in references() if ref['origin'] == 'scenario.militia']
    order = ['Hitpoints','Bravery','Stamina','Initiative','MeleeSkill','RangedSkill','MeleeDefense','RangedDefense']
    expected = []
    for ref in refs:
        matches = 0
        for member in ref['members']:
            traits = set(member['traits'])
            needed = (all(trait in traits for trait in required) if match == 'all' else
                      any(trait in traits for trait in required)) if required else True
            fits = (sum(member['talents']) >= total and needed and not traits.intersection(excluded)
                and all(bounds[0] <= member['talents'][order.index(attr)] <= bounds[1]
                        for attr, bounds in stars.items()))
            matches += fits
        if matches >= count:
            expected.append(ref['seed'])
    condition = brother_condition(count, {}, required, excluded, match,
                                  total_min=total, star_ranges=stars)
    search = run(OfflineSeedSearch(seeds=[ref['seed'] for ref in refs]), config(condition=condition))
    assert [result.seed for result in search.results] == expected


def test_traits_and_stars_must_belong_to_the_same_brother():
    ref = next(ref for ref in references() if ref['origin'] == 'scenario.militia')
    members = ref['members']
    order = ['Hitpoints','Bravery','Stamina','Initiative','MeleeSkill','RangedSkill','MeleeDefense','RangedDefense']
    pair = next((trait, attr, number) for member in members for trait in member['traits']
        for index, attr in enumerate(order) for number in (1, 2, 3)
        if any(other['talents'][index] >= number for other in members)
        and not any(trait in other['traits'] and other['talents'][index] >= number for other in members))
    trait, attr, number = pair
    condition = brother_condition(1, {}, required=[trait], star_ranges={attr: (number, 3)})
    search = run(OfflineSeedSearch(seeds=[ref['seed']]), config(condition=condition))
    assert search.results == []


def test_hit_limit_no_game_import_or_game_process(monkeypatch):
    import core.game as game
    def forbidden(*args, **kwargs):
        raise AssertionError('Independent searches must not use game or mod sessions')
    for name in ('locate_game', 'launch_game', 'launch_executable', 'kill_game', 'probe_game_running'):
        monkeypatch.setattr(game, name, forbidden)
    search = run(OfflineSeedSearch(limits=StopLimits(hits=2), count=20), config())
    assert len(search.results) == 2
    assert search.progress.loop_idx == 2 and search.progress.hits == 2
    assert search.stop_reason == '已达到命中数量'
    assert all(result.done and result.dlc_mask == 342 and not result.mods for result in search.results)
    assert search._process is None and search._temporary is None


def test_cancel_with_backpressure_reaps_process_and_keeps_complete_results():
    search = OfflineSeedSearch()
    search.prepare(config())
    try:
        search.launch()
        time.sleep(.3)
        process = search._process
    finally:
        search.stop_and_restore()
    assert process.poll() is not None
    assert search.results and all(result.done for result in search.results)
    assert not search.script_error
    assert not search._reader.is_alive() and not search._errors.is_alive()


def test_unsupported_origin_or_combination_is_explicit():
    cfg = config('scenario.afeix_expedition')
    assert not supports(cfg)
    with pytest.raises(ValueError, match='独立解算'):
        OfflineSeedSearch().prepare(cfg)
    cfg = config()
    cfg.common = CommonConfig.preset('bro_map')
    assert supports(cfg)


def test_fixed_gladiator_traits_use_the_existing_chinese_names():
    assert [trait_label('trait.glorious', 'scenario.gladiators', i) for i in (1, 2, 3)] == [
        '坚定意志', '不屈耐力', '迅捷连杀']

"""Campaign searches use original rules and the same filters in every mode."""
import gzip
import json
from pathlib import Path
import time

import pytest

from core.seedgen.config_emitter import (BroCondition, CampaignConfig, CommonConfig,
    OriginConfig, SeedGenConfig)
from core.seedgen.offline import OfflineSeedSearch, ORIGINS
from core.seedgen.orchestrator import StopLimits
from core.worldmap.engine import Components, MapSolver
from core.worldmap.model import Campaign

SEED = 'AbCdEfGhIj'
FIXTURES = Path(__file__).with_name('fixtures')/'worldmap'


@pytest.fixture(autouse=True)
def available():
    if not Components.locate().binary.is_file():
        pytest.skip('Independent component unavailable')


def config(mode='map_lair', origin='scenario.militia', difficulties=(2, 2, 2)):
    return SeedGenConfig(common=CommonConfig.preset(mode),
        campaign=CampaignConfig(origin, *difficulties),
        origins={origin: OriginConfig(conditions=[BroCondition('TeamScore', [-100])])},
        map_conditions=[['SettlementNum', 1]], lair_conditions=[['NamedNumber', 0]])


def run(cfg, seeds=(SEED,), **kwargs):
    search = OfflineSeedSearch(seeds=seeds, return_all=kwargs.pop('return_all', True), **kwargs)
    search.prepare(cfg)
    started = time.monotonic()
    try:
        search.launch()
        while not search.stop_reason:
            search.poll()
            assert time.monotonic()-started < 60
            time.sleep(.005)
    finally:
        search.stop_and_restore()
    assert not search.script_error, search.script_error
    return search


@pytest.mark.parametrize('mode', ['map_only', 'lair_only', 'map_lair', 'bro_map', 'bro_lair', 'all'])
def test_all_modes_return_complete_matching_archives_without_a_game(mode, monkeypatch):
    import core.game as game
    def forbidden(*args, **kwargs):
        raise AssertionError('Offline campaign searches must never touch an installed game')
    for name in ('locate_game', 'launch_game', 'launch_executable', 'kill_game', 'probe_game_running'):
        monkeypatch.setattr(game, name, forbidden)
    search = run(config(mode))
    assert len(search.results) == 1
    result = search.results[0]
    assert result.done and result.dlc_mask == 342 and result.mods == []
    assert bool(result.brothers) == config(mode).common.GenerateBrotherMode
    assert bool(result.named_items) == config(mode).common.PrintLairInfo
    assert any(line.startswith('SettlementInfo:') for line in result.lines)
    from core.seedgen.protocol import share_payload
    assert share_payload(result)['record']['origin'] == result.origin


def test_batch_campaign_matches_original_game_camps_and_independent_character_reference():
    search = run(config('all'))
    campaign = search.records[0]['campaign']
    expected = next(json.loads(gzip.decompress(p.read_bytes()))['campaign']
                    for p in FIXTURES.glob('camp-*.json.gz')
                    if json.loads(gzip.decompress(p.read_bytes()))['campaign']['seed'] == SEED)
    assert Campaign.from_dict(campaign, SEED, 140, 170, len(expected['settlement_names'])).to_dict() == expected
    original = next(r for line in gzip.decompress((FIXTURES/'brothers.json.gz').read_bytes()).splitlines()
                    if (r := json.loads(line)).get('seed') == SEED and r.get('origin') == 'scenario.militia')
    for actual, reference in zip(search.records[0]['raw'], original['members'], strict=True):
        assert actual['Attr'] == reference['attr'] and actual['Talents'] == reference['talents']
        assert set(actual['Traits']) == set(reference['traits'])
        assert actual['Level11TalentsAdd'] == [sum(values) for values in reference['growth']]


@pytest.mark.parametrize('origin', sorted(ORIGINS))
def test_every_official_origin_has_independent_map_and_loot(origin):
    index = sorted(ORIGINS).index(origin)
    difficulties = (index % 3,) * 3
    search = run(config('all', origin, difficulties))
    result = search.results[0]
    assert result.origin == origin
    assert (result.combat_difficulty, result.economic_difficulty, result.budget_difficulty) == difficulties
    assert result.brothers and result.named_items
    value = search.records[0]['campaign']
    actual = Campaign.from_dict(value, SEED, 140, 170, len(value['settlement_names'])).to_dict()
    references = json.loads(gzip.decompress((FIXTURES.parent/'seed_campaigns.json.gz').read_bytes()))
    reference = next(case for case in references if case['campaign']['origin'] == origin
        and tuple(case['campaign'][key] for key in ('combat','economic','budget')) == difficulties)
    from tools.validate_campaign_search import comparison
    assert comparison(actual, reference['campaign'], ('Tomb of Willibald',))[0]
    for raw, original in zip(search.records[0]['raw'], reference['members'], strict=True):
        assert raw['Attr'] == original['attr'] and raw['Talents'] == original['talents']
        assert sorted(raw['Traits']) == sorted(original['traits'])
        assert raw['Level11TalentsAdd'] == [sum(values) for values in original['growth']]
    assert reference['provenance']['restored']


@pytest.mark.parametrize('filter_kind', ['brothers', 'map', 'loot'])
def test_combined_search_requires_every_selected_condition(filter_kind):
    cfg = config('all')
    if filter_kind == 'brothers':
        cfg.origins[cfg.campaign.origin].conditions = [BroCondition('TeamScore', [100])]
    elif filter_kind == 'map':
        cfg.map_conditions = [['SettlementNum', 1000]]
    else:
        cfg.lair_conditions = [['NamedNumber', 1000]]
    search = run(cfg)
    assert not search.results and len(search.records) == 1 and search.progress.hits == 0


def test_hit_limit_and_stop_keep_only_fully_completed_candidates():
    search = run(config(), seeds=(SEED, 'ABCDEFGHIJ'), limits=StopLimits(hits=1))
    assert len(search.results) == 1 and search.progress.loop_idx == 1
    assert search.stop_reason == '已达到命中数量'
    running = OfflineSeedSearch()
    running.prepare(config())
    try:
        running.launch()
        deadline = time.monotonic()+20
        while not running.results and time.monotonic() < deadline:
            running.poll(); time.sleep(.01)
        assert len(running.results) == 1
    finally:
        running.stop_and_restore()
    assert running._process is None and running._temporary is None
    assert not running._reader.is_alive() and not running.script_error
    assert all(result.done for result in running.results)


def test_same_seed_different_campaigns_have_separate_verified_caches(tmp_path):
    solver = MapSolver(cache=tmp_path)
    militia = solver.solve(SEED, include_camps=True)
    trader = solver.solve(SEED, include_camps=True, origin='scenario.trader', combat=0, economic=1, budget=0)
    replay = solver.solve(SEED, include_camps=True, origin='scenario.trader', combat=0, economic=1, budget=0)
    assert not militia.cached and not trader.cached and replay.cached
    assert militia.world.campaign != trader.world.campaign
    assert replay.world == trader.world


def unique_weapon():
    from collections import Counter
    from core.worldmap.loot import item_rating
    expected = next(json.loads(gzip.decompress(p.read_bytes()))['campaign']
                    for p in FIXTURES.glob('camp-*.json.gz')
                    if json.loads(gzip.decompress(p.read_bytes()))['campaign']['seed'] == SEED)
    world = Campaign.from_dict(expected, SEED, 140, 170, len(expected['settlement_names']))
    items = [item for camp in world.camps for item in camp.items]
    counts = Counter(item.identifier for item in items)
    return next((item, item_rating(item)) for item in items if item.kind == 'weapon'
                and counts[item.identifier] == 1 and item_rating(item).score < 100)


@pytest.mark.parametrize('extra,matched', [(0, True), (1, False)])
def test_weapon_score_boundary_uses_the_recorded_original_affixes(extra, matched):
    from core.seedgen.weapons import WeaponRequirement, weapon_filter_condition
    item, rating = unique_weapon()
    cfg = config('lair_only')
    cfg.lair_conditions = [weapon_filter_condition([WeaponRequirement(item.identifier, score=rating.score+extra)])]
    search = run(cfg)
    assert bool(search.results) is matched


def test_two_weapon_requirements_cannot_reuse_the_same_item():
    from core.seedgen.weapons import WeaponRequirement, weapon_filter_condition
    item, _ = unique_weapon()
    cfg = config('lair_only')
    cfg.lair_conditions = [weapon_filter_condition([WeaponRequirement(item.identifier), WeaponRequirement(item.identifier)])]
    assert not run(cfg).results


def test_original_weapon_damage_uses_float32_multiplier_before_rounding():
    search = run(config('lair_only', 'scenario.trader', (0, 0, 0)))
    items = [item for camp in search.records[0]['campaign']['camps'] for item in camp['items']]
    shamshir = next(item for item in items if item['id'] == 'weapon.named_shamshir')
    warbrand = next(item for item in items if item['id'] == 'weapon.named_warbrand')
    assert shamshir['stats']['RegularDamageMax'] == 60  # 50 * float32(1.21), original roll 121
    assert warbrand['stats']['RegularDamage'] == 58     # 50 * float32(1.17), original roll 117


def test_rejected_characters_never_generate_a_map(monkeypatch):
    import core.seedgen.offline as offline
    stages = []
    popen = offline.subprocess.Popen
    def launch(command, **kwargs):
        stages.append(command[-1])
        return popen(command, **kwargs)
    monkeypatch.setattr(offline.subprocess, 'Popen', launch)
    cfg = config('all')
    cfg.origins[cfg.campaign.origin].conditions = [BroCondition('TeamScore', [100])]
    seeds = [SEED, 'ABCDEFGHIJ', 'BattleBros'] * 30
    search = run(cfg, seeds=seeds, return_all=False)
    assert search.progress.loop_idx == len(seeds) and not search.results
    assert search.prefilter_rejected == len(seeds) and search.campaign_candidates == 0
    assert stages == ['brothers', 'brothers']


def selective_characters():
    from core.seedgen.config_emitter import brother_condition
    refs = [json.loads(line) for line in gzip.decompress((FIXTURES/'brothers.json.gz').read_bytes()).splitlines()
            if (value := json.loads(line)).get('kind') == 'brothers' and value['origin'] == 'scenario.militia']
    first, second = refs[:2]
    trait = next(trait for member in first['members'] for trait in member['traits']
                 if not any(trait in other['traits'] for other in second['members']))
    return brother_condition(1, {}, required=[trait]), first['seed'], second['seed']


@pytest.mark.parametrize('mode', ['bro_map', 'bro_lair', 'all'])
def test_prefilter_preserves_archives_order_limits_and_loop_numbers(mode):
    condition, hit, reject = selective_characters()
    cfg = config(mode)
    cfg.origins[cfg.campaign.origin].conditions = [condition]
    seeds = [reject, hit, hit]
    baseline = run(cfg, seeds=seeds, return_all=False, prefilter=False, limits=StopLimits(hits=1))
    optimized = run(cfg, seeds=seeds, return_all=False, limits=StopLimits(hits=1))
    assert optimized.results == baseline.results
    assert len(optimized.results) == 1 and optimized.results[0].seed == hit
    assert optimized.progress.loop_idx == baseline.progress.loop_idx == 2
    assert optimized.progress.hits == 1 and optimized.prefilter_rejected == 1
    assert optimized.campaign_candidates == 1 and baseline.campaign_candidates == 2
    assert optimized.stop_reason == '已达到命中数量'


def test_cancel_and_deadline_reap_the_prefilter_without_generating_maps():
    cfg = config('all')
    cfg.origins[cfg.campaign.origin].conditions = [BroCondition('TeamScore', [100])]
    search = OfflineSeedSearch()
    search.prepare(cfg)
    search.launch()
    try:
        deadline = time.monotonic()+10
        while search._process is None and time.monotonic() < deadline:
            search.poll(); time.sleep(.001)
        assert search._process is not None
    finally:
        search.stop_and_restore()
    assert search.campaign_candidates == 0 and not search.script_error
    assert search._process is None and search._temporary is None and not search._reader.is_alive()
    limited = OfflineSeedSearch(limits=StopLimits(minutes=1))
    limited.prepare(cfg)
    limited.launch()
    try:
        deadline = time.monotonic()+10
        while limited._process is None and time.monotonic() < deadline:
            limited.poll(); time.sleep(.001)
        assert limited._process is not None
        # Advance the session age while a real probe child is running. The
        # public settings keep their supported whole-minute precision.
        limited._started -= 61
        while not limited.stop_reason and time.monotonic() < deadline:
            limited.poll(); time.sleep(.001)
    finally:
        limited.stop_and_restore()
    assert limited.campaign_candidates == 0 and not limited.script_error
    assert limited.stop_reason == '已达到运行时限'


def test_bad_prefilter_seed_order_is_rejected():
    cfg = config('all')
    search = OfflineSeedSearch(seeds=[SEED])
    def wrong_order(*args):
        yield dict(kind='prefilter', seed='ABCDEFGHIJ', match=-1, score=0)
    search._campaign_job = wrong_order
    search.prepare(cfg)
    try:
        search.launch()
        deadline = time.monotonic()+10
        while not search.stop_reason and time.monotonic() < deadline:
            search.poll(); time.sleep(.001)
    finally:
        search.stop_and_restore()
    assert '种子顺序' in search.script_error and not search.results

"""Original-game campaign fixtures protect RNG, camp loot and cache scope."""
import copy
import gzip
import json
from pathlib import Path
import re

import pytest

from core.worldmap.engine import MapSolver
from core.worldmap.localization import building_label, place_label, site_label, term_dictionary, town_label
from core.worldmap.loot import item_appraisal, item_label, item_rating, weapon_rolls
from core.worldmap.model import Campaign, WorldMap
from core.worldmap.trade import GOODS, goods_label
from core.item_inspector import rounded

FIXTURES = Path(__file__).with_name('fixtures')/'worldmap'


def test_original_rounding_keeps_negative_half_fatigue_values():
    assert rounded(-16.5) == -17 and rounded(16.5) == 17
    c = next(case['campaign'] for case in campaigns() if case['campaign']['seed'] == '0oO1lI2zZ3')
    axe = next(i for camp in c['camps'] for i in camp['items'] if i['id'] == 'weapon.named_orc_axe')
    assert axe['stats']['StaminaModifier'] == -17


def campaigns():
    return [json.loads(gzip.decompress(p.read_bytes())) for p in sorted(FIXTURES.glob('camp-*.json.gz'))]


def test_ten_complete_campaigns_match_original_game(tmp_path):
    cases = campaigns()
    assert len(cases) == 10
    solver = MapSolver(cache=tmp_path)
    if not solver.components.binary.is_file():
        pytest.skip('Build the independent runtime and rule pack first')
    for case in cases:
        expected = case['campaign']
        result = solver.solve(expected['seed'], include_camps=True, use_cache=False)
        assert result.world.campaign.to_dict() == expected
        assert case['provenance']['restored'] is True


def test_every_reference_item_has_valid_stats_and_weapon_roll_scores():
    weapons = 0
    for case in campaigns():
        c = case['campaign']
        campaign = Campaign.from_dict(c, c['seed'], 140, 170, len(c['settlement_names']))
        for camp in campaign.camps:
            assert re.search('[\u3400-\u9fff]', place_label(camp.name)) and place_label(camp.name) != '未收录地名'
            for item in camp.items:
                assert item_appraisal(item)['valid']
                assert re.search('[\u3400-\u9fff]', item_label(item))
                if item.kind == 'weapon':
                    weapons += 1
                    assert len(weapon_rolls(item)) == 2
                    rating = item_rating(item)
                    assert rating and 0 <= rating.score <= 100 and 0 <= rating.quality <= 100
    assert weapons > 30


def test_existing_chinese_catalog_covers_map_terms_and_places():
    translations = term_dictionary()
    for good, (english, *_) in GOODS.items():
        assert goods_label(good) == translations[english]
    for path in FIXTURES.glob('map-*.json.gz'):
        world = WorldMap.from_dict(json.loads(gzip.decompress(path.read_bytes()))['map'])
        for town in world.settlements:
            assert town_label(world, town.index) != '未收录地名'
            assert all(site_label(a) == translations[a['name']] for a in town.attached)
            assert all(building_label(b) != '其他建筑' for b in town.buildings if b and b != 'building.crowd')
            assert all(goods_label(g) not in ('其他物资', '未收录译名') for g in town.produce)
        assert all(place_label(r['name']) != '未收录地名' for r in world.regions)
    for case in campaigns():
        assert all(place_label(name) != '未收录地名' for name in case['campaign']['settlement_names'])


def test_wrong_seed_context_or_damaged_loot_is_rejected():
    value = campaigns()[0]['campaign']
    changes = [('seed', '0000000000'), ('origin', 'scenario.trader'), ('combat', 0)]
    for key, bad in changes:
        c = copy.deepcopy(value); c[key] = bad
        with pytest.raises(ValueError, match='配置'):
            Campaign.from_dict(c, value['seed'], 140, 170, len(value['settlement_names']))
    c = copy.deepcopy(value); next(x for x in c['camps'] if x['items'])['items'][0]['stats']['ConditionMax'] = float('nan')
    with pytest.raises(ValueError, match='属性'):
        Campaign.from_dict(c, value['seed'], 140, 170, len(value['settlement_names']))


def test_static_and_full_campaign_caches_do_not_cross(tmp_path):
    solver = MapSolver(cache=tmp_path)
    if not solver.components.binary.is_file(): pytest.skip('Independent runtime unavailable')
    plain = solver.solve('46U2HMOORH')
    full = solver.solve('46U2HMOORH', include_camps=True)
    assert plain.world.campaign is None and full.world.campaign
    assert not full.cached and solver.solve('46U2HMOORH', include_camps=True).cached
    assert solver.solve('46U2HMOORH').world.campaign is None
    assert WorldMap.from_dict(full.world.to_dict()) == full.world

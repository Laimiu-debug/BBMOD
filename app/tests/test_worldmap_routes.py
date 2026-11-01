import gzip
import json
from pathlib import Path
from dataclasses import replace

import pytest

from core.worldmap.model import WorldMap, distance, adjacent
from core.worldmap.routes import RoutePlanner
from core.worldmap.trade import opportunities, prices


def world():
    path = next((Path(__file__).with_name('fixtures')/'worldmap').glob('map-*.json.gz'))
    return WorldMap.from_dict(json.loads(gzip.decompress(path.read_bytes()))['map'])


def test_land_route_is_continuous_avoids_ocean_and_is_symmetric():
    data = world(); planner = RoutePlanner(data)
    route = planner.plan([0, 1, 2]); reverse = planner.plan([2, 1, 0])
    assert route.tiles[0] == data.settlements[0].xy and route.tiles[-1] == data.settlements[2].xy
    assert all(distance(a, b) == 1 for a, b in zip(route.tiles, route.tiles[1:]))
    assert all(data.tile(xy)[0] not in (0, 1) for xy in route.tiles)
    assert route.hours == pytest.approx(reverse.hours)
    assert len(route.legs) == 2


def test_road_only_never_crosses_a_missing_road():
    data = world(); planner = RoutePlanner(data)
    for target in range(1, len(data.settlements)):
        try: route = planner.plan([0, target], road_only=True)
        except ValueError: continue
        for a, b in zip(route.tiles, route.tiles[1:]):
            direction = next(d for d in range(6) if adjacent(*a, d) == b)
            assert data.tile(a)[4] & (1 << direction)
            assert data.tile(b)[4] & (1 << ((direction+3) % 6))
        assert route.road_steps == len(route.tiles)-1
        return
    pytest.fail('Reference seed should have at least one road connection')


def test_unreachable_and_invalid_stops_are_explicit():
    data = world()
    rows = tuple(tuple((1, *t[1:]) for t in row) for row in data.rows)
    planner = RoutePlanner(replace(data, rows=rows))
    with pytest.raises(ValueError, match='陆路'): planner.plan([0, 1])
    with pytest.raises(ValueError, match='无效'): planner.plan([-1, 1])


def test_trade_uses_production_culture_ports_and_no_unavailable_stock_claims():
    data = world(); offers = opportunities(data)
    assert offers and all(o.profit > 0 for o in offers)
    town = replace(data.settlements[0], price_mult=1, buy_mult=1, sell_mult=1,
                   buildings=(), attached=({'id': 'attached_location.plantation'},), culture=2)
    assert prices(town, 'trade/spices_item') == (320, 48)
    northern = replace(town, culture=0, attached=())
    assert prices(northern, 'trade/spices_item')[1] == 355
    port = replace(northern, buildings=('building.port',))
    assert prices(port, 'trade/spices_item')[1] == 323

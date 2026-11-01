"""Canonical static geography; transient native entity IDs never enter a map."""
from __future__ import annotations

from dataclasses import dataclass
import re
import math

PROFILE = 'bb-1.5.2.3-all-dlc-v1'
PROFILE_LABEL = '原版 1.5.2.3 · 全 DLC'
CAMP_PROFILE = 'militia-expert-v1'
CAMP_PROFILE_LABEL = '农民民兵 · 战斗/经济/资金专家 · 开局营地'
CAMPAIGN_PROFILE = 'official-campaign-v2'
OFFICIAL_ORIGINS = frozenset('scenario.'+name for name in (
    'early_access', 'southern_quickstart', 'trader', 'militia', 'lone_wolf',
    'rangers', 'paladins', 'raiders', 'anatomists', 'beast_hunters',
    'gladiators', 'manhunters', 'cultists', 'deserters'))


def campaign_key(origin='scenario.militia', combat=2, economic=2, budget=2):
    if origin not in OFFICIAL_ORIGINS or any(type(v) is not int or v not in (0, 1, 2)
                                            for v in (combat, economic, budget)):
        raise ValueError('离线开局需要官方起源与有效的战斗、经济、资金档位。')
    return f'{origin}:{combat}:{economic}:{budget}'


TERRAIN_NAMES = ('不可通行', '海洋', '平原', '沼泽', '丘陵', '森林', '雪林', '疏林',
                 '秋林', '山脉', '城镇', '农田', '雪地', '荒地', '苔原', '草原', '海岸', '沙漠', '绿洲')
SPEED_MULT = (0, 0, 1, .5, .65, .65, .65, .65, .65, .25, .5, 1, .75, .9, .9, 1, .5, .75, .9)


def validate_seed(seed: str) -> str:
    seed = seed.strip()
    if not re.fullmatch(r'[A-Za-z0-9]{10}', seed):
        raise ValueError('请输入十位种子码（英文字母或数字，区分大小写）。')
    return seed


def adjacent(x: int, y: int, direction: int) -> tuple[int, int]:
    return ((x, y+1), (x+1, y+(x & 1)), (x+1, y-1+(x & 1)),
            (x, y-1), (x-1, y-1+(x & 1)), (x-1, y+(x & 1)))[direction]


def distance(a: tuple[int, int], b: tuple[int, int]) -> int:
    q = a[0]-b[0]
    r = a[1]-a[0]//2-b[1]+b[0]//2
    return max(abs(q), abs(r), abs(q+r))


@dataclass(frozen=True)
class Settlement:
    index: int
    name: str
    xy: tuple[int, int]
    size: int
    culture: int
    military: bool
    coastal: bool
    buildings: tuple[str | None, ...]
    attached: tuple[dict, ...]
    produce: tuple[str, ...]
    connected: tuple[int, ...]
    roads: tuple[int, ...]
    price_mult: float
    buy_mult: float
    sell_mult: float
    building_mult: float
    incense_mult: float

    def to_dict(self):
        return dict(id=self.index, name=self.name, xy=list(self.xy), size=self.size,
                    culture=self.culture, military=self.military, coastal=self.coastal,
                    buildings=list(self.buildings), attached=list(self.attached),
                    produce=list(self.produce), connected=list(self.connected), roads=list(self.roads),
                    price_mult=self.price_mult, buy_mult=self.buy_mult, sell_mult=self.sell_mult,
                    building_mult=self.building_mult, incense_mult=self.incense_mult)


def _coordinate(value, width, height):
    if (not isinstance(value, (tuple, list)) or len(value) != 2
            or any(type(n) is not int for n in value)
            or not 0 <= value[0] < width or not 0 <= value[1] < height):
        raise ValueError('营地或玩家坐标越界。')
    return tuple(value)


@dataclass(frozen=True)
class NamedItem:
    identifier: str
    name: str
    kind: str
    stats: dict[str, float]
    trace: tuple[dict, ...]

    @classmethod
    def from_dict(cls, value):
        from ..item_inspector import FIELDS
        if (not re.fullmatch(r'[a-zA-Z0-9_.-]{1,128}', value['id'])
                or not isinstance(value['name'], str) or len(value['name']) > 500
                or value['kind'] not in ('weapon', 'armor', 'helmet', 'shield')
                or not value['stats'] or any(k not in FIELDS or type(v) not in (int, float)
                    or not math.isfinite(v) or abs(v) > 1000000 for k, v in value['stats'].items())):
            raise ValueError('离线红装属性损坏。')
        trace = value['trace']
        if (not isinstance(trace, list) or not 2 <= len(trace) <= 20
                or any(not isinstance(t, dict) or type(t.get('value')) is not int
                    or not isinstance(t.get('args'), list) or len(t['args']) != 2
                    or any(type(n) is not int for n in t['args'])
                    or not t['args'][0] <= t['value'] <= t['args'][1] for t in trace)):
            raise ValueError('离线红装随机词条记录损坏。')
        return cls(value['id'], value['name'], value['kind'], dict(value['stats']), tuple(trace))

    def to_dict(self):
        return dict(id=self.identifier, name=self.name, kind=self.kind, stats=self.stats, trace=list(self.trace))


@dataclass(frozen=True)
class Camp:
    index: int
    name: str
    type: str
    faction: int
    xy: tuple[int, int]
    resources: float
    strength: float
    items: tuple[NamedItem, ...]

    def to_dict(self):
        return dict(name=self.name, type=self.type, faction=self.faction, xy=list(self.xy),
                    resources=self.resources, strength=self.strength, items=[i.to_dict() for i in self.items])


@dataclass(frozen=True)
class Campaign:
    seed: str
    camps: tuple[Camp, ...]
    settlement_names: tuple[str, ...]
    player_xy: tuple[int, int]
    profile: str = CAMP_PROFILE
    origin: str = 'scenario.militia'
    combat: int = 2
    economic: int = 2
    budget: int = 2

    @classmethod
    def from_dict(cls, value, seed, width, height, towns):
        origin, combat, economic, budget = (value.get(k) for k in ('origin', 'combat', 'economic', 'budget'))
        campaign_key(origin, combat, economic, budget)
        expected_profile = CAMP_PROFILE if (origin, combat, economic, budget) == ('scenario.militia', 2, 2, 2) else CAMPAIGN_PROFILE
        if value.get('profile') != expected_profile or value.get('seed') != seed:
            raise ValueError('营地数据的种子或开局配置不匹配。')
        names = value['settlement_names']
        if len(names) != towns or any(not isinstance(n, str) or not n or len(n) > 500 for n in names):
            raise ValueError('营地数据的城镇名称不完整。')
        camps, occupied = [], set()
        if not isinstance(value['camps'], list) or not value['camps'] or len(value['camps']) > 500:
            raise ValueError('营地数据不完整。')
        for index, camp in enumerate(value['camps']):
            xy = _coordinate(camp['xy'], width, height)
            if (xy in occupied or not isinstance(camp['name'], str) or not camp['name']
                    or not re.fullmatch(r'location\.[a-z_.]+', camp['type'])
                    or type(camp['faction']) is not int or camp['faction'] < 0
                    or any(type(camp[k]) not in (int, float) or not math.isfinite(camp[k])
                           or camp[k] < 0 for k in ('resources', 'strength'))):
                raise ValueError('营地属性或位置损坏。')
            occupied.add(xy)
            camps.append(Camp(index, camp['name'], camp['type'], camp['faction'], xy,
                              camp['resources'], camp['strength'], tuple(NamedItem.from_dict(i) for i in camp['items'])))
        return cls(seed, tuple(camps), tuple(names), _coordinate(value['player_xy'], width, height),
                   expected_profile, origin, combat, economic, budget)

    def to_dict(self):
        return dict(profile=self.profile, seed=self.seed, origin=self.origin, combat=self.combat,
                    economic=self.economic, budget=self.budget,
                    camps=[c.to_dict() for c in self.camps], settlement_names=list(self.settlement_names),
                    player_xy=list(self.player_xy))


@dataclass(frozen=True)
class WorldMap:
    seed: str
    width: int
    height: int
    rows: tuple[tuple[tuple[int, ...], ...], ...]
    settlements: tuple[Settlement, ...]
    regions: tuple[dict, ...]
    profile: str = PROFILE
    campaign: Campaign | None = None

    @classmethod
    def from_dict(cls, value: dict) -> 'WorldMap':
        seed = validate_seed(value['seed'])
        if value.get('profile', PROFILE) != PROFILE:
            raise ValueError('地图规则版本不匹配。')
        width, height = value['width'], value['height']
        if (width, height) != (140, 170):
            raise ValueError('地图尺寸与规则版本不符。')
        rows = tuple(tuple(tuple(tile) for tile in row) for row in value['rows'])
        if len(rows) != height or any(len(row) != width for row in rows):
            raise ValueError('地图地块数据不完整。')
        for row in rows:
            for tile in row:
                if (len(tile) != 5 or any(type(v) is not int for v in tile)
                        or not 0 <= tile[0] < 19 or not 0 <= tile[1] < 25
                        or not 0 <= tile[2] < 65536 or not 0 <= tile[3] < 65536
                        or not 0 <= tile[4] < 64):
                    raise ValueError('地图地块数据损坏。')
        towns = value['settlements']
        identifiers = {t['id']: i for i, t in enumerate(towns)}
        if len(identifiers) != len(towns):
            raise ValueError('城镇标识重复。')
        settlements = []
        for i, t in enumerate(towns):
            xy = tuple(t['xy'])
            if len(xy) != 2 or not 0 <= xy[0] < width or not 0 <= xy[1] < height:
                raise ValueError('城镇坐标越界。')
            if any(not isinstance(t[k], (int, float)) or not math.isfinite(t[k]) or t[k] <= 0
                   for k in ('price_mult', 'buy_mult', 'sell_mult', 'building_mult', 'incense_mult')):
                raise ValueError('城镇价格系数损坏。')
            settlements.append(Settlement(i, t['name'], xy, t['size'], t['culture'],
                t['military'], t['coastal'], tuple(t['buildings']), tuple(t['attached']),
                tuple(t['produce']), tuple(identifiers[k] for k in t['connected']),
                tuple(identifiers[k] for k in t['roads']), t['price_mult'], t['buy_mult'], t['sell_mult'],
                t['building_mult'], t['incense_mult']))
        regions = tuple({k: r[k] for k in ('name', 'type', 'size', 'xy')} for r in value['regions'])
        campaign = Campaign.from_dict(value['campaign'], seed, width, height, len(settlements)) if value.get('campaign') else None
        return cls(seed, width, height, rows, tuple(settlements), regions, campaign=campaign)

    def to_dict(self):
        result = dict(schema=1, profile=self.profile, seed=self.seed, width=self.width, height=self.height,
                    rows=self.rows, settlements=[t.to_dict() for t in self.settlements], regions=self.regions)
        if self.campaign:
            result['campaign'] = self.campaign.to_dict()
        return result

    def town_name(self, index):
        return self.campaign.settlement_names[index] if self.campaign else self.settlements[index].name

    def tile(self, xy: tuple[int, int]) -> tuple[int, ...]:
        return self.rows[xy[1]][xy[0]]

    def contains(self, xy: tuple[int, int]) -> bool:
        return 0 <= xy[0] < self.width and 0 <= xy[1] < self.height

"""Static trade opportunities; live events, reputation and stock are not seeded."""
from __future__ import annotations

from dataclasses import dataclass
import math

from .model import Settlement, WorldMap
from .localization import SUPPLIES, town_label, term_label

# Original 1.5.2.3 item values and producing locations, checked against rule pack.
GOODS = {
    'trade/amber_shards_item': ('Amber Shards', 260, 0, 'amber_collector'),
    'trade/cloth_rolls_item': ('Cloth Rolls', 140, 0, 'wool_spinner'),
    'trade/copper_ingots_item': ('Copper Ingots', 220, 0, 'surface_copper_vein'),
    'trade/dies_item': ('Dyes', 400, 0, 'dye_maker'),
    'trade/furs_item': ('Furs', 300, 1, 'trapper'),
    'trade/incense_item': ('Incense', 380, 2, 'incense_dryer'),
    'trade/peat_bricks_item': ('Peat Bricks', 100, 0, 'peat_pit'),
    'trade/quality_wood_item': ('Quality Wood', 180, 0, 'lumber_camp'),
    'trade/salt_item': ('Salt', 340, 0, 'salt_mine'),
    'trade/silk_item': ('Silk', 460, 2, 'silk_farm'),
    'trade/spices_item': ('Spices', 320, 2, 'plantation'),
    'trade/uncut_gems_item': ('Uncut Gems', 520, 0, 'gem_mine'),
}


def goods_label(key: str) -> str:
    if key in GOODS:
        return term_label(GOODS[key][0])
    return term_label(SUPPLIES.get(key.rsplit('/', 1)[-1].removesuffix('_item'), ''), '其他物资')


def prices(town: Settlement, key: str) -> tuple[int, int]:
    _, value, culture, production = GOODS[key]
    produced = any(a.get('id') == 'attached_location.'+production for a in town.attached)
    # Before faction setup northern settlements carry Neutral in the map rules.
    local_culture = culture == 0 or culture == (2 if town.culture == 2 else 1) or 'building.port' in town.buildings
    multiplier = 1 if local_culture else 1.5
    item_mult = (town.building_mult if good_uses_building_modifier(key) else town.incense_mult if key == 'trade/incense_item' else 1)
    sell = math.floor(value*item_mult*town.price_mult*town.sell_mult*(.15 if produced else 1.01)*(1 if local_culture else 1.1))
    buy = max(sell, math.ceil(value*item_mult*town.price_mult*town.buy_mult*(1 if produced else 1.5)*multiplier))
    return buy, sell


def good_uses_building_modifier(key: str) -> bool:
    return key in ('trade/copper_ingots_item', 'trade/quality_wood_item')


@dataclass(frozen=True)
class Offer:
    good: str
    source: int
    target: int
    buy: int
    sell: int

    @property
    def profit(self):
        return self.sell-self.buy

    @property
    def roi(self):
        return self.profit/self.buy


def opportunities(world: WorldMap) -> list[Offer]:
    result = []
    for source in world.settlements:
        for good in dict.fromkeys(source.produce):
            if good not in GOODS:
                continue
            buy, _ = prices(source, good)
            candidates = [Offer(good, source.index, target.index, buy, prices(target, good)[1])
                          for target in world.settlements if target.index != source.index and target.index in source.connected]
            if candidates:
                best = max(candidates, key=lambda offer: (offer.profit, -offer.target))
                if best.profit > 0:
                    result.append(best)
    return sorted(result, key=lambda offer: (-offer.roi, -offer.profit, offer.good, offer.source))


def town_opportunities(world: WorldMap, index: int) -> tuple[list[Offer], list[Offer]]:
    """All profitable exports and imports for one town, based on actual producers."""
    exports, imports = [], []
    for source in world.settlements:
        for good in dict.fromkeys(source.produce):
            if good not in GOODS:
                continue
            buy = prices(source, good)[0]
            for target in world.settlements:
                if source.index == target.index or target.index not in source.connected:
                    continue
                if index not in (source.index, target.index):
                    continue
                offer = Offer(good, source.index, target.index, buy, prices(target, good)[1])
                if offer.profit > 0:
                    (exports if index == source.index else imports).append(offer)
    order = lambda offer: (-offer.profit, -offer.roi, offer.good, offer.source, offer.target)
    return sorted(exports, key=order), sorted(imports, key=order)


def offer_reason(world: WorldMap, offer: Offer) -> str:
    source, target = world.settlements[offer.source], world.settlements[offer.target]
    reasons = ['产地采购']
    if not any(a.get('id') == 'attached_location.'+GOODS[offer.good][3] for a in target.attached):
        reasons.append('销地不生产此商品')
    culture = GOODS[offer.good][2]
    if culture and culture != (2 if target.culture == 2 else 1) and 'building.port' not in target.buildings:
        reasons.append('跨文化内陆溢价')
    if target.price_mult > source.price_mult:
        reasons.append('销地规模价格系数较高')
    return '；'.join(reasons)


def town_advice(world: WorldMap, index: int) -> str:
    town = world.settlements[index]
    exports, imports = town_opportunities(world, index)
    lines = [f'价格系数 {town.price_mult:.0%}；采购系数 {town.buy_mult:.0%}；售出系数 {town.sell_mult:.0%}']
    for title, offers, other_index in [('在此买入，运往外地', exports, 'target'), ('从外地买入，在此卖出', imports, 'source')]:
        lines.append(title+'：')
        chosen, seen = [], set()
        for offer in offers:
            if offer.good in seen:
                continue
            seen.add(offer.good)
            other = world.settlements[getattr(offer, other_index)]
            chosen.append(f'{goods_label(offer.good)}：{offer.buy} → {offer.sell}，毛利 {offer.profit} 克朗/件；'
                          + ('卖到 ' if other_index == 'target' else '采购地 ')+town_label(world, other.index))
            if len(chosen) == 3:
                break
        lines.extend(chosen or ['当前基础行情未找到正毛利组合'])
    return '\n'.join(lines)

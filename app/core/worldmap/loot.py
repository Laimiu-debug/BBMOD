"""Chinese loot labels and existing weapon appraisal for offline camp results."""
from functools import lru_cache

from ..item_inspector import appraise, catalog
from ..seedgen.weapon_rating import WEIGHTS, eligible_affixes, rate_weapon
from .localization import place_label, town_label
from .model import distance

KINDS = {'weapon': '武器', 'armor': '盔甲', 'helmet': '头盔', 'shield': '盾牌'}


@lru_cache(maxsize=1)
def item_catalog():
    return catalog()


def item_label(item):
    return item_catalog().get(item.identifier, {}).get('zh', '未收录红装')


def weapon_rolls(item):
    """Decode observed original draws, including rounding-ambiguous affixes."""
    base = item_catalog().get(item.identifier)
    if not base or base['kind'] != 'weapon':
        return None
    available = [key for key in WEIGHTS if key in eligible_affixes()[item.identifier]]
    trace = list(item.trace)
    if base['base']['ConditionMax'] > 1:
        if not trace or trace.pop(0)['args'] != [90, 140]:
            return None
    if len(trace) != 4:
        return None
    bounds = {'RegularDamage': (110, 130), 'ArmorDamageMult': (10, 30),
              'ChanceToHitHead': (10, 20), 'DirectDamageAdd': (8, 16),
              'StaminaModifier': (50, 80), 'ShieldDamage': (150, 200),
              'AmmoMax': (1, 3), 'AdditionalAccuracy': (5, 15), 'FatigueOnSkillUse': (1, 3)}
    result = {}
    for index in (0, 2):
        choice, roll = trace[index:index+2]
        if choice['args'] != [0, len(available)-1] or not 0 <= choice['value'] < len(available):
            return None
        key = available.pop(choice['value'])
        low, high = bounds[key]
        if roll['args'] != [low, high] or not low <= roll['value'] <= high:
            return None
        result[key] = (200*(roll['value']-low)+(high-low))//(2*(high-low))
    return result


def item_rating(item):
    rolls = weapon_rolls(item)
    return rate_weapon(item.identifier, rolls) if rolls is not None else None


def item_appraisal(item):
    return appraise(dict(schema=1, seq=0, kind='item', id=item.identifier, name=item_label(item),
                         named=True, attachment=False, stats=item.stats), item_catalog())


def camp_position(world, camp):
    nearest = min(world.settlements, key=lambda town: (distance(town.xy, camp.xy), town.index))
    dx, dy = camp.xy[0]-nearest.xy[0], camp.xy[1]-nearest.xy[1]
    direction = ('北' if dy > 0 else '南' if dy < 0 else '') + ('东' if dx > 0 else '西' if dx < 0 else '')
    direction = {'北东': '东北', '北西': '西北', '南东': '东南', '南西': '西南'}.get(direction, direction)
    return f'{town_label(world, nearest.index)}{direction}方 {distance(nearest.xy, camp.xy)} 格（直线六角格距离）'


def camp_detail(world, camp, item=None):
    lines = [place_label(camp.name), f'地图坐标：{camp.xy[0]}, {camp.xy[1]}', camp_position(world, camp),
             f'营地强度 {camp.strength:g}（非人数） · 开局红装 {len(camp.items)} 件']
    if item is None:
        if not camp.items:
            lines.append('此营地没有开局红装。')
        return '\n'.join(lines)
    lines += ['', f'红装：{item_label(item)} · {KINDS[item.kind]}']
    rating = item_rating(item)
    if rating:
        lines.append(f'实用词条评分 {rating.score}/100 · roll 品质 {rating.quality}%')
        lines.append('实用分采用现有「伤穿优先 v1」；适合比较同类武器。')
    appraisal = item_appraisal(item)
    for row in appraisal.get('rows', []):
        if row['state'] == '未抽中':
            lines.append(f'{row["label"]}：{row["value"]}（基础值，未抽中此词条）')
        else:
            lines.append(f'{row["label"]}：{row["value"]}　原版区间 {row["range"]}')
    return '\n'.join(lines)

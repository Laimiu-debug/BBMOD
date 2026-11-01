"""Named weapon choices for the supported game's ordinary camp loot."""
from __future__ import annotations

from dataclasses import dataclass

from ..item_inspector import catalog

# Share the equipment catalog's reviewed type names. The randomized in-game
# name identifies an individual item, not the type used by camp-loot filters.
NAMED_WEAPONS = {identifier: item['zh'] for identifier, item in catalog().items()
                 if item['kind'] == 'weapon'}
WEAPON_CHOICES = {
    'weapon': '任意武器',
    'one_hand': '任意单手近战武器',
    'two_hand': '任意双手近战武器',
    'range': '任意远程 / 投掷武器',
    **NAMED_WEAPONS,
}


def weapon_condition(weapon: str, count: int = 1, damage_roll: int | None = None,
                     penetration_roll: int | None = None) -> list:
    """Count weapons of one type satisfying both optional affix rolls.

    None does not require the affix. Zero requires that affix, at any roll.
    Keep both slots even when unused: the Squirrel reader consumes six fields.
    """
    if not isinstance(weapon, str) or weapon not in WEAPON_CHOICES:
        raise ValueError('请选择支持的红装武器类型')
    if type(count) is not int or not 1 <= count <= 200:
        raise ValueError('红装武器数量应在 1 至 200 之间')
    if any(value is not None and (type(value) is not int or not 0 <= value <= 100)
           for value in (damage_roll, penetration_roll)):
        raise ValueError('红装武器品质应为不限或 0 至 100 的整数')
    return ['NamedAttrValue', weapon, count,
            'RegularDamage' if damage_roll is not None else '', damage_roll or 0,
            'DirectDamageAdd' if penetration_roll is not None else '', penetration_roll or 0]


@dataclass(frozen=True)
class WeaponRequirement:
    weapon: str = 'weapon'
    count: int = 1
    damage: int | None = None
    penetration: int | None = None
    score: int | None = None
    quality: int | None = None

    def __post_init__(self):
        weapon_condition(self.weapon, self.count, self.damage, self.penetration)
        if any(value is not None and (type(value) is not int or not 0 <= value <= 100)
               for value in (self.score, self.quality)):
            raise ValueError('红武评分门槛应为不限或 0 至 100 的整数')

    def fields(self) -> list:
        return [self.weapon, self.count, *[value if value is not None else -1
                for value in (self.damage, self.penetration, self.score, self.quality)]]


def weapon_filter_condition(requirements: list[WeaponRequirement], total: int = 0,
                            match: str = 'all') -> list:
    """One compound condition: total AND (all / any weapon requirements).

    Keep this in a single outer row: the legacy generator ORs outer rows.
    In all mode, each physical item can fill only one requirement's quantity.
    """
    if type(total) is not int or not 0 <= total <= 200:
        raise ValueError('红装总数应在 0 至 200 之间')
    if match not in ('all', 'any'):
        raise ValueError('请选择全部满足或任一满足')
    if not isinstance(requirements, list) or len(requirements) > 20 or any(
            not isinstance(row, WeaponRequirement) for row in requirements):
        raise ValueError('最多可添加 20 条武器要求')
    if not requirements:
        if total:
            return ['NamedNumber', total]
        raise ValueError('请至少启用红装总数或武器要求中的一项')
    return ['NamedWeaponFilter', total, match,
            *[field for requirement in requirements for field in requirement.fields()]]

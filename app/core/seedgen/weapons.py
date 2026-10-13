"""Named weapon choices for the supported game's ordinary camp loot."""
from __future__ import annotations

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

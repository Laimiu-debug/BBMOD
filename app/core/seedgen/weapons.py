"""Named weapon choices for the supported game's ordinary camp loot."""
from __future__ import annotations

# IDs checked against the official 1.5.2.3 named weapon scripts. These are
# weapon types; the random individual item name does not identify its type.
NAMED_WEAPONS = {
    'weapon.named_javelin': '红标枪',
    'weapon.named_throwing_axe': '红投斧',
    'weapon.named_crossbow': '红弩',
    'weapon.named_warbow': '红战弓',
    'weapon.named_handgonne': '红火铳',
    'weapon.named_greatsword': '红大剑',
    'weapon.named_greataxe': '红巨斧',
    'weapon.named_two_handed_mace': '红双手锤',
    'weapon.named_two_handed_hammer': '红双手战锤',
    'weapon.named_two_handed_flail': '红双手链枷',
    'weapon.named_two_handed_scimitar': '红双手弯刀',
    'weapon.named_two_handed_spiked_mace': '红双手钉锤',
    'weapon.named_fencing_sword': '红刺剑',
    'weapon.named_estoc': '红破甲刺剑',
    'weapon.named_exesword': '红行刑剑',
    'weapon.named_qatal_dagger': '红南方匕首',
    'weapon.named_dagger': '红匕首',
    'weapon.named_sword': '红单手剑',
    'weapon.named_shamshir': '红弯刀',
    'weapon.named_axe': '红单手斧',
    'weapon.named_mace': '红单手锤',
    'weapon.named_warhammer': '红单手战锤',
    'weapon.named_flail': '红链枷',
    'weapon.named_three_headed_flail': '红三头链枷',
    'weapon.named_spear': '红矛',
    'weapon.named_cleaver': '红砍刀',
    'weapon.named_battle_whip': '红战鞭',
    'weapon.named_khopesh': '红镰剑',
    'weapon.named_warbrand': '红战刃',
    'weapon.named_bardiche': '红斩斧',
    'weapon.named_longaxe': '红长斧',
    'weapon.named_billhook': '红钩镰',
    'weapon.named_pike': '红长枪',
    'weapon.named_bladed_pike': '红刃矛',
    'weapon.named_spetum': '红三叉矛',
    'weapon.named_poleaxe': '红长柄斧',
    'weapon.named_polehammer': '红长柄战锤',
    'weapon.named_polemace': '红长柄锤',
    'weapon.named_swordlance': '红剑枪',
    'weapon.named_warscythe': '红战镰',
    'weapon.named_crypt_cleaver': '红墓穴斩首剑',
    'weapon.named_heavy_rusty_axe': '红重型锈斧',
    'weapon.named_rusty_warblade': '红锈蚀战刃',
    'weapon.named_skullhammer': '红碎颅锤',
    'weapon.named_orc_axe': '红兽人斧',
    'weapon.named_orc_cleaver': '红兽人砍刀',
    'weapon.named_goblin_spear': '红地精矛',
    'weapon.named_goblin_pike': '红地精长枪',
    'weapon.named_goblin_falchion': '红地精弯刀',
    'weapon.named_goblin_heavy_bow': '红地精重弓',
}
WEAPON_CHOICES = {
    'weapon': '任意红武器',
    'one_hand': '任意单手近战红武器',
    'two_hand': '任意双手近战红武器',
    'range': '任意远程 / 投掷红武器',
    **NAMED_WEAPONS,
}


def weapon_condition(weapon: str, count: int = 1, damage_roll: int | None = None,
                     penetration_roll: int | None = None) -> list:
    """Count weapons of one type satisfying both optional affix rolls.

    None does not require the affix. Zero requires that affix, at any roll.
    Keep both slots even when unused: the Squirrel reader consumes six fields.
    """
    if not isinstance(weapon, str) or weapon not in WEAPON_CHOICES:
        raise ValueError('请选择支持的红武器类型')
    if type(count) is not int or not 1 <= count <= 200:
        raise ValueError('红武器数量应在 1 至 200 之间')
    if any(value is not None and (type(value) is not int or not 0 <= value <= 100)
           for value in (damage_roll, penetration_roll)):
        raise ValueError('红武器品质应为不限或 0 至 100 的整数')
    return ['NamedAttrValue', weapon, count,
            'RegularDamage' if damage_roll is not None else '', damage_roll or 0,
            'DirectDamageAdd' if penetration_roll is not None else '', penetration_roll or 0]

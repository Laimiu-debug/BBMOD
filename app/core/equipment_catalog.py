"""Offline equipment browsing; named ranges share the appraisal rules."""
from __future__ import annotations

from dataclasses import dataclass
from html import escape
import json

from .item_inspector import rolls_for
from .paths import resource_path

GROUPS = {'one_handed': '单手近战', 'two_handed': '双手近战', 'ranged': '远程 / 投掷',
          'armor': '身体护甲', 'helmet': '头盔', 'shield': '盾牌'}
RARITIES = {'regular': '普通', 'named': '红装', 'legendary': '传奇', 'special': '特殊条目'}

# name, stat keys, kind applicability, percent, offset key
STATS = (
    ('伤害', ('RegularDamage', 'RegularDamageMax'), ('weapon',), False, None),
    ('破甲效率', ('ArmorDamageMult',), ('weapon',), True, None),
    ('穿甲效率', ('DirectDamageAdd',), ('weapon',), True, 'DirectDamageMult'),
    ('护甲 / 耐久', ('ConditionMax',), ('weapon', 'armor', 'helmet', 'shield'), False, None),
    ('疲劳负担', ('StaminaModifier',), ('weapon', 'armor', 'helmet', 'shield'), False, None),
    ('近战防御', ('MeleeDefense',), ('shield',), False, None),
    ('远程防御', ('RangedDefense',), ('shield',), False, None),
    ('破盾伤害', ('ShieldDamage',), ('weapon',), False, None),
    ('额外爆头率（百分点）', ('ChanceToHitHead',), ('weapon',), False, None),
    ('额外命中', ('AdditionalAccuracy',), ('weapon',), False, None),
    ('弹药上限', ('AmmoMax',), ('weapon',), False, None),
    ('技能疲劳变化', ('FatigueOnSkillUse',), ('weapon', 'shield'), False, None),
    ('视野变化', ('Vision',), ('helmet',), False, None),
    ('攻击距离', ('RangeMin', 'RangeMax'), ('weapon',), False, None),
)


def load_equipment():
    return json.loads(resource_path('data/equipment_catalog.json').read_text('utf-8'))


def load_equipment_icons():
    return json.loads(resource_path('assets/equipment/manifest.json').read_text('utf-8'))


@dataclass(frozen=True)
class Attribute:
    label: str
    baseline: str
    display: str
    sort_key: tuple[float, ...] | None
    rule: str


def attributes(item):
    base = item['base']
    rolls = {roll.keys: roll for roll in rolls_for(item)} if item['rarity'] == 'named' else {}
    rows = []
    for label, keys, kinds, percent, offset in STATS:
        if item['kind'] not in kinds or (keys == ('ConditionMax',) and item['kind'] == 'weapon' and base['ConditionMax'] <= 1):
            rows.append(Attribute(label, '—', '—', None, '不适用'))
            continue
        values = tuple(base[key] + (base[offset] if offset else 0) for key in keys)
        baseline = '–'.join(f'{round(value * (100 if percent else 1), 4):g}' for value in values) + ('%' if percent else '')
        roll = rolls.get(keys)
        if roll:
            low = tuple(min(option[i] for option in roll.options) for i in range(len(keys)))
            high = tuple(max(option[i] for option in roll.options) for i in range(len(keys)))
            display = roll.format(low) + ' ～ ' + roll.format(high)
            rule = '抽中此词条时；未抽中保留基础值' if roll.optional else '每件独立随机'
            sortable = tuple(value + roll.offset for value in (*low, *high))
            rows.append(Attribute(label, baseline, display, sortable, rule))
        else:
            rows.append(Attribute(label, baseline, baseline, values, '固定基础值'))
    return rows


def matches(item, query='', group='', rarity=''):
    if group and item['group'] != group or rarity and item['rarity'] != rarity:
        return False
    haystack = ' '.join((item['zh'], item['en'], item['id'], item['category'],
                         GROUPS[item['group']], RARITIES[item['rarity']])).casefold()
    return all(word in haystack for word in query.casefold().split())


def detail_html(item, game_version, artwork=None):
    text = ('<h2>' + escape(item['zh']) + '</h2><p>' + escape(item['en']) + '</p><p>'
            + escape(GROUPS[item['group']] + ' · ' + RARITIES[item['rarity']]) + '</p>')
    if artwork and artwork.get('large'):
        image = resource_path('assets/equipment/' + artwork['large']).as_uri()
        text = '<table><tr><td width="155" align="center"><img src="' + escape(image, quote=True) + '"></td><td>' + text + '</td></tr></table>'
        text += '<p>原版装备外观示例，具体装备可能采用其他外观变体。</p>'
    elif artwork and artwork.get('reason'):
        text += '<p>' + escape(artwork['reason']) + '</p>'
    if item['category']:
        text += '<p>' + escape(item['category']) + '</p>'
    named = item['rarity'] == 'named'
    if named:
        rule = ('武器和盾牌随机抽取两组强化词条，不能同时取得表中所有强化。武器耐久另行随机；伤害上下限使用同一次随机倍率。'
                if item['kind'] in ('weapon', 'shield') else '护甲上限和疲劳负担分别随机，不含护甲附件。')
        text += '<p><b>' + rule + '</b></p>'
    text += '<table width="100%" cellspacing="0" cellpadding="8"><tr bgcolor="#d4c09a"><th align="left">属性</th><th align="left">基础值</th>'
    if named:
        text += '<th align="left">随机范围</th><th align="left">规则</th>'
    text += '</tr>'
    for row in attributes(item):
        if row.sort_key is None:
            continue
        text += '<tr><td>' + escape(row.label) + '</td><td>' + escape(row.baseline) + '</td>'
        if named:
            text += '<td>' + escape(row.display) + '</td><td>' + escape(row.rule) + '</td>'
        text += '</tr>'
    text += '</table><hr><p>疲劳负担越接近零越轻，技能疲劳变化越低越省力。</p>'
    if not item['loot']:
        text += '<p>此条目未设为常规战利品掉落；是否可获取取决于游戏事件等条件。</p>'
    text += ('<p>原版 ' + escape(game_version) + ' · 原始装备数值，不含角色技能、附件及装备特殊效果。'
             '红装范围沿用装备鉴定的离散随机规则，区间位置不代表实战强度。</p>')
    return text

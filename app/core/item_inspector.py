"""Read-only named-item appraisal using the game's actual randomized fields."""
from __future__ import annotations
from dataclasses import dataclass
import codecs
from html import unescape
from itertools import combinations
import json
import math
from pathlib import Path
import re
import struct

from .paths import resource_path

MARKER = 'BBMOD_ITEM_V1 '
FIELDS = ('ConditionMax StaminaModifier RegularDamage RegularDamageMax ArmorDamageMult DirectDamageMult '
          'DirectDamageAdd ChanceToHitHead ShieldDamage AmmoMax AdditionalAccuracy FatigueOnSkillUse MeleeDefense RangedDefense').split()


def catalog():
    return json.loads(resource_path('data/item_inspector/catalog.json').read_text('utf-8'))['items']


def number(value):
    return type(value) in (int, float) and math.isfinite(value) and abs(value) <= 1000000


def validate_event(data):
    if (isinstance(data, dict) and data.get('schema') == 1 and type(data.get('seq')) is int
            and data['seq'] >= 0 and type(data.get('token')) is int and 0 < data['token'] <= 2147483647
            and data.get('kind') == 'hover' and type(data.get('visible')) is bool):
        bounds = data.get('bounds')
        if bounds is not None and (not isinstance(bounds, list) or len(bounds) != 6
                or any(not number(x) or abs(x) > 32768 for x in bounds)
                or any(x <= 0 for x in bounds[2:])):
            raise ValueError('游戏提示框位置无效')
        return data
    if (not isinstance(data, dict) or data.get('schema') != 1 or type(data.get('seq')) is not int
            or data['seq'] < 0 or data.get('kind', 'item') != 'item'
            or ('token' in data and (type(data['token']) is not int or not 0 < data['token'] <= 2147483647))
            or not isinstance(data.get('id'), str) or not re.fullmatch(r'[a-zA-Z0-9_.-]{1,128}', data['id'])
            or not isinstance(data.get('name'), str) or len(data['name']) > 500
            or type(data.get('named')) is not bool or type(data.get('attachment')) is not bool
            or not isinstance(data.get('stats'), dict) or len(data['stats']) > len(FIELDS)
            or any(k not in FIELDS or not number(v) for k, v in data['stats'].items())):
        raise ValueError('装备读取数据不完整或格式不受支持')
    return data


class HoverSession:
    """Require a matching UI lifecycle event; an item record alone is not a hover."""
    timeout = 1.2

    def __init__(self):
        self.reset()

    def reset(self):
        self.item = None
        self.token = None
        self.visible = False
        self.heartbeat = 0
        self.sequence = -1
        self.bounds = None

    def accept(self, event, now):
        validate_event(event)
        if event['seq'] <= self.sequence:
            return
        self.sequence = event['seq']
        if event.get('kind') == 'hover':
            if event['token'] == self.token:
                self.visible = event['visible']
                self.heartbeat = now
                self.bounds = event.get('bounds')
        else:
            self.item, self.token = event, event.get('token')
            self.visible = False
            self.bounds = None

    def current(self, now):
        if (self.visible and self.item and self.item['named']
                and 0 <= now - self.heartbeat < self.timeout):
            return self.item
        return None


def f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


def scaled(value, percent):
    # Squirrel in the supported 32-bit game stores floating point values as F32.
    return f32(f32(value * percent) * f32(.01))


def rounded(value):
    return math.floor(value + .5)


@dataclass
class Roll:
    label: str
    keys: tuple[str, ...]
    baseline: tuple[float, ...]
    options: list[tuple[float, ...]]
    optional: bool = True
    lower_better: bool = False
    percent: bool = False
    offset: float = 0

    def matches(self, current, values):
        return all(abs(a - b) < .0001 for a, b in zip(current, values))

    def describe(self, stats):
        current = tuple(stats[k] for k in self.keys)
        low = tuple(min(x[i] for x in self.options) for i in range(len(self.keys)))
        high = tuple(max(x[i] for x in self.options) for i in range(len(self.keys)))
        rolled = any(self.matches(current, option) for option in self.options)
        base = self.optional and self.matches(current, self.baseline)
        score = None
        if rolled and not base:
            denominator = high[0] - low[0]
            fraction = (current[0] - low[0]) / denominator if denominator else 1
            score = round(100 * (1 - fraction if self.lower_better and denominator else fraction))
        state = '可能未抽中' if base and rolled else '未抽中' if base else '已抽中' if rolled else '超出原版范围'
        return {'label': self.label, 'value': self.format(current), 'range': self.format(low) + ' ～ ' + self.format(high),
                'score': score, 'state': state, 'valid': rolled or base}

    def format(self, values):
        return '–'.join(f'{((v + self.offset) * (100 if self.percent else 1)):g}' for v in values) + ('%' if self.percent else '')


def rolls_for(item):
    b, kind = item['base'], item['kind']
    rolls = []
    def add(label, keys, options, **kwargs):
        if isinstance(keys, str): keys = (keys,)
        rolls.append(Roll(label, keys, tuple(b[k] for k in keys),
                          [tuple(x) if isinstance(x, tuple) else (x,) for x in options], **kwargs))
    def scale(key, first, last, rounding=rounded):
        return [rounding(scaled(b[key], n)) for n in range(first, last + 1)]
    if kind in ('armor', 'helmet'):
        add('护甲上限', 'ConditionMax', scale('ConditionMax', 110, 125, math.floor), optional=False)
        start, end, cap = (3, 9, -8) if kind == 'armor' else (1, 4, -4)
        add('疲劳负担（越接近零越好）', 'StaminaModifier', [min(cap, b['StaminaModifier'] + n) for n in range(start, end + 1)], optional=False)
    elif kind == 'shield':
        add('近战防御', 'MeleeDefense', scale('MeleeDefense', 120, 140))
        add('远程防御', 'RangedDefense', scale('RangedDefense', 120, 140))
        add('耐久上限', 'ConditionMax', scale('ConditionMax', 120, 160))
        add('疲劳负担（越接近零越好）', 'StaminaModifier', scale('StaminaModifier', 70, 90))
        add('技能疲劳变化（越低越好）', 'FatigueOnSkillUse', [b['FatigueOnSkillUse'] - n for n in range(1, 4)], lower_better=True)
    else:
        # Damage endpoints share one roll, rather than two independent affixes.
        add('伤害', ('RegularDamage', 'RegularDamageMax'), [(rounded(f32(b['RegularDamage'] * f32(n * f32(.01)))),
            rounded(f32(b['RegularDamageMax'] * f32(n * f32(.01))))) for n in range(110, 131)])
        add('破甲效率', 'ArmorDamageMult', [f32(b['ArmorDamageMult'] + n * .01) for n in range(10, 31)], percent=True)
        add('穿甲效率', 'DirectDamageAdd', [f32(b['DirectDamageAdd'] + n * .01) for n in range(8, 17)], percent=True, offset=b['DirectDamageMult'])
        if b['ChanceToHitHead'] > 0:
            add('额外爆头率（百分点）', 'ChanceToHitHead', [b['ChanceToHitHead'] + n for n in range(10, 21)])
        if b['StaminaModifier'] <= -10:
            add('疲劳负担（越接近零越好）', 'StaminaModifier', scale('StaminaModifier', 50, 80))
        if b['ShieldDamage'] >= 16:
            add('破盾伤害', 'ShieldDamage', scale('ShieldDamage', 150, 200))
        if b['AmmoMax'] > 0:
            add('弹药上限', 'AmmoMax', [b['AmmoMax'] + n for n in range(1, 4)])
        if b['AdditionalAccuracy'] != 0 or item['ranged']:
            add('额外命中', 'AdditionalAccuracy', [b['AdditionalAccuracy'] + n for n in range(5, 16)])
        add('技能疲劳变化（越低越好）', 'FatigueOnSkillUse', [b['FatigueOnSkillUse'] - n for n in range(1, 4)], lower_better=True)
        if b['ConditionMax'] > 1:
            add('耐久上限', 'ConditionMax', scale('ConditionMax', 90, 140), optional=False)
    return rolls


def appraise(event, items=None):
    validate_event(event)
    if event.get('kind') == 'hover':
        raise ValueError('悬停状态不是装备数据')
    item = (items if items is not None else catalog()).get(event['id'])
    if not event['named'] or item is None:
        return {'supported': False, 'title': event['name'] or event['id'], 'rows': [],
                'message': '此装备不在原版红装范围表中（普通、传奇或 MOD 装备）。'}
    stats, rolls = event['stats'], rolls_for(item)
    required = {k for roll in rolls for k in roll.keys}
    if not required.issubset(stats):
        raise ValueError('装备字段不完整，请更新读取 MOD 后重新悬停')
    rows = [roll.describe(stats) for roll in rolls]
    optional = [roll for roll in rolls if roll.optional]
    valid = all(row['valid'] for row in rows)
    if optional:
        valid = valid and any(all(any(roll.matches(tuple(stats[k] for k in roll.keys), option) for option in roll.options)
              if i in selected else roll.matches(tuple(stats[k] for k in roll.keys), roll.baseline)
              for i, roll in enumerate(optional)) for selected in combinations(range(len(optional)), 2))
    # A mod may also alter a field that vanilla does not randomize for this base.
    if item['kind'] == 'weapon':
        for key in FIELDS:
            if key not in required and key in stats and abs(stats[key] - item['base'][key]) > .0001:
                valid = False
    note = ('数值符合原版随机规则。区间位置只表示该属性的高低，不代表实战强度或掉落概率。' if valid else
            '数值或词条组合与原版不符，可能受 MOD 或特殊效果影响；仅显示参考范围，不给出品质结论。')
    if event['attachment']:
        note += ' 护甲已按附件记录还原未加附件的数值。'
    if not valid:
        for row in rows: row['score'] = None
    return {'supported': True, 'valid': valid, 'title': item['zh'], 'english': item['en'],
            'instance': event['name'], 'rows': rows, 'message': note}


class HoverLog:
    """Bounded tail that starts at EOF, so yesterday's gear is never presented live."""
    def __init__(self, path: Path):
        self.path = path
        self.offset = None
        self.identity = None
        self.anchor = b''
        self.buffer = ''
        self.generation = 0
        self.decoder = codecs.getincrementaldecoder('utf-8')(errors='replace')

    def poll(self):
        try:
            with self.path.open('rb') as stream:
                stat = self.path.stat()
                identity = (stat.st_dev, stat.st_ino)
                if self.offset is None:
                    self.identity, self.offset = identity, stat.st_size
                    stream.seek(max(0, self.offset - 64)); self.anchor = stream.read(64)
                    return []
                stream.seek(max(0, self.offset - len(self.anchor)))
                if identity != self.identity or stat.st_size < self.offset or stream.read(len(self.anchor)) != self.anchor:
                    self.identity, self.offset, self.buffer, self.anchor = identity, 0, '', b''
                    self.generation += 1
                    self.decoder.reset()
                stream.seek(self.offset); raw = stream.read(256 * 1024); self.offset = stream.tell()
                stream.seek(max(0, self.offset - 64)); self.anchor = stream.read(min(64, self.offset))
        except OSError:
            return []
        self.buffer += self.decoder.decode(raw)
        events = []
        while MARKER in self.buffer:
            start = self.buffer.index(MARKER) + len(MARKER)
            candidate = unescape(self.buffer[start:])
            try:
                data, end = json.JSONDecoder().raw_decode(candidate)
            except ValueError:
                next_start = self.buffer.find(MARKER, start)
                if next_start >= 0:
                    self.buffer = self.buffer[next_start:]
                    continue
                if len(self.buffer) - start > 8192:
                    self.buffer = self.buffer[start:]
                    continue
                break
            try: events.append(validate_event(data))
            except ValueError: pass
            # Advance to the next marker using the raw stream, not decoded offsets.
            next_start = self.buffer.find(MARKER, start)
            self.buffer = self.buffer[next_start:] if next_start >= 0 else ''
        self.buffer = self.buffer[-8192:]
        return events

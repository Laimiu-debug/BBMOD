"""Transparent, themed assessments of recorded level-11 potential.

These are BBMOD presentation rules, not game ranks or historical comparisons.
Every threshold in a tier must pass; missing attributes never pass a tier.
"""
from dataclasses import dataclass

from .config_emitter import ATTRIBUTES


TIERS = ('待培养', '骁将档', '颜良文丑档', '关张档', '吕布档')
# Each tuple lists the thresholds for 骁将 / 颜良文丑 / 关张 / 吕布.
PROFILES = (
    ('猛将', ('MeleeSkill', 'MeleeDefense', 'Hitpoints', 'Stamina', 'Bravery'),
     ((80, 15, 75, 95, 40), (90, 25, 85, 105, 45),
      (95, 35, 95, 115, 55), (100, 40, 105, 125, 65))),
    ('神射', ('RangedSkill', 'Hitpoints', 'Stamina', 'Bravery'),
     ((85, 75, 95, 40), (90, 80, 100, 45),
      (95, 85, 110, 50), (100, 90, 120, 55))),
    ('盾卫', ('MeleeDefense', 'Hitpoints', 'Stamina', 'Bravery'),
     ((30, 90, 105, 55), (35, 100, 115, 60),
      (40, 110, 125, 65), (45, 120, 135, 70))),
    ('快剑', ('MeleeSkill', 'MeleeDefense', 'Initiative', 'Hitpoints'),
     ((85, 20, 150, 75), (90, 25, 160, 80),
      (95, 30, 170, 85), (100, 35, 180, 90))),
    ('统领', ('Bravery', 'Hitpoints', 'MeleeDefense'),
     ((80, 80, 20), (90, 90, 25), (100, 100, 30), (110, 110, 35))),
)


@dataclass(frozen=True)
class BrotherRating:
    rank: int
    title: str
    evidence: str

    @property
    def label(self):
        return f'{TIERS[self.rank]} · {self.title}' + ('方向' if self.rank == 0 else '')


def rate_brother(brother):
    candidates = []
    for title, keys, levels in PROFILES:
        if not all(key in brother.projected for key in keys):
            continue
        values = [brother.projected[key] for key in keys]
        rank = 0
        for level, thresholds in enumerate(levels, 1):
            if all(value >= threshold for value, threshold in zip(values, thresholds)):
                rank = level
        # The weakest required attribute determines progress toward the next tier.
        next_level = levels[min(rank, len(levels) - 1)]
        progress = min(value / threshold for value, threshold in zip(values, next_level))
        evidence = '、'.join(f'{ATTRIBUTES[key]}{value}' for key, value in zip(keys, values))
        candidates.append((rank, progress, BrotherRating(rank, title, evidence)))
    if not candidates:
        return None
    return max(candidates, key=lambda item: (item[0], item[1]))[2]


def rating_rules():
    lines = ['三国评价为本软件的潜力分档；按最擅长的方向取最高档，每档所有门槛均须满足。',
             '数值均为11级逐项成长预估，不能同时把全部属性都点满；未计装备、特技与实战配装。',
             '总星数不直接决定档位；特质对已记录属性的修正体现在数值中，特殊效果仍需另看特质。']
    for title, keys, levels in PROFILES:
        lines.append(title + '：')
        for rank, thresholds in enumerate(levels, 1):
            lines.append(TIERS[rank] + '：' + '、'.join(
                f'{ATTRIBUTES[key]}≥{value}' for key, value in zip(keys, thresholds)))
    return '\n'.join(lines)

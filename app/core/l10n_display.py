"""Expand reviewed name forms for display; never rename game/save entities."""
from __future__ import annotations

import json

from .paths import resource_path
from .place_names import load_policy

ENTRY = 'ui/mods/bbmod_l10n/name_forms.js'


def build_southern_name_parts(dictionary):
    """Recognize given name + family name + title without a huge cross product."""
    review = json.loads(resource_path('localization/name_order.json').read_text(encoding='utf-8'))
    result = {}
    for group, field in [('given', 'southern_given_names'), ('family', 'southern_family_names'),
                         ('titles', 'vizier_titles')]:
        terms = {}
        for source in review[field]:
            target = dictionary.get(source, '').strip()
            if not target:
                raise ValueError('人物或势力名称缺少译文：' + source)
            for variant in {source, target}:
                if variant in terms and terms[variant] != target:
                    raise ValueError('南方人物名称存在歧义：' + variant)
                terms[variant] = target
        result[group] = terms
    return result


def build_name_forms(catalog, dictionary):
    policy = load_policy(catalog)
    if not policy:
        return {}
    review = json.loads(resource_path('localization/name_order.json').read_text(encoding='utf-8'))
    forms = {}

    def translated(source):
        value = dictionary.get(source, '').strip()
        if not value:
            raise ValueError('人物或势力名称缺少译文：' + source)
        return value

    def add(source, target):
        if source in forms and forms[source] != target:
            raise ValueError('人物或势力名称存在歧义：' + source)
        forms[source] = target

    for name in policy['owner_pools']['CharacterNames']:
        chinese_name = translated(name)
        for title in review['council_titles']:
            chinese_title = translated(title)
            for original_name in {name, chinese_name}:
                for original_title in {title, chinese_title}:
                    add(original_name + ' ' + original_title, chinese_title + chinese_name)
    house_word = translated('House ')
    for name in review['noble_houses']:
        chinese_name = translated(name)
        for original_name in {name, chinese_name}:
            for prefix in {'House ', house_word + ' '}:
                add(prefix + original_name, chinese_name + house_word)
    return forms

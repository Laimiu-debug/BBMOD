import copy
from types import SimpleNamespace

import pytest

from core.full_l10n import load_full_catalog
from core.l10n_tokens import validate_translation
from core.place_names import (
    MANAGER_FILE, POOL_KEYS, allowed_pool_change, geographic_spans, load_policy,
    original_names, owner_pool_patches, preserve_inline_names,
)
from tools.prepare_place_names import contexts, geographic_context


def test_geographic_names_cover_cities_regions_camps_and_landmarks():
    catalog = load_full_catalog()
    policy = load_policy(catalog)
    names = original_names(catalog, policy)
    assert {'Wiesendorf', 'Stormy Sea', 'Icy Cave', 'Black Monolith', 'Ruins of '} <= names
    assert any('%randomname%' in name for name in names)
    assert any('%randomnoble%' in name for name in names)
    assert 'New Campaign' not in names
    assert policy['policy'] == 'original_english'


def test_equipment_and_contract_title_are_not_geographic_sites():
    catalog = load_full_catalog()
    policy = load_policy(catalog)
    assert not geographic_spans(policy, 'scripts/items/armor/named/green_coat_of_plates_armor.cnut')
    assert not geographic_spans(policy, 'scripts/contracts/contracts/hunting_sand_golems_contract.cnut')


def test_classification_does_not_confuse_settlement_description_with_its_name():
    file = 'scripts/entity/world/settlements/example.cnut'
    ctx = contexts('this.m.Name = this.getRandomName(["Riverford"]); this.m.Description = "A riverside village.";')
    assert geographic_context(file, ctx['Riverford'])
    assert not geographic_context(file, ctx['A riverside village.'])
    assert not geographic_context(file.replace('example.cnut', 'buildings/temple.cnut'), ctx['Riverford'])


def test_policy_fails_closed_for_different_game_sources():
    catalog = copy.deepcopy(load_full_catalog())
    catalog['files']['scripts/config/world_location_names.cnut']['sha256'] = 'changed'
    with pytest.raises(ValueError, match='不匹配'):
        load_policy(catalog)


def test_owner_names_redirect_only_inside_location_generator():
    literals = [SimpleNamespace(function='0.1', text=name, start=i*30, end=i*30+20)
                for i, name in enumerate(POOL_KEYS)]
    literals.append(SimpleNamespace(function='0.2', text='CharacterNames', start=90, end=110))
    parsed = SimpleNamespace(functions=[{'name': 'getUniqueLocationName', 'path': '0.1'},
                                       {'name': 'createCharacter', 'path': '0.2'}], literals=literals)
    patches, entries = owner_pool_patches(MANAGER_FILE, parsed)
    assert len(patches) == 2 and all(p[0] != 90 for p in patches)
    assert {e['translation'] for e in entries.values()} == set(POOL_KEYS.values())
    assert owner_pool_patches('scripts/other.cnut', parsed) == ([], {})
    assert not allowed_pool_change(MANAGER_FILE, 'createCharacter', 'CharacterNames', 'BBMODPlaceCharacterNames')
    assert not allowed_pool_change('scripts/other.cnut', 'getUniqueLocationName', 'CharacterNames', 'BBMODPlaceCharacterNames')
    assert not allowed_pool_change(MANAGER_FILE, 'getUniqueLocationName', 'CharacterNames', 'AnythingElse')
    assert not allowed_pool_change(MANAGER_FILE, 'getUniqueLocationName', 'OtherGameKey', None)


def test_static_story_mentions_preserve_markup_and_other_translation():
    source = '[img]gfx/ui/events/event_1.png[/img]{Visit the Black Monolith with %bro%.}'
    entry = {'source': source, 'translation': '[img]gfx/ui/events/event_1.png[/img]{与%bro%一同前往黑色巨石。}'}
    entries = {'story': entry, 'ordinary': {'source': 'Sword', 'translation': '剑'}}
    result = preserve_inline_names(entries, {'inline_mentions': {'story': {'黑色巨石': 'Black Monolith'}}})
    assert result['story']['translation'].endswith('与%bro%一同前往Black Monolith。}')
    assert validate_translation(source, result['story']['translation']) == []
    assert result['ordinary'] == entries['ordinary']
    assert entries['story'] == entry


def test_no_place_name_policy_for_ui_only_catalog():
    assert load_policy(None) is None
    assert load_policy({'files': {}, 'entries': {}}) is None


def test_published_inline_rules_match_their_english_source():
    catalog = load_full_catalog()
    policy = load_policy(catalog)
    entries = preserve_inline_names(catalog['entries'], policy)
    for key, replacements in policy['inline_mentions'].items():
        for chinese, english in replacements.items():
            assert english in entries[key]['translation']
            assert chinese not in entries[key]['translation']
        assert not validate_translation(entries[key]['source'], entries[key]['translation'])

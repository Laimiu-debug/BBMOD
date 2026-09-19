from core.full_l10n import load_full_catalog
from core.l10n import translated_catalog
from core.l10n_display import build_name_forms, build_person_names, build_city_places
from tools.prepare_full_catalog import reason


def test_plural_suffix_is_visible_only_in_battle_results():
    assert reason('s', 'scripts/states/tactical_state.cnut',
                  'tactical_combat_result_screen_onQueryCombatInformation', []) == 'visible_grammar'
    assert not reason('s', 'scripts/contracts/contract.cnut', 'getBanner', []).startswith('visible_')
    assert reason('s', 'scripts/states/tactical_state.cnut',
                  'tactical_combat_result_screen_onQueryCombatInformation', [], key=True) == 'program_key'


def test_composed_names_use_current_overrides_without_editing_saved_names():
    catalog = load_full_catalog()
    dictionary = translated_catalog({'Adler': '测试姓名', 'the Councilman': '测试职位', 'Grimmund': '测试家族名'})
    forms = build_name_forms(catalog, dictionary)
    assert forms['Adler the Councilman'] == '测试职位测试姓名'
    assert forms['测试姓名 测试职位'] == '测试职位测试姓名'
    assert forms['House Grimmund'] == '测试家族名家族'
    assert forms['家族 测试家族名'] == '测试家族名家族'
    assert 'Adler' not in forms
    assert '测试姓名' not in forms


def test_missing_name_translations_fail_before_packaging():
    import pytest
    dictionary = translated_catalog()
    dictionary.pop('the Councilman')
    with pytest.raises(ValueError, match='人物或势力名称缺少译文'):
        build_name_forms(load_full_catalog(), dictionary)


def test_geographic_person_names_include_original_and_custom_translations():
    dictionary = translated_catalog({'Edmund': '测试姓名'})
    names = build_person_names(load_full_catalog(), dictionary)
    assert names['Edmund'] == names['测试姓名'] == '测试姓名'
    assert 'Sommerstad' not in names
    assert 'of ' not in names
    dictionary.pop('Edmund')
    import pytest
    with pytest.raises(ValueError, match='人物或势力名称缺少译文'):
        build_person_names(load_full_catalog(), dictionary)


def test_southern_city_names_are_also_available_for_old_save_display():
    dictionary = translated_catalog({'Al-Hazif': '测试城邦'})
    cities = build_city_places(dictionary)
    assert len(cities) == 14
    assert cities['Al-Hazif'] == '测试城邦'
    assert 'Sommerstad' not in cities
    dictionary.pop('Al-Hazif')
    import pytest
    with pytest.raises(ValueError, match='城邦名称缺少译文'):
        build_city_places(dictionary)

import json
from pathlib import Path

import pytest

from core.full_l10n import load_full_catalog
from core.l10n import translated_catalog
from core.l10n_context import load_contextual_terms
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


COMPOSED_CASES = json.loads((Path(__file__).parent / 'fixtures/localization_composed_sentences.json').read_text(encoding='utf8'))


@pytest.fixture(scope='module')
def composed_dictionary():
    return translated_catalog()


@pytest.mark.parametrize('case', COMPOSED_CASES, ids=lambda case: case['name'])
def test_reviewed_fragments_form_complete_chinese_sentences(case, composed_dictionary):
    # Boundaries were checked against the original callers. Test the complete
    # sentence, including the otherwise invisible name/count insertion points.
    dictionary = composed_dictionary
    if 'context' in case:
        # Fragments shared by several scripts can carry a script-specific meaning.
        catalog = load_full_catalog()
        scoped = load_contextual_terms(catalog)[case['context']]
        dictionary = {**dictionary, **{catalog['entries'][key]['source']: value for key, value in scoped.items()}}
    text = ''.join(dictionary[part['source']] if 'source' in part else part['literal']
                   for part in case['parts'])
    for key, value in case['substitutions'].items():
        text = text.replace('%' + key + '%', value)
    assert text == case['expected']


@pytest.mark.parametrize('direction', ['北', '东北', '东', '东南', '南', '西南', '西', '西北'])
def test_contract_directions_work_for_all_eight_points(direction, composed_dictionary):
    tail = composed_dictionary[' %direction% of %origin%']
    text = composed_dictionary['Destroy '] + '黑石营地' + tail
    text = text.replace('%origin%', '石桥镇').replace('%direction%', direction)
    assert text == f'摧毁黑石营地，位于石桥镇的{direction}方'

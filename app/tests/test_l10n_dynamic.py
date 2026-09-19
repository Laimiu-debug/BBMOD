from core.full_l10n import load_full_catalog
from core.l10n import translated_catalog
from core.l10n_display import build_name_forms
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

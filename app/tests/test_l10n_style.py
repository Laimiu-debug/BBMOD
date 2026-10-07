from core.full_l10n import load_full_catalog
from core.l10n_style import normalize_spacing, paren_problems, reference_problems, spacing_problems


def test_catalog_has_no_spacing_bracket_or_name_reference_problems():
    catalog = load_full_catalog()
    assert spacing_problems(catalog['entries']) == []
    assert paren_problems(catalog) == []
    assert reference_problems(catalog['entries']) == []


def test_spacing_rule_keeps_branch_separators_and_fragment_boundaries():
    assert normalize_spacing('{胜利！ | 干掉了。}') == '{胜利！ | 干掉了。}'
    assert normalize_spacing(']+10[/color] 意志， [color=') == ']+10[/color]意志，[color='
    assert normalize_spacing('共 3 天') == '共3天'
    assert normalize_spacing(' 并命中 ') == ' 并命中 '


def _entry(source, translation, file='scripts/a.cnut'):
    return {'source': source, 'translation': translation, 'contexts': [{'file': file}]}


def test_quoted_name_must_match_its_translation():
    entries = {'n': _entry('Whipped', '遭受鞭笞'),
               'd': _entry("Gives the 'Whipped' effect.", '获得“鞭策”效果。')}
    assert reference_problems(entries) == ['d: 引用“Whipped”时应使用当前译名“遭受鞭笞”']
    entries['d']['translation'] = '获得“遭受鞭笞”效果。'
    assert reference_problems(entries) == []


def test_translated_half_of_a_bracket_follows_the_untranslated_half():
    catalog = {'entries': {'o': _entry(' breaks free (Chance: ', ' 挣脱束缚（几率：'),
                           'p': _entry('Bonus (now ', '加成（目前', 'scripts/b.cnut'),
                           'q': _entry(' so far).', '）。', 'scripts/b.cnut')},
               'files': {'scripts/a.cnut': {'patches': [[0, 1, 'o']]},
                         'scripts/b.cnut': {'patches': [[0, 1, 'p'], [2, 3, 'q']]}}}
    assert [p.split(':')[0] for p in paren_problems(catalog)] == ['o']
    catalog['entries']['q']['translation'] = ')。'
    assert {p.split(':')[0] for p in paren_problems(catalog)} == {'o', 'p', 'q'}

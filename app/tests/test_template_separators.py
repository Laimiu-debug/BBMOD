"""Regression cases observed in the original 1.5.2.3 template interpreter."""
from core.l10n_tokens import restore_template_separators, validate_translation


def test_original_engine_choice_delimiter_must_keep_spaces():
    source = "{Let's talk money. | What does it pay?}"
    collapsed = '{谈谈报酬吧。|这活儿给多少报酬？}'
    assert validate_translation(source, collapsed)
    repaired = restore_template_separators(source, collapsed)
    assert repaired == '{谈谈报酬吧。 | 这活儿给多少报酬？}'
    assert validate_translation(source, repaired) == []


def test_multiple_groups_keep_variables_markup_and_source_delimiters():
    source = '[img]art.png[/img]{%name% one. | %name% two.}\n{Three | Four}'
    repaired = restore_template_separators(source, '[img]art.png[/img]{%name%甲。|%name%乙。}\n{丙|丁}')
    assert validate_translation(source, repaired) == []
    assert repaired.count(' | ') == 2
    assert repaired.count('%name%') == 2


def test_literal_pipes_and_invalid_counts_are_not_invented_into_choices():
    assert restore_template_separators('A|B', '甲 | 乙') == '甲|乙'
    assert restore_template_separators('{A | B}', '{甲}') == '{甲}'
    assert validate_translation('{A | B}', '{甲}')

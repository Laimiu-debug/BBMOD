"""Only the audited stray digit in '2takes' may be omitted."""
import json
from pathlib import Path

from core.l10n_tokens import protected_tokens, validate_translation


CATALOG = Path(__file__).resolve().parents[1] / 'localization/full_catalog.json'
SOURCE = json.loads(CATALOG.read_text(encoding='utf8'))['entries']['1d93308f84c551079323']['source']
TRANSLATION = (
    '[img]gfx/ui/events/event_145.png[/img]{蛮族之王已死。%randombrother%'
    '收起他的头颅，你准备返回%employer%处。}'
)


def test_audited_misspelling_does_not_invent_a_chinese_quantity():
    assert '%randombrother% 2takes' in SOURCE
    assert protected_tokens(SOURCE)['numbers'] == {'2': 1}
    assert not validate_translation(SOURCE, TRANSLATION)
    assert '数字发生变化' in validate_translation(SOURCE, TRANSLATION.replace('头颅', '2颗头颅'))


def test_exception_requires_the_complete_original_source():
    # A changed upstream paragraph must be reviewed afresh, not silently exempted.
    assert '数字发生变化' in validate_translation(SOURCE + ' ', TRANSLATION)
    assert '数字发生变化' in validate_translation('He 2takes the head.', '他拿起头颅。')
    assert '数字发生变化' in validate_translation(SOURCE.replace('2takes', '3takes'), TRANSLATION)


def test_real_quantities_and_percentages_remain_protected():
    source = 'Pay 2 crowns for 20 arrows at 50% durability.'
    assert not validate_translation(source, '花费2克朗购买20支耐久为50%的箭。')
    assert '数字发生变化' in validate_translation(source, '花费克朗购买20支耐久为50%的箭。')
    assert '数字发生变化' in validate_translation(source, '花费2克朗购买21支耐久为50%的箭。')


def test_audited_source_still_protects_variables_and_markup():
    assert '剧情变量发生变化' in validate_translation(SOURCE, TRANSLATION.replace('%employer%', '雇主'))
    assert '排版标记或分支符号发生变化' in validate_translation(SOURCE, TRANSLATION.replace('event_145', 'event_146'))
    assert '排版标记或分支符号发生变化' in validate_translation(SOURCE, TRANSLATION[:-1])

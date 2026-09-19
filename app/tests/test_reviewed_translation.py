"""A checked narrative must win over a cached machine draft."""
import json
from pathlib import Path

from core.l10n_tokens import validate_translation
from tools.translate_full_catalog import fixed_text, job_parts, load_terms

ROOT = Path(__file__).resolve().parents[1]


def test_reviewed_onboarding_is_used_whole_with_markup_and_variables():
    reviewed = json.loads((ROOT/'localization/reviewed_onboarding.json').read_text(encoding='utf8'))['terms']
    refined = json.loads((ROOT/'localization/reviewed_refinement.json').read_text(encoding='utf8'))['terms']
    terms = load_terms()
    for source, value in reviewed.items():
        assert not validate_translation(source, value), source
        expected = refined.get(source, value)
        assert not validate_translation(source, expected), source
        assert job_parts(source, terms) == [(True, expected)], source


def test_reviewed_fragment_matches_trimmed_concatenation_part():
    terms = load_terms()
    assert fixed_text('is reborn by the power of the Lorekeeper!', terms) == '借助典籍守护者的力量重生了！'


def test_reviewed_equipment_and_contracts_are_preserved_whole():
    reviewed = json.loads((ROOT/'localization/reviewed_equipment_contracts.json').read_text(encoding='utf8'))['terms']
    refined = json.loads((ROOT/'localization/reviewed_refinement.json').read_text(encoding='utf8'))['terms']
    terms = load_terms()
    for source, value in reviewed.items():
        assert not validate_translation(source, value), source
        # Later editorial revisions still have to win as a complete template.
        expected = refined.get(source, value)
        assert not validate_translation(source, expected), source
        assert job_parts(source, terms) == [(True, expected)], source


def test_initial_review_preserves_variables_and_wins_over_machine_cache():
    reviewed = json.loads((ROOT/'localization/reviewed_initial.json').read_text(encoding='utf8'))['terms']
    refined = json.loads((ROOT/'localization/reviewed_refinement.json').read_text(encoding='utf8'))['terms']
    refined_fragments = {source.strip(): value.strip() for source, value in refined.items()}
    terms = load_terms()
    for source, value in reviewed.items():
        assert not validate_translation(source, value), source
        # An explicitly reviewed refinement supersedes an earlier reviewed draft.
        expected = refined_fragments.get(source, refined.get(source, value))
        assert not validate_translation(source, expected), source
        assert fixed_text(source, terms) == expected, source


def test_refined_necromancer_terminology_overrides_initial_review():
    source = 'You return to %employer% with the head of the necromancer.'
    expected = '你带着亡灵法师的头颅，返回%employer%那里。'
    assert job_parts(source, load_terms()) == [(True, expected)]


def test_refined_equipment_backgrounds_and_contracts_keep_complete_templates():
    reviewed = json.loads((ROOT/'localization/reviewed_refinement.json').read_text(encoding='utf8'))['terms']
    terms = load_terms()
    for source, value in reviewed.items():
        assert not validate_translation(source, value), source
        assert job_parts(source, terms) == [(True, value)], source


def test_generated_prose_rejects_unrelated_invented_scene():
    from tools.translate_full_catalog import content_warnings
    assert content_warnings('He nods at the scene.', '说着，他就朝厨房走去。')
    assert not content_warnings('He walks to the kitchen.', '他走向厨房。')


def test_draft_body_details_need_evidence_in_original():
    from tools.translate_full_catalog import content_warnings
    assert content_warnings('He grabs the weapon and leaves.', '他抓住鸡巴便走了。')
    assert content_warnings('She slowly raises her hand.', '她缓缓抬起乳房。')
    assert not content_warnings('The arrow struck his penis.', '箭射中了他的阴茎。')
    assert not content_warnings('The cow has a swollen udder.', '奶牛的乳房肿胀了。')

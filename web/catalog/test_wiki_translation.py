"""Regression tests for complete, revision-bound wiki prose translations."""
from copy import deepcopy
from contextlib import closing
import gzip
import html
import json
from pathlib import Path
import sqlite3
import tempfile

from bs4 import BeautifulSoup
from django.test import SimpleTestCase

from catalog.wiki_render import render_article, term_catalog
from catalog.wiki_store import search_expression
from catalog.wiki_translation import TranslationCatalog, TranslationError, extract_units, validate_unit
from tools.build_wiki import build
from tools.wiki_translation_units import exact_reuse_record, extract, game_matches, match_key, validate


def translation(unit, zh, status='reviewed', **extra):
    return {'id': unit.id, 'source_sha256': unit.source_sha256, 'source': unit.source,
            'zh': zh, 'status': status, **extra}


class WikiTranslationTests(SimpleTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def write(self, units, revisions=None, filename='prose.json'):
        document = {'schema_version': 1, 'kind': 'wiki_units',
                    'page_revisions': revisions or {'1': 10}, 'units': units}
        (self.root / filename).write_text(json.dumps(document, ensure_ascii=False), encoding='utf-8')
        return TranslationCatalog(self.root)

    def unit(self, body):
        units = extract_units(body)[1]
        self.assertEqual(len(units), 1)
        return units[0]

    def test_no_text_is_distinct_from_missing_translation(self):
        catalog = TranslationCatalog()
        for body in ('<p></p>', '<p><img src="/wiki/media/example.png"></p>',
                     '<table><tr><td>25%</td></tr></table>'):
            with self.subTest(body=body):
                info = catalog.apply(1, 10, body)['translation']
                self.assertTrue(info['no_translatable_text'])
                self.assertEqual((info['status'], info['review_status']), ('not_applicable', 'not_applicable'))
                self.assertEqual(info['total_blocks'], 0)
                self.assertFalse(info['review_complete'])
        info = catalog.apply(1, 10, '<p>This English still requires translation.</p>')['translation']
        self.assertFalse(info['no_translatable_text'])
        self.assertEqual((info['status'], info['untranslated_blocks']), ('untranslated', 1))

    def test_an_explicit_missing_translation_directory_is_an_error(self):
        with self.assertRaisesRegex(TranslationError, 'translation directory'):
            TranslationCatalog(self.root / 'missing')
        file_path = self.root / 'file.txt'
        file_path.write_text('not a directory', encoding='utf-8')
        with self.assertRaisesRegex(TranslationError, 'translation directory'):
            TranslationCatalog(file_path)
        self.assertEqual(TranslationCatalog(None).records, {})

    def test_paragraph_inline_list_and_table_are_whole_units(self):
        _, units = extract_units('<p>Use <a href="/wiki/read/Skill/">this <b>skill</b></a> wisely.</p>'
            '<ul><li>First <em>choice</em><ul><li>Nested choice.</li></ul></li></ul>'
            '<table><tr><td>Costs <strong>2</strong> points.</td><td>123</td></tr></table>')
        self.assertEqual([unit.source for unit in units], [
            'Use {#1}this {#2}skill{/#2}{/#1} wisely.',
            'First {#1}choice{/#1}', 'Nested choice.', 'Costs {#1}2{/#1} points.'])

    def test_old_term_decoration_is_not_source_prose(self):
        unit = self.unit('<p>Use <span class="w-term"><span class="w-term-en">Aim</span>'
                         '<span class="w-term-zh">瞄准</span></span> now.</p>')
        self.assertEqual(unit.source, 'Use Aim now.')

    def test_link_destinations_are_part_of_unit_identity(self):
        weapon = self.unit('<p><a href="/wiki/read/Cudgel/">Cudgel</a></p>')
        skill = self.unit('<p><a href="/wiki/read/Cudgel_(15_fatigue)/">Cudgel</a></p>')
        lang = self.unit('<p><a href="/wiki/read/Cudgel/?lang=zh">Cudgel</a></p>')
        self.assertNotEqual(weapon.id, skill.id)
        self.assertEqual(weapon.id, lang.id)
        self.assertNotEqual(self.unit('<p><a href="#w-A">See</a></p>').id,
                            self.unit('<p><a href="#w-B">See</a></p>').id)

    def test_sibling_spans_can_reorder_but_preserve_href(self):
        body = '<p>From <a href="/wiki/read/A/">A</a> to <a href="/wiki/read/B/">B</a>.</p>'
        unit = self.unit(body)
        catalog = self.write([translation(unit, '到{#2}乙{/#2}，从{#1}甲{/#1}出发。')])
        result = catalog.apply(1, 10, body)
        soup = BeautifulSoup(result['html_zh'], 'html.parser')
        self.assertEqual([(tag['href'], tag.text) for tag in soup.find_all('a')],
                         [('/wiki/read/B/', '乙'), ('/wiki/read/A/', '甲')])
        self.assertEqual(soup.div['lang'], 'zh-Hans')
        catalog.assert_used()

    def test_placeholder_deletion_duplication_crossing_and_parent_changes_fail(self):
        unit = self.unit('<p><a href="/wiki/read/A/">A <b>bold</b></a> and <i>B</i>.</p>')
        invalid = ['甲', '{#1}甲{/#1}{#2}乙{/#2}{#3}丙{/#3}',
                   '{#1}{#2}甲{/#1}{/#2}{#3}乙{/#3}',
                   '{#1}{#2}甲{/#2}{/#1}{#3}乙{/#3}{#3}乙{/#3}',
                   '{#1}{#2}甲{/#2}{/#1}{#3}乙{/#3}{#x}']
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(TranslationError):
                validate_unit(unit, translation(unit, value))

    def test_numbers_variables_and_html_are_guarded(self):
        unit = self.unit('<p>%name% receives +10% for 2 turns.</p>')
        validate_unit(unit, translation(unit, '%name%获得+10%，持续2回合。'))
        for value in ('%name%获得10%，持续2回合。', '此人获得+10%，持续2回合。',
                      '%name%获得+10%，持续3回合。', '%name%获得+10%，持续2回合。<img src=x>',
                      '%name%获得+10%，持续2回合。\x00'):
            with self.subTest(value=value), self.assertRaises(TranslationError):
                validate_unit(unit, translation(unit, value))

    def test_handedness_terms_only_have_explicit_numeric_equivalence(self):
        unit = self.unit('<p>A 2-handed weapon deals 23 damage.</p>')
        validate_unit(unit, translation(unit, '一件双手武器造成23伤害。'))
        for value in ('一件双手武器造成24伤害。', '一件单手武器造成23伤害。'):
            with self.subTest(value=value), self.assertRaises(TranslationError):
                validate_unit(unit, translation(unit, value))
        unit = self.unit('<p>A 1 handed weapon costs 10 points.</p>')
        validate_unit(unit, translation(unit, '一件单手武器消耗10点。'))
        unit = self.unit('<p>Companion (2Hand), 23 damage.</p>')
        validate_unit(unit, translation(unit, '老战友（双手），23伤害。'))
        for value in ('老战友（单手），23伤害。', '老战友（双手），24伤害。'):
            with self.subTest(value=value), self.assertRaises(TranslationError):
                validate_unit(unit, translation(unit, value))
        unit = self.unit('<p>Companion (1Hand)</p>')
        validate_unit(unit, translation(unit, '老战友（单手）'))
        for en, zh in (('Companion 1H', '老战友（单手）'), ('Companion 2H', '老战友（双手）')):
            unit = self.unit('<p>' + en + '</p>')
            validate_unit(unit, translation(unit, zh))
        for en, zh in (('Use 1hander for 23 damage.', '用单手武器造成23伤害。'),
                       ('Switch to 2handers for 23 damage.', '换上双手武器造成23伤害。'),
                       ('Switch to 2-handers for 23 damage.', '换上双手武器造成23伤害。'),
                       ('Use a 2handed weapon for 23 damage.', '用双手武器造成23伤害。'),
                       ('Swing (2h sword attack #3), Split (2h sword attack #2), 23 damage.', '挥砍（双手剑攻击#3），劈砍（双手剑攻击#2），23伤害。')):
            unit = self.unit('<p>' + en + '</p>')
            validate_unit(unit, translation(unit, zh))
            with self.assertRaisesRegex(TranslationError, 'Numbers changed'):
                validate_unit(unit, translation(unit, zh.replace('23', '24')))
        unit = self.unit('<p>Use 2handers.</p>')
        with self.assertRaisesRegex(TranslationError, 'Numbers changed'):
            validate_unit(unit, translation(unit, '使用单手武器。'))
        for source in ('1Hour', '1h'):
            unit = self.unit('<p>' + source + '</p>')
            with self.subTest(source=source), self.assertRaisesRegex(TranslationError, 'Numbers changed'):
                validate_unit(unit, translation(unit, '单手'))

    def test_lowercase_companion_handedness_requires_the_exact_background_label(self):
        for digit, term in (('1', '单手'), ('2', '双手')):
            unit = self.unit('<p>Possible starting gear: <a href="/wiki/read/Companion/">Companion (' + digit + 'h)</a>, 23 damage.</p>')
            validate_unit(unit, translation(unit, '可能的初始装备：{#1}老战友（' + term + '）{/#1}，23伤害。'))
            with self.assertRaisesRegex(TranslationError, 'Numbers changed'):
                validate_unit(unit, translation(unit, '可能的初始装备：{#1}老战友（' + term + '）{/#1}，24伤害。'))
        for source, zh in (('Companion (1h)', '老战友（双手）'),
                           ('Rest for 1h.', '休息单手。'),
                           ('Guard (2h)', '卫兵（双手）'),
                           ('Companion (1h), 1-handed weapon.', '老战友（单手），武器。'),
                           ('Companion (2h), wait 2h.', '老战友（双手），等待。'),
                           ('Wait 2h with a 2h sword.', '拿着双手剑等待。'),
                           ('2h sword attack #3.', '单手剑攻击#3。')):
            unit = self.unit('<p>' + source + '</p>')
            with self.subTest(source=source), self.assertRaisesRegex(TranslationError, 'Numbers changed'):
                validate_unit(unit, translation(unit, zh))

    def test_compound_handedness_does_not_hide_ranges_or_reuse_chinese_terms(self):
        unit = self.unit('<p>Attacks of 1- and 2-handed <a href="/wiki/read/Cleavers/">Cleavers</a> deal 23 damage.</p>')
        validate_unit(unit, translation(unit, '单手与双手{#1}斩刀{/#1}的攻击造成23伤害。'))
        for value in ('双手{#1}斩刀{/#1}的攻击造成23伤害。', '单手与双手{#1}斩刀{/#1}的攻击造成24伤害。'):
            with self.subTest(value=value), self.assertRaises(TranslationError):
                validate_unit(unit, translation(unit, value))
        unit = self.unit('<p>1- and 2-handed weapons, and a 1-handed attack.</p>')
        with self.assertRaisesRegex(TranslationError, 'Numbers changed'):
            validate_unit(unit, translation(unit, '单手与双手武器，以及一次攻击。'))
        for source in ('1-2 damage.', '1- and 3-handed weapons.'):
            unit = self.unit('<p>' + source + '</p>')
            with self.subTest(source=source), self.assertRaisesRegex(TranslationError, 'Numbers changed'):
                validate_unit(unit, translation(unit, '单手与双手武器。'))

    def test_signed_numbers_next_to_inline_labels_and_wrapped_digits(self):
        unit = self.unit('<p>Minstrel<br>+1 point, +<b>10</b>% chance.</p>')
        validate_unit(unit, translation(unit, '吟游诗人{#1/}+1点，+{#2}10{/#2}%概率。'))
        validate_unit(unit, translation(unit, '吟游诗人{#1/}+ 1点，+{#2}10{/#2}%概率。'))
        for zh in ('吟游诗人{#1/}1点，+{#2}10{/#2}%概率。', '吟游诗人{#1/}+1点，{#2}10{/#2}%概率。'):
            with self.subTest(zh=zh), self.assertRaises(TranslationError):
                validate_unit(unit, translation(unit, zh))

    def test_illustrated_talent_probability_separator_is_not_a_negative_modifier(self):
        unit = self.unit('<p><img src="/star.png" alt="1 Star Talent"> - 60% chance</p>')
        validate_unit(unit, translation(unit, '{#1/}——概率60%'))
        penalty = self.unit('<p>Penalty - 60% chance</p>')
        with self.assertRaisesRegex(TranslationError, 'Numbers changed'):
            validate_unit(penalty, translation(penalty, '概率60%'))

    def test_both_map_dimensions_remain_numeric(self):
        unit = self.unit('<p>The map is 140x140.</p>')
        validate_unit(unit, translation(unit, '地图大小为140×140。'))
        for value in ('地图大小为140×139。', '地图大小为140x139。'):
            with self.subTest(value=value), self.assertRaisesRegex(TranslationError, 'Numbers changed'):
                validate_unit(unit, translation(unit, value))

    def test_unicode_minus_cannot_be_silently_lost(self):
        unit = self.unit('<p>A penalty of −10% for 2 turns.</p>')
        validate_unit(unit, translation(unit, '惩罚为-10%，持续2回合。'))
        with self.assertRaisesRegex(TranslationError, 'Numbers changed'):
            validate_unit(unit, translation(unit, '惩罚为10%，持续2回合。'))

    def test_compact_level_labels_are_checked_without_affecting_character_identifiers(self):
        unit = self.unit('<p>Brother1 and the others are average lvl14.</p>')
        validate_unit(unit, translation(unit, '弟兄甲和其他人平均为14级。'))
        for zh in ('弟兄甲和其他人平均为15级。', '弟兄甲和其他人都达到了一定等级。'):
            with self.subTest(zh=zh), self.assertRaisesRegex(TranslationError, 'Numbers changed'):
                validate_unit(unit, translation(unit, zh))

    def test_approximate_english_numeric_bands_do_not_become_negative_modifiers(self):
        unit = self.unit('<p>mid-200s, low/mid-200s, mid/high-300s and mid/high 200s; -5 damage.</p>')
        zh = '200多点中段、200多点低段或中段、300多点中段或高段和200多点中段或高段；-5伤害。'
        validate_unit(unit, translation(unit, zh))
        for bad in (zh.replace('300', '200'), zh.replace('-5', '5')):
            with self.subTest(bad=bad), self.assertRaisesRegex(TranslationError, 'Numbers changed'):
                validate_unit(unit, translation(unit, bad))
        unit = self.unit('<p>high-200</p>')
        with self.assertRaisesRegex(TranslationError, 'Numbers changed'):
            validate_unit(unit, translation(unit, '高200'))

    def test_hyphenated_level_labels_preserve_actual_negative_values(self):
        unit = self.unit('<p>A level-11 recruit and level-25 veteran take -11 damage.</p>')
        zh = '一名11级新兵和25级老兵受到-11伤害。'
        validate_unit(unit, translation(unit, zh))
        for bad in (zh.replace('25级', '24级'), zh.replace('-11伤害', '11伤害')):
            with self.subTest(bad=bad), self.assertRaisesRegex(TranslationError, 'Numbers changed'):
                validate_unit(unit, translation(unit, bad))

    def test_both_compact_duel_counts_remain_numeric(self):
        unit = self.unit('<p>The barbarians offer a 1vs1 duel.</p>')
        validate_unit(unit, translation(unit, '蛮族提出进行1对1的决斗。'))
        for value in ('蛮族提出进行1对2的决斗。', '蛮族提出进行1人的决斗。'):
            with self.subTest(value=value), self.assertRaisesRegex(TranslationError, 'Numbers changed'):
                validate_unit(unit, translation(unit, value))

    def test_source_hash_and_revision_changes_fail(self):
        unit = self.unit('<p>Original prose.</p>')
        for key, value in [('id', 'u-' + '0' * 24), ('source_sha256', '0' * 64), ('source', 'Changed prose.')]:
            record = translation(unit, '原正文。')
            record[key] = value
            with self.subTest(key=key), self.assertRaises(TranslationError):
                validate_unit(unit, record)
        catalog = self.write([translation(unit, '原正文。')])
        with self.assertRaisesRegex(TranslationError, 'revision changed'):
            catalog.validate_revisions([{'id': 1, 'revision': 11}])
        with self.assertRaisesRegex(TranslationError, 'revision changed'):
            catalog.apply(1, 11, '<p>Original prose.</p>')

    def test_coverage_and_review_are_independent_and_english_is_retained(self):
        body = '<div lang="en"><p>First sentence.</p><p>Second sentence.</p><p>Third sentence.</p></div>'
        units = extract_units(body)[1]
        catalog = self.write([translation(units[0], '第一句。'), translation(units[1], '第二句。', 'translated')])
        result = catalog.apply(1, 10, body)
        info = result['translation']
        self.assertEqual((info['status'], info['review_status']), ('partial', 'partial'))
        self.assertEqual((info['total_blocks'], info['translated_blocks'], info['reviewed_blocks']), (3, 2, 1))
        self.assertFalse(info['review_complete'])
        self.assertIn('<span lang="en">Third sentence.</span>', result['html_zh'])
        self.assertEqual(result['summary_zh'], '第一句。 第二句。')
        self.assertEqual(body, '<div lang="en"><p>First sentence.</p><p>Second sentence.</p><p>Third sentence.</p></div>')

    def test_complete_initial_translation_does_not_claim_review(self):
        unit = self.unit('<p>Complete text.</p>')
        catalog = self.write([translation(unit, '完整文本。', 'translated')])
        info = catalog.apply(1, 10, '<p>Complete text.</p>')['translation']
        self.assertEqual((info['status'], info['review_status'], info['reviewed_blocks']), ('complete', 'unreviewed', 0))
        self.assertFalse(info['review_complete'])

    def test_empty_catalog_does_not_claim_chinese_prose(self):
        result = TranslationCatalog().apply(1, 10, '<p>English only.</p>')
        self.assertEqual(result['html_zh'], '')
        self.assertEqual(result['summary_zh'], '')
        self.assertEqual(result['translation']['status'], 'untranslated')
        self.assertEqual(TranslationCatalog().apply(1, 10, '', applicable=False)['translation']['status'], 'not_applicable')

    def test_headings_populate_section_titles_without_changing_anchors(self):
        body = '<h2 id="w-Stats"><span>Statistics</span></h2><p>Details.</p>'
        unit = extract_units(body)[1][0]
        catalog = self.write([translation(unit, '{#1}属性统计{/#1}')])
        result = catalog.apply(1, 10, body, [{'title': 'Statistics', 'anchor': 'w-Stats'}])
        self.assertEqual(result['sections'][0], {'title': 'Statistics', 'title_zh': '属性统计', 'anchor': 'w-Stats'})
        self.assertIn('id="w-Stats"', result['html_zh'])

    def test_images_formula_and_final_sanitization(self):
        body = '<p onclick="bad()">A <img src="/wiki/media/abc.png" alt="Icon" onerror="bad()">'
        body += '<math><mi>x</mi><mo>+</mo><mn>2</mn></math><a href="javascript:bad()">link</a>.</p>'
        unit = self.unit(body)
        catalog = self.write([translation(unit, '甲{#1/}{#2/}{#3}链接{/#3}。')])
        result = catalog.apply(1, 10, body)
        self.assertIn('<math>', result['html_zh'])
        self.assertIn('<mn>2</mn>', result['html_zh'])
        self.assertIn('src="/wiki/media/abc.png"', result['html_zh'])
        for forbidden in ('onclick', 'onerror', 'javascript:'):
            self.assertNotIn(forbidden, result['html_zh'])

    def test_reviewed_duplicate_image_exception_is_narrow(self):
        duplicate = '<a href="https://example.org/Tier_3_%282019%29.png"><img src="/wiki/media/icon12.png" width="40"/></a>'
        body = '<p><img src="/wiki/media/icon12.png">' + html.escape(duplicate) + ' 2 Ammo</p>'
        unit = self.unit(body)
        record = translation(unit, '{#1/}2 弹药', source_exception={
            'kind': 'escaped_image_markup', 'source': duplicate, 'reason': 'Upstream duplicated the existing icon as escaped markup.'})
        catalog = self.write([record])
        result = catalog.apply(1, 10, body)
        soup = BeautifulSoup(result['html_zh'], 'html.parser')
        self.assertEqual(len(soup.find_all('img')), 1)
        self.assertEqual(soup.get_text(strip=True), '2 弹药')
        for change in ({'status': 'translated'}, {'zh': '{#1/}3 弹药'},
                       {'source_exception': {**record['source_exception'], 'source': '2 Ammo'}},
                       {'source_exception': {**record['source_exception'], 'source': duplicate.replace('icon12', 'other')}}):
            with self.subTest(change=change), self.assertRaises(TranslationError):
                validate_unit(unit, {**record, **change})

    def test_context_specific_translation_and_no_last_writer_wins(self):
        unit = self.unit('<td>A</td>')
        records = [translation(unit, '一名', page_ids=[1]), translation(unit, '甲级', page_ids=[2])]
        catalog = self.write(records, {'1': 10, '2': 20})
        self.assertIn('一名', catalog.apply(1, 10, '<td>A</td>')['html_zh'])
        self.assertIn('甲级', catalog.apply(2, 20, '<td>A</td>')['html_zh'])
        catalog.assert_used()
        with self.assertRaisesRegex(TranslationError, 'Conflicting duplicate'):
            self.write(records + [translation(unit, '另一译文', page_ids=[1])], {'1': 10, '2': 20})

    def test_each_translation_record_must_match_its_own_scope(self):
        unit = self.unit('<p>Text.</p>')
        catalog = self.write([translation(unit, '文本。', page_ids=[1]), translation(unit, '文本。', page_ids=[2])],
                             {'1': 10, '2': 20})
        catalog.apply(1, 10, '<p>Text.</p>')
        with self.assertRaisesRegex(TranslationError, 'did not match'):
            catalog.assert_used()
        with self.assertRaisesRegex(TranslationError, 'outside revision-locked'):
            self.write([translation(unit, '文本。', page_ids=[3])])

    def test_duplicate_json_keys_and_conflicting_titles_fail(self):
        (self.root / 'bad.json').write_text('{"schema_version":1,"schema_version":1}', encoding='utf-8')
        with self.assertRaisesRegex(TranslationError, 'Duplicate JSON key'):
            TranslationCatalog(self.root)
        (self.root / 'bad.json').unlink()
        for name, value in [('a.json', '甲'), ('b.json', '乙')]:
            (self.root / name).write_text(json.dumps({'schema_version': 1, 'titles': {'Test': value}}), encoding='utf-8')
        with self.assertRaisesRegex(TranslationError, 'Conflicting title'):
            TranslationCatalog(self.root)

    def test_final_game_display_labels_override_old_terms_without_importing_name_pools(self):
        path = self.root / 'game.json'
        path.write_text(json.dumps({'entries': {
            'resolve': {'source': 'Resolve', 'translation': '决心', 'status': 'reviewed',
                        'contexts': [{'reason': 'visible_field'}]},
            'wolf': {'source': 'Wolf', 'translation': '沃尔夫', 'status': 'reviewed',
                     'contexts': [{'file': 'scripts/config/character_names.cnut', 'reason': 'visible_name_or_term'}]},
            'cudgel': {'source': 'Cudgel', 'translation': '短棒', 'status': 'reviewed',
                       'contexts': [{'file': 'scripts/items/weapons/cudgel.cnut', 'reason': 'visible_field'},
                                    {'file': 'scripts/skills/actives/cudgel_skill.cnut', 'reason': 'visible_field'}]}},
            'display_fallbacks': {'Resolve': '意志', 'Melee Skill': '近战命中', 'Ranged Skill': '远程命中',
                                  'Brawny': '壮硕', 'Student': '好学', 'Wolf': '沃尔夫', 'Cudgel': '短棒'}}), encoding='utf-8')
        terms, _ = term_catalog(path)
        for en, zh in [('resolve', '意志'), ('melee skill', '近战命中'), ('ranged skill', '远程命中'),
                       ('brawny', '壮硕'), ('student', '好学')]:
            self.assertEqual(terms[en][1], zh)
        self.assertNotIn('wolf', terms)
        self.assertNotIn('cudgel', terms)

    def test_game_match_normalization_is_exact_and_preserves_real_variables(self):
        path = self.root / 'game.json'
        entries = {
            'one': {'source': '[img]gfx/ui/events/event_75.png[/img]First paragraph.\\n\\n%SPEECH_ON%Hello, %name%.%SPEECH_OFF%',
                    'translation': '[img]gfx/ui/events/event_75.png[/img]第一段。\n\n%SPEECH_ON%你好，%name%。%SPEECH_OFF%', 'status': 'reviewed'},
            'two': {'source': 'One.\n\nTwo.', 'translation': '只剩一段。', 'status': 'reviewed'},
            'three': {'source': 'Not reviewed.', 'translation': '未复核。', 'status': 'translated'},
            'terrain': {'source': '%terrainImage%Travel through %terrain%.',
                        'translation': '%terrainImage%穿过%terrain%。', 'status': 'reviewed'},
            'town': {'source': '%townImage%Visit %townname%.',
                     'translation': '%townImage%前往%townname%。', 'status': 'reviewed'}}
        path.write_text(json.dumps({'entries': entries}), encoding='utf-8')
        matches = game_matches(path)
        self.assertEqual(matches['First paragraph.'][0]['translation'], '第一段。')
        self.assertEqual(matches[match_key('“Hello, %name%.”')][0]['translation'], '"你好，%name%。"')
        self.assertNotIn('Hello, Bob.', matches)
        self.assertNotIn('first paragraph.', matches)
        self.assertNotIn('One.', matches)
        self.assertNotIn('Not reviewed.', matches)
        self.assertFalse(any('gfx/' in key for key in matches))
        self.assertEqual(matches['Travel through %terrain%.'][0]['translation'], '穿过%terrain%。')
        self.assertEqual(matches['Visit %townname%.'][0]['translation'], '前往%townname%。')
        self.assertNotIn('Travel through .', matches)
        self.assertNotIn('Visit .', matches)

    def test_exact_game_reuse_preserves_whole_wrappers_and_refuses_fragment_guessing(self):
        unit = self.unit('<p><i>Keep 2 points.</i></p>')
        record = exact_reuse_record({**unit.record(), 'page_ids': [1]}, [{'translation': '保留2点。'}])
        self.assertEqual(record['zh'], '{#1}保留2点。{/#1}')
        inside = self.unit('<p>Keep <b>2</b> points.</p>')
        with self.assertRaisesRegex(TranslationError, 'positioning'):
            exact_reuse_record({**inside.record(), 'page_ids': [1]}, [{'translation': '保留2点。'}])
        with self.assertRaisesRegex(TranslationError, 'Ambiguous'):
            exact_reuse_record({**unit.record(), 'page_ids': [1]}, [{'translation': '保留2点。'}, {'translation': '留出2点。'}])

    def test_retention_scope_is_explicit_and_checks_complete_source_membership(self):
        body = '<p>Original English.</p>'
        unit = self.unit(body)
        self.write([translation(unit, '原文中文。', page_ids=[1, 2])], {'1': 10, '2': 20})
        document = {'schema_version': 1, 'kind': 'wiki_translation_scope', 'retained_english': {
            'source_category': 'Developer Posts', 'reason': '历史日志保留英文。',
            'pages': [{'id': 1, 'title': 'Historical post', 'revision': 10}]}}
        (self.root / 'scope.json').write_text(json.dumps(document), encoding='utf-8')
        catalog = TranslationCatalog(self.root)
        rows = [{'id': 1, 'title': 'Historical post', 'revision': 10, 'namespace': 0,
                 'categories_json': '["Developer Posts"]'}]
        catalog.validate_revisions([*rows, {'id': 2, 'revision': 20}])
        catalog.validate_retention_sources(rows)
        with self.assertRaisesRegex(TranslationError, 'identity/category'):
            catalog.validate_retention_sources([{**rows[0], 'categories_json': '[]'}])
        with self.assertRaisesRegex(TranslationError, 'identity/category'):
            catalog.validate_retention_sources([{**rows[0], 'title': 'Renamed post'}])
        with self.assertRaisesRegex(TranslationError, 'membership'):
            catalog.validate_retention_sources([*rows, {**rows[0], 'id': 3}])
        with self.assertRaisesRegex(TranslationError, 'revision changed'):
            catalog.validate_revisions([{**rows[0], 'revision': 11}, {'id': 2, 'revision': 20}])
        result = catalog.apply(1, 10, body)
        self.assertTrue(result['translation']['retained_english'])
        self.assertEqual(result['html_zh'], '')
        self.assertEqual(catalog.suppressed_translation_records, 0)
        # One retained page must not hide an unmatched record's other page scope.
        with self.assertRaisesRegex(TranslationError, 'did not match'):
            catalog.assert_used()


class WikiTranslationBuildTests(SimpleTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'source'
        (self.source / 'pages').mkdir(parents=True)
        self.catalog = self.root / 'catalog.json'
        self.catalog.write_text(json.dumps({'source_game': 'test', 'entries': {}}), encoding='utf-8')
        row = {'pageid': 1, 'title': 'Test', 'ns': 0, 'lastrevid': 10}
        (self.source / 'inventory.json').write_text(json.dumps({'pages': [row], 'retrieved_at': 'today',
            'statistics': {}, 'rights': {'text': 'CC-BY-SA'}}), encoding='utf-8')
        self.parsed = {'title': 'Test', 'revid': 10, 'text': '<h2 id="Stats">Statistics</h2><p>Keep 2 points.</p><p>English remains.</p>',
                       'wikitext': 'Original English source', 'categories': [], 'images': [],
                       'sections': [{'line': 'Statistics', 'anchor': 'Stats', 'level': '2'}]}
        (self.source / 'pages/1.json.gz').write_bytes(gzip.compress(json.dumps({'page': row,
            'requested_revision': 10, 'response': {'parse': self.parsed}, 'retrieved_at': 'today'}).encode()))
        self.original = render_article(self.parsed, {}, {'Test': 'Test', 'test': 'Test'}, {}, {})
        self.translations = self.root / 'translations'
        self.translations.mkdir()
        units = extract_units(self.original['html'])[1]
        records = [translation(units[0], '属性统计'), translation(units[1], '保留2点。', 'translated')]
        (self.translations / 'prose.json').write_text(json.dumps({'schema_version': 1, 'kind': 'wiki_units',
            'page_revisions': {'1': 10}, 'units': records}, ensure_ascii=False), encoding='utf-8')
        (self.translations / 'titles.json').write_text(json.dumps({'schema_version': 1, 'titles': {'Test': '测试词条'}}), encoding='utf-8')

    def test_build_retains_originals_searches_chinese_and_reports_truthful_coverage(self):
        release = build(self.source, self.root / 'wiki', self.catalog, activate=True, translations=self.translations)
        with closing(sqlite3.connect(release / 'wiki.sqlite3')) as db:
            db.row_factory = sqlite3.Row
            row = db.execute('SELECT * FROM pages WHERE id=1').fetchone()
            self.assertEqual(row['html'], self.original['html'])
            self.assertEqual(row['source_text'], 'Original English source')
            self.assertEqual(row['title_zh'], '测试词条')
            self.assertIn('保留2点', row['html_zh'])
            self.assertIn('English remains.', row['html_zh'])
            self.assertNotIn('English', row['summary_zh'])
            self.assertEqual(json.loads(row['sections_json'])[0]['title_zh'], '属性统计')
            info = json.loads(row['translation_json'])
            self.assertEqual((info['status'], info['review_status']), ('partial', 'partial'))
            self.assertEqual(db.execute("SELECT rowid FROM page_search WHERE page_search MATCH '保留'").fetchone()[0], 1)
            self.assertEqual(db.execute("SELECT rowid FROM page_search WHERE page_search MATCH 'English'").fetchone()[0], 1)
        report = json.loads((release / 'report.json').read_text(encoding='utf-8'))
        self.assertEqual(report['translation']['translated_blocks'], 2)
        self.assertEqual(report['translation']['reviewed_blocks'], 1)
        self.assertEqual(report['translation']['reviewed_titles'], 1)
        validation = validate(release / 'wiki.sqlite3', self.translations, self.root / 'validation.json')
        self.assertEqual(validation['status'], 'valid')
        corpus = self.root / 'corpus'
        extracted = extract(release / 'wiki.sqlite3', corpus, self.catalog, source=self.source)
        self.assertEqual((extracted['pages'], extracted['total_units']), (1, 3))
        self.assertEqual(json.loads((corpus / 'pages.json').read_text())['pages']['1']['revision'], 10)

    def test_stale_translation_cannot_activate_snapshot(self):
        path = self.translations / 'prose.json'
        document = json.loads(path.read_text(encoding='utf-8'))
        document['page_revisions']['1'] = 9
        path.write_text(json.dumps(document), encoding='utf-8')
        with self.assertRaisesRegex(TranslationError, 'revision changed'):
            build(self.source, self.root / 'wiki', self.catalog, activate=True, translations=self.translations)
        self.assertFalse((self.root / 'wiki/current.json').exists())

    def test_red_equipment_search_alias_keeps_canonical_title(self):
        path = self.source / 'inventory.json'
        inventory = json.loads(path.read_text(encoding='utf-8'))
        inventory['pages'][0]['title'] = 'Named Greatsword'
        path.write_text(json.dumps(inventory), encoding='utf-8')
        path = self.source / 'pages/1.json.gz'
        document = json.loads(gzip.decompress(path.read_bytes()))
        document['page']['title'] = 'Named Greatsword'
        document['response']['parse']['title'] = 'Named Greatsword'
        path.write_bytes(gzip.compress(json.dumps(document).encode()))
        (self.translations / 'titles.json').write_text(json.dumps({'schema_version': 1,
            'titles': {'Named Greatsword': '名贵巨剑'}}), encoding='utf-8')
        release = build(self.source, self.root / 'wiki', self.catalog, translations=self.translations)
        with closing(sqlite3.connect(release / 'wiki.sqlite3')) as db:
            self.assertEqual(db.execute('SELECT title_zh FROM pages WHERE id=1').fetchone()[0], '名贵巨剑')
            self.assertEqual(db.execute('SELECT rowid FROM page_search WHERE page_search MATCH ?',
                (search_expression('红装巨剑'),)).fetchone()[0], 1)

    def test_explicit_retained_english_policy_preserves_source_and_excludes_coverage(self):
        source_path = self.source / 'pages/1.json.gz'
        source = json.loads(gzip.decompress(source_path.read_bytes()))
        source['response']['parse']['categories'] = [{'category': 'Developer_Posts'}]
        source_path.write_bytes(gzip.compress(json.dumps(source).encode()))
        (self.translations / 'scope.json').write_text(json.dumps({
            'schema_version': 1, 'kind': 'wiki_translation_scope', 'retained_english': {
                'source_category': 'Developer Posts', 'reason': '历史日志保留英文。',
                'pages': [{'id': 1, 'revision': 10, 'title': 'Test'}]}}), encoding='utf-8')
        release = build(self.source, self.root / 'wiki', self.catalog, translations=self.translations)
        with closing(sqlite3.connect(release / 'wiki.sqlite3')) as db:
            db.row_factory = sqlite3.Row
            row = db.execute('SELECT * FROM pages WHERE id=1').fetchone()
            self.assertEqual(row['html'], self.original['html'])
            self.assertEqual(row['source_text'], 'Original English source')
            self.assertEqual((row['title_zh'], row['html_zh'], row['summary_zh']), ('', '', ''))
            self.assertNotIn('title_zh', json.loads(row['sections_json'])[0])
            info = json.loads(row['translation_json'])
            self.assertTrue(info['retained_english'])
            self.assertEqual(info['status'], 'not_applicable')
            self.assertEqual((info['translated_blocks'], info['untranslated_blocks'], info['excluded_blocks']), (0, 0, 3))
        report = json.loads((release / 'report.json').read_text())['translation']
        self.assertEqual((report['retained_english_pages'], report['retained_english_blocks']), (1, 3))
        self.assertEqual(report['total_blocks'], 0)
        self.assertEqual(report['source_words'], 0)
        self.assertEqual(report['suppressed_translation_records'], 2)
        validated = validate(release / 'wiki.sqlite3', self.translations, self.root / 'retained.json')
        self.assertEqual(validated['totals']['retained_english_pages'], 1)
        self.assertEqual(validated['totals'].get('untranslated_blocks', 0), 0)

    def test_translated_redirects_and_red_equipment_aliases_find_the_destination(self):
        titles = [('Feathered Nasal Helmet', '羽饰护鼻盔', ''), ('Events', '事件', ''),
                  ('Named Warbow', '名贵战弓', ''),
                  ('Hardened Nasal Helmet', '硬化护鼻盔', 'Feathered Nasal Helmet'),
                  ('Global map events', '世界地图事件', 'Events'),
                  ('Named Bow', '名贵弓', 'Named Warbow')]
        inventory_path = self.source / 'inventory.json'
        inventory = json.loads(inventory_path.read_text(encoding='utf-8'))
        rows = [{'pageid': i, 'title': title, 'ns': 0, 'lastrevid': i * 10}
                for i, (title, _, _) in enumerate(titles, 1)]
        inventory['pages'] = rows
        inventory_path.write_text(json.dumps(inventory), encoding='utf-8')
        for row, (title, _, target) in zip(rows, titles):
            parsed = {**self.parsed, 'title': title, 'revid': row['lastrevid']}
            if target:
                parsed.update(text='', wikitext='#REDIRECT [[' + target + ']]')
            (self.source / f"pages/{row['pageid']}.json.gz").write_bytes(gzip.compress(json.dumps({
                'page': row, 'requested_revision': row['lastrevid'], 'response': {'parse': parsed},
                'retrieved_at': 'today'}).encode()))
        (self.translations / 'titles.json').write_text(json.dumps({'schema_version': 1,
            'titles': {title: zh for title, zh, _ in titles}}), encoding='utf-8')
        release = build(self.source, self.root / 'wiki', self.catalog, translations=self.translations)
        with closing(sqlite3.connect(release / 'wiki.sqlite3')) as db:
            for query, page_id in [('硬化护鼻盔', 1), ('世界地图事件', 2), ('名贵弓', 3), ('红装弓', 3),
                                   ('Hardened Nasal Helmet', 1), ('Named Bow', 3)]:
                with self.subTest(query=query):
                    ids = [r[0] for r in db.execute('SELECT rowid FROM page_search WHERE page_search MATCH ?',
                                                    (search_expression(query),))]
                    self.assertEqual(ids, [page_id])
            self.assertEqual(db.execute('SELECT title_zh FROM pages WHERE id=3').fetchone()[0], '名贵战弓')

    def test_missing_translation_directory_cannot_activate_but_none_keeps_original_mode(self):
        destination = self.root / 'wiki'
        with self.assertRaisesRegex(TranslationError, 'translation directory'):
            build(self.source, destination, self.catalog, activate=True, translations=self.root / 'missing')
        self.assertFalse((destination / 'current.json').exists())
        release = build(self.source, destination, self.catalog, activate=True, translations=None)
        self.assertTrue((destination / 'current.json').exists())
        with closing(sqlite3.connect(release / 'wiki.sqlite3')) as db:
            self.assertEqual(db.execute('SELECT html_zh FROM pages WHERE id=1').fetchone()[0], '')

"""Reading the same immutable snapshot in Chinese, English and both languages."""
import json
from pathlib import Path
import sqlite3
import tempfile
from urllib.parse import parse_qs, urlsplit

from bs4 import BeautifulSoup
from django.test import SimpleTestCase, override_settings

from catalog.wiki import reading_html
from catalog.wiki_store import chinese_tokens, open_store, page_url, title_key, translation_info


LEGACY_SCHEMA = '''
CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
CREATE TABLE pages(id INTEGER PRIMARY KEY,title TEXT NOT NULL,title_key TEXT NOT NULL,
 namespace INTEGER NOT NULL,revision INTEGER NOT NULL,redirect TEXT NOT NULL DEFAULT '',
 title_zh TEXT NOT NULL DEFAULT '',summary TEXT NOT NULL DEFAULT '',html TEXT NOT NULL DEFAULT '',
 source_text TEXT NOT NULL DEFAULT '',sections_json TEXT NOT NULL DEFAULT '[]',
 categories_json TEXT NOT NULL DEFAULT '[]',fetched_at TEXT NOT NULL DEFAULT '');
CREATE TABLE categories(category_key TEXT NOT NULL,page_id INTEGER NOT NULL);
CREATE TABLE page_terms(page_id INTEGER NOT NULL,en TEXT NOT NULL,zh TEXT NOT NULL);
CREATE TABLE assets(id INTEGER PRIMARY KEY,metadata_json TEXT NOT NULL);
CREATE VIRTUAL TABLE page_search USING fts5(title,title_zh,names,body,zh_tokens);
'''
IMAGE = '/wiki/media/' + 'a' * 64 + '.png'
ENGLISH = '''<div lang="en"><h2 id="w-Stats">Statistics</h2>
<p>A heavy two-handed sword can cut through enemy armour.</p>
<a href="/wiki/read/Shield/?view=detail&amp;lang=en#w-Stats">Shield</a>
<a href="#w-Stats">Statistics</a><a href="/wiki/read/Greatsword/#w-Stats">This section</a>
<a href="https://battlebrothers.fandom.com/wiki/Greatsword">Source</a>
<img src="''' + IMAGE + '''" alt="example id='literal'" width="40" height="40">
<math><mfrac><mn>1</mn><mn>2</mn></mfrac></math>
<table><tr><th colspan="2">Damage</th></tr><tr><td>60</td><td>90</td></tr></table></div>'''
CHINESE = ENGLISH.replace('lang="en"', 'lang="zh-Hans"').replace('Statistics', '属性').replace(
    'A heavy two-handed sword can cut through enemy armour.', '沉重的双手剑可以劈开敌人的护甲。')


def make_snapshot(root, legacy=False):
    snapshot = '20260919T120000Z-012345abcdef'
    release = root / 'releases' / snapshot
    release.mkdir(parents=True)
    db = sqlite3.connect(release / 'wiki.sqlite3')
    db.executescript(LEGACY_SCHEMA)
    if not legacy:
        for name, default in (('html_zh', ''), ('summary_zh', ''), ('translation_json', '{}')):
            db.execute(f"ALTER TABLE pages ADD COLUMN {name} TEXT NOT NULL DEFAULT '{default}'")
    report = {'article_pages': 108, 'inventory_at': '2026-09-19T00:00:00Z',
              'term_catalog': {'game_version': '1.5.2.3'}}
    db.execute('INSERT INTO metadata VALUES (?,?)', ('report', json.dumps(report)))

    def insert(page_id, title, zh='', body='<p>Original entry.</p>', translated='', status='untranslated',
               review='unreviewed', namespace=0, redirect='', source_revision=100, retained_english=False,
               no_translatable_text=False):
        summary = BeautifulSoup(body, 'html.parser').get_text(' ', strip=True)
        summary_zh = BeautifulSoup(translated, 'html.parser').get_text(' ', strip=True)
        values = {'id': page_id, 'title': title, 'title_key': title_key(title),
                  'namespace': namespace, 'revision': 100, 'redirect': redirect,
                  'title_zh': zh, 'html': body, 'summary': summary, 'source_text': 'Original source: ' + title,
                  'sections_json': json.dumps([{'anchor': 'w-Stats', 'title': 'Statistics',
                                               'title_zh': '属性', 'level': '2'}]),
                  'categories_json': json.dumps(['Weapons'] if namespace == 0 else [])}
        info = {'schema_version': 1, 'source': 'BBMOD independent wiki review',
                'source_revision': source_revision, 'status': status,
                'review_status': review, 'review_complete': review == 'reviewed',
                'total_blocks': 2, 'translated_blocks': 2 if status == 'complete' else 1 if translated else 0,
                'reviewed_blocks': 2 if review == 'reviewed' else 0}
        if retained_english:
            info.update(retained_english=True, status='not_applicable', review_status='not_applicable')
        if no_translatable_text:
            info.update(no_translatable_text=True, status='not_applicable', review_status='not_applicable',
                        total_blocks=0, translated_blocks=0, reviewed_blocks=0)
        if not legacy:
            values.update(html_zh=translated, summary_zh=summary_zh, translation_json=json.dumps(info))
        columns = ','.join(values)
        db.execute(f"INSERT INTO pages ({columns}) VALUES ({','.join('?' for _ in values)})", tuple(values.values()))
        db.execute('INSERT INTO page_search(rowid,title,title_zh,names,body,zh_tokens) VALUES (?,?,?,?,?,?)',
                   (page_id, title, zh, 'Old Sword' if page_id == 1 else '', summary,
                    chinese_tokens(zh + (' ' + summary_zh if not legacy else ''))))
        if namespace == 0 and not redirect:
            db.execute('INSERT INTO categories VALUES (?,?)', ('weapons', page_id))

    insert(1, 'Greatsword', '巨剑', ENGLISH, CHINESE, 'complete', 'reviewed')
    insert(2, 'Shield', '盾牌')
    insert(3, 'Armour', '护甲', '<p>Armour protects the body.</p><p>English remains here.</p>',
           '<p>护甲可以保护身体。</p><p lang="en">English remains here.</p>', 'partial')
    insert(4, 'Old Sword', redirect='Greatsword#Stats')
    insert(5, 'Category:Weapons', '分类：武器', '', status='not_applicable', namespace=14)
    insert(6, 'Spear', '长矛', '<p>A spear can thrust.</p>', '<p>长矛可以突刺。</p>', 'complete')
    insert(7, 'Helm', '头盔', '<p>A helm protects the head.</p>', '<p>头盔保护头部。</p>',
           'complete', 'reviewed', source_revision=99)
    insert(8, 'Dev Blog Example', body='<p>Historical development notes.</p>', retained_english=True)
    insert(9, 'Image Only', '图示词条', body='<p><img src="' + IMAGE + '"></p>', no_translatable_text=True)
    insert(10, 'Empty Article', '空词条', body='', no_translatable_text=True)
    for page_id in range(100, 203):
        insert(page_id, f'Entry {page_id}', f'词条 {page_id}')
    db.execute('INSERT INTO page_terms VALUES (?,?,?)', (1, 'Greatsword', '巨剑'))
    db.commit()
    db.close()
    (release / 'styles.css').write_text('', encoding='utf-8')
    (root / 'current.json').write_text(json.dumps({'snapshot': snapshot}), encoding='utf-8')


class WikiReadingTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.wiki, cls.legacy = cls.root / 'modern', cls.root / 'legacy'
        make_snapshot(cls.wiki)
        make_snapshot(cls.legacy, legacy=True)
        cls.override = override_settings(WIKI_ROOT=cls.wiki)
        cls.override.enable()

    @classmethod
    def tearDownClass(cls):
        cls.override.disable()
        cls.temp.cleanup()
        super().tearDownClass()

    def test_default_chinese_body_directory_and_links_without_javascript(self):
        response = self.client.get(page_url('Greatsword'))
        self.assertContains(response, '沉重的双手剑可以劈开敌人的护甲。')
        self.assertNotContains(response, 'A heavy two-handed sword')
        self.assertEqual(response.context['wiki_mode'], 'zh')
        self.assertEqual(response.context['entry']['reading_note'], '中文译文')
        soup = BeautifulSoup(response.content, 'html.parser')
        self.assertEqual(soup.select_one('input[name=lang]')['value'], 'zh')
        self.assertEqual(soup.select_one('.wiki-contents a[href="#w-Stats"]').text, '属性')
        self.assertEqual(soup.select_one('.wiki-tags a').text, '武器')
        self.assertIsNotNone(soup.select_one('a[href="/wiki/read/Shield/?view=detail&lang=zh#w-Stats"]'))
        self.assertEqual(soup.select_one('.wiki-content img')['src'], IMAGE)
        self.assertIsNotNone(soup.select_one('.wiki-content mfrac'))
        self.assertContains(response, 'CC BY-SA 3.0')
        self.assertContains(response, 'oldid=100')
        self.assertContains(response, '贡献者与历史')

    def test_english_mode_has_original_body_and_preserves_query_and_fragment(self):
        response = self.client.get(page_url('Greatsword'), {'lang': 'en'})
        self.assertContains(response, 'A heavy two-handed sword')
        self.assertNotContains(response, '沉重的双手剑可以劈开敌人的护甲。')
        self.assertEqual(response.context['entry']['label'], 'Greatsword')
        soup = BeautifulSoup(response.content, 'html.parser')
        self.assertEqual(soup.select_one('.wiki-contents a[href="#w-Stats"]').text, 'Statistics')
        self.assertIsNotNone(soup.select_one('a[href="/wiki/read/Shield/?view=detail&lang=en#w-Stats"]'))
        self.assertEqual(soup.select_one('.wiki-source')['lang'], 'en')

    def test_bilingual_has_two_full_bodies_and_unambiguous_anchors(self):
        response = self.client.get(page_url('Greatsword'), {'lang': 'bi'})
        soup = BeautifulSoup(response.content, 'html.parser')
        self.assertEqual(len(soup.select('.wiki-reading-pane')), 2)
        self.assertIn('沉重的双手剑', soup.select_one('#wiki-translation').text)
        self.assertIn('A heavy two-handed sword', soup.select_one('#wiki-original').text)
        self.assertIsNotNone(soup.select_one('#wiki-translation #w-Stats'))
        self.assertIsNotNone(soup.select_one('#wiki-original #wiki-en-w-Stats'))
        self.assertIsNotNone(soup.select_one('#wiki-original a[href="#wiki-en-w-Stats"]'))
        self.assertIsNotNone(soup.select_one('#wiki-original a[href="/wiki/read/Greatsword/?lang=bi#wiki-en-w-Stats"]'))
        ids = [node['id'] for node in soup.select('[id]')]
        self.assertEqual(len(ids), len(set(ids)))
        for pane in soup.select('.wiki-reading-pane'):
            self.assertEqual(pane.img['src'], IMAGE)
            self.assertEqual(pane.img['alt'], "example id='literal'")
            self.assertEqual(pane.select_one('mfrac').text, '12')
            self.assertEqual([node.text for node in pane.select('td')], ['60', '90'])

    def test_coverage_review_and_stale_revision_are_distinct(self):
        for title, expected in (('Shield', '本页暂无中文正文'), ('Armour', '部分内容保留英文'),
                                ('Spear', '中文译文（待复核）'), ('Helm', '原文已更新')):
            response = self.client.get(page_url(title), {'lang': 'zh'})
            self.assertIn(expected, response.context['entry']['reading_note'])
        partial = self.client.get(page_url('Armour'))
        self.assertContains(partial, '护甲可以保护身体。')
        self.assertContains(partial, 'English remains here.')
        with open_store() as store:
            counts = store.translation_counts()
        self.assertEqual(counts['complete'], 3)
        self.assertEqual(counts['reviewed'], 1)
        self.assertEqual(counts['translated'], 4)
        self.assertContains(self.client.get('/wiki/about/'), '词条标注实际翻译与复核状态')

    def test_language_persists_on_pagination_search_and_regular_navigation(self):
        response = self.client.get('/wiki/search/', {'q': 'Entry', 'lang': 'bi', 'page': 2})
        soup = BeautifulSoup(response.content, 'html.parser')
        for link in soup.select('.wiki-mode a'):
            query = parse_qs(urlsplit(link['href']).query)
            self.assertEqual(query['q'], ['Entry'])
            self.assertEqual(query['page'], ['2'])
        for link in soup.select('.pagination a, .wiki-results a'):
            self.assertEqual(parse_qs(urlsplit(link['href']).query)['lang'], ['bi'])
        self.assertEqual(response.cookies['bbmod_wiki_lang'].value, 'bi')
        self.assertEqual(self.client.get('/wiki/').context['wiki_mode'], 'bi')
        self.assertEqual(self.client.get('/wiki/about/').context['wiki_mode'], 'bi')
        self.assertEqual(self.client.get('/wiki/', {'lang': 'invalid'}).context['wiki_mode'], 'zh')

    def test_retained_historical_english_is_explicit_and_excluded_from_game_coverage(self):
        for mode in ('zh', 'en', 'bi'):
            response=self.client.get(page_url('Dev Blog Example'), {'lang':mode})
            self.assertEqual(response.context['entry']['reading_note'], '历史日志 · 保留英文原文')
            self.assertContains(response, 'Historical development notes.')
            self.assertFalse(response.context['entry']['has_translation'])
        response=self.client.get('/wiki/search/', {'q':'Dev Blog Example','lang':'zh'})
        self.assertContains(response, '历史日志 · 英文原文')
        self.assertNotContains(response, '中文译文（待复核）')
        with open_store() as store:
            counts=store.translation_counts()
        self.assertEqual(counts['retained_english'], 1)
        self.assertEqual(counts['total'], 108)

    def test_redirect_preserves_every_mode_and_source_section(self):
        for language in ('zh', 'en', 'bi'):
            response = self.client.get(page_url('Old Sword'), {'lang': language})
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response['Location'], f'/wiki/read/Greatsword/?lang={language}#w-Stats')

    def test_image_only_and_empty_articles_are_not_reported_as_untranslated_or_directories(self):
        for title in ('Image Only', 'Empty Article'):
            response = self.client.get(page_url(title), {'lang': 'zh'})
            self.assertEqual(response.context['entry']['reading_note'], '本页没有需要翻译的正文。')
            self.assertFalse(response.context['entry']['translation']['reviewed'])
            self.assertNotContains(response, '本页暂无中文正文')
            self.assertNotContains(response, '本页为资料目录')
        image = self.client.get(page_url('Image Only'), {'lang': 'bi'})
        self.assertEqual(BeautifulSoup(image.content, 'html.parser').select_one('.wiki-content img')['src'], IMAGE)
        result = self.client.get('/wiki/search/', {'q': 'Image Only', 'lang': 'zh'})
        self.assertContains(result, '无须翻译正文')
        self.assertNotContains(result, '暂无中文正文')
        with open_store() as store:
            counts = store.translation_counts()
        self.assertEqual((counts['total'], counts['no_translatable_text']), (108, 2))
        self.assertContains(self.client.get('/wiki/about/'), '2 篇（不计入完成率）')
        self.assertContains(self.client.get(page_url('Shield')), '本页暂无中文正文')

    def test_category_labels_pagination_and_page_bounds(self):
        response = self.client.get(page_url('Category:Weapons'), {'lang': 'bi', 'page': 999})
        self.assertEqual(response.context['page'], 2)
        self.assertEqual(response.context['entry']['label'], '分类：武器')
        self.assertEqual(response.context['entry']['reading_note'], '本页为资料目录。')
        soup = BeautifulSoup(response.content, 'html.parser')
        for link in soup.select('.wiki-members a'):
            self.assertEqual(parse_qs(urlsplit(link['href']).query)['lang'], ['bi'])

    def test_search_finds_chinese_body_and_english_body_without_matching_title(self):
        for query in ('劈开敌人', 'heavy two handed'):
            response = self.client.get('/api/v1/wiki/search/', {'q': query, 'lang': 'bi'})
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data['schema_version'], 1)
            self.assertEqual([row['id'] for row in data['results']], [1])
            self.assertEqual(data['results'][0]['url'], page_url('Greatsword'))
            self.assertEqual(data['results'][0]['reading_url'], page_url('Greatsword', lang='bi'))
        response = self.client.get('/wiki/search/', {'q': '劈开敌人'})
        self.assertContains(response, '沉重的双手剑')

    def test_page_api_preserves_original_html_and_adds_translation_provenance(self):
        data = self.client.get('/api/v1/wiki/pages/1/', {'lang': 'bi'}).json()
        self.assertEqual(data['schema_version'], 1)
        page = data['page']
        self.assertEqual(page['html'], ENGLISH)
        self.assertEqual(page['html_zh'], CHINESE)
        self.assertEqual(page['translation']['source_revision'], 100)
        self.assertTrue(page['translation']['reviewed'])
        self.assertEqual(page['license'], 'CC-BY-SA-3.0')
        self.assertIn('action=history', page['contributors_url'])

    def test_legacy_snapshot_reads_searches_and_reports_missing_chinese_honestly(self):
        with override_settings(WIKI_ROOT=self.legacy):
            response = self.client.get(page_url('Greatsword'))
            self.assertContains(response, 'A heavy two-handed sword')
            self.assertContains(response, '本页暂无中文正文')
            self.assertNotContains(response, '沉重的双手剑')
            self.assertFalse(response.context['entry']['has_translation'])
            self.assertEqual(self.client.get('/wiki/search/', {'q': '巨剑'}).context['result_count'], 1)
            category = self.client.get(page_url('Category:Weapons'))
            self.assertEqual(category.status_code, 200)
            self.assertEqual(category.context['entry']['reading_note'], '本页为资料目录。')
            self.assertEqual(self.client.get('/wiki/').context['wiki_translation_counts']['complete'], 0)
            page = self.client.get('/api/v1/wiki/pages/1/').json()['page']
            self.assertEqual(page['html'], ENGLISH)
            self.assertEqual(page['html_zh'], '')
            self.assertEqual(page['translation']['status'], 'untranslated')

    def test_link_rewrite_keeps_unrelated_attributes_math_and_external_urls(self):
        rendered = reading_html(ENGLISH, 'bi', prefix='wiki-en-', current_path=page_url('Greatsword'))
        self.assertIn('alt="example id=\'literal\'"', rendered)
        self.assertIn('<mfrac><mn>1</mn><mn>2</mn></mfrac>', rendered)
        self.assertIn('href="https://battlebrothers.fandom.com/wiki/Greatsword"', rendered)
        self.assertEqual(page_url('Greatsword', 'w-Stats', lang='bi'), '/wiki/read/Greatsword/?lang=bi#w-Stats')

    def test_duplicate_source_ids_keep_first_target_and_reserve_later_original_ids(self):
        body = ('<h2 id="w-assassin_minmax">First</h2>'
                '<a href="#w-assassin_minmax">Original target</a>'
                '<div id="w-assassin_minmax">Repeated</div>'
                '<div id="w-assassin_minmax--2">Existing suffix</div>'
                '<a href="#w-assassin_minmax--2">Existing suffix target</a>'
                '<div id="w-assassin_minmax">Repeated again</div>'
                '<div id="w-indebted_minmax">Indebted</div>'
                '<div id="w-indebted_minmax">Repeated indebted</div>')
        for language in ('zh', 'en'):
            with self.subTest(language=language):
                rendered = reading_html(body, language)
                soup = BeautifulSoup(rendered, 'html.parser')
                ids = [node['id'] for node in soup.select('[id]')]
                self.assertEqual(ids, ['w-assassin_minmax', 'w-assassin_minmax--3',
                    'w-assassin_minmax--2', 'w-assassin_minmax--4',
                    'w-indebted_minmax', 'w-indebted_minmax--2'])
                self.assertEqual([node['href'] for node in soup.select('a')],
                    ['#w-assassin_minmax', '#w-assassin_minmax--2'])
                self.assertEqual(soup.find(id='w-assassin_minmax').text, 'First')
                self.assertEqual(soup.find(id='w-assassin_minmax--2').text, 'Existing suffix')
                reading_html.cache_clear()
                self.assertEqual(reading_html(body, language), rendered)

    def test_duplicate_ids_are_unique_in_both_reading_panes_without_changing_media(self):
        body = ('<div id="w-adventurous_noble">First</div>'
                '<img id="w-adventurous_noble" src="' + IMAGE + '" alt="id=\'literal\'"/>'
                '<span id="w-adventurous_noble--2">Existing suffix</span>'
                '<a href="#w-adventurous_noble">Same page</a>'
                '<a href="/wiki/read/Character_Backgrounds/#w-adventurous_noble--2">Named target</a>')
        chinese = reading_html(body, 'bi')
        english = reading_html(body, 'bi', 'wiki-en-', page_url('Character Backgrounds'))
        soup = BeautifulSoup(chinese + english, 'html.parser')
        ids = [node['id'] for node in soup.select('[id]')]
        self.assertEqual(len(ids), len(set(ids)))
        original = BeautifulSoup(english, 'html.parser')
        self.assertEqual(original.img['id'], 'wiki-en-w-adventurous_noble--3')
        self.assertEqual(original.img['src'], IMAGE)
        self.assertEqual(original.img['alt'], "id='literal'")
        self.assertEqual([node['href'] for node in original.select('a')],
            ['#wiki-en-w-adventurous_noble',
             '/wiki/read/Character_Backgrounds/?lang=bi#wiki-en-w-adventurous_noble--2'])

    def test_invalid_or_missing_translation_metadata_never_claims_full_review(self):
        for metadata in ('[]', '{bad', '', '{}'):
            info = translation_info({'translation_json': metadata, 'html': ENGLISH, 'revision': 100})
            self.assertEqual(info['status'], 'untranslated')
            self.assertFalse(info['reviewed'])
        info = translation_info({'translation_json': '{"status":"complete","review_status":"reviewed"}',
                                 'html': ENGLISH, 'html_zh': '', 'revision': 100})
        self.assertEqual(info['status'], 'untranslated')
        self.assertFalse(info['reviewed'])

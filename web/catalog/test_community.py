import copy
import json
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from .community import community_data
from .models import Mod, Release, CATEGORIES
from . import test_quick_publish as quick_tests


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class CommunityCatalogueTests(TestCase):
    setUp = quick_tests.QuickPublishTests.setUp
    upload = quick_tests.QuickPublishTests.upload

    def test_hosted_collection_reuses_source_entry_and_keeps_original_url(self):
        source = 'https://www.nexusmods.com/battlebrothers/mods/542'
        self.upload(title='游戏加速 Swifter 收藏版', original_author='Enduriel', source_url=source)
        release = Release.objects.get()
        public = Client()
        self.assertEqual(public.get('/', {'q':'Swifter'}).context['page'].paginator.count, 1)
        self.assertRedirects(public.get('/mods/community/swifter/'), reverse('detail', args=[release.mod_id]))
        self.assertContains(public.get(reverse('detail', args=[release.mod_id])), source)
        release.status = 'withdrawn'
        release.save(update_fields=['status'])
        self.assertEqual(public.get('/mods/community/swifter/').status_code, 200)

    def test_original_creator_and_uploader_are_distinct_in_public_snapshot(self):
        response = self.upload(original_author='Original Creator', source_url='https://example.org/original-mod', license='Allowed with credit')
        self.assertEqual(response.status_code, 302)
        release = Release.objects.get()
        self.assertEqual(release.metadata['author'], 'Original Creator')
        self.assertEqual(release.metadata['uploader'], 'author')
        public = Client()
        page = public.get(reverse('detail', args=[release.mod_id]))
        self.assertContains(page, '原作者 Original Creator')
        self.assertContains(page, '整理发布 author')
        self.assertEqual(public.get('/api/v1/catalog/').json()['mods'][0]['metadata']['author'], 'Original Creator')
        self.assertContains(public.get('/?q=Original%20Creator'), 'Original Creator')
        Mod.objects.filter(pk=release.mod_id).update(original_author='Later metadata')
        release.refresh_from_db()
        self.assertEqual(release.metadata['author'], 'Original Creator')

    def test_reposted_creator_requires_a_source(self):
        self.assertContains(self.upload(original_author='Original Creator'), '请为原作者署名补充可核实的原作链接')
        self.assertFalse(Mod.objects.exists())

    def test_original_sources_share_catalogue_search_category_and_pagination(self):
        self.upload(title='本站工具', category='框架', original_author='Test Author', source_url='https://example.org/mod')
        public = Client()
        result = public.get('/', {'q':'Swifter'})
        self.assertEqual(result.context['page'].paginator.count, 1)
        self.assertContains(result, '游戏加速')
        hosted = public.get('/', {'source':'hosted'})
        self.assertEqual(hosted.context['page'].paginator.count, 1)
        external = public.get('/', {'source':'original', 'category':'框架'})
        self.assertEqual(external.context['page'].paginator.count, 2)
        first = public.get('/', {'source':'original'})
        second = public.get('/', {'source':'original','page':2})
        self.assertTrue(first.context['page'].has_next())
        self.assertTrue(second.context['page'].has_previous())
        self.assertContains(first, 'source=original')
        self.assertNotContains(first, 'MOD 兼容与来源')
        self.assertEqual(public.get('/mod-guide/').status_code, 404)
        self.assertNotContains(public.get('/', {'q':'<script>alert(1)</script>'}), '<script>alert(1)</script>')

    def test_source_detail_is_credited_without_fake_download_or_new_tab(self):
        public = Client()
        response = public.get(reverse('community_detail', args=['swifter']))
        self.assertContains(response, '原作者 Enduriel')
        self.assertContains(response, 'https://www.nexusmods.com/battlebrothers/mods/542')
        self.assertContains(response, '前往作者原站')
        self.assertNotContains(response, '下载 ZIP')
        self.assertNotContains(response, 'target="_blank"')
        self.assertEqual(public.get(reverse('community_detail', args=['missing'])).status_code, 404)
        self.assertEqual(public.get(reverse('community_detail', args=['armour-indicators'])).status_code, 404)
        # The desktop installer API must never mistake an original-site link for an installable file.
        self.assertEqual(public.get('/api/v1/catalog/').json()['mods'], [])

    def test_hosted_curated_work_is_not_duplicated_or_resurrected(self):
        self.upload(title='职业属性范围')
        release = Release.objects.get()
        data = copy.deepcopy(community_data())
        row = next(r for r in data['mods'] if r['slug']=='background-ranges')
        row['published_mod_id'] = str(release.mod_id)
        with patch('catalog.community.community_data', return_value=data):
            self.assertEqual(Client().get('/', {'q':'职业属性范围'}).context['page'].paginator.count, 1)
            self.assertEqual(Client().get('/', {'q':'Backgrounds and Attribute Ranges'}).context['page'].paginator.count, 1)
            for status in ('draft','withdrawn'):
                release.status=status; release.save(update_fields=['status'])
                self.assertEqual(Client().get('/', {'q':'职业属性范围'}).context['page'].paginator.count, 0)
            release.status='published';release.save(update_fields=['status'])
            release.mod.blocked=True;release.mod.save(update_fields=['blocked'])
            self.assertEqual(Client().get('/', {'q':'职业属性范围'}).context['page'].paginator.count, 0)

    def test_framework_ids_have_plain_language_links(self):
        self.upload(requires='mod_msu\nmod_modern_hooks\nmod_hooks\nmod_unknown')
        release = Release.objects.get()
        page = Client().get(reverse('detail', args=[release.mod_id]))
        self.assertContains(page, 'MOD 设置库 · MSU')
        self.assertContains(page, reverse('community_detail', args=['modern-hooks']))
        self.assertContains(page, reverse('detail', args=['ce170bce-dd19-51c8-a637-d73dad0423c7']))
        self.assertContains(page, 'mod_unknown')

    def test_author_downloads_filter_preserves_search_and_excludes_desktop_api(self):
        self.upload(title='Local MOD')
        public = Client()
        page = public.get('/', {'source': 'direct'})
        self.assertEqual(page.context['page'].paginator.count, 16)
        self.assertContains(page, '作者文件下载')
        self.assertNotContains(page, 'Local MOD')
        self.assertContains(page, 'source=direct')
        search = public.get('/', {'source': 'direct', 'q': 'Tooltip Toggle'})
        self.assertEqual(search.context['page'].paginator.count, 1)
        self.assertContains(search, '提示信息开关')
        detail = public.get(reverse('community_detail', args=['tooltip-toggle']))
        self.assertContains(detail, 'https://github.com/jcsato/sato_tooltip_toggle/releases/download/v0.1/sato_tooltip_toggle_0.1.zip')
        self.assertContains(detail, '暂不支持通过 BBMOD 桌面工具导入')
        self.assertEqual(len(public.get('/api/v1/catalog/').json()['mods']), 1)

    def test_curated_introductions_have_sources_and_no_private_environment_claims(self):
        rows = community_data()['mods']
        self.assertEqual(len(rows), 37)
        self.assertEqual(len({r['slug'] for r in rows}), len(rows))
        self.assertEqual(sum(bool(r.get('published_mod_id')) for r in rows), 4)
        for row in rows:
            self.assertTrue(row['author'])
            self.assertIn(row['category'], dict(CATEGORIES))
            self.assertTrue(row['source_url'].startswith(('https://www.nexusmods.com/battlebrothers/mods/', 'https://github.com/')))
            self.assertLessEqual(len(row['summary']), 70)
            for phrase in ('当前启用环境', '你的电脑', 'G:\\', 'E:\\', '当前环境缺少'):
                self.assertNotIn(phrase, json.dumps(row, ensure_ascii=False))
        audit=json.loads((Path(settings.BASE_DIR)/'content/mod-compatibility-2026-09-19.json').read_text(encoding='utf-8'))
        self.assertEqual(len(audit['entries']), 59)
        for row in audit['entries']:
            for digest in row['sha256']:
                self.assertRegex(digest, r'^[0-9a-f]{64}$')

    def test_requested_mods_keep_download_pages_distinct_from_files(self):
        public = Client()
        for slug in ('extra-keybinds', 'detailed-status-effects'):
            row = next(r for r in community_data()['mods'] if r['slug'] == slug)
            response = public.get(reverse('community_detail', args=[slug]))
            self.assertContains(response, row['source_files_url'])
            self.assertContains(response, '前往作者下载页')
            self.assertNotContains(response, '作者原包由 GitHub 提供')
            filtered = public.get('/', {'source': 'direct', 'q': row['english_name']})
            self.assertEqual(filtered.context['page'].paginator.count, 0)
        legends = public.get(reverse('community_detail', args=['legends']))
        self.assertContains(legends, '/19.4.22/mod_legends-19.4.22.zip')
        self.assertContains(legends, '/19.4.3/mod_legends-assets-19.4.3.zip')
        self.assertContains(legends, '两包都需要')
        self.assertContains(legends, 'Installation-Guide')
        maxi = public.get(reverse('community_detail', args=['maxiqe-tooltips']))
        self.assertContains(maxi, 'nested-tooltips/releases')
        self.assertContains(maxi, '/536?tab=files')
        self.assertContains(maxi, '安装方法')
        self.assertEqual(public.get('/api/v1/catalog/').json()['mods'], [])

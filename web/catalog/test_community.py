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
        self.assertEqual(external.context['page'].paginator.count, 3)
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
        self.upload(requires='mod_msu\nmod_modern_hooks\nmod_unknown')
        release = Release.objects.get()
        page = Client().get(reverse('detail', args=[release.mod_id]))
        self.assertContains(page, 'MOD 设置库 · MSU')
        self.assertContains(page, reverse('community_detail', args=['modern-hooks']))
        self.assertContains(page, 'mod_unknown')

    def test_curated_introductions_have_sources_and_no_private_environment_claims(self):
        rows = community_data()['mods']
        self.assertEqual(len(rows), 24)
        self.assertEqual(len({r['slug'] for r in rows}), len(rows))
        self.assertEqual(sum(bool(r.get('published_mod_id')) for r in rows), 3)
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

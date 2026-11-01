from urllib.parse import parse_qs, urlsplit

from bs4 import BeautifulSoup
from django.contrib.auth.models import User
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from .models import AuditLog, Mod, Suggestion


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class ManagementTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser('manager', password='Isolated-Test-Password-1234')
        cls.author = User.objects.create_user('smith', first_name='铁匠')
        cls.normal = Mod.objects.create(owner=cls.author, title='战斗工具 Alpha', install_name='mod_tools.zip')
        cls.blocked = Mod.objects.create(owner=cls.author, title='旧版装备', install_name='mod_old.zip',
                                         blocked=True, block_reason='不再兼容')
        cls.feedback = Suggestion.objects.create(kind='bug', title='私密待办标题', details='私密反馈内容',
            contact='private@example.test', diagnostic_report='PRIVATE-DIAGNOSTIC', internal_notes='PRIVATE-NOTE')
        Suggestion.objects.create(kind='feature', title='跟进建议', details='功能说明', status='reviewing')
        Suggestion.objects.create(kind='bug', title='已完成事项', details='已处理', status='done')

    def setUp(self):
        self.client.force_login(self.admin)

    def test_dashboard_counts_and_pending_feedback_are_separate_from_mod_filter(self):
        response = self.client.get('/manage/', {'q': 'old', 'state': 'blocked'})
        self.assertEqual(response.context['mod_totals'], {'total': 2, 'blocked': 1})
        self.assertEqual(response.context['new_suggestions'], 1)
        self.assertEqual(response.context['reviewing_suggestions'], 1)
        self.assertEqual(list(response.context['mods']), [self.blocked])
        self.assertCountEqual([s.title for s in response.context['pending_suggestions']], ['私密待办标题', '跟进建议'])
        for private in ['私密反馈内容', 'private@example.test', 'PRIVATE-DIAGNOSTIC', 'PRIVATE-NOTE']:
            self.assertNotContains(response, private)
        self.assertEqual(response['Cache-Control'], 'private, no-store')

    def test_search_supports_title_filename_and_both_author_names(self):
        for term, expected in [('Alpha', [self.normal]), ('MOD_TOOLS.ZIP', [self.normal]),
                               ('铁匠', [self.normal, self.blocked]), ('smith', [self.normal, self.blocked])]:
            with self.subTest(term=term):
                response = self.client.get('/manage/', {'q': term})
                self.assertCountEqual(response.context['mods'], expected)
        response = self.client.get('/manage/', {'q': 'smith', 'state': 'normal'})
        self.assertEqual(list(response.context['mods']), [self.normal])
        response = self.client.get('/manage/', {'state': 'not-a-status', 'page': 'bad'})
        self.assertEqual(response.context['state'], '')
        self.assertEqual(response.context['mods'].number, 1)

    def test_search_and_moderation_context_are_escaped_and_pagination_keeps_filters(self):
        Mod.objects.bulk_create([Mod(owner=self.author, title=f'测试 & 分类 {n}', install_name=f'mod_extra_{n}.zip') for n in range(31)])
        response = self.client.get('/manage/', {'q': '测试 & 分类', 'state': 'normal'})
        soup = BeautifulSoup(response.content, 'html.parser')
        next_link = soup.select_one('nav[aria-label="作品分页"] a')['href']
        self.assertEqual(parse_qs(urlsplit(next_link).query), {'q': ['测试 & 分类'], 'state': ['normal'], 'page': ['2']})
        second = self.client.get('/manage/' + next_link)
        self.assertEqual(len(second.context['mods']), 1)
        escaped = self.client.get('/manage/', {'q': '\"><script>alert(1)</script>'})
        self.assertNotContains(escaped, '<script>alert(1)</script>')
        self.assertEqual(escaped.context['mods'].paginator.count, 0)

    def test_moderation_preserves_context_and_existing_audit_and_reason_rules(self):
        response = self.client.post(reverse('moderate', args=[self.normal.pk]), {
            'action': 'block', 'reason': '测试原因', 'q': '铁匠 & Alpha', 'state': 'normal', 'page': '2',
            'next': 'https://outside.example/'})
        destination = urlsplit(response['Location'])
        self.assertEqual((destination.netloc, destination.path, destination.fragment), ('', '/manage/', 'mods'))
        self.assertEqual(parse_qs(destination.query), {'q': ['铁匠 & Alpha'], 'state': ['normal'], 'page': ['2']})
        self.normal.refresh_from_db()
        self.assertTrue(self.normal.blocked)
        self.assertEqual(self.normal.block_reason, '测试原因')
        self.assertTrue(AuditLog.objects.filter(action='下架作品', target=str(self.normal.pk)).exists())
        self.client.post(reverse('moderate', args=[self.normal.pk]), {'action': 'restore'})
        self.client.post(reverse('moderate', args=[self.normal.pk]), {'action': 'block', 'reason': ''})
        self.normal.refresh_from_db()
        self.assertFalse(self.normal.blocked)
        self.assertEqual(self.normal.block_reason, '')

    def test_shared_navigation_and_current_section_on_all_management_pages(self):
        cases = [('/manage/', '工作台'), ('/manage/suggestions/', '错误报告与建议'),
                 (reverse('suggestion_detail', args=[self.feedback.pk]), '错误报告与建议'),
                 ('/manage/seeds/', '种子分享'), ('/manage/profiles/', '共享方案与文件'),
                 ('/manage/saves/', '存档分享'), ('/manage/wiki/', '百科导入报告'),
                 ('/manage/software/', '管理器版本'), ('/manage/accounts/', '作者账号'),
                 (reverse('account_change', args=[self.author.pk]), '作者账号')]
        for path, label in cases:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                soup = BeautifulSoup(response.content, 'html.parser')
                active = soup.select('nav[aria-label="后台功能"] [aria-current="page"]')
                self.assertEqual(len(active), 1)
                self.assertIn(label, active[0].get_text())
                self.assertIsNone(soup.select_one('[data-visitor-welcome]'))

    def test_management_remains_private_and_mutation_requires_csrf(self):
        for user in [None, self.author]:
            client = Client()
            if user:
                client.force_login(user)
            response = client.get('/manage/')
            self.assertEqual(response.status_code, 302)
            self.assertNotIn('私密待办标题', response.content.decode())
        secure = Client(enforce_csrf_checks=True)
        secure.force_login(self.admin)
        self.assertEqual(secure.post(reverse('moderate', args=[self.normal.pk]), {'action': 'restore'}).status_code, 403)
        self.assertEqual(self.client.post('/manage/').status_code, 405)
        public = Client().get('/')
        self.assertNotContains(public, 'management.css')
        self.assertNotContains(public, '私密待办标题')

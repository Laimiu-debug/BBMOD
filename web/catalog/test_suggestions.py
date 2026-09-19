from datetime import timedelta
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth.models import User
from django.core import signing
from django.db import OperationalError
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import AuditLog, Suggestion, SuggestionBudget
from .suggestions import TOKEN_SALT


class DesktopSuggestionTests(TestCase):
    url = '/api/v1/suggestions/'

    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        challenge = self.client.get(self.url)
        self.assertEqual(challenge['Cache-Control'], 'private, no-store')
        self.ticket = challenge.json()
        self.data = {'kind': 'bug', 'title': '桌面反馈', 'details': '希望改善快捷键冲突提示。',
                     'submission': self.ticket['submission'], 'version': 'BBMOD desktop test',
                     'contact': 'private@example.test'}

    def post(self, data=None, **headers):
        return self.client.post(self.url, data or self.data, content_type='application/json',
                                HTTP_X_CSRFTOKEN=self.ticket['csrf_token'], **headers)

    def test_native_submission_and_retry_share_admin_inbox(self):
        first = self.post()
        self.assertEqual(first.status_code, 201)
        self.assertEqual(self.post().json()['reference'], first.json()['reference'])
        self.assertEqual(Suggestion.objects.count(), 1)
        self.assertEqual(Suggestion.objects.get().contact, 'private@example.test')
        self.assertNotIn('contact', first.json())
        self.assertNotIn('details', self.client.get(self.url).json())
        self.assertEqual(self.client.get('/manage/suggestions/').status_code, 302)

    def test_csrf_cross_session_and_foreign_origin_rejected(self):
        self.assertEqual(self.client.post(self.url, self.data, content_type='application/json').status_code, 403)
        self.assertEqual(self.post(HTTP_ORIGIN='https://foreign.example').status_code, 403)
        other = Client(enforce_csrf_checks=True)
        token = other.get(self.url).json()
        result = other.post(self.url, self.data, content_type='application/json', HTTP_X_CSRFTOKEN=token['csrf_token'])
        self.assertEqual(result.status_code, 400)
        self.assertEqual(result.json()['code'], 'ticket_expired')
        self.assertEqual(Suggestion.objects.count(), 0)

    def test_validation_and_storage_retry_do_not_spend_ticket(self):
        invalid = self.post({**self.data, 'details': 'x' * 5001})
        self.assertEqual(invalid.status_code, 400)
        self.assertIn('details', invalid.json()['errors'])
        with patch('catalog.suggestions._save_submission', side_effect=OperationalError):
            failed = self.post()
        self.assertEqual(failed.status_code, 503)
        self.assertEqual(failed['Retry-After'], '5')
        self.assertEqual(self.post().status_code, 201)

    def test_web_and_desktop_share_submission_budget(self):
        for index in range(5):
            ticket = self.client.get(self.url).json()
            self.assertEqual(self.post({**self.data, 'submission': ticket['submission']}).status_code, 201)
        ticket = self.client.get(self.url).json()
        result = self.post({**self.data, 'submission': ticket['submission']})
        self.assertEqual(result.status_code, 429)
        self.assertEqual(result['Retry-After'], '3600')
        self.assertEqual(Suggestion.objects.count(), 5)


class SuggestionTests(TestCase):
    def form_data(self, client=None, **overrides):
        client = client or self.client
        page = client.get('/suggestions/')
        data = {'kind': 'feature', 'title': '搜索已安装的 MOD',
                'details': '希望在管理器中按名称查找已经安装的 MOD。',
                'submission': page.context['form']['submission'].value()}
        data.update(overrides)
        return data

    def create_suggestion(self, **overrides):
        data = self.form_data(**overrides)
        self.assertRedirects(self.client.post('/suggestions/', data), '/suggestions/thanks/')
        return Suggestion.objects.latest('created_at')

    def admin(self):
        user = User.objects.create_superuser('suggestion-admin', password='isolated-tests-only')
        self.client.force_login(user)
        return user

    def test_anonymous_submission_persists_optional_details_and_receipt(self):
        suggestion = self.create_suggestion(nickname='营地兄弟', contact='private@example.test', version='0.3.0-rc.12')
        self.assertEqual(suggestion.status, Suggestion.Status.NEW)
        self.assertEqual(suggestion.contact, 'private@example.test')
        self.assertEqual(suggestion.version, '0.3.0-rc.12')
        receipt = self.client.get('/suggestions/thanks/')
        self.assertContains(receipt, suggestion.reference)
        self.assertNotContains(receipt, suggestion.contact)
        self.assertEqual(receipt['Cache-Control'], 'private, no-store')
        self.assertEqual(Suggestion.objects.count(), 1)
        self.assertRedirects(Client().get('/suggestions/thanks/'), '/suggestions/')

    def test_refresh_and_replayed_submission_do_not_duplicate_or_overwrite(self):
        data = self.form_data()
        self.assertEqual(self.client.post('/suggestions/', data).status_code, 302)
        original = Suggestion.objects.get()
        before = list(SuggestionBudget.objects.order_by('key').values_list('count', flat=True))
        data['details'] = '重复提交不能覆盖原内容'
        self.assertEqual(self.client.post('/suggestions/', data).status_code, 302)
        self.client.get('/suggestions/thanks/')
        original.refresh_from_db()
        self.assertEqual(Suggestion.objects.count(), 1)
        self.assertNotEqual(original.details, data['details'])
        self.assertEqual(before, list(SuggestionBudget.objects.order_by('key').values_list('count', flat=True)))

    def test_validation_preserves_input_and_rejects_whitespace_or_oversize(self):
        for overrides, field in [({'title': '   '}, 'title'), ({'details': ''}, 'details'),
                                 ({'kind': 'invented'}, 'kind'), ({'details': '长' * 5001}, 'details'),
                                 ({'contact': 'x' * 151}, 'contact')]:
            with self.subTest(field=field):
                data = self.form_data(**overrides)
                result = self.client.post('/suggestions/', data)
                self.assertEqual(result.status_code, 400)
                self.assertIn(field, result.context['form'].errors)
                self.assertEqual(result.context['form']['details'].value(), data['details'])
        self.assertEqual(Suggestion.objects.count(), 0)
        self.assertEqual(SuggestionBudget.objects.count(), 0)

    def test_csrf_is_required_including_cross_origin_posts(self):
        browser = Client(enforce_csrf_checks=True)
        data = self.form_data(browser)
        self.assertEqual(browser.post('/suggestions/', data).status_code, 403)
        data['csrfmiddlewaretoken'] = browser.cookies[settings.CSRF_COOKIE_NAME].value
        self.assertEqual(browser.post('/suggestions/', data, HTTP_ORIGIN='https://attacker.invalid').status_code, 403)
        self.assertEqual(browser.post('/suggestions/', data).status_code, 302)
        self.assertEqual(Suggestion.objects.count(), 1)

    def test_form_token_is_browser_bound_and_recovery_preserves_input(self):
        data = self.form_data()
        other = Client()
        response = other.post('/suggestions/', data)
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, data['title'], status_code=400)
        data['submission'] = response.context['form']['submission'].value()
        self.assertEqual(other.post('/suggestions/', data).status_code, 302)
        self.assertEqual(Suggestion.objects.count(), 1)

    def test_expired_or_missing_token_can_be_retried_without_retyping(self):
        data = self.form_data()
        for invalid in ['', 'tampered']:
            data['submission'] = invalid
            result = self.client.post('/suggestions/', data)
            self.assertEqual(result.status_code, 400)
            self.assertEqual(result.context['form']['title'].value(), data['title'])
            self.assertTrue(result.context['form']['submission'].value())
        with patch('catalog.suggestions.signing.loads', side_effect=signing.SignatureExpired):
            expired = self.client.post('/suggestions/', data)
        self.assertEqual(expired.status_code, 400)
        data['submission'] = expired.context['form']['submission'].value()
        self.assertEqual(self.client.post('/suggestions/', data).status_code, 302)

    def test_browser_quota_is_atomic_and_resets_next_hour(self):
        fixed = timezone.now().replace(minute=10, second=0, microsecond=0)
        with patch('catalog.suggestions.timezone.now', return_value=fixed):
            for _ in range(5):
                self.assertEqual(self.client.post('/suggestions/', self.form_data()).status_code, 302)
            rejected_data = self.form_data()
            rejected = self.client.post('/suggestions/', rejected_data)
            self.assertEqual(rejected.status_code, 429)
            self.assertEqual(rejected['Retry-After'], '3600')
            self.assertContains(rejected, rejected_data['details'], status_code=429)
            self.assertEqual(list(SuggestionBudget.objects.values_list('count', flat=True)), [5, 5, 5])
            self.assertEqual(Client().post('/suggestions/', self.form_data(Client())).status_code, 400)
            second = Client()
            self.assertEqual(second.post('/suggestions/', self.form_data(second)).status_code, 302)
        with patch('catalog.suggestions.timezone.now', return_value=fixed + timedelta(hours=1)):
            self.assertEqual(self.client.post('/suggestions/', rejected_data).status_code, 302)
        self.assertEqual(Suggestion.objects.count(), 7)

    @override_settings(TRUST_PROXY=False)
    def test_forwarded_header_does_not_bypass_address_quota(self):
        self.create_suggestion()
        SuggestionBudget.objects.all().update(count=30)
        browser = Client()
        response = browser.post('/suggestions/', self.form_data(browser), HTTP_X_REAL_IP='invented')
        self.assertEqual(response.status_code, 429)
        self.assertEqual(Suggestion.objects.count(), 1)
        self.assertEqual(SuggestionBudget.objects.count(), 3)
        self.assertTrue(all(len(key) == 64 for key in SuggestionBudget.objects.values_list('key', flat=True)))

    def test_global_quota_rolls_back_earlier_scope_increments(self):
        data = self.form_data()
        with patch('catalog.suggestions._budget_scopes', return_value=[('global', 1)]):
            self.client.post('/suggestions/', data)
        with patch('catalog.suggestions._budget_scopes', return_value=[('new-browser', 5), ('global', 1)]):
            result = self.client.post('/suggestions/', self.form_data())
        self.assertEqual(result.status_code, 429)
        self.assertEqual(SuggestionBudget.objects.count(), 1)
        self.assertEqual(SuggestionBudget.objects.get().count, 1)

    def test_database_failure_keeps_input_and_never_claims_success(self):
        data = self.form_data(contact='private@example.test')
        with patch('catalog.suggestions._save_submission', side_effect=OperationalError('locked')):
            result = self.client.post('/suggestions/', data)
        self.assertEqual(result.status_code, 503)
        self.assertContains(result, data['contact'], status_code=503)
        self.assertNotIn('last_suggestion', self.client.session)
        self.assertFalse(Suggestion.objects.exists())

    def test_anonymous_and_author_cannot_read_or_handle_suggestions(self):
        suggestion = self.create_suggestion(contact='private@example.test')
        url = reverse('suggestion_detail', args=[suggestion.pk])
        self.client.logout()
        for user in [None, User.objects.create_user('author', password='isolated-tests-only')]:
            if user:
                self.client.force_login(user)
            for path in ['/manage/suggestions/', url]:
                self.assertEqual(self.client.get(path).status_code, 302)
                self.assertEqual(self.client.post(path, {'status': 'done', 'internal_notes': 'forged'}).status_code, 302)
            for path in ['/', '/suggestions/', '/api/v1/catalog/', '/seeds/']:
                self.assertNotContains(self.client.get(path), suggestion.contact)
        suggestion.refresh_from_db()
        self.assertEqual(suggestion.status, 'new')
        self.assertEqual(suggestion.internal_notes, '')

    def test_admin_updates_status_notes_and_audit_without_exposing_private_content(self):
        suggestion = self.create_suggestion(contact='private@example.test')
        admin = self.admin()
        url = reverse('suggestion_detail', args=[suggestion.pk])
        page = self.client.get(url)
        self.assertContains(page, suggestion.contact)
        result = self.client.post(url, {'status': 'reviewing', 'internal_notes': '计划排查搜索入口',
                                       'revision': page.context['form']['revision'].value()})
        self.assertRedirects(result, url)
        suggestion.refresh_from_db()
        self.assertEqual(suggestion.status, 'reviewing')
        self.assertEqual(suggestion.internal_notes, '计划排查搜索入口')
        self.assertEqual(suggestion.handled_by, admin)
        log = AuditLog.objects.get(action='处理建议')
        self.assertEqual(log.target, str(suggestion.pk))
        self.assertEqual(log.detail, '处理中')
        self.assertNotContains(self.client.get('/manage/suggestions/'), suggestion.contact)

    def test_invalid_or_stale_admin_changes_do_not_overwrite_saved_record(self):
        suggestion = self.create_suggestion()
        self.admin()
        url = reverse('suggestion_detail', args=[suggestion.pk])
        revision = self.client.get(url).context['form']['revision'].value()
        self.assertEqual(self.client.post(url, {'status': 'invalid', 'revision': revision}).status_code, 400)
        self.assertEqual(self.client.post(url, {'status': 'done', 'internal_notes': '已经完成', 'revision': revision}).status_code, 302)
        stale = self.client.post(url, {'status': 'closed', 'internal_notes': '我的待合并备注', 'revision': revision})
        self.assertEqual(stale.status_code, 409)
        self.assertContains(stale, '我的待合并备注', status_code=409)
        suggestion.refresh_from_db()
        self.assertEqual((suggestion.status, suggestion.internal_notes), ('done', '已经完成'))
        self.assertEqual(AuditLog.objects.filter(action='处理建议').count(), 1)

    def test_admin_filters_paginates_and_escapes_submitted_html(self):
        suggestion = self.create_suggestion(title='<script>alert(1)</script>', details='<img src=x onerror=alert(2)>', contact='<b>private</b>')
        self.admin()
        for i in range(21):
            Suggestion.objects.create(kind='bug', title=f'窗口问题 {i}', details='窗口缩放异常', status='reviewing')
        listing = self.client.get('/manage/suggestions/?status=reviewing&kind=bug&q=窗口&page=2')
        self.assertEqual(len(listing.context['page']), 1)
        self.assertEqual(listing.context['page'].paginator.count, 21)
        self.assertEqual(listing.context['new_count'], 1)
        self.assertContains(listing, 'status=reviewing')
        detail = self.client.get(reverse('suggestion_detail', args=[suggestion.pk]))
        self.assertNotContains(detail, '<script>alert(1)</script>')
        self.assertContains(detail, '&lt;script&gt;alert(1)&lt;/script&gt;')
        self.assertContains(detail, '&lt;b&gt;private&lt;/b&gt;')
        self.assertNotContains(detail, 'data-visitor-welcome')

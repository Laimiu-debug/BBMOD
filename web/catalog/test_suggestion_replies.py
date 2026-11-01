from datetime import timedelta
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth.models import User
from django.db import OperationalError
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from .models import AuditLog, Suggestion, SuggestionBudget, SuggestionReply
from .suggestions import RECEIPT_COOKIE, QuotaExceeded


class SuggestionReplyTests(TestCase):
    def setUp(self):
        self.item = Suggestion.objects.create(kind='bug', title='PRIVATE_TITLE', details='PRIVATE_DETAILS',
            contact='private-contact@example.test', nickname='PRIVATE_NICKNAME', diagnostic_report='PRIVATE_LOG',
            internal_notes='PRIVATE_INTERNAL_NOTES', version='PRIVATE_VERSION')
        self.admin = User.objects.create_superuser('reply-admin', password='test-only-password')
        self.manage = reverse('suggestion_detail', args=[self.item.pk])
        self.receipt = reverse('suggestion_receipt', args=[self.item.reference])

    def handle(self, body='', **extra):
        self.client.force_login(self.admin)
        revision = self.client.get(self.manage).context['form']['revision'].value()
        return self.client.post(self.manage, {'status': 'reviewing', 'internal_notes': 'new private note',
            'revision': revision, 'reply_body': body, **extra})

    def test_reply_and_status_are_published_together_without_leaking_private_fields(self):
        result = self.handle('请升级管理器，然后重新运行健康诊断。')
        self.assertRedirects(result, self.manage)
        reply = SuggestionReply.objects.get()
        self.assertEqual(reply.author, self.admin)
        self.assertEqual(reply.status, 'reviewing')
        page = Client().get(self.receipt)
        self.assertContains(page, reply.body)
        self.assertContains(page, '处理中')
        for private in ['PRIVATE_TITLE', 'PRIVATE_DETAILS', 'PRIVATE_LOG', 'PRIVATE_NICKNAME',
                        'PRIVATE_VERSION', 'new private note', 'private-contact@example.test', 'reply-admin']:
            self.assertNotContains(page, private)
        self.assertEqual(set(page.context['receipt']), {'reference', 'status', 'status_label', 'updated_at', 'replies'})
        self.assertEqual(page['Cache-Control'], 'private, no-store')
        self.assertEqual(page['Referrer-Policy'], 'strict-origin')
        self.assertEqual(page['X-Robots-Tag'], 'noindex, nofollow')
        self.assertNotContains(page, 'data-visitor-welcome')
        self.assertEqual(AuditLog.objects.get(action='回复建议').detail, '已发布回复')

    def test_legacy_receipt_works_without_republishing_internal_notes(self):
        page = self.client.get(self.receipt)
        self.assertContains(page, '管理员暂未回复')
        self.assertNotContains(page, self.item.internal_notes)
        self.assertFalse(SuggestionReply.objects.exists())

    def test_anonymous_and_ordinary_authors_cannot_reply(self):
        for user in [None, User.objects.create_user('ordinary-author', password='test-only-password')]:
            client = Client()
            if user:
                client.force_login(user)
            self.assertEqual(client.post(self.manage, {'status': 'done', 'reply_body': 'forged',
                'revision': self.item.updated_at.isoformat()}).status_code, 302)
        self.assertFalse(SuggestionReply.objects.exists())
        self.item.refresh_from_db()
        self.assertEqual(self.item.status, 'new')

    def test_csrf_protection_covers_both_admin_reply_and_receipt_post(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.admin)
        self.assertEqual(client.post(self.manage, {'reply_body': 'forged'}).status_code, 403)
        self.assertEqual(client.post(reverse('suggestion_lookup'), {'reference': self.item.reference}).status_code, 403)
        page = client.get(reverse('suggestion_lookup'))
        token = client.cookies[settings.CSRF_COOKIE_NAME].value
        self.assertEqual(client.post(reverse('suggestion_lookup'), {'reference': self.item.reference},
            HTTP_X_CSRFTOKEN=token, HTTP_ORIGIN='https://attacker.invalid').status_code, 403)
        self.assertFalse(SuggestionReply.objects.exists())

    def test_duplicate_and_stale_admin_posts_do_not_duplicate_or_overwrite_replies(self):
        self.client.force_login(self.admin)
        revision = self.client.get(self.manage).context['form']['revision'].value()
        data = {'status': 'done', 'reply_body': '已在新版本修复', 'revision': revision, 'internal_notes': 'private'}
        self.assertEqual(self.client.post(self.manage, data).status_code, 302)
        conflict = self.client.post(self.manage, {**data, 'reply_body': '未发布的草稿'})
        self.assertEqual(conflict.status_code, 409)
        self.assertContains(conflict, '未发布的草稿', status_code=409)
        self.assertEqual(list(SuggestionReply.objects.values_list('body', flat=True)), ['已在新版本修复'])

    def test_atomic_failure_keeps_status_and_reply_unchanged(self):
        with patch('catalog.suggestions.SuggestionReply.objects.create', side_effect=OperationalError('locked')):
            page = self.handle('不能只保存状态')
        self.assertEqual(page.status_code, 503)
        self.assertEqual(page['Retry-After'], '5')
        self.assertContains(page, '不能只保存状态', status_code=503)
        self.item.refresh_from_db()
        self.assertEqual(self.item.status, 'new')
        self.assertFalse(SuggestionReply.objects.exists())
        self.assertFalse(AuditLog.objects.exists())

    def test_blank_reply_only_saves_internal_notes_and_oversize_reply_keeps_draft(self):
        self.assertEqual(self.handle('   ').status_code, 302)
        self.assertFalse(SuggestionReply.objects.exists())
        invalid = self.handle('长' * 5001)
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(invalid.context['form']['reply_body'].value(), '长' * 5001)
        self.assertFalse(SuggestionReply.objects.exists())

    def test_multiple_replies_are_chronological_and_html_is_escaped(self):
        self.handle('第一条说明')
        self.handle('<script>alert(1)</script>\n第二条说明')
        page = self.client.get(self.receipt)
        self.assertContains(page, '&lt;script&gt;alert(1)&lt;/script&gt;')
        self.assertNotContains(page, '<script>alert(1)</script>')
        self.assertLess(page.content.index('第一条说明'.encode()), page.content.index('第二条说明'.encode()))

    def test_lookup_normalizes_reference_and_remembers_only_receipts_in_signed_cookie(self):
        result = self.client.post(reverse('suggestion_lookup'), {'reference': self.item.reference.lower()})
        self.assertRedirects(result, self.receipt)
        cookie = result.cookies[RECEIPT_COOKIE]
        self.assertTrue(cookie['httponly'])
        self.assertEqual(cookie['samesite'], 'Lax')
        self.assertEqual(int(cookie['max-age']), 365 * 86400)
        page = self.client.get(reverse('suggestion_lookup'))
        self.assertContains(page, self.item.reference)
        self.assertNotContains(page, self.item.title)
        self.client.cookies[RECEIPT_COOKIE] = 'forged'
        self.assertNotContains(self.client.get(reverse('suggestion_lookup')), self.item.reference)

    def test_invalid_missing_and_ambiguous_references_never_expose_data(self):
        for reference, status in [('wrong', 400), ('0' * 12, 404), ('a' * 1000, 400)]:
            response = self.client.get(reverse('suggestion_receipt', args=[reference]))
            self.assertEqual(response.status_code, status)
            self.assertNotContains(response, self.item.details, status_code=status)
        import uuid
        other = uuid.UUID(self.item.id.hex[:12] + '0' * 20)
        Suggestion.objects.create(id=other, kind='bug', title='another', details='another private item')
        self.assertEqual(self.client.get(self.receipt).status_code, 404)

    def test_lookup_limits_are_separate_and_failure_never_claims_a_result(self):
        with patch('catalog.suggestions._lookup_budget', side_effect=QuotaExceeded):
            page = self.client.get(self.receipt)
        self.assertEqual(page.status_code, 429)
        self.assertEqual(page['Retry-After'], '3600')
        self.assertIsNone(page.context['receipt'])
        with patch('catalog.suggestions._lookup_budget', side_effect=OperationalError):
            page = self.client.get(self.receipt)
        self.assertEqual(page.status_code, 503)
        self.assertIsNone(page.context['receipt'])
        self.assertEqual(page['Retry-After'], '5')
        now = timezone.now()
        with patch('catalog.suggestions.timezone.now', return_value=now):
            for _ in range(120):
                self.assertEqual(self.client.get(self.receipt).status_code, 200)
            self.assertEqual(self.client.get(self.receipt).status_code, 429)
        with patch('catalog.suggestions.timezone.now', return_value=now + timedelta(hours=1)):
            self.assertEqual(self.client.get(self.receipt).status_code, 200)
        self.assertTrue(all(row.key != '127.0.0.1' for row in SuggestionBudget.objects.all()))

    def test_management_filters_and_paginates_reply_state(self):
        self.handle('可查看的说明')
        for index in range(22):
            Suggestion.objects.create(kind='bug', title=f'no-reply-{index}', details='private')
        page = self.client.get(reverse('suggestion_management') + '?replied=no&page=2')
        self.assertEqual(page.context['page'].paginator.count, 22)
        self.assertEqual(len(page.context['page']), 2)
        self.assertContains(page, 'replied=no')
        self.assertEqual(self.client.get(reverse('suggestion_management') + '?replied=yes').context['page'].paginator.count, 1)

    def test_api_and_web_submissions_supply_receipt_url_without_changing_existing_contract(self):
        client = Client()
        ticket = client.get(reverse('suggestion_api')).json()
        result = client.post(reverse('suggestion_api'), {'submission': ticket['submission'], 'kind': 'bug',
            'title': 'new submission', 'details': 'private new details'}, content_type='application/json')
        self.assertEqual(result.status_code, 201)
        data = result.json()
        self.assertEqual(data['schema_version'], 1)
        self.assertEqual(data['reply_url'], reverse('suggestion_receipt', args=[data['reference']]))
        self.assertContains(client.get(reverse('suggestion_lookup')), data['reference'])
        self.assertNotContains(client.get(data['reply_url']), 'private new details')

from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import timedelta
import hashlib
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth.models import User
from django.db import close_old_connections, OperationalError
from django.test import Client, TestCase, TransactionTestCase
from django.utils import timezone
from .models import SiteVisitor
from .visitors import COOKIE, record_visit, traffic_summary


class VisitorTests(TestCase):
    def browser(self):
        client = Client(enforce_csrf_checks=True)
        client.get('/seeds/')
        return client

    def visit(self, client, **headers):
        return client.post('/api/v1/visitor/', HTTP_X_CSRFTOKEN=client.cookies[settings.CSRF_COOKIE_NAME].value,
            HTTP_USER_AGENT='Mozilla/5.0 Browser', **headers)

    def test_refresh_navigation_and_new_browser_get_correct_numbers(self):
        first, second = self.browser(), self.browser()
        one = self.visit(first)
        self.assertEqual(one.status_code, 200)
        number = one.json()['visitor_number']
        self.assertEqual(one.json()['greeting'], f'欢迎你，第{number}位好兄弟')
        first.get('/downloads/')
        again = self.visit(first)
        self.assertEqual(again.json()['visitor_number'], number)
        self.assertEqual(again.json()['total_visitors'], 1)
        two = self.visit(second)
        self.assertEqual(two.json()['visitor_number'], number + 1)
        self.assertEqual(two.json()['total_visitors'], 2)
        self.assertEqual(SiteVisitor.objects.get(pk=number).page_views, 2)
        self.assertTrue(one.cookies[COOKIE]['httponly'])
        self.assertEqual(one.cookies[COOKIE]['samesite'], 'Lax')
        self.assertEqual(one.cookies[COOKIE]['max-age'], 365 * 24 * 60 * 60)

    def test_cookie_survives_browser_session_and_is_secure_on_https(self):
        first = self.browser()
        result = self.visit(first, secure=True, HTTP_ORIGIN='https://testserver')
        self.assertEqual(result.status_code, 200)
        returning = self.browser()
        returning.cookies[COOKIE] = first.cookies[COOKIE].value
        self.assertEqual(self.visit(returning).json()['visitor_number'], result.json()['visitor_number'])
        self.assertTrue(result.cookies[COOKIE]['secure'])
        self.assertEqual(SiteVisitor.objects.count(), 1)
        # Neither a raw browser token nor an IP/user-agent is persisted.
        self.assertEqual(set(SiteVisitor._meta.fields[i].name for i in range(len(SiteVisitor._meta.fields))),
                         {'id', 'token_hash', 'first_seen', 'last_seen', 'page_views'})

    def test_tampered_cookie_cannot_claim_someone_elses_number(self):
        client = self.browser()
        original = self.visit(client).json()['visitor_number']
        client.cookies[COOKIE] = client.cookies[COOKIE].value + 'tampered'
        self.assertNotEqual(self.visit(client).json()['visitor_number'], original)
        self.assertEqual(SiteVisitor.objects.get(pk=original).page_views, 1)

    def test_csrf_and_read_only_endpoints_cannot_inflate_visitors(self):
        client = self.browser()
        self.assertEqual(client.post('/api/v1/visitor/').status_code, 403)
        self.assertEqual(client.get('/api/v1/visitor/').status_code, 405)
        for path in ['/health/', '/api/v1/catalog/', '/missing/', '/login/', '/seeds/00000000-0000-0000-0000-000000000000/']:
            response = client.get(path)
            self.assertNotIn(b'data-visitor-welcome', response.content)
        self.assertEqual(SiteVisitor.objects.count(), 0)
        self.assertEqual(client.post('/api/v1/visitor/', HTTP_X_CSRFTOKEN=client.cookies[settings.CSRF_COOKIE_NAME].value,
            HTTP_USER_AGENT='Googlebot/2.1').status_code, 204)
        self.assertEqual(SiteVisitor.objects.count(), 0)
        self.assertEqual(self.visit(client, HTTP_ORIGIN='https://other.invalid').status_code, 403)

    def test_counter_failure_does_not_break_public_page(self):
        client = self.browser()
        with patch('catalog.visitors.record_visit', side_effect=OperationalError('locked')):
            self.assertEqual(self.visit(client).status_code, 503)
            self.assertContains(client.get('/seeds/'), '欢迎你，好兄弟')

    def test_admin_summary_uses_local_calendar_and_counts_returning_visitors(self):
        now = timezone.now()
        old = record_visit('a' * 32, now - timedelta(days=2))
        SiteVisitor.objects.filter(pk=old.pk).update(first_seen=now - timedelta(days=2))
        record_visit('a' * 32, now)
        record_visit('b' * 32, now)
        data = traffic_summary()
        self.assertEqual((data['total'], data['today'], data['new_today'], data['page_views']), (2, 2, 1, 3))
        self.assertEqual(self.client.get('/manage/').status_code, 302)
        admin = User.objects.create_superuser('traffic-admin', password='only-used-in-isolated-tests')
        self.client.force_login(admin)
        page = self.client.get('/manage/')
        self.assertContains(page, '累计访客')
        self.assertContains(page, '今日新访客')
        self.assertEqual(page.context['traffic']['total'], 2)
        self.assertNotContains(page, 'data-visitor-welcome')


class ConcurrentVisitorTests(TransactionTestCase):
    def test_parallel_tabs_preserve_one_number_and_all_page_views(self):
        # File-backed SQLite exercises real locking; in-memory shared SQLite
        # deliberately fails immediately on a contested table lock.
        from tempfile import TemporaryDirectory
        from pathlib import Path
        import sqlite3
        with TemporaryDirectory() as folder:
            path = Path(folder) / 'visitors.sqlite3'
            with closing(sqlite3.connect(path)) as db, db:
                db.execute('CREATE TABLE catalog_sitevisitor (id INTEGER PRIMARY KEY AUTOINCREMENT, token_hash varchar(64) NOT NULL UNIQUE, first_seen datetime NOT NULL, last_seen datetime NOT NULL, page_views bigint NOT NULL)')
            def add(_):
                close_old_connections()
                from django.db import connections
                own = connections['default']
                own.settings_dict = {**own.settings_dict, 'NAME': str(path), 'OPTIONS': {'timeout': 5}}
                try:
                    return record_visit('c' * 32, timezone.now()).pk
                finally:
                    own.close()
            with ThreadPoolExecutor(max_workers=4) as pool:
                ids = list(pool.map(add, range(12)))
            self.assertEqual(len(set(ids)), 1)
            with closing(sqlite3.connect(path)) as db:
                self.assertEqual(db.execute('SELECT COUNT(*), SUM(page_views) FROM catalog_sitevisitor').fetchone(), (1, 12))

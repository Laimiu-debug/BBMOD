from contextlib import closing
import hashlib
import io
import sqlite3
import tarfile
import tempfile
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.paginator import Paginator
from django.db import connection
from django.test import Client, RequestFactory, TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from .community import catalogue_items
from .models import LoginAttempt, Mod, Release, SharedModFile, SiteVisitor
from .profiles import _source, _sources
from .services import public_releases
from .test_profiles import item, manifest, zipped
from .views import _login_keys
from .visitors import visitor_total


def reference_catalogue(params):
    """The catalogue algorithm before it moved into the database."""
    seen, latest = set(), []
    for release in public_releases():
        if release.mod_id not in seen:
            seen.add(release.mod_id)
            latest.append(release)
    releases = catalogue_items(latest)
    count = len(releases)
    query, category, source = params.get('q', '').strip()[:200], params.get('category', ''), params.get('source', '')
    if query:
        releases = [r for r in releases if query.casefold() in ' '.join(str(r['metadata'].get(k, '')) for k in ['title', 'english_name', 'summary', 'author']).casefold()]
    if category:
        releases = [r for r in releases if r['metadata'].get('category') == category]
    if source in ('hosted', 'original'):
        releases = [r for r in releases if r['source_kind'] == source]
    elif source == 'direct':
        releases = [r for r in releases if r['source_kind'] == 'original' and r['metadata'].get('official_downloads')]
    if params.get('sort') == 'name':
        releases.sort(key=lambda r: r['metadata'].get('title', ''))
    return count, Paginator(releases, 12).get_page(params.get('page'))


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class CatalogueQueryTests(TestCase):
    def setUp(self):
        owner = User.objects.create_user('author', first_name='测试作者')
        hidden = User.objects.create_user('hidden', is_active=False)
        start = timezone.now() - timedelta(days=30)
        categories = ['框架', '汉化', '基础功能']
        step = 0
        for number in range(16):
            mod = Mod.objects.create(owner=hidden if number == 15 else owner, install_name=f'mod_{number:02}.zip',
                title=f'作品 {number:02} Alpha' if number % 2 else f'Work {number:02}', summary='测试介绍',
                description='说明', license='测试授权', category=categories[number % 3], blocked=number == 14,
                source_url='https://www.nexusmods.com/battlebrothers/mods/542' if number == 3 else '')
            for version, status in [('1', 'published'), ('2', 'withdrawn' if number % 4 == 0 else 'published'), ('3', 'draft')]:
                release = Release.objects.create(mod=mod, version=version, notes='更新', metadata=mod.snapshot(),
                    archive=f'archives/{number}-{version}.zip', sha256=f'{number:02}{version}'.ljust(64, '0'), size=1, status=status,
                    published_at=start if status == 'published' else None)
                step += 1
                Release.objects.filter(pk=release.pk).update(created_at=start + timedelta(hours=step if number != 7 else 1000 - step))

    def test_database_pagination_matches_python_catalogue(self):
        variants = [{}, {'category': '框架'}, {'category': '汉化', 'source': 'original'}, {'source': 'hosted'},
                    {'source': 'original'}, {'source': 'direct'}, {'category': '不存在'}, {'q': 'alpha'},
                    {'q': 'Swifter'}, {'sort': 'name'}, {'q': '作品', 'category': '框架', 'source': 'hosted'}]
        public = Client()
        for params in variants:
            for page in ['1', '2', '3', '4', 'bad', '999']:
                query = {**params, 'page': page}
                response = public.get('/', query)
                count, expected = reference_catalogue(query)
                actual = response.context['page']
                self.assertEqual(response.context['count'], count, query)
                self.assertEqual(actual.paginator.count, expected.paginator.count, query)
                self.assertEqual(actual.number, expected.number, query)
                self.assertEqual([(r['url'], r['version'], r['metadata'].get('english_name')) for r in actual],
                                 [(r['url'], r['version'], r['metadata'].get('english_name')) for r in expected], query)

    def test_catalogue_crosses_from_hosted_releases_to_original_sources(self):
        first, second = (Client().get('/', {'page': n}).context['page'] for n in (1, 2))
        self.assertTrue(all(r['source_kind'] == 'hosted' for r in first))
        self.assertEqual([r['source_kind'] for r in second][:3], ['hosted', 'hosted', 'original'])
        self.assertEqual(sum(r['metadata'].get('slug') == 'swifter' for n in range(1, 5)
                             for r in Client().get('/', {'page': n}).context['page']), 0)

    def test_api_catalog_matches_latest_public_releases_and_supports_etag(self):
        public = Client()
        response = public.get('/api/v1/catalog/')
        mods = response.json()['mods']
        seen, expected = set(), []
        for release in public_releases():
            if release.mod_id not in seen:
                seen.add(release.mod_id)
                expected.append(str(release.pk))
        self.assertEqual([m['release_id'] for m in mods], expected)
        self.assertEqual(set(mods[0]), {'id', 'release_id', 'version', 'file_name', 'sha256', 'size', 'published_at',
                                        'notes', 'metadata', 'inspection', 'download_path', 'page_path'})
        tag = response['ETag']
        self.assertEqual(response['Cache-Control'], 'private, no-store')
        cached = public.get('/api/v1/catalog/', HTTP_IF_NONE_MATCH=tag)
        self.assertEqual((cached.status_code, cached.content, cached['ETag']), (304, b'', tag))
        self.assertEqual(public.get('/api/v1/catalog/', HTTP_IF_NONE_MATCH='"other"').status_code, 200)
        Release.objects.filter(pk=expected[0]).update(status='withdrawn')
        changed = public.get('/api/v1/catalog/', HTTP_IF_NONE_MATCH=tag)
        self.assertEqual(changed.status_code, 200)
        self.assertNotEqual(changed['ETag'], tag)
        Release.objects.filter(pk=expected[0]).update(status='published')
        self.assertEqual(public.get('/api/v1/catalog/', HTTP_IF_NONE_MATCH=tag).status_code, 304)
        for change in (lambda: Mod.objects.filter(install_name='mod_01.zip').update(blocked=True),
                       lambda: Mod.objects.filter(install_name='mod_02.zip').update(install_name='renamed.zip'),
                       lambda: User.objects.filter(username='author').update(is_active=False)):
            change()
            response = public.get('/api/v1/catalog/', HTTP_IF_NONE_MATCH=tag)
            self.assertEqual(response.status_code, 200)
            tag = response['ETag']

    def test_desktop_releases_api_supports_etag(self):
        response = Client().get('/api/v1/desktop/releases/')
        self.assertEqual(response.json(), {'schema_version': 1, 'recommended_version': None, 'releases': []})
        cached = Client().get('/api/v1/desktop/releases/', HTTP_IF_NONE_MATCH=response['ETag'])
        self.assertEqual(cached.status_code, 304)


class ProfileSourceBatchTests(TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.enterContext(override_settings(MEDIA_ROOT=temporary.name))
        self.owner = User.objects.create_user('author')
        self.files = [zipped(name) for name in ('public', 'withdrawn', 'blob', 'blocked', 'gone', 'missing')]

    def release(self, data, version, status='published', store=True):
        mod, _ = Mod.objects.get_or_create(owner=self.owner, install_name='batch.zip', defaults={'title': '作品'})
        release = Release(mod=mod, version=version, status=status, size=len(data), sha256=hashlib.sha256(data).hexdigest())
        if store:
            release.archive.save(version + '.zip', SimpleUploadedFile('mod.zip', data))
        else:
            release.archive = 'archives/absent.zip'
            release.save()
        return release

    def blob(self, data, blocked=False):
        blob = SharedModFile(sha256=hashlib.sha256(data).hexdigest(), size=len(data), blocked=blocked)
        blob.archive.save('blob.zip', SimpleUploadedFile('mod.zip', data))
        return blob

    def test_batched_sources_match_single_lookups_with_two_queries(self):
        public, withdrawn, blob, blocked, gone, missing = self.files
        self.release(public, '1')
        self.release(withdrawn, '2', 'withdrawn')
        self.blob(blob)
        self.blob(blocked, blocked=True)
        self.release(gone, '3', store=False)
        wanted = [(hashlib.sha256(d).hexdigest(), len(d)) for d in self.files]
        wanted += [(wanted[0][0], wanted[0][1] + 1), (wanted[2][0], None)]
        expected = [_source(sha, size) for sha, size in wanted]
        self.assertEqual([s for s, _ in expected],
                         ['available', 'blocked', 'available', 'blocked', 'missing', 'missing', 'missing', 'available'])
        with self.assertNumQueries(2):
            batched = _sources(wanted)
        self.assertEqual([(s, a.name if a else None) for s, a in batched],
                         [(s, a.name if a else None) for s, a in expected])

    def test_profile_negotiation_queries_do_not_grow_with_mod_count(self):
        def queries(*data):
            names = [f'mod_{n}.zip' for n in range(len(data))]
            payload = manifest(*(item(d, name) for d, name in zip(data, names)))
            client = Client()
            with CaptureQueriesContext(connection) as captured:
                response = client.post('/api/v1/profiles/plan/', payload, content_type='application/json',
                                       HTTP_X_BBMOD_PROFILE_SHARE='1')
            self.assertEqual(response.status_code, 200, response.content)
            return len(captured)
        self.release(self.files[0], '1')
        queries(self.files[0])
        self.assertEqual(queries(self.files[0]), queries(*self.files))


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class OperationalTests(TestCase):
    def test_accounts_page_is_paginated(self):
        admin = User.objects.create_superuser('admin', password='Admin-Password-1234')
        User.objects.bulk_create([User(username=f'author{n:02}') for n in range(55)])
        self.client.force_login(admin)
        first = self.client.get('/manage/accounts/')
        self.assertEqual(len(first.context['accounts']), 50)
        self.assertContains(first, '?page=2')
        second = self.client.get('/manage/accounts/', {'page': 2})
        self.assertEqual(len(second.context['accounts']), 6)
        self.assertContains(second, '上一页')
        self.assertEqual(self.client.get('/manage/accounts/', {'page': 'bad'}).context['accounts'].number, 1)

    def test_expired_attempts_never_throttle_even_between_sweeps(self):
        User.objects.create_user('author', password='Original-Password-1234')
        request = RequestFactory().post('/login/', {'username': 'author'}, REMOTE_ADDR='127.0.0.1')
        old = timezone.now() - timedelta(minutes=16)
        LoginAttempt.objects.bulk_create([LoginAttempt(key=k, failures=30, since=old) for k in _login_keys(request)])
        LoginAttempt.objects.create(key='other', failures=1, since=old)
        cache.set('bbmod-login-sweep', True, 600)
        self.addCleanup(cache.delete, 'bbmod-login-sweep')
        response = self.client.post('/login/', {'username': 'author', 'password': 'Original-Password-1234'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(list(LoginAttempt.objects.values_list('key', flat=True)), ['other'])
        cache.delete('bbmod-login-sweep')
        self.client.post('/login/', {'username': 'author', 'password': 'wrong'})
        self.assertFalse(LoginAttempt.objects.filter(key='other').exists())

    def test_upload_limit_applies_only_to_requests_with_bodies(self):
        self.assertEqual(self.client.get('/health/', CONTENT_LENGTH=str(10 * 1024**3)).status_code, 200)
        self.assertEqual(self.client.post('/login/', {}, CONTENT_LENGTH=str(10 * 1024**3)).status_code, 413)

    def test_visitor_total_follows_new_ids_and_recounts_after_reset(self):
        cache.delete('bbmod-visitor-total')
        self.addCleanup(cache.delete, 'bbmod-visitor-total')
        now = timezone.now()
        rows = SiteVisitor.objects.bulk_create([SiteVisitor(token_hash=str(n) * 64, last_seen=now) for n in range(3)])
        self.assertEqual(visitor_total(), 3)
        SiteVisitor.objects.create(token_hash='x' * 64, last_seen=now)
        with self.assertNumQueries(1):
            self.assertEqual(visitor_total(), 4)
        SiteVisitor.objects.filter(pk__gte=rows[1].pk).delete()
        self.assertEqual(visitor_total(), 1)

    def test_backup_keeps_only_newest_archives(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            backups = root / 'backups'
            backups.mkdir()
            for stamp in ('20260101T000000000000Z', '20260102T000000000000Z', '20260103T000000000000Z'):
                (backups / f'bbmod-hub-{stamp}.tar.gz').write_bytes(b'old')
            (backups / 'notes.txt').write_text('keep', encoding='utf-8')
            database = root / 'db.sqlite3'
            with closing(sqlite3.connect(database)) as db, db:
                db.executescript('CREATE TABLE catalog_release(archive, cover); CREATE TABLE catalog_sharedmodfile(archive);'
                                 'CREATE TABLE catalog_desktoprelease(file);')
            with override_settings(DATA_DIR=root, MEDIA_ROOT=root / 'private', DESKTOP_DOWNLOAD_ROOT=root / 'desktop',
                                   WIKI_ROOT=root / 'wiki'), patch.dict(settings.DATABASES['default'], {'NAME': str(database)}):
                output = io.StringIO()
                call_command('backup_hub', '--keep', '2', stdout=output)
                created = Path(output.getvalue().strip())
                with tarfile.open(created) as archive:
                    self.assertEqual(archive.getnames(), ['db.sqlite3'])
                self.assertEqual(sorted(p.name for p in backups.iterdir()),
                                 ['bbmod-hub-20260103T000000000000Z.tar.gz', created.name, 'notes.txt'])
                call_command('backup_hub', stdout=io.StringIO())
                self.assertEqual(len(list(backups.glob('bbmod-hub-*.tar.gz'))), 3)

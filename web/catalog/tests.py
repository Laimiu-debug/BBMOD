import hashlib
import io
import stat
import tempfile
import zipfile
from datetime import timedelta
from pathlib import Path
from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.utils import timezone
from app.core.archive_safety import inspect_archive
from .models import Mod, Release, AuthorProfile, AuditLog


def zipped(name='scripts/test.nut', content=b'// original test fixture only'):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr(name, content)
    return buf.getvalue()


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class PublishingTests(TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.override = override_settings(MEDIA_ROOT=self.temp.name)
        self.override.enable(); self.addCleanup(self.override.disable)
        self.author = User.objects.create_user('author', password='Original-Password-1234', first_name='测试作者')
        self.other = User.objects.create_user('other', password='Other-Password-1234')
        self.admin = User.objects.create_superuser('admin', password='Admin-Password-1234')
        self.mod = Mod.objects.create(owner=self.author, install_name='mod_test.zip', title='测试用作品',
            summary='测试正文', description='原创离线测试文件', license='测试授权', category='基础功能')
        self.client.force_login(self.author)

    def upload(self, version='1.0', publish=True, data=None, **extra):
        fields = {'version': version, 'notes': '初次发布', 'rights': 'on',
                  'archive': SimpleUploadedFile('mod.zip', data if data is not None else zipped(), content_type='application/zip')}
        if publish: fields['publish'] = 'on'
        fields.update(extra)
        return self.client.post(reverse('upload', args=[self.mod.pk]), fields)

    def test_direct_publish_and_anonymous_download(self):
        self.assertEqual(self.upload().status_code, 302)
        release = Release.objects.get()
        visitor = Client()
        payload = visitor.get('/api/v1/catalog/').json()
        self.assertEqual(payload['mods'][0]['version'], '1.0')
        self.assertContains(visitor.get(reverse('detail', args=[self.mod.pk])), '原创离线测试文件')
        response = visitor.get(reverse('download', args=[release.pk]))
        data = b''.join(response.streaming_content)
        self.assertEqual(hashlib.sha256(data).hexdigest(), payload['mods'][0]['sha256'])
        self.assertIn('attachment', response['Content-Disposition'])
        self.assertEqual(response['Cache-Control'], 'private, no-store')
        self.assertFalse(payload['mods'][0]['inspection']['game_tested'])

    @override_settings(
        ALLOWED_HOSTS=['bbmod.vercel.app'],
        CSRF_TRUSTED_ORIGINS=['https://bbmod.vercel.app'],
        SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTO', 'https'),
        SESSION_COOKIE_SECURE=True, CSRF_COOKIE_SECURE=True,
    )
    def test_gateway_login_csrf_cookies_and_private_cache(self):
        visitor = Client(enforce_csrf_checks=True)
        headers = {'HTTP_HOST': 'bbmod.vercel.app', 'HTTP_X_FORWARDED_PROTO': 'https'}
        page = visitor.get('/login/', **headers)
        self.assertEqual(page.status_code, 200)
        self.assertTrue(page.cookies[settings.CSRF_COOKIE_NAME]['secure'])
        fields = {'username': self.author.username, 'password': 'Original-Password-1234',
                  'csrfmiddlewaretoken': visitor.cookies[settings.CSRF_COOKIE_NAME].value}
        self.assertEqual(visitor.post('/login/', fields, HTTP_ORIGIN='https://untrusted.example', **headers).status_code, 403)
        login = visitor.post('/login/', fields, HTTP_ORIGIN='https://bbmod.vercel.app', **headers)
        self.assertEqual(login.status_code, 302)
        self.assertEqual(login['Location'], '/workshop/')
        self.assertTrue(login.cookies[settings.SESSION_COOKIE_NAME]['secure'])
        for path in ['/', '/api/v1/catalog/', '/workshop/', '/missing-page/']:
            response = visitor.get(path, **headers)
            self.assertEqual(response['Cache-Control'], 'private, no-store', path)

    def test_draft_private_and_published_by_author(self):
        self.upload(publish=False)
        release = Release.objects.get()
        self.assertEqual(Client().get(reverse('download', args=[release.pk])).status_code, 404)
        self.assertEqual(Client().get('/api/v1/catalog/').json()['mods'], [])
        self.client.post(reverse('release_action', args=[release.pk]), {'action': 'publish'})
        self.assertEqual(len(Client().get('/api/v1/catalog/').json()['mods']), 1)

    def test_author_cannot_edit_or_download_other_draft(self):
        self.upload(publish=False)
        release = Release.objects.get()
        self.client.force_login(self.other)
        for route in ['edit_mod', 'upload']:
            self.assertEqual(self.client.get(reverse(route, args=[self.mod.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse('download', args=[release.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse('release_action', args=[release.pk]), {'action': 'publish'}).status_code, 404)
        self.assertEqual(self.client.get('/manage/').status_code, 302)

    def test_admin_delist_blocks_author_republish_and_file(self):
        self.upload()
        release = Release.objects.get()
        self.client.force_login(self.admin)
        self.client.post(reverse('moderate', args=[self.mod.pk]), {'action': 'block', 'reason': '测试下架'})
        visitor = Client()
        self.assertEqual(visitor.get('/api/v1/catalog/').json()['mods'], [])
        self.assertEqual(visitor.get(reverse('download', args=[release.pk])).status_code, 404)
        self.client.force_login(self.author)
        self.client.post(reverse('release_action', args=[release.pk]), {'action': 'publish'})
        self.assertContains(self.upload(version='2.0'), '作品已被管理员下架')
        self.assertEqual(Release.objects.count(), 1)
        self.client.force_login(self.admin)
        self.client.post(reverse('moderate', args=[self.mod.pk]), {'action': 'restore'})
        self.assertEqual(len(visitor.get('/api/v1/catalog/').json()['mods']), 1)

    def test_disable_account_hides_files_and_invalidates_session(self):
        self.upload()
        author_client = Client(); author_client.force_login(self.author)
        self.client.force_login(self.admin)
        self.client.post(reverse('account_change', args=[self.author.pk]), {'action': 'toggle'})
        self.assertEqual(author_client.get('/workshop/').status_code, 302)
        self.assertEqual(Client().get('/api/v1/catalog/').json()['mods'], [])
        self.assertEqual(Client().get(reverse('download', args=[Release.objects.get().pk])).status_code, 404)

    def test_duplicate_versions_immutable(self):
        self.upload()
        original = Release.objects.get().sha256
        self.assertContains(self.upload(data=zipped(content=b'changed')), '版本号已存在')
        self.assertEqual(Release.objects.count(), 1)
        self.assertEqual(Release.objects.get().sha256, original)
        self.assertEqual(len(list(Path(self.temp.name).rglob('*.zip'))), 1)

    def test_draft_edit_never_mutates_published_snapshot(self):
        self.upload()
        self.mod.title = '<script>alert(1)</script>'
        self.mod.save()
        self.assertEqual(Client().get('/api/v1/catalog/').json()['mods'][0]['metadata']['title'], '测试用作品')
        self.upload(version='2.0')
        response = Client().get(reverse('detail', args=[self.mod.pk]))
        self.assertContains(response, '&lt;script&gt;')
        self.assertNotContains(response, '<script>alert(1)</script>')

    def test_withdraw_newest_falls_back_to_old_version(self):
        self.upload(); self.upload(version='2.0')
        release = Release.objects.get(version='2.0')
        self.client.post(reverse('release_action', args=[release.pk]), {'action': 'withdraw'})
        self.assertEqual(Client().get('/api/v1/catalog/').json()['mods'][0]['version'], '1.0')
        self.assertEqual(Client().get(reverse('download', args=[release.pk])).status_code, 404)

    def test_upload_permissions_size_quota_and_rights(self):
        self.assertContains(self.upload(rights=''), '这个字段是必填项')
        self.assertEqual(Release.objects.count(), 0)
        with override_settings(AUTHOR_QUOTA_BYTES=1):
            self.assertContains(self.upload(), '存储空间不足')
        with override_settings(MAX_MOD_BYTES=10):
            self.assertContains(self.upload(), 'ZIP 大小')
        self.assertEqual(Release.objects.count(), 0)
        with override_settings(UPLOADS_PER_DAY=0):
            self.assertContains(self.upload(), '今日上传次数')

    def test_image_reencoded_and_private_until_publish(self):
        from PIL import Image
        buf = io.BytesIO(); Image.new('RGB', (64, 64), '#be9870').save(buf, 'PNG')
        self.upload(publish=False, cover=SimpleUploadedFile('image.png', buf.getvalue()))
        r = Release.objects.get()
        self.assertTrue(r.cover.name.endswith('.webp'))
        self.assertEqual(Client().get(reverse('cover', args=[r.pk])).status_code, 404)
        response = self.client.get(reverse('cover', args=[r.pk]))
        self.assertEqual(response['Content-Type'], 'image/webp')
        response.close()

    def test_malicious_archives_rejected_without_writing(self):
        for path in ['../evil.nut', '/scripts/evil.nut', 'scripts\\evil.nut', 'scripts/exploit.exe', 'wrapper/mod.zip', 'wrapper/scripts/test.nut']:
            # Windows ZipInfo normalizes backslashes at construction; emulate a foreign archive.
            data = zipped(path.replace('\\', '/'))
            if '\\' in path:
                data = data.replace(path.replace('\\', '/').encode(), path.encode())
            response = self.upload(data=data)
            self.assertEqual(response.status_code, 200, path)
            self.assertEqual(Release.objects.count(), 0, path)
        self.assertEqual(list(Path(self.temp.name).rglob('*.zip')), [])

    def test_zip_symlinks_duplicates_and_crc(self):
        for kind in ['symlink', 'duplicate', 'bomb', 'bad_crc']:
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
                if kind == 'symlink':
                    info = zipfile.ZipInfo('scripts/link'); info.external_attr = (stat.S_IFLNK | 0o777) << 16
                    z.writestr(info, '/etc/passwd')
                elif kind == 'duplicate':
                    z.writestr('scripts/test.nut', 'a'); z.writestr('scripts/TEST.nut', 'b')
                elif kind == 'bomb': z.writestr('scripts/huge.nut', b'0' * 4_000_000)
                else: z.writestr('scripts/test.nut', 'hello')
            data = buf.getvalue()
            if kind == 'bad_crc': data = data[:-20]
            with self.assertRaises(ValueError, msg=kind): inspect_archive(io.BytesIO(data))

    def test_csrf_required_and_get_cannot_mutate(self):
        csrf_client = Client(enforce_csrf_checks=True); csrf_client.force_login(self.admin)
        self.assertEqual(csrf_client.post('/manage/accounts/', {'username': 'bad'}).status_code, 403)
        self.assertEqual(self.client.get('/logout/').status_code, 405)
        self.upload()
        r = Release.objects.get()
        self.assertEqual(self.client.get(reverse('release_action', args=[r.pk])).status_code, 405)

    def test_initial_password_and_admin_reset_force_change(self):
        self.client.force_login(self.admin)
        result = self.client.post('/manage/accounts/', {'username': 'new_author', 'first_name': '作者二',
            'password1': 'Initial-WellChosen-834', 'password2': 'Initial-WellChosen-834'})
        self.assertEqual(result.status_code, 302)
        new = User.objects.get(username='new_author')
        self.assertFalse(new.is_staff)
        self.client.force_login(new)
        self.assertRedirects(self.client.get('/workshop/'), '/password/')
        self.assertEqual(self.client.post('/password/', {'old_password': 'Initial-WellChosen-834',
            'new_password1': 'Changed-Personal-945', 'new_password2': 'Changed-Personal-945'}).status_code, 302)
        self.assertEqual(self.client.get('/workshop/').status_code, 200)
        self.assertFalse(AuthorProfile.objects.get(user=new).must_change_password)

    def test_login_throttles_and_logout_requires_post(self):
        self.client.logout()
        for _ in range(8): self.client.post('/login/', {'username': 'author', 'password': 'wrong'})
        self.assertContains(self.client.post('/login/', {'username': 'author', 'password': 'Original-Password-1234'}), '尝试次数过多')

    def test_public_and_private_page_rendering(self):
        self.upload()
        for path in ['/', '/?q=测试', '/?q=不存在', '/downloads/', '/workshop/', reverse('upload', args=[self.mod.pk]), reverse('edit_mod', args=[self.mod.pk])]:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200, path)
            self.assertIn('Content-Security-Policy', response)
        self.client.force_login(self.admin)
        for path in ['/manage/', '/manage/accounts/', reverse('account_change', args=[self.author.pk])]:
            self.assertEqual(self.client.get(path).status_code, 200, path)
        self.assertGreater(AuditLog.objects.count(), 0)

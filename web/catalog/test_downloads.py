import hashlib
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone

from .models import Mod, Release, SharedModFile, SharedProfile
from .tests import zipped


@override_settings(MOD_DOWNLOAD_ACCEL=True)
class AcceleratedDownloadTests(TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.enterContext(override_settings(MEDIA_ROOT=self.root))
        owner = User.objects.create_user('download-author')
        mod = Mod.objects.create(owner=owner, install_name='mod_fixture.zip', title='下载测试')
        self.data = zipped()
        self.sha = hashlib.sha256(self.data).hexdigest()
        self.release = Release.objects.create(mod=mod, version='1', status='published',
            archive=SimpleUploadedFile('mod_fixture.zip', self.data), size=len(self.data), sha256=self.sha,
            published_at=timezone.now())
        self.url = f'/files/{self.release.pk}/download/'

    def test_large_file_is_not_streamed_by_application_and_head_works(self):
        for method in (self.client.get, self.client.head):
            with patch('django.db.models.fields.files.FieldFile.open', side_effect=AssertionError('must not stream')):
                response = method(self.url, HTTP_RANGE='bytes=10-')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.content, b'')
            self.assertEqual(response['X-Accel-Redirect'], '/_mods/' + self.release.archive.name)
            self.assertEqual(response['Content-Length'], str(len(self.data)))
            self.assertEqual(response['X-Checksum-SHA256'], self.sha)
            self.assertIn('mod_fixture.zip', response['Content-Disposition'])
            self.assertEqual(response['Cache-Control'], 'private, no-store')

    def test_resume_requests_still_obey_moderation(self):
        self.release.status = 'withdrawn'
        self.release.save()
        for method in (self.client.get, self.client.head):
            response = method(self.url, HTTP_RANGE='bytes=10-')
            self.assertEqual(response.status_code, 404)
            self.assertNotIn('X-Accel-Redirect', response)

    def test_missing_or_truncated_file_is_unavailable(self):
        path = Path(self.release.archive.path)
        path.write_bytes(b'partial')
        self.assertEqual(self.client.get(self.url).status_code, 404)
        path.unlink()
        self.assertEqual(self.client.head(self.url).status_code, 404)

    def test_path_outside_storage_is_unavailable(self):
        self.release.archive.name = '../private.txt'
        self.release.save()
        self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_symlink_cannot_escape_storage(self):
        path = Path(self.release.archive.path)
        target = self.root / 'original.zip'
        path.replace(target)
        try:
            path.symlink_to(target)
        except OSError:
            self.skipTest('symlink creation unavailable')
        self.assertEqual(self.client.get(self.url).status_code, 404)

    @override_settings(MOD_DOWNLOAD_ACCEL=False)
    def test_development_fallback_and_head(self):
        response = self.client.get(self.url)
        self.assertEqual(b''.join(response.streaming_content), self.data)
        response.close()
        response = self.client.head(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'')
        self.assertNotIn('X-Accel-Redirect', response)

    def test_shared_file_uses_acceleration_and_honors_blocking(self):
        blob = SharedModFile.objects.create(sha256=self.sha, size=len(self.data),
            archive=SimpleUploadedFile('shared.zip', self.data))
        profile = SharedProfile.objects.create(fingerprint='a' * 64, manifest={'mods': [
            {'sha256': self.sha, 'size': len(self.data), 'file_name': 'mod_shared.zip'}]})
        url = f'/api/v1/profiles/{profile.pk}/files/{self.sha}/'
        response = self.client.head(url, HTTP_RANGE='bytes=10-')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response['X-Accel-Redirect'].startswith('/_mods/'))
        self.assertIn('mod_shared.zip', response['Content-Disposition'])
        blob.blocked = True
        blob.save()
        self.assertEqual(self.client.get(url, HTTP_RANGE='bytes=10-').status_code, 404)

    def test_covers_keep_image_type(self):
        self.release.cover.save('cover.webp', SimpleUploadedFile('cover.webp', b'fixture'))
        response = self.client.get(f'/files/{self.release.pk}/cover/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/webp')
        self.assertNotIn('X-Checksum-SHA256', response)

    @override_settings(PUBLIC_DOWNLOAD_BASE='https://gongpro.cn/bbmod-origin')
    def test_browser_links_use_direct_origin_but_api_paths_stay_relative(self):
        from .templatetags.downloads import download_url
        self.assertEqual(download_url('download', self.release.pk), 'https://gongpro.cn/bbmod-origin' + self.url)
        self.assertEqual(download_url('login'), '/login/')
        page = self.client.get(f'/mods/{self.release.mod_id}/')
        self.assertContains(page, 'href="https://gongpro.cn/bbmod-origin' + self.url + '"')
        self.assertEqual(self.client.get('/api/v1/catalog/').json()['mods'][0]['download_path'], self.url)

    @override_settings(PUBLIC_DOWNLOAD_BASE='')
    def test_default_browser_links_remain_same_site(self):
        from .templatetags.downloads import download_url
        self.assertEqual(download_url('download', self.release.pk), self.url)

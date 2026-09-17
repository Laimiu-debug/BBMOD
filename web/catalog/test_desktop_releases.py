import hashlib
import io
import struct
import tarfile
import tempfile
from pathlib import Path
from unittest.mock import patch
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from .desktop import version_key
from .models import DesktopRelease


def exe_fixture(marker=b'test'):
    # Minimal header fixture for format checks; never launched as a program.
    data = bytearray(256)
    data[:2] = b'MZ'
    struct.pack_into('<I', data, 60, 64)
    data[64:68] = b'PE\0\0'
    struct.pack_into('<H', data, 68, 0x8664)
    struct.pack_into('<HH', data, 86, 2, 0x20b)
    data.extend(marker)
    return bytes(data)


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class DesktopReleaseTests(TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.enterContext(override_settings(DESKTOP_DOWNLOAD_ROOT=self.root / 'desktop',
            DESKTOP_DOWNLOAD_ACCEL=False, DATA_DIR=self.root, MEDIA_ROOT=self.root / 'private'))
        self.admin = User.objects.create_superuser('admin', password='Local-Test-Password-2948')
        self.author = User.objects.create_user('author', password='Local-Test-Password-9845')
        self.client.force_login(self.admin)

    def upload(self, version='0.3.0-rc.5', publish=True, body=None, **fields):
        values = {'version': version, 'notes': '本次版本的更新说明',
                  'file': SimpleUploadedFile('BBMOD.exe', body if body is not None else exe_fixture())}
        if publish:
            values['publish'] = 'on'
        values.update(fields)
        return self.client.post('/manage/software/', values)

    def test_admin_upload_anonymous_download_and_versioned_filename(self):
        self.assertRedirects(self.upload(), '/manage/software/')
        release = DesktopRelease.objects.get()
        self.assertTrue(release.prerelease)
        self.assertEqual(release.filename, 'BBMOD-0.3.0-rc.5.exe')
        self.assertTrue(Path(release.file.path).is_relative_to(self.root / 'desktop'))
        visitor = Client()
        url = reverse('desktop_version_download', args=[release.pk])
        page = visitor.get('/downloads/')
        self.assertContains(page, f'href="{url}" download="{release.filename}"')
        self.assertNotContains(page, 'github.com')
        response = visitor.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('Location', response)
        self.assertEqual(b''.join(response.streaming_content), exe_fixture())
        response.close()
        for response in [response, visitor.head(url)]:
            self.assertEqual(response['Content-Disposition'], 'attachment; filename="BBMOD-0.3.0-rc.5.exe"')
            self.assertEqual(response['X-Checksum-SHA256'], hashlib.sha256(exe_fixture()).hexdigest())
            self.assertEqual(int(response['Content-Length']), len(exe_fixture()))
            self.assertEqual(response['Cache-Control'], 'private, no-store')
        self.assertEqual(visitor.post(url).status_code, 405)

    def test_history_numeric_order_channels_and_stable_recommendation(self):
        for version in ['0.3.0-rc.10', '0.2.0', '0.3.0-rc.9', '0.1.0']:
            self.upload(version)
        self.upload('0.4.0', publish=False)
        payload = Client().get('/api/v1/desktop/releases/').json()
        self.assertEqual([r['version'] for r in payload['releases']], ['0.3.0-rc.10', '0.3.0-rc.9', '0.2.0', '0.1.0'])
        self.assertEqual(payload['recommended_version'], '0.2.0')
        self.assertTrue(all(r['download_path'].startswith('/downloads/windows/') for r in payload['releases']))
        self.assertContains(Client().get('/downloads/?channel=stable'), '0.2.0')
        self.assertNotContains(Client().get('/downloads/?channel=stable'), '0.3.0-rc.10')
        self.assertContains(Client().get('/downloads/?channel=preview'), '推荐 0.3.0-rc.10')
        self.assertEqual(Client().head('/downloads/windows/')['Content-Disposition'], 'attachment; filename="BBMOD-0.2.0.exe"')
        self.assertGreater(version_key('0.3.0'), version_key('0.3.0-rc.10'))

    def test_author_cannot_publish_program_or_change_status(self):
        self.upload()
        release = DesktopRelease.objects.get()
        url = reverse('software_action', args=[release.pk])
        self.client.force_login(self.author)
        self.assertEqual(self.upload('1.0.0').status_code, 302)
        self.assertEqual(self.client.get('/manage/software/').status_code, 302)
        self.assertEqual(self.client.post(url, {'action': 'withdraw'}).status_code, 302)
        release.refresh_from_db()
        self.assertEqual(release.status, 'published')
        self.assertEqual(DesktopRelease.objects.count(), 1)
        self.assertNotContains(self.client.get('/'), '>管理后台<')

    def test_draft_and_withdrawn_downloads_are_private(self):
        self.upload(publish=False)
        release = DesktopRelease.objects.get()
        url = reverse('desktop_version_download', args=[release.pk])
        action = reverse('software_action', args=[release.pk])
        visitor = Client()
        self.assertEqual(visitor.get(url).status_code, 404)
        self.assertEqual(self.client.head(url).status_code, 200)
        self.client.post(action, {'action': 'publish'})
        self.assertEqual(visitor.head(url).status_code, 200)
        self.client.post(action, {'action': 'withdraw'})
        self.assertEqual(visitor.get(url).status_code, 404)
        self.assertEqual(visitor.get('/api/v1/desktop/releases/').json()['releases'], [])
        self.assertEqual(self.client.get(action).status_code, 405)

    def test_invalid_exe_or_version_and_duplicate_cannot_overwrite(self):
        for body in [b'not exe', exe_fixture().replace(b'PE\0\0', b'NOPE'), exe_fixture()[:80]]:
            self.assertEqual(self.upload(body=body).status_code, 200)
        for version in ['latest', '0.3.0-rc.05', '../../bad', '01.0.0']:
            self.assertEqual(self.upload(version).status_code, 200)
        self.assertEqual(DesktopRelease.objects.count(), 0)
        self.assertContains(self.upload('1.0.0', file=SimpleUploadedFile('BBMOD-2.0.0.exe', exe_fixture())), '版本号与 EXE 文件名不一致')
        self.upload()
        original = DesktopRelease.objects.get()
        self.assertContains(self.upload(body=exe_fixture(b'changed')), '该版本已存在')
        self.assertEqual(DesktopRelease.objects.count(), 1)
        self.assertEqual(Path(original.file.path).read_bytes(), exe_fixture())
        self.assertEqual(len(list((self.root / 'desktop').rglob('*.exe'))), 1)

    def test_validation_failure_and_storage_failure_leave_no_release_file(self):
        with override_settings(MAX_DESKTOP_BYTES=100):
            self.assertContains(self.upload(), '程序大小不能超过')
        with patch('catalog.desktop.audit', side_effect=RuntimeError('database write failed')):
            with self.assertRaises(RuntimeError):
                self.upload()
        self.assertEqual(DesktopRelease.objects.count(), 0)
        self.assertEqual(list((self.root / 'desktop').rglob('*.exe')), [])

    def test_missing_file_unavailable_and_nginx_internal_response(self):
        self.upload()
        release = DesktopRelease.objects.get()
        url = reverse('desktop_version_download', args=[release.pk])
        with override_settings(DESKTOP_DOWNLOAD_ACCEL=True):
            response = Client().get(url)
            self.assertEqual(response['X-Accel-Redirect'], '/_desktop/' + release.file.name)
            self.assertEqual(response.content, b'')
        self.assertEqual(Client().get('/_desktop/' + release.file.name).status_code, 404)
        Path(release.file.path).write_bytes(b'incomplete')
        self.assertEqual(Client().get(url).status_code, 404)
        self.assertNotContains(Client().get('/downloads/'), '直接下载 Windows 版')

    def test_ajax_publish_and_csrf(self):
        csrf = Client(enforce_csrf_checks=True)
        csrf.force_login(self.admin)
        self.assertEqual(csrf.post('/manage/software/', {}).status_code, 403)
        response = self.client.post('/manage/software/', {'version': '1.0.0', 'notes': '说明', 'publish': 'on',
            'file': SimpleUploadedFile('BBMOD.exe', exe_fixture())}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.json(), {'redirect': '/manage/software/'})

    def test_import_command_validates_checksum_and_preserves_existing_version(self):
        executable = self.root / 'BBMOD-0.3.0-rc.5.exe'
        executable.write_bytes(exe_fixture())
        notes = self.root / 'notes.txt'
        notes.write_text('服务器导入验证', encoding='utf8')
        args = [str(executable), '--release-version', '0.3.0-rc.5', '--admin', self.admin.username,
                '--notes', str(notes), '--publish']
        with self.assertRaisesMessage(CommandError, 'SHA-256'):
            call_command('import_desktop', *args, '--sha256', '0' * 64, stdout=io.StringIO())
        self.assertEqual(DesktopRelease.objects.count(), 0)
        digest = hashlib.sha256(exe_fixture()).hexdigest()
        for _ in range(2):
            call_command('import_desktop', *args, '--sha256', digest, stdout=io.StringIO())
        self.assertEqual(DesktopRelease.objects.count(), 1)
        release = DesktopRelease.objects.get()
        self.assertEqual(release.status, 'published')
        self.assertEqual(Path(release.file.path).read_bytes(), exe_fixture())

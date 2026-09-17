import tempfile
from pathlib import Path
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from .models import Mod, Release
from .tests import zipped


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class QuickPublishTests(TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.enterContext(override_settings(MEDIA_ROOT=self.temp.name))
        self.author = User.objects.create_user('author', password='Author-Password-1234')
        self.client.force_login(self.author)

    def upload(self, **extra):
        fields = {'summary': '便于查看装备状态。', 'version': '1.0.0', 'rights': 'on', 'publish': 'on',
                  'archive': SimpleUploadedFile('mod_example.zip', zipped())}
        fields.update(extra)
        return self.client.post('/workshop/new/', fields)

    def test_one_form_creates_and_publishes_mod_without_advanced_fields(self):
        response = self.upload()
        self.assertEqual(response.status_code, 302)
        mod = Mod.objects.get()
        release = Release.objects.get()
        self.assertEqual(mod.install_name, 'mod_example.zip')
        self.assertEqual(mod.description, mod.summary)
        self.assertEqual(release.status, 'published')
        self.assertEqual(release.metadata['license'], '上传者确认具备本站分发授权，其他用途请联系作者。')
        self.assertEqual(Client().get('/api/v1/catalog/').json()['mods'][0]['version'], '1.0.0')

    def test_unicode_filename_gets_installable_name_but_title_is_preserved(self):
        self.assertEqual(self.upload(archive=SimpleUploadedFile('装备状态.zip', zipped())).status_code, 302)
        mod = Mod.objects.get()
        self.assertEqual(mod.title, '装备状态')
        self.assertRegex(mod.install_name, r'^mod_[a-f0-9]+\.zip$')

    def test_missing_rights_bad_zip_or_quota_does_not_leave_empty_work(self):
        self.assertContains(self.upload(rights=''), '这个字段是必填项')
        self.assertContains(self.upload(archive=SimpleUploadedFile('bad.zip', b'broken')), 'ZIP 损坏')
        with override_settings(AUTHOR_QUOTA_BYTES=1):
            self.assertContains(self.upload(), '存储空间不足')
        self.assertEqual(Mod.objects.count(), 0)
        self.assertEqual(Release.objects.count(), 0)
        self.assertEqual(list(Path(self.temp.name).rglob('*.zip')), [])

    def test_advanced_fields_preserved_and_draft_not_exposed(self):
        self.upload(title='自定标题', description='详细使用方法', license='MIT', requires='mod_hooks',
                    install_name='z_mod_order.zip', publish='')
        release = Release.objects.get()
        self.assertEqual(release.metadata['requires'], ['mod_hooks'])
        self.assertEqual(release.metadata['description'], '详细使用方法')
        self.assertEqual(release.mod.install_name, 'z_mod_order.zip')
        self.assertEqual(Client().get('/api/v1/catalog/').json()['mods'], [])

    def test_duplicate_does_not_overwrite_or_create_extra_work(self):
        self.upload()
        self.assertContains(self.upload(), '这个安装文件名已被另一作品使用')
        self.assertEqual(Mod.objects.count(), 1)
        self.assertEqual(Release.objects.count(), 1)

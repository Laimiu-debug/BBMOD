import copy
import hashlib
import importlib.util
import io
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import patch
from unittest import skipUnless

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, LiveServerTestCase, Client, override_settings

from .models import Mod, Release, SharedModFile, SharedProfile


def zipped(label='one'):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('scripts/' + label + '.nut', '// ' + label)
    return stream.getvalue()


def item(data, name='mod_one.zip'):
    return {'file_name': name, 'sha256': hashlib.sha256(data).hexdigest(), 'size': len(data),
            'title': name, 'version': '1'}


def manifest(*items):
    return {'schema_version': 1, 'name': '测试组合', 'note': '测试介绍', 'game_version': '1.5.2.3', 'mods': list(items)}


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class ProfileTests(TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.storage = Path(temporary.name)
        override = override_settings(MEDIA_ROOT=temporary.name)
        override.enable()
        self.addCleanup(override.disable)
        self.client = Client(enforce_csrf_checks=True)
        self.first, self.second = zipped('first'), zipped('second')
        self.payload = manifest(item(self.first), item(self.second, 'mod_two.zip'))

    def post(self, path, payload=None, **headers):
        return self.client.post('/api/v1/profiles/' + path, payload or self.payload,
            content_type='application/json', HTTP_X_BBMOD_PROFILE_SHARE='1', **headers)

    def upload(self, data, row):
        return self.client.post('/api/v1/profiles/files/' + row['sha256'] + '/',
            {'ticket': row.get('ticket', ''), 'archive': SimpleUploadedFile('mod.zip', data)},
            HTTP_X_BBMOD_PROFILE_SHARE='1')

    def publish_all(self):
        rows = self.post('plan/').json()['files']
        for data, row in zip((self.first, self.second), rows):
            self.assertEqual(self.upload(data, row).status_code, 201)
        response = self.post('')
        self.assertEqual(response.status_code, 201, response.content)
        return response.json()

    def release(self, data, version='1', status='published'):
        owner, _ = User.objects.get_or_create(username='author')
        mod, _ = Mod.objects.get_or_create(owner=owner, install_name='different_name.zip', defaults={'title': '官方作品'})
        release = Release(mod=mod, version=version, status=status, size=len(data), sha256=hashlib.sha256(data).hexdigest())
        release.archive.save(version + '.zip', SimpleUploadedFile('mod.zip', data))
        return release

    def test_reuse_historical_release_by_content_and_upload_only_miss(self):
        old = self.release(self.first)
        self.release(zipped('newer'), '2')
        plan = self.post('plan/').json()['files']
        self.assertEqual([r['status'] for r in plan], ['available', 'missing'])
        self.assertNotIn('ticket', plan[0])
        self.assertEqual(self.post('').status_code, 400)
        self.assertEqual(SharedProfile.objects.count(), 0)
        self.assertEqual(self.upload(self.second, plan[1]).status_code, 201)
        response = self.post('')
        self.assertEqual(response.status_code, 201)
        profile = response.json()['id']
        self.assertEqual(SharedModFile.objects.count(), 1)
        self.assertEqual(self.post('').status_code, 200)
        self.assertEqual(SharedProfile.objects.count(), 1)
        self.assertEqual(self.post('plan/').json()['files'][1]['status'], 'available')
        result = self.client.get(f'/api/v1/profiles/{profile}/files/{old.sha256}/')
        self.assertEqual(b''.join(result.streaming_content), self.first)
        result.close()
        self.assertEqual(result['X-Checksum-SHA256'], old.sha256)

    def test_same_name_different_bytes_is_missing_and_renamed_bytes_reused(self):
        self.release(self.first)
        changed = manifest(item(self.second, 'different_name.zip'))
        self.assertEqual(self.post('plan/', changed).json()['files'][0]['status'], 'missing')
        renamed = manifest(item(self.first, 'renamed.zip'))
        self.assertEqual(self.post('plan/', renamed).json()['files'][0]['status'], 'available')

    def test_interrupted_sharing_reuses_uploaded_file_and_publishes_only_when_complete(self):
        plan = self.post('plan/').json()['files']
        self.assertEqual(self.upload(self.first, plan[0]).status_code, 201)
        self.assertEqual(self.upload(self.first, plan[0]).status_code, 200)
        self.assertEqual(len(list(self.storage.rglob('*.zip'))), 1)
        self.assertEqual(self.post('').status_code, 400)
        self.assertEqual([r['status'] for r in self.post('plan/').json()['files']], ['available', 'missing'])
        self.assertEqual(self.upload(self.second, plan[1]).status_code, 201)
        self.assertEqual(self.post('').status_code, 201)

    def test_hash_mismatch_corrupt_archive_and_forged_ticket_store_nothing(self):
        row = self.post('plan/').json()['files'][0]
        same_size = b'x' * len(self.first)
        self.assertEqual(self.upload(same_size, row).status_code, 400)
        row['ticket'] = 'invalid'
        self.assertEqual(self.upload(self.first, row).status_code, 400)
        self.assertFalse(SharedModFile.objects.exists())
        self.assertFalse(list(self.storage.rglob('*.zip')))

    def test_browser_requests_and_unsafe_manifests_are_rejected(self):
        self.assertEqual(self.post('plan/', HTTP_ORIGIN='https://other.invalid').status_code, 400)
        self.assertEqual(self.client.post('/api/v1/profiles/plan/', self.payload, content_type='application/json').status_code, 400)
        for transform in (lambda p: p['mods'][0].update(file_name='../escape.zip'),
                          lambda p: p['mods'][0].update(file_name='CON.zip'),
                          lambda p: p['mods'][0].update(file_name='data_001.dat'),
                          lambda p: p['mods'][0].update(file_name='zzzz_bbmod_preload.zip'),
                          lambda p: p['mods'][0].update(size=True),
                          lambda p: p['mods'].append(dict(p['mods'][0])),
                          lambda p: p.update(schema_version=True)):
            value = copy.deepcopy(self.payload)
            transform(value)
            self.assertEqual(self.post('plan/', value).status_code, 400)
        self.assertFalse(SharedProfile.objects.exists())

    def test_moderated_or_withdrawn_content_cannot_be_reintroduced(self):
        release = self.release(self.first, status='withdrawn')
        self.assertEqual(self.post('plan/').json()['files'][0]['status'], 'blocked')
        release.status = 'published'
        release.save()
        plan = self.post('plan/').json()['files']
        self.upload(self.second, plan[1])
        identity = self.post('').json()['id']
        release.status = 'withdrawn'
        release.save()
        self.assertEqual(self.client.get(f'/api/v1/profiles/{identity}/').status_code, 409)
        self.assertEqual(self.client.get(f'/api/v1/profiles/{identity}/files/{release.sha256}/').status_code, 404)
        self.assertContains(self.client.get(f'/profiles/{identity}/'), '暂不可用')
        self.assertNotContains(self.client.get(f'/profiles/{identity}/'), f'bbmod://profiles/{identity}')

    def test_blob_block_and_profile_block_apply_to_api_and_retry(self):
        published = self.publish_all()
        identity = published['id']
        self.assertContains(self.client.get(published['page_path']), f'bbmod://profiles/{identity}')
        self.assertContains(self.client.get('/profiles/'), self.payload['name'])
        blob = SharedModFile.objects.get(pk=self.payload['mods'][0]['sha256'])
        blob.blocked = True
        blob.save()
        self.assertEqual(self.client.get(f'/api/v1/profiles/{identity}/').status_code, 409)
        self.assertEqual(self.post('plan/').json()['files'][0]['status'], 'blocked')
        blob.blocked = False
        blob.save()
        SharedProfile.objects.update(blocked=True)
        self.assertEqual(self.client.get(published['page_path']).status_code, 404)
        self.assertEqual(self.client.get(f'/api/v1/profiles/{identity}/').status_code, 404)
        self.assertEqual(self.post('plan/').status_code, 400)
        self.assertEqual(self.post('').status_code, 400)

    @override_settings(PROFILE_STORAGE_BYTES=1)
    def test_storage_limit_leaves_no_orphan_file(self):
        plan = self.post('plan/').json()['files']
        self.assertEqual(self.upload(self.first, plan[0]).status_code, 429)
        self.assertFalse(SharedModFile.objects.exists())
        self.assertFalse(list(self.storage.rglob('*.zip')))

    def test_missing_stored_file_is_not_reported_available_and_can_be_repaired(self):
        published = self.publish_all()
        blob = SharedModFile.objects.first()
        blob.archive.storage.delete(blob.archive.name)
        self.assertEqual(self.client.get('/api/v1/profiles/' + published['id'] + '/').status_code, 409)
        rows = self.post('plan/').json()['files']
        row = next(r for r in rows if r['sha256'] == blob.pk)
        self.assertEqual(row['status'], 'missing')
        data = self.first if row['file_name'] == 'mod_one.zip' else self.second
        self.assertEqual(self.upload(data, row).status_code, 201)
        self.assertEqual(self.post('').status_code, 200)

    def test_admin_management_and_untrusted_titles_are_escaped(self):
        self.payload['name'] = '<script>alert(1)</script>'
        published = self.publish_all()
        self.assertContains(self.client.get(published['page_path']), '&lt;script&gt;')
        self.assertEqual(self.client.post('/manage/profiles/', {'id': published['id'], 'action': 'block'}).status_code, 403)
        admin = User.objects.create_superuser('admin', password='test')
        admin_client = Client()
        admin_client.force_login(admin)
        self.assertEqual(admin_client.post('/manage/profiles/', {'id': published['id'], 'action': 'block'}).status_code, 302)
        self.assertTrue(SharedProfile.objects.get().blocked)

    def test_public_catalog_search_pagination_and_blocked_profiles(self):
        from app.core.profile_protocol import manifest_key
        for number in range(14):
            payload = copy.deepcopy(self.payload)
            payload['name'] = f'组合 {number:02}'
            payload['note'] = '新手 & 汉化' if number == 13 else '其他玩法'
            SharedProfile.objects.create(manifest=payload, fingerprint=manifest_key(payload), blocked=number == 0)
        response = self.client.get('/api/v1/profiles/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Cache-Control'], 'private, no-store')
        result = response.json()
        self.assertEqual((result['total'], result['page'], result['pages'], len(result['items'])), (13, 1, 2, 12))
        first = result['items'][0]
        self.assertEqual(first['name'], '组合 13')
        self.assertEqual(first['mod_count'], 2)
        self.assertEqual(first['total_size'], sum(item['size'] for item in self.payload['mods']))
        self.assertEqual(first['page_path'], f'/profiles/{first["id"]}/')
        self.assertNotIn('manifest', first)
        second = self.client.get('/api/v1/profiles/', {'page': 2}).json()
        self.assertEqual([item['name'] for item in second['items']], ['组合 01'])
        self.assertEqual(self.client.get('/api/v1/profiles/', {'q': '新手 & 汉化'}).json()['total'], 1)
        self.assertEqual(self.client.get('/api/v1/profiles/', {'q': '组合 00'}).json()['total'], 0)
        self.assertEqual(self.client.get('/api/v1/profiles/', {'page': 'bad'}).json()['page'], 1)
        self.assertEqual(self.client.get('/api/v1/profiles/', {'page': 999}).json()['page'], 2)
        self.assertEqual(self.client.get('/api/v1/profiles/', {'q': '无结果'}).json()['items'], [])


@skipUnless(importlib.util.find_spec('app.core.shared_profiles'), 'Desktop integration requires the desktop source checkout')
class DesktopProfileIntegrationTests(LiveServerTestCase):
    """Real urllib multipart upload/download against a temporary local hub."""
    def test_two_games_share_only_missing_and_apply_exact_files(self):
        from app.core.modmanager import ModManager
        from app.core import shared_profiles as desktop
        with tempfile.TemporaryDirectory() as temporary, override_settings(MEDIA_ROOT=Path(temporary) / 'media'):
            root = Path(temporary)
            sender, receiver = ModManager(root / 'sender'), ModManager(root / 'receiver')
            sender.data.mkdir(parents=True)
            receiver.data.mkdir(parents=True)
            a, b = zipped('alpha'), zipped('beta')
            (sender.data / 'mod_a.zip').write_bytes(a)
            (sender.data / 'mod_b.zip').write_bytes(b)
            sender.save_profile('兄弟组合')
            prepared = desktop.prepare_share(sender, '兄弟组合')
            self.assertEqual([r['status'] for r in desktop.negotiate(self.live_server_url, prepared)], ['missing', 'missing'])
            link = desktop.publish_share(self.live_server_url, prepared)
            with patch.object(desktop, '_upload', side_effect=AssertionError('must not reupload')):
                self.assertEqual(desktop.publish_share(self.live_server_url, prepared), link)
            identity = desktop.profile_identity(link, self.live_server_url)
            catalog = desktop.fetch_profiles(self.live_server_url, '兄弟')
            self.assertEqual(catalog['total'], 1)
            self.assertEqual(catalog['items'][0]['id'], identity)
            self.assertEqual(catalog['items'][0]['mod_count'], 2)
            received = desktop.fetch_profile(self.live_server_url, identity)
            receiver.disabled_dir.mkdir()
            (receiver.disabled_dir / 'mod_a.zip').write_bytes(a)
            (receiver.data / 'old.zip').write_bytes(zipped('old'))
            plan = desktop.preview_apply(receiver, received)
            self.assertEqual(plan['download'], ['mod_b.zip'])
            with patch('app.core.game.is_game_running', return_value=False):
                result = desktop.apply_shared(receiver, self.live_server_url, identity, received, expected=plan)
            self.assertEqual(result['downloaded'], 1)
            self.assertEqual((receiver.data / 'mod_a.zip').read_bytes(), a)
            self.assertEqual((receiver.data / 'mod_b.zip').read_bytes(), b)
            self.assertTrue((receiver.disabled_dir / 'old.zip').is_file())
            self.assertEqual(receiver.load_profiles()['兄弟组合']['enabled'], ['mod_a.zip', 'mod_b.zip'])

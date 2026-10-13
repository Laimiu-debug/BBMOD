"""Synthetic campaign bytes exercise uploads, moderation, bundles and real clients."""
import hashlib
import io
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, LiveServerTestCase, TestCase, override_settings

from .models import SharedModFile, SharedSave, SharedSaveFile
from .test_profiles import item, zipped


def campaign(label=b'fixture'):
    return b'\xbb\x00\x02\x41\x00\x00\x00' + label * 100


class SaveTests(TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        override = override_settings(MEDIA_ROOT=temporary.name)
        override.enable()
        self.addCleanup(override.disable)
        self.client = Client(enforce_csrf_checks=True)
        self.mod, self.save = zipped('fixture'), campaign()
        self.payload = {'schema_version': 1, 'name': '战团存档', 'note': '第 100 天', 'game_version': '1.5.2.3',
            'mods': [item(self.mod)], 'dlcs': ['Lindwurm'],
            'save': {'file_name': 'campaign.sav', 'sha256': hashlib.sha256(self.save).hexdigest(), 'size': len(self.save)}}

    def post(self, path='', payload=None, **headers):
        return self.client.post('/api/v1/saves/' + path, self.payload if payload is None else payload,
            content_type='application/json', HTTP_X_BBMOD_SAVE_SHARE='1', **headers)

    def upload(self, plan):
        sha = self.payload['save']['sha256']
        return self.client.post('/api/v1/saves/files/' + sha + '/',
            {'ticket': plan['save'].get('ticket', ''), 'save': SimpleUploadedFile('campaign.sav', self.save)},
            HTTP_X_BBMOD_SAVE_SHARE='1')

    def publish_all(self):
        plan = self.post('plan/').json()
        self.assertEqual(self.upload(plan).status_code, 201)
        if plan['files']:
            row = plan['files'][0]
            response = self.client.post('/api/v1/profiles/files/' + row['sha256'] + '/',
                {'ticket': row['ticket'], 'archive': SimpleUploadedFile('mod.zip', self.mod)}, HTTP_X_BBMOD_PROFILE_SHARE='1')
            self.assertEqual(response.status_code, 201)
        response = self.post()
        self.assertEqual(response.status_code, 201, response.content)
        return response.json()

    def test_share_is_not_public_until_save_and_all_mods_exist(self):
        plan = self.post('plan/').json()
        self.assertEqual(self.post().status_code, 400)
        self.assertEqual(self.upload(plan).status_code, 201)
        self.assertEqual(self.post().status_code, 400)
        self.assertEqual(SharedSave.objects.count(), 0)

    def test_reuse_and_bundle_contain_exact_save_and_mod_bytes(self):
        record = self.publish_all()
        self.assertEqual(self.post().status_code, 200)
        plan = self.post('plan/').json()
        self.assertEqual(plan['save']['status'], 'available')
        self.assertEqual(plan['files'][0]['status'], 'available')
        self.assertEqual(SharedSaveFile.objects.count(), 1)
        self.assertEqual(SharedModFile.objects.count(), 1)
        response = self.client.get(record['page_path'] + 'bundle/')
        with zipfile.ZipFile(io.BytesIO(b''.join(response.streaming_content))) as archive:
            self.assertEqual(archive.read('savegames/campaign.sav'), self.save)
            self.assertEqual(archive.read('data/mod_one.zip'), self.mod)
            self.assertIn('BBMOD_SAVE.json', archive.namelist())
        self.assertContains(self.client.get('/saves/'), '战团存档')
        self.assertContains(self.client.get(record['page_path']), 'bbmod://saves/' + record['id'])
        self.assertEqual(self.client.get('/api/v1/saves/?q=100').json()['total'], 1)

    def test_vanilla_campaign_can_share_without_any_mods(self):
        self.payload['mods'] = []
        record = self.publish_all()
        self.assertEqual(self.client.get('/api/v1/saves/').json()['items'][0]['mod_count'], 0)
        self.assertEqual(self.client.get('/api/v1/saves/' + record['id'] + '/').status_code, 200)

    def test_native_headers_tickets_hash_and_campaign_header_are_required(self):
        self.assertEqual(self.client.post('/api/v1/saves/plan/', self.payload, content_type='application/json').status_code, 400)
        self.assertEqual(self.post('plan/', HTTP_ORIGIN='https://bad.example').status_code, 400)
        plan = self.post('plan/').json()
        plan['save']['ticket'] = 'bad'
        self.assertEqual(self.upload(plan).status_code, 400)
        for bad in (b'\xbb\x00\x02' + b'\0' * 700, b'MZ' + b'x' * 700, b'PK' + b'x' * 700):
            self.save = bad
            self.payload['save'].update(size=len(bad), sha256=hashlib.sha256(bad).hexdigest())
            self.assertEqual(self.upload(self.post('plan/').json()).status_code, 400)
        self.assertEqual(SharedSaveFile.objects.count(), 0)

    def test_delisting_mod_or_save_closes_all_download_and_restore_entries(self):
        record = self.publish_all()
        SharedModFile.objects.update(blocked=True)
        prefix = '/api/v1/saves/' + record['id'] + '/'
        self.assertEqual(self.client.get(prefix).status_code, 409)
        self.assertEqual(self.client.get(prefix + 'files/' + self.payload['save']['sha256'] + '/').status_code, 404)
        self.assertEqual(self.client.get(record['page_path'] + 'bundle/').status_code, 404)
        self.assertNotContains(self.client.get(record['page_path']), 'bbmod://saves/' + record['id'])
        self.assertEqual(self.post().status_code, 400)
        SharedModFile.objects.update(blocked=False)
        SharedSaveFile.objects.update(blocked=True)
        self.assertEqual(self.client.get(prefix).status_code, 409)
        self.assertEqual(self.post('plan/').json()['save']['status'], 'blocked')

    @override_settings(SAVE_STORAGE_BYTES=1)
    def test_quota_failure_keeps_file_private_and_does_not_leave_blob(self):
        response = self.upload(self.post('plan/').json())
        self.assertEqual(response.status_code, 429)
        self.assertEqual(SharedSaveFile.objects.count(), 0)

    def test_management_requires_admin_and_csrf_and_blocks_duplicates(self):
        record = self.publish_all()
        self.assertEqual(self.client.post('/manage/saves/', {'id': record['id'], 'action': 'block'}).status_code, 403)
        admin = User.objects.create_superuser('saveadmin', '', 'fixture-password')
        client = Client()
        client.force_login(admin)
        self.assertEqual(client.post('/manage/saves/', {'id': record['id'], 'action': 'block'}).status_code, 302)
        self.assertEqual(self.post().status_code, 400)
        self.assertEqual(self.client.get(record['page_path']).status_code, 404)
        self.assertEqual(self.client.get('/api/v1/saves/').json()['total'], 0)


class DesktopSaveIntegrationTests(LiveServerTestCase):
    def test_share_and_restore_two_games_with_pinned_mods_and_preserved_save(self):
        from app.core.modmanager import ModManager
        from app.core import shared_saves as desktop
        with tempfile.TemporaryDirectory() as temporary, override_settings(MEDIA_ROOT=Path(temporary) / 'media'), \
                patch('app.core.game.is_game_running', return_value=False):
            root = Path(temporary)
            sender, receiver = ModManager(root/'sender'), ModManager(root/'receiver')
            sender.data.mkdir(parents=True)
            receiver.data.mkdir(parents=True)
            a, b = zipped('a'), zipped('b')
            (sender.data/'mod_a.zip').write_bytes(a)
            (sender.data/'mod_b.zip').write_bytes(b)
            save = root/'source.sav'
            save.write_bytes(campaign())
            prepared = desktop.prepare_share(sender, save, '远征战团', game_version='1.5.2.3')
            link = desktop.publish_share(self.live_server_url, prepared)
            with patch.object(desktop.profiles, '_upload', side_effect=AssertionError('No duplicate MOD upload')), \
                    patch.object(desktop, '_upload_save', side_effect=AssertionError('No duplicate save upload')):
                self.assertEqual(desktop.publish_share(self.live_server_url, prepared), link)
            identity = desktop.save_identity(link, self.live_server_url)
            self.assertEqual(desktop.fetch_saves(self.live_server_url)['total'], 1)
            manifest = desktop.fetch_save(self.live_server_url, identity)
            receiver.disabled_dir.mkdir()
            (receiver.disabled_dir/'mod_a.zip').write_bytes(a)
            old = receiver.data/'old.zip'
            old.write_bytes(zipped('old'))
            directory = root/'documents/savegames'
            directory.mkdir(parents=True)
            existing = directory/'existing.sav'
            existing.write_bytes(campaign(b'previous'))
            before = existing.read_bytes()
            plan = desktop.preview_restore(receiver, manifest, directory, '1.5.2.3')
            self.assertEqual(plan['mods']['download'], ['mod_b.zip'])
            result = desktop.restore(receiver, self.live_server_url, identity, manifest, expected=plan, game_version='1.5.2.3')
            self.assertEqual(Path(result['save_path']).read_bytes(), save.read_bytes())
            self.assertEqual(existing.read_bytes(), before)
            self.assertEqual((receiver.data/'mod_a.zip').read_bytes(), a)
            self.assertEqual((receiver.data/'mod_b.zip').read_bytes(), b)
            self.assertTrue((receiver.disabled_dir/'old.zip').exists())
            self.assertFalse(receiver.transaction.journal.exists())

    def test_vanilla_restore_disables_mods_and_preserves_source_save(self):
        from app.core.modmanager import ModManager
        from app.core import shared_saves as desktop
        with tempfile.TemporaryDirectory() as temporary, override_settings(MEDIA_ROOT=Path(temporary)/'media'), \
                patch('app.core.game.is_game_running', return_value=False):
            root = Path(temporary)
            manager = ModManager(root/'game')
            manager.data.mkdir(parents=True)
            save = root/'source.sav'
            save.write_bytes(campaign())
            prepared = desktop.prepare_share(manager, save, '原版战团', game_version='1.5.2.3')
            link = desktop.publish_share(self.live_server_url, prepared)
            (manager.data/'extra.zip').write_bytes(zipped('extra'))
            identity = desktop.save_identity(link, self.live_server_url)
            manifest = desktop.fetch_save(self.live_server_url, identity)
            plan = desktop.preview_restore(manager, manifest, root/'savegames', '1.5.2.3')
            result = desktop.restore(manager, self.live_server_url, identity, manifest, expected=plan, game_version='1.5.2.3')
            self.assertTrue(Path(result['save_path']).is_file())
            self.assertFalse((manager.data/'extra.zip').exists())
            self.assertTrue(save.is_file())

from contextlib import nullcontext
import gzip
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

from django.conf import settings
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from app.core.worldmap.model import WorldMap
from app.core.worldmap.routes import RoutePlanner
from . import worldmaps
from .models import SeedUploadBudget


def reference_world():
    fixtures = settings.BASE_DIR.parent/'app/tests/fixtures/worldmap'
    raw = next(json.loads(gzip.decompress(p.read_bytes()))['map'] for p in fixtures.glob('map-*.json.gz')
               if json.loads(gzip.decompress(p.read_bytes()))['map']['seed'] == '46U2HMOORH')
    raw['campaign'] = next(json.loads(gzip.decompress(p.read_bytes()))['campaign'] for p in fixtures.glob('camp-*.json.gz')
               if json.loads(gzip.decompress(p.read_bytes()))['campaign']['seed'] == raw['seed'])
    return WorldMap.from_dict(raw)


@override_settings(WORLDMAP_ASYNC=False)
class AtlasTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.world = reference_world()

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='bbmod-atlas-test-')
        self.addCleanup(self.temporary.cleanup)
        self.override = override_settings(DATA_DIR=Path(self.temporary.name))
        self.override.enable(); self.addCleanup(self.override.disable)
        self.calls = []
        def solve(seed, **kwargs):
            self.calls.append(seed)
            raw = self.world.to_dict(); raw['seed'] = raw['campaign']['seed'] = seed
            return SimpleNamespace(world=WorldMap.from_dict(raw), elapsed=2.8)
        service = SimpleNamespace(components=SimpleNamespace(fingerprint=lambda:'test-native-fingerprint'), solve=solve)
        self.service = service
        self.mock = patch.object(worldmaps, 'solver', return_value=service)
        self.mock.start(); self.addCleanup(self.mock.stop)

    def test_real_page_entry_seed_and_csrf(self):
        response = self.client.get(reverse('seed_atlas'), {'seed':'AbCdEfGhIj'})
        self.assertContains(response, 'seed-atlas.js')
        self.assertContains(response, 'AbCdEfGhIj')
        self.assertContains(response, '农民民兵')
        self.assertIn('bbmod_csrftoken', response.cookies)
        self.assertContains(self.client.get('/seeds/'), '/seeds/map/')

    def test_map_matches_fixture_and_reuses_chinese_labels_scores_and_cache(self):
        url = '/api/v1/worldmaps/46U2HMOORH/'
        data = self.client.get(url).json()
        self.assertEqual((len(data['towns']),len(data['camps']),len(data['loot'])), (19,102,10))
        self.assertEqual(data['rows'][33][19], list(self.world.rows[33][19]))
        self.assertTrue(all(t['name']!='未收录地名' for t in data['towns']))
        self.assertTrue(all(i['score'] is not None and i['quality'] is not None for i in data['loot'] if i['kind']=='weapon'))
        self.assertTrue(all(o['profit'] == o['sell']-o['buy'] > 0 for o in data['offers']))
        self.assertIn('在此买入', data['towns'][0]['advice'])
        self.assertEqual(self.client.get(url).json(), data)
        self.assertEqual(self.calls, ['46U2HMOORH'])
        self.assertEqual(SeedUploadBudget.objects.count(), 2)

    def test_seed_case_is_distinct(self):
        for seed in ('AbCdEfGhIj', 'ABCDEFGHIJ'):
            self.assertEqual(self.client.get(f'/api/v1/worldmaps/{seed}/').json()['seed'], seed)
        self.assertEqual(len(self.calls),2)
        self.assertEqual(len(list((Path(self.temporary.name)/'worldmap-cache/display').glob('*.gz'))),2)

    def test_invalid_seed_does_not_compute_or_charge(self):
        for seed in ('bad','<script>','abcdefghijk'):
            self.assertEqual(self.client.get(f'/api/v1/worldmaps/{seed}/').status_code,400)
        self.assertEqual(self.calls,[])
        self.assertEqual(SeedUploadBudget.objects.count(),0)

    def test_busy_returns_retry_without_charging(self):
        with patch.object(worldmaps,'compute_slot',return_value=nullcontext(False)):
            response = self.client.get('/api/v1/worldmaps/46U2HMOORH/')
        self.assertEqual(response.status_code,202)
        self.assertEqual(response['Retry-After'],'3')
        self.assertEqual(self.calls,[])
        self.assertEqual(SeedUploadBudget.objects.count(),0)

    def test_corrupted_display_is_reconstructed(self):
        self.client.get('/api/v1/worldmaps/46U2HMOORH/')
        path=next((Path(self.temporary.name)/'worldmap-cache/display').glob('*.gz'))
        path.write_bytes(b'broken')
        self.assertEqual(self.client.get('/api/v1/worldmaps/46U2HMOORH/').status_code,200)
        self.assertEqual(len(self.calls),2)

    def test_route_uses_same_terrain_planner(self):
        self.client.get('/api/v1/worldmaps/46U2HMOORH/')
        result=self.client.post('/api/v1/worldmaps/46U2HMOORH/route/',data=json.dumps({'stops':[0,1,2]}),content_type='application/json')
        self.assertEqual(result.status_code,200)
        expected=RoutePlanner(self.world).plan([0,1,2])
        self.assertAlmostEqual(result.json()['hours'],expected.hours)
        self.assertEqual(result.json()['tiles'],[list(xy) for xy in expected.tiles])

    def test_route_rejects_invalid_body_and_requires_map(self):
        url='/api/v1/worldmaps/46U2HMOORH/route/'
        self.assertEqual(self.client.post(url,data='{"stops":[0,1]}',content_type='application/json').status_code,409)
        for body in ({'stops':[True,1]}, {'stops':[40,1]}, {'stops':[0]*13}, {'stops':[0,1],'road_only':'yes'}, []):
            self.assertEqual(self.client.post(url,data=json.dumps(body),content_type='application/json').status_code,400)
        self.assertEqual(self.calls,[])

    def test_route_requires_csrf_token(self):
        client=Client(enforce_csrf_checks=True)
        self.assertEqual(client.post('/api/v1/worldmaps/46U2HMOORH/route/',data='{"stops":[0,1]}',content_type='application/json').status_code,403)

    def test_solver_failure_returns_safe_message(self):
        self.service.solve=lambda *a,**k:(_ for _ in ()).throw(RuntimeError('private/path'))
        with self.assertLogs('catalog.worldmaps',level='ERROR'):
            response=self.client.get('/api/v1/worldmaps/46U2HMOORH/')
        self.assertEqual(response.status_code,503)
        self.assertNotContains(response,'private/path',status_code=503)

    def test_quota_stops_uncached_work_and_rolls_back_counters(self):
        request=SimpleNamespace(META={'REMOTE_ADDR':'test-address'})
        for _ in range(20):worldmaps.quota(request,'solve')
        before=list(SeedUploadBudget.objects.values_list('key','count'))
        with self.assertRaises(ValueError):worldmaps.quota(request,'solve')
        self.assertEqual(list(SeedUploadBudget.objects.values_list('key','count')),before)

    def test_native_compute_slot_is_exclusive_and_released(self):
        with worldmaps.compute_slot() as first:
            self.assertTrue(first)
            with worldmaps.compute_slot() as second:self.assertFalse(second)
        with worldmaps.compute_slot() as third:self.assertTrue(third)

    @override_settings(WORLDMAP_ASYNC=True)
    def test_background_job_returns_promptly_then_reuses_completed_result(self):
        jobs=[]
        class Deferred:
            def __init__(self, target, args, daemon):jobs.append((target,args))
            def start(self):pass
        with patch.object(worldmaps.threading,'Thread',Deferred):
            first=self.client.get('/api/v1/worldmaps/46U2HMOORH/')
            self.assertEqual(first.status_code,202)
            self.assertEqual(self.calls,[])
            self.assertEqual(self.client.get('/api/v1/worldmaps/ABCDEFGHIJ/').status_code,202)
            self.assertEqual(len(jobs),1)
            jobs[0][0](*jobs[0][1])
        self.assertEqual(self.client.get('/api/v1/worldmaps/46U2HMOORH/').status_code,200)
        self.assertEqual(self.calls,['46U2HMOORH'])
        self.assertEqual(list(SeedUploadBudget.objects.values_list('count',flat=True)),[1,1])

    def test_route_cache_is_keyed_by_stops_and_road_policy(self):
        self.client.get('/api/v1/worldmaps/46U2HMOORH/')
        url='/api/v1/worldmaps/46U2HMOORH/route/'
        one=self.client.post(url,data='{"stops":[0,1]}',content_type='application/json')
        self.assertEqual(one.status_code,200)
        count=len(self.calls)
        self.assertEqual(self.client.post(url,data='{"stops":[0,1]}',content_type='application/json').json(),one.json())
        self.assertEqual(len(self.calls),count)
        self.assertEqual(self.client.post(url,data='{"stops":[1,0]}',content_type='application/json').json()['stops'],[1,0])

    def test_failed_computation_has_cooldown_and_releases_slot(self):
        self.service.solve=lambda *a,**k:(_ for _ in ()).throw(TimeoutError('internal path'))
        with self.assertLogs('catalog.worldmaps',level='ERROR'):
            first=self.client.get('/api/v1/worldmaps/46U2HMOORH/')
        self.assertEqual(first.status_code,504)
        self.assertEqual(self.client.get('/api/v1/worldmaps/46U2HMOORH/').status_code,504)
        with worldmaps.compute_slot() as acquired:self.assertTrue(acquired)

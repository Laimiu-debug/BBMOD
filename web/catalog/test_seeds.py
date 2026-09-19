from copy import deepcopy
from dataclasses import asdict
from unittest.mock import patch
from django.contrib.auth.models import User
from django.test import Client, TestCase
from app.core.seedgen.log_watcher import SeedResult
from .models import SharedSeed, SeedUploadBudget


def payload(code='AbCdEfGhIj'):
    return {'schema_version': 1, 'note': '北港开局', 'record': asdict(SeedResult(code, 123,
        origin='scenario.militia', game_version='1.5.2.3', combat_difficulty=2,
        economic_difficulty=1, budget_difficulty=0, done=True, lines=[
        'CharInfo: 0 Melee:0.9 MeleeSkill:60(95)3 MeleeDefense:5(20)1', 'Trait: trait.strong',
        'CharInfo: 1 Guard:0.9 MeleeSkill:50(80)1 MeleeDefense:10(40)3', 'Trait: trait.fearless',
        'SettlementInfo: Port:7', 'NamedInfo: Sum:12(2)']))}


class SeedSharingTests(TestCase):
    def publish(self, value=None, **kwargs):
        return self.client.post('/api/v1/seeds/', value or payload(), content_type='application/json',
            HTTP_X_BBMOD_SEED_SHARE='1', **kwargs)

    def test_anonymous_roundtrip_duplicate_is_idempotent_and_keeps_original_note(self):
        self.client = Client(enforce_csrf_checks=True)
        response = self.publish()
        self.assertEqual(response.status_code, 201)
        page = response.json()['page_path']
        self.assertContains(self.client.get(page), '近战命中 60→95（3星）')
        self.assertContains(self.client.get('/seeds/'), 'AbCdEfGhIj')
        retry = payload()
        retry['record']['loop_idx'] = 99999
        retry['note'] = '不应覆盖'
        self.assertEqual(self.publish(retry).status_code, 200)
        self.assertEqual(SharedSeed.objects.count(), 1)
        self.assertEqual(SharedSeed.objects.get().note, '北港开局')
        self.assertEqual(self.publish(payload('aBcDeFgHiJ')).status_code, 201)

    def test_filters_require_same_brother_and_distinguish_unknown_from_zero(self):
        self.publish()
        for query in ({'melee': 90}, {'defense': 30}, {'ports': 7, 'named': 12, 'combat': 2}):
            self.assertContains(self.client.get('/seeds/', query), 'AbCdEfGhIj')
        for query in ({'melee': 90, 'defense': 30}, {'melee': 90, 'trait': 'trait.fearless'},
                      {'melee': 90, 'people': 2}, {'ports': 8}, {'combat': 1},
                      {'melee': 90, 'exclude': 'trait.strong'}):
            self.assertNotContains(self.client.get('/seeds/', query), 'AbCdEfGhIj')
        unknown = payload('UNKNOWNabc')
        unknown['record']['seed'] = 'UNKNOWNabc'
        unknown['record']['lines'] = ['CharInfo: 0 Melee:1 MeleeSkill:50(80)1']
        self.assertEqual(self.publish(unknown).status_code, 201)
        self.assertNotContains(self.client.get('/seeds/', {'ports': 0}), 'UNKNOWNabc')

    def test_validation_does_not_create_records_or_expose_paths(self):
        for transform in (lambda p: p['record'].update(done=False),
            lambda p: p['record'].update(origin='unknown'), lambda p: p['record'].update(seed='../bad'),
            lambda p: p['record'].update(lines=['local file: C:/private/log.html']),
            lambda p: p['record'].update(lines=['SettlementInfo: Port:' + '9' * 100]),
            lambda p: p['record'].update(combat_difficulty=True), lambda p: p.update(extra='private')):
            value = payload(); transform(value)
            self.assertEqual(self.publish(value).status_code, 400)
        self.assertEqual(SharedSeed.objects.count(), 0)
        self.assertEqual(self.client.post('/api/v1/seeds/', payload(), content_type='application/json').status_code, 403)
        self.assertEqual(self.publish(HTTP_ORIGIN='https://evil.invalid').status_code, 403)
        huge = payload(); huge['note'] = 'x' * 70000
        self.assertEqual(self.publish(huge).status_code, 413)

    def test_xss_escape_empty_state_and_invalid_filters(self):
        self.assertContains(self.client.get('/seeds/'), '等你第一份发现')
        value = payload(); value['note'] = '<script>alert(1)</script>'
        page = self.publish(value).json()['page_path']
        self.assertContains(self.client.get(page), '&lt;script&gt;')
        self.assertNotContains(self.client.get(page), '<script>alert')
        self.assertContains(self.client.get('/seeds/', {'melee': '-1'}), 'errorlist')

    def test_moderation_requires_admin_and_blocked_seed_cannot_be_republished(self):
        page = self.publish().json()['page_path']
        seed = SharedSeed.objects.get()
        self.assertEqual(self.client.post('/manage/seeds/', {'id': seed.pk, 'action': 'block'}).status_code, 302)
        seed.refresh_from_db(); self.assertFalse(seed.blocked)
        user = User.objects.create_superuser('seed-admin', password='safe-test-password')
        self.client.force_login(user)
        self.assertEqual(self.client.post('/manage/seeds/', {'id': seed.pk, 'action': 'block'}).status_code, 302)
        self.assertEqual(self.client.get(page).status_code, 404)
        self.assertEqual(self.publish().status_code, 409)
        self.assertNotContains(self.client.get('/seeds/'), 'AbCdEfGhIj')
        self.client.post('/manage/seeds/', {'id': seed.pk, 'action': 'restore'})
        self.assertEqual(self.client.get(page).status_code, 200)

    def test_rate_limit_persists_and_duplicates_are_retryable(self):
        self.publish()
        SeedUploadBudget.objects.update(count=2000)
        self.assertEqual(self.publish(payload('ABCDEFGHIJ')).status_code, 429)
        self.assertEqual(self.publish().status_code, 200)
        self.assertEqual(SharedSeed.objects.count(), 1)


class SeedPaginationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Direct fixtures avoid testing publication quotas in pagination tests.
        for index in range(23):
            code = 'SEED' + f'{index:06d}'
            record = payload(code)['record']
            SharedSeed.objects.create(fingerprint=str(index), seed=code, origin=record['origin'],
                game_version=record['game_version'], record=record, note='北港 & 远征',
                ports=7, named=index, combat_difficulty=2, economic_difficulty=1, budget_difficulty=0)
        record = payload('BLOCKEDabc')['record']
        SharedSeed.objects.create(fingerprint='blocked', seed='BLOCKEDabc', origin=record['origin'],
            record=record, blocked=True)

    def test_six_per_page_no_duplicates_and_numeric_navigation(self):
        seen = []
        for number, count in ((1, 6), (2, 6), (3, 6), (4, 5)):
            response = self.client.get('/seeds/', {'page': number})
            page = response.context['page']
            self.assertEqual(page.paginator.count, 23)
            self.assertEqual(len(page), count)
            self.assertContains(response, 'aria-current="page" aria-label="第 ' + str(number) + ' 页"', count=2)
            self.assertNotContains(response, 'BLOCKEDabc')
            seen.extend(seed.seed for seed in page)
        self.assertEqual(len(set(seen)), 23)
        self.assertEqual(seen, [seed.seed for seed in SharedSeed.objects.filter(blocked=False)])

    def test_filters_page_size_sort_and_url_preserved(self):
        query = {'q': '北港 &', 'ports': '7', 'sort': 'named', 'origin': 'scenario.militia', 'per_page': '12', 'page': '2'}
        response = self.client.get('/seeds/', query)
        self.assertEqual(len(response.context['page']), 11)
        self.assertEqual(response.context['page'][0].named, 10)
        self.assertIn('q=%E5%8C%97%E6%B8%AF+%26', response.context['params'])
        self.assertIn('per_page=12', response.context['params'])
        self.assertNotIn('&page=', response.context['params'])
        self.assertContains(response, '第 13–23 条 / 共 23 条')
        self.assertEqual(len(self.client.get('/seeds/', {'per_page': 24}).context['page']), 23)

    def test_invalid_pages_and_sizes_are_bounded(self):
        for value in ('0', '-3', '10000000', 'abc'):
            self.assertEqual(len(self.client.get('/seeds/', {'per_page': value}).context['page']), 6)
        self.assertEqual(self.client.get('/seeds/', {'page': 'bad'}).context['page'].number, 1)
        self.assertEqual(self.client.get('/seeds/', {'page': 999}).context['page'].number, 4)
        response = self.client.get('/seeds/', {'q': 'nothing matches'})
        self.assertEqual(response.context['page'].paginator.count, 0)
        self.assertContains(response, '第 0–0 条 / 共 0 条')

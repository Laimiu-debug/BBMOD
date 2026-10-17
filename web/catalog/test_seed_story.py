from copy import deepcopy
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

from app.core.seedgen.config_emitter import ATTRIBUTES
from app.core.seedgen.log_watcher import SeedResult
from .cover_art import ART, mod_artwork
from .seed_story import seed_story


def character_result(kind='lu-bu', code='HeroSeedAb'):
    projected = {'Hitpoints':105, 'Bravery':65, 'Stamina':125, 'MeleeSkill':100,
                 'RangedSkill':60, 'MeleeDefense':40, 'RangedDefense':10, 'Initiative':120}
    if kind in ('guan-yu','zhang-fei'):
        projected.update(Hitpoints=105 if kind=='zhang-fei' else 95, Bravery=55,
                         Stamina=115, MeleeSkill=95, MeleeDefense=35)
    elif kind == 'huang-zhong':
        projected.update(Hitpoints=85, Bravery=50, Stamina=110, MeleeSkill=60,
                         MeleeDefense=5, RangedSkill=95)
    elif kind == 'hebei':
        projected.update(Hitpoints=85, Bravery=45, Stamina=105, MeleeSkill=90, MeleeDefense=25)
    elif kind == 'weak-nine':
        projected.update(Hitpoints=70, Bravery=40, Stamina=90, MeleeSkill=75, MeleeDefense=10)
    stars = {'MeleeSkill':3,'MeleeDefense':3,'Stamina':3}
    line = 'CharInfo: 0 Melee:0.9 ' + ' '.join(
        f'{key}:50({value}){stars.get(key,0)}' for key,value in projected.items())
    return SeedResult(code,1,origin='scenario.militia',game_version='1.5.2.3',done=True,lines=[line])


class SeedStoryTests(SimpleTestCase):
    def test_hero_motifs_follow_distinct_qualified_brothers(self):
        for key in ('lu-bu','guan-yu','zhang-fei','huang-zhong'):
            with self.subTest(key=key):
                story=seed_story(character_result(key))
                self.assertEqual(story['cover']['key'],key)
                self.assertTrue(story['featured']['evidence'])
                self.assertIn('11级潜力',story['intro'])

    def test_hebei_variant_is_stable_and_does_not_promote_to_top_tier(self):
        story=seed_story(character_result('hebei'))
        self.assertIn(story['cover']['key'],('yan-liang','wen-chou'))
        self.assertEqual(story['featured']['rank'],2)
        self.assertEqual(story['cover'],seed_story(character_result('hebei'))['cover'])

    def test_nine_stars_do_not_invent_a_top_warrior(self):
        story=seed_story(character_result('weak-nine'))
        self.assertFalse(story['has_hero'])
        self.assertEqual(story['cover']['key'],'mercenary-camp')
        self.assertIn('九星',story['headline'])
        self.assertEqual(story['brothers'][0]['stars'],9)

    def test_partial_stats_do_not_receive_an_invented_hero(self):
        result=SeedResult('PartialABC',1,lines=['CharInfo: 0 Melee:1 MeleeSkill:80(115)3'])
        story=seed_story(result)
        self.assertFalse(story['has_hero'])
        self.assertIsNone(story['brothers'][0]['stars'])
        self.assertEqual(story['brothers'][0]['rating'],'资料不足，暂不分档')

    def test_map_and_loot_covers_use_recorded_counts(self):
        for lines,key in ((['SettlementInfo: Port:7'],'trade-port'),
                          (['NamedInfo: Sum:12(2)'],'named-loot')):
            story=seed_story(SeedResult('WorldABCde',1,lines=lines))
            self.assertEqual(story['cover']['key'],key)
            self.assertFalse(story['has_hero'])
        zero=seed_story(SeedResult('ZeroABCdef',1,lines=['SettlementInfo: Port:0','NamedInfo: Sum:0(0)']))
        self.assertIn('记录有0座港口',zero['facts'])
        missing=seed_story(SeedResult('EmptyABCde',1))
        self.assertFalse(any('0座' in fact or '0件' in fact for fact in missing['facts']))

    def test_generating_story_keeps_original_record_untouched(self):
        result=character_result()
        before=deepcopy(result)
        seed_story(result)
        self.assertEqual(result,before)

    def test_every_theme_asset_is_present_and_has_alt_text(self):
        for key,(_,alt) in ART.items():
            self.assertTrue((Path(settings.BASE_DIR)/f'static/covers/v1/{key}.webp').is_file(),key)
            self.assertTrue(alt)


class ModCoverTests(SimpleTestCase):
    def test_uploaded_cover_has_priority_even_for_named_hero(self):
        cover=mod_artwork({'title':'吕布装备包'},'/mods/author-cover/')
        self.assertEqual(cover['url'],'/mods/author-cover/')
        self.assertEqual(cover['source'],'author')

    def test_hero_mod_titles_receive_matching_art(self):
        for title,key in (('吕布','lu-bu'),('张飞','zhang-fei'),('关二爷','guan-yu'),
                          ('黄忠','huang-zhong'),('颜良','yan-liang'),('文丑','wen-chou')):
            self.assertEqual(mod_artwork({'title':title+'外观包'})['key'],key)

    def test_mod_fallbacks_follow_content_and_category(self):
        for metadata,key in (({'title':'港口贸易调整'},'trade-port'),
                             ({'title':'红装掉落'},'named-loot'),
                             ({'category':'装备与外观'},'armoury'),
                             ({'category':'汉化'},'chronicle'),
                             ({'category':'起源与事件'},'mercenary-camp')):
            self.assertEqual(mod_artwork(metadata)['key'],key)

    def test_world_map_utilities_do_not_imply_trade_or_ports(self):
        self.assertEqual(mod_artwork({'title':'世界地图自动暂停','category':'基础功能'})['key'], 'chronicle')

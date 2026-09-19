import gzip
import hashlib
import json
from pathlib import Path
import tempfile

from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, SimpleTestCase, override_settings
from bs4 import BeautifulSoup

from catalog.wiki_render import render_article
from catalog.wiki_store import page_url, open_store
from tools.build_wiki import build


class WikiRenderingTests(SimpleTestCase):
    def render_source(self,text):
        parsed={'title':'Test','text':text,'sections':[{'line':'Stats','anchor':'Stats','level':'2'}]}
        terms={'greatsword':('Greatsword','巨剑')}
        available={'greatsword':'Greatsword','category:weapons':'Category:Weapons'}
        assets={'sword.png':{'local_name':'a'*64+'.png'}}
        styles={}
        return render_article(parsed,terms,available,assets,styles),styles

    def test_active_html_external_images_and_css_are_removed(self):
        result,styles=self.render_source('''<script>alert(1)</script><iframe src="javascript:alert(2)"></iframe>
          <img src="https://tracker.invalid/x" onerror="alert(3)"><a href="javascript:alert(4)">bad</a>
          <div style="position:fixed;background:url(https://tracker.invalid/x);color:red" onclick="alert(5)">safe</div>
          <svg><foreignObject><script>bad()</script></foreignObject></svg>''')
        for forbidden in ('<script','<iframe','<svg','onerror','onclick','javascript:','tracker.invalid','position:fixed','url('):
            self.assertNotIn(forbidden,result['html']+' '.join(styles.values()))
        self.assertIn('safe',result['html']);self.assertIn('color:red',' '.join(styles.values()))

    def test_links_anchors_images_and_reviewed_names(self):
        result,_=self.render_source('''<h2 id="Stats">Stats</h2><a href="#Stats">section</a>
          <a href="/wiki/Greatsword#Damage">Greatsword</a><a href="/wiki/Category:Weapons">Weapons</a>
          <img data-image-name="Sword.png" src="https://foreign.invalid/image.png" width="40" height="40">''')
        soup=BeautifulSoup(result['html'],'html.parser')
        self.assertIsNotNone(soup.find(id='w-Stats'))
        self.assertIsNotNone(soup.find('a',href='/wiki/read/Greatsword/#w-Damage'))
        self.assertIsNotNone(soup.find('a',href='#w-Stats'))
        self.assertIn('巨剑',result['html'])
        self.assertEqual(soup.img['src'],'/wiki/media/'+'a'*64+'.png')
        self.assertEqual(result['missing_links'],[])

    def test_math_and_merged_tables_remain_readable(self):
        result,_=self.render_source('''<span class="mwe-math-element"><span style="display:none"><math><mfrac><mn>1</mn><mn>2</mn></mfrac></math></span><img src="https://external/math.svg"></span>
          <table><tr><th colspan="2">Damage</th></tr><tr><td>10</td><td>20</td></tr></table>''')
        self.assertIsNotNone(BeautifulSoup(result['html'],'html.parser').find('mfrac'))
        self.assertIn('<math',result['html'])
        self.assertIn('colspan="2"',result['html']);self.assertIn('w-table-scroll',result['html'])
        self.assertNotIn('display:none',result['html']);self.assertNotIn('external',result['html'])

    def test_dark_source_tables_are_adapted_and_names_remain_distinct(self):
        result,styles=self.render_source('<td style="background-color:#141414;color:white">Greatsword</td>')
        self.assertNotIn('background-color:#141414',' '.join(styles.values()))
        self.assertNotIn('color:white',' '.join(styles.values()))
        self.assertIn('巨剑',result['html'])

    def test_video_references_are_links_instead_of_missing_illustrations(self):
        result=render_article({'title':'Preview','text':'<img data-image-name="Trailer" src="https://external/video">'},
            {},{},{'Trailer':{'mime':'video/youtube','description_url':'https://battlebrothers.fandom.com/wiki/File:Trailer'}},{})
        self.assertEqual(result['missing_images'],[])
        self.assertEqual(result['external_media'],['Trailer'])
        self.assertIn('查看视频：Trailer',result['html'])
        self.assertNotIn('<img',result['html'])


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class WikiIntegrationTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.temp=tempfile.TemporaryDirectory();cls.root=Path(cls.temp.name)
        source=cls.root/'source';(source/'pages').mkdir(parents=True)
        rows=[{'pageid':1,'title':'Greatsword','ns':0,'lastrevid':100},
              {'pageid':2,'title':'Old Sword','ns':0,'lastrevid':101},
              {'pageid':3,'title':'Events','ns':0,'lastrevid':102},
              {'pageid':4,'title':'Template:Test','ns':10,'lastrevid':103}]
        (source/'inventory.json').write_text(json.dumps({'pages':rows,'retrieved_at':'2026-09-18T00:00:00Z',
            'statistics':{'articles':2},'rights':{'text':'CC-BY-SA'}}),encoding='utf-8')
        for row in rows:
            text='#REDIRECT [[Greatsword#Stats]]' if row['pageid']==2 else 'Original source '+row['title']
            response={'parse':{'title':row['title'],'text':'<h2 id="Stats">Stats</h2><p>Greatsword</p>',
                'wikitext':text,'categories':[{'category':'Weapons'}],'images':[],
                'sections':[{'line':'Stats','anchor':'Stats','level':'2'}]}}
            if row['ns']==10:response={'query':{'pages':[{'revisions':[{'slots':{'main':{'content':text}}}]}]}}
            document={'page':row,'requested_revision':row['lastrevid'],'response':response,'retrieved_at':'2026-09-18T00:00:00Z'}
            (source/'pages'/f"{row['pageid']}.json.gz").write_bytes(gzip.compress(json.dumps(document).encode()))
        catalog=cls.root/'catalog.json'
        catalog.write_text(json.dumps({'source_game':'1.5.2.3','entries':{'one':{'source':'Greatsword','translation':'巨剑',
            'status':'reviewed','contexts':[{'reason':'visible_field'}]}}}),encoding='utf-8')
        cls.source=source;cls.catalog=catalog;cls.wiki=cls.root/'wiki'
        # File description previews must be staged even when no article uses them.
        data=b'unreferenced-file-preview';name=hashlib.sha256(data).hexdigest()+'.png'
        (source/'media').mkdir();(source/'media'/name).write_bytes(data)
        (source/'media-index.json').write_text(json.dumps({'files':{'5':{'file_id':5,'title':'Preview.png',
            'local_name':name,'sha256':name.split('.')[0],'size':len(data),'mime':'image/png'}},'errors':[]}),encoding='utf-8')
        cls.preview_name=name
        cls.release=build(source,cls.wiki,catalog,activate=True)
        cls.override=override_settings(WIKI_ROOT=cls.wiki);cls.override.enable()

    @classmethod
    def tearDownClass(cls):
        cls.override.disable();cls.temp.cleanup();super().tearDownClass()

    def test_home_article_and_original_source(self):
        self.assertContains(self.client.get('/wiki/'),'战场兄弟百科')
        response=self.client.get(page_url('Greatsword'))
        for value in ('巨剑','Greatsword','CC BY-SA 3.0','oldid=100','/wiki/source/1/'):
            self.assertContains(response,value)
        self.assertEqual(response['Cache-Control'],'private, no-store')
        self.assertEqual(self.client.get('/wiki/source/1/').content.decode(),'Original source Greatsword')

    def test_chinese_english_and_punctuation_search(self):
        for query in ('巨剑','Greatsword','剑'):
            response=self.client.get('/api/v1/wiki/search/',{'q':query})
            self.assertEqual(response.status_code,200);self.assertGreater(response.json()['total'],0)
            self.assertEqual(response.json()['results'][0]['id'],1)
        self.assertEqual(self.client.get('/wiki/search/',{'q':'" OR " <script>'}).status_code,200)
        self.assertContains(self.client.get('/wiki/search/',{'q':'NO_MATCH_abcdef'}),'还没有找到对应词条')

    def test_redirect_fragment_language_and_category(self):
        response=self.client.get(page_url('Old Sword'),{'lang':'en'})
        self.assertEqual(response.status_code,302)
        self.assertEqual(response['Location'],'/wiki/read/Greatsword/?lang=en#w-Stats')
        self.assertContains(self.client.get(page_url('Category:Weapons')),'分类词条')
        self.assertContains(self.client.get(page_url('Events')),'wiki-spoilers')
        data=self.client.get('/api/v1/wiki/search/',{'q':'Old Sword'}).json()
        self.assertEqual(data['results'][0]['id'],1)

    def test_missing_page_and_api_provenance(self):
        self.assertEqual(self.client.get(page_url('Missing')).status_code,404)
        data=self.client.get('/api/v1/wiki/pages/1/').json()['page']
        self.assertEqual(data['revision'],100);self.assertEqual(data['license'],'CC-BY-SA-3.0')
        self.assertEqual(data['terms'],[{'en':'Greatsword','zh':'巨剑'}])

    def test_private_report_permissions(self):
        self.assertEqual(self.client.get('/manage/wiki/').status_code,302)
        author=User.objects.create_user('wiki-author',password='x');self.client.force_login(author)
        self.assertEqual(self.client.get('/manage/wiki/').status_code,302)
        admin=User.objects.create_superuser('wiki-admin',password='x');self.client.force_login(admin)
        self.assertContains(self.client.get('/manage/wiki/'),'百科导入报告')
        self.assertTrue(self.client.get('/manage/wiki/?download=1').json()['complete_source'])

    def test_snapshot_validation_atomic_activation_and_asset_paths(self):
        call_command('publish_wiki',self.release.name,check_only=True)
        pointer=(self.wiki/'current.json').read_bytes()
        with self.assertRaises(CommandError):call_command('publish_wiki','../../outside')
        self.assertEqual((self.wiki/'current.json').read_bytes(),pointer)
        self.assertEqual(self.client.get('/wiki/media/anything.svg').status_code,404)
        response=self.client.get('/wiki/media/'+self.preview_name)
        self.assertEqual(response.status_code,200);response.close()
        self.assertIn(self.preview_name,json.loads((self.release/'manifest.json').read_text())['assets'])
        response=self.client.get('/wiki/styles/'+self.release.name+'/')
        self.assertEqual(response.status_code,200);self.assertIn('immutable',response['Cache-Control']);response.close()

    def test_unavailable_snapshot_and_source_revision_guard(self):
        with override_settings(WIKI_ROOT=self.root/'empty'):
            self.assertEqual(self.client.get('/wiki/').status_code,503)
            self.assertEqual(self.client.get('/api/v1/wiki/search/').status_code,503)
        inventory=json.loads((self.source/'inventory.json').read_text())
        inventory['pages'][0]['lastrevid']=9999
        changed=self.root/'incomplete';changed.mkdir()
        (changed/'pages').mkdir();(changed/'inventory.json').write_text(json.dumps(inventory))
        with self.assertRaisesRegex(ValueError,'source revisions missing'):
            build(changed,self.root/'failed',self.catalog,activate=True)
        self.assertFalse((self.root/'failed/current.json').exists())

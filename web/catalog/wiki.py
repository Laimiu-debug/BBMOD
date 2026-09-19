"""Public encyclopedia and a private import report. All reads are local."""
import json
import math
import re
from functools import lru_cache
from html import escape, unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from django.conf import settings
from django.contrib.auth.decorators import user_passes_test
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import redirect, render as django_render
from django.utils.safestring import mark_safe
from django.views.decorators.http import require_safe

from .wiki_store import (ASSET_PATTERN, LICENSE_URL, SNAPSHOT_PATTERN, open_store,
                         page_url, source_url, translation_info)

GROUPS = [
    ('01','兄弟与培养','背景、天赋、属性与成长', [('Character Backgrounds','人物背景'),('Traits','人物特性'),('Attributes','属性'),('Talents','天赋'),('Level and Experience','等级与经验')]),
    ('02','技能与战斗','特长、技能、伤病与战斗机制', [('Perks','特长'),('Skills','技能'),('Game Mechanics','游戏机制'),('Injuries','伤病'),('Game Guide','游戏指南')]),
    ('03','装备与物品','从基础装备到红装与传奇', [('Named and Legendary Items','红装与传奇装备'),('Melee Weapons','近战武器'),('Ranged Weapons','远程武器'),('Armor','护甲'),('Headgear','头部装备'),('Shields','盾牌')]),
    ('04','敌人与怪物','敌人、野兽及其战斗能力', [('Enemies','全部敌人'),('Beasts','野兽'),('Undead','亡灵'),('Orcs','兽人'),('Goblins','地精')]),
    ('05','起源与佣兵团','开局规则、随从和战团抱负', [('Origins','起源'),('Retinue','随从'),('Ambitions','战团抱负')]),
    ('06','世界与探索','定居点、阵营和传奇地点', [('Category:Settlements','定居点'),('Factions and Relations','阵营与关系'),('Legendary locations','传奇地点'),('Category:Locations','地点目录')]),
    ('07','委托与事件','触发条件、选项与故事结果', [('Contracts','委托'),('Events','事件'),('Category:Event','事件目录')]),
    ('08','制作与物资','配方、战利材料与消耗品', [('Crafting','制作配方'),('Trophies','战利材料'),('Taxidermist','制作工坊'),('Category:Consumable','消耗品')]),
]


def mode(request):
    selected = request.GET.get('lang', request.COOKIES.get('bbmod_wiki_lang', 'zh'))
    return selected if selected in ('zh', 'en', 'bi') else 'zh'


def render(request, template, context, status=200):
    response = django_render(request, template, context, status=status)
    if request.GET.get('lang') in ('zh', 'en', 'bi') and request.COOKIES.get('bbmod_wiki_lang') != mode(request):
        response.set_cookie('bbmod_wiki_lang', mode(request), max_age=31536000,
                            httponly=True, samesite='Lax', secure=request.is_secure())
    return response


def reading_url(url, language):
    parsed = urlsplit(url)
    if parsed.scheme or parsed.netloc or not parsed.path.startswith('/wiki/'):
        return url
    if not (parsed.path.startswith('/wiki/read/') or parsed.path in ('/wiki/', '/wiki/search/', '/wiki/about/')):
        return url
    query = [(key, value) for key, value in parse_qsl(parsed.query, keep_blank_values=True) if key != 'lang']
    return urlunsplit(('', '', parsed.path, urlencode(query + [('lang', language)]), parsed.fragment))


class ReadingIDs(HTMLParser):
    """Reserve original anchors before assigning names to repeated elements."""
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.ids = set()

    def handle_starttag(self, tag, attrs):
        self.ids.update(value for name, value in attrs if name == 'id' and value is not None)

    handle_startendtag = handle_starttag


class ReadingHTML(HTMLParser):
    """Rewrite only link/ID attributes, preserving text, MathML and media bytes."""
    # Match whole attributes so text such as id='example' inside an alt/title
    # value can never be mistaken for an attribute of the element.
    attributes = re.compile(r'(\s+)([^\s=/>]+)(\s*=\s*)([\"\'])(.*?)\4', re.S)

    def __init__(self, language, prefix='', current_path='', reserved_ids=()):
        super().__init__(convert_charrefs=False)
        self.language, self.prefix, self.current_path = language, prefix, current_path
        self.output = []
        self.reserved_ids = {prefix + value for value in reserved_ids}
        self.seen_ids, self.id_suffixes = set(), {}

    def start(self):
        def replace(match):
            space, name, assignment, quote, value = match.groups()
            if name.lower() not in ('href', 'id'):
                return match.group()
            decoded = unescape(value)
            changed = decoded
            if name.lower() == 'id':
                original = self.prefix + decoded
                changed = original
                if original in self.seen_ids:
                    suffix = self.id_suffixes.get(original, 2)
                    changed = f'{original}--{suffix}'
                    while changed in self.reserved_ids or changed in self.seen_ids:
                        suffix += 1
                        changed = f'{original}--{suffix}'
                    self.id_suffixes[original] = suffix + 1
                self.seen_ids.add(changed)
            elif name.lower() == 'href':
                parsed = urlsplit(decoded)
                if self.prefix and parsed.fragment and not parsed.scheme and not parsed.netloc and parsed.path in ('', self.current_path):
                    decoded = urlunsplit(('', '', parsed.path, parsed.query, self.prefix + parsed.fragment))
                changed = reading_url(decoded, self.language)
            if changed == unescape(value):
                return match.group()
            return space + name + assignment + quote + escape(changed, quote=True) + quote
        self.output.append(self.attributes.sub(replace, self.get_starttag_text()))

    def handle_starttag(self, tag, attrs): self.start()
    def handle_startendtag(self, tag, attrs): self.start()
    def handle_endtag(self, tag): self.output.append('</' + tag + '>')
    def handle_data(self, data): self.output.append(data)
    def handle_entityref(self, name): self.output.append('&' + name + ';')
    def handle_charref(self, name): self.output.append('&#' + name + ';')
    def handle_comment(self, data): self.output.append('<!--' + data + '-->')
    def handle_decl(self, decl): self.output.append('<!' + decl + '>')


@lru_cache(maxsize=12)
def reading_html(value, language, prefix='', current_path=''):
    anchors = ReadingIDs()
    anchors.feed(value)
    anchors.close()
    parser = ReadingHTML(language, prefix, current_path, anchors.ids)
    parser.feed(value)
    parser.close()
    return mark_safe(''.join(parser.output))


def page_number(request):
    try:return min(10000,max(1,int(request.GET.get('page','1'))))
    except ValueError:return 1


def decorate(row, language='zh'):
    row['url']=page_url(row['title'], lang=language)
    row['label']=(row.get('title_zh') if language != 'en' else '') or row['title'].removeprefix('Category:')
    row['secondary_title']=row['title'] if language != 'en' and row.get('title_zh') else ''
    row['display_summary']=(row.get('summary_zh') if language != 'en' else '') or row.get('summary', '')
    row['summary_language']='zh-Hans' if language != 'en' and row.get('summary_zh') else 'en'
    row['translation']=translation_info(row)
    return row


def common(store, request):
    report=store.report() if store else None
    choices=[]
    for value,label in (('zh','中文'),('en','英文原文'),('bi','中英对照')):
        query=request.GET.copy();query['lang']=value
        choices.append({'value':value,'label':label,'url':'?'+query.urlencode()})
    return {'wiki_report':report,'wiki_snapshot':store.release.name if store else '',
            'wiki_mode':mode(request),'wiki_modes':choices,'track_visit':True,'license_url':LICENSE_URL,
            'wiki_home_url':reading_url('/wiki/',mode(request)),
            'wiki_search_url':reading_url('/wiki/search/',mode(request)),
            'wiki_about_url':reading_url('/wiki/about/',mode(request))}


@require_safe
def home(request):
    with open_store() as store:
        context=common(store,request)
        if not store:return render(request,'wiki/unavailable.html',context,status=503)
        groups=[]
        for number,title,description,entries in GROUPS:
            links=[]
            for target,label in entries:
                entry=store.page(target,summary_only=True)
                if entry:links.append({'url':page_url(target,lang=mode(request)),
                    'label':target.removeprefix('Category:') if mode(request)=='en' else (entry.get('title_zh') or label).removeprefix('分类：')})
            groups.append({'number':number,'title':title,'description':description,'links':links})
        featured=[]
        for title in ('Named and Legendary Items','Character Backgrounds','Perks','Events'):
            entry=store.page(title,summary_only=True)
            if entry:featured.append(decorate(entry,mode(request)))
        context.update(groups=groups,featured=featured,
          wiki_translation_counts=store.translation_counts(),
          original_home_url=page_url('Battle Brothers Wiki',lang=mode(request)))
        return render(request,'wiki/home.html',context)


@require_safe
def search(request):
    with open_store() as store:
        context=common(store,request)
        if not store:return render(request,'wiki/unavailable.html',context,status=503)
        query=request.GET.get('q','').strip()[:100];number=page_number(request)
        count,rows=store.search(query,limit=24,offset=(number-1)*24,lang=mode(request))
        pages=max(1,math.ceil(count/24));number=min(number,pages)
        if number!=page_number(request):count,rows=store.search(query,limit=24,offset=(number-1)*24,lang=mode(request))
        context.update(query=query,results=[decorate(r,mode(request)) for r in rows],result_count=count,page=number,pages=pages,
            previous=urlencode({'q':query,'page':number-1,'lang':mode(request)}),
            following=urlencode({'q':query,'page':number+1,'lang':mode(request)}))
        return render(request,'wiki/search.html',context)


@require_safe
def article(request,title):
    if len(title)>350:raise Http404
    with open_store() as store:
        context=common(store,request)
        if not store:return render(request,'wiki/unavailable.html',context,status=503)
        row=store.page(title)
        if not row:
            context.update(missing_title=title.replace('_',' '),query=title.replace('_',' '),source_url=source_url(title))
            return render(request,'wiki/missing.html',context,status=404)
        if row['redirect']:
            visited={row['id']};target=row['redirect'];fragment=''
            for _ in range(12):
                name,separator,anchor=target.partition('#')
                if separator:fragment='w-'+anchor.replace(' ','_')
                destination=store.page(name)
                if not destination and name.startswith(('Battle Brothers Wiki:','Help:','User:','User blog:')):
                    return redirect(source_url(name))
                if not destination or destination['id'] in visited:break
                visited.add(destination['id'])
                if not destination['redirect']:
                    url=page_url(destination['title'],lang=mode(request))
                    if fragment:url+='#'+fragment
                    return redirect(url)
                target=destination['redirect']
            context.update(missing_title=row['title'],source_url=source_url(row['title']))
            return render(request,'wiki/missing.html',context,status=404)
        language=mode(request)
        row=decorate(row,language);row['sections']=json.loads(row['sections_json'])
        for section in row['sections']:
            section['label']=(section.get('title_zh') if language != 'en' else '') or section['title']
        categories=json.loads(row['categories_json'])
        row['categories']=[]
        for name in categories:
            category=store.page('Category:'+name,summary_only=True)
            label=category.get('title_zh') if category and language != 'en' else ''
            row['categories'].append({'label':label.removeprefix('分类：') if label else name,
                                      'url':page_url('Category:'+name,lang=language)})
        row['is_event']=row['title']=='Events' or any('event' in name.lower() for name in categories)
        row['has_translation']=bool(row['html_zh'])
        info=row['translation']
        row['reading_note']='中文译文' if info['reviewed'] else '中文译文（待复核）'
        if info['status']=='partial':row['reading_note']+=' · 部分内容保留英文'
        if info['stale']:row['reading_note']+=' · 原文已更新，译文待核对'
        if not row['has_translation']:
            row['reading_note']='本页暂无中文正文，以下显示英文原文。'
            empty_category=row['namespace']==14 and not unescape(re.sub(r'<[^>]+>','',row['html'])).strip()
            if empty_category or (info['status']=='not_applicable' and row['namespace']==14):
                row['reading_note']='本页为资料目录。'
            elif info['no_translatable_text']:
                row['reading_note']='本页没有需要翻译的正文。'
        if language=='en':row['reading_note']='英文原文'
        if info.get('retained_english'):row['reading_note']='历史日志 · 保留英文原文'
        row['readings']=[]
        if language != 'en' and row['has_translation']:
            row['readings'].append({'id':'wiki-translation','language':'zh-Hans','label':'中文译文',
                'content':reading_html(row['html_zh'],language),'source':False})
        if language in ('en','bi') or not row['has_translation']:
            row['readings'].append({'id':'wiki-original','language':'en','label':'英文原文','source':True,
                'content':reading_html(row['html'],language,'wiki-en-' if row['readings'] else '',page_url(row['title']))})
        row['parallel']=len(row['readings'])==2
        context.update(entry=row,glossary=store.glossary(row['id']),source_url=source_url(row['title']),
            revision_url='https://battlebrothers.fandom.com/index.php?'+urlencode({'title':row['title'],'oldid':row['revision']}),
            history_url='https://battlebrothers.fandom.com/index.php?'+urlencode({'title':row['title'],'action':'history'}))
        if row['namespace']==14:
            number=page_number(request)
            count,members=store.members(row['title'],100,(number-1)*100,lang=language)
            pages=max(1,math.ceil(count/100));number=min(number,pages)
            if number!=page_number(request):count,members=store.members(row['title'],100,(number-1)*100,lang=language)
            context.update(category_members=[decorate(r,language) for r in members],member_count=count,
                page=number,pages=max(1,math.ceil(count/100)),
                previous=urlencode({'page':number-1,'lang':mode(request)}),
                following=urlencode({'page':number+1,'lang':mode(request)}))
        if row['namespace']==6:
            asset=store.db.execute('SELECT * FROM assets WHERE id=?',(row['id'],)).fetchone()
            if asset:
                context['file_info']=json.loads(asset['metadata_json'])
        return render(request,'wiki/article.html',context)


@require_safe
def about(request):
    with open_store() as store:
        context=common(store,request)
        if store:context['wiki_translation_counts']=store.translation_counts()
        return render(request,'wiki/about.html',context)


@require_safe
def source(request,page_id):
    with open_store() as store:
        row=store.page(page_id=page_id) if store else None
        if not row:raise Http404
        response=HttpResponse(row['source_text'],content_type='text/plain; charset=utf-8')
        response['Content-Disposition']=f'attachment; filename="wiki-{page_id}-r{row["revision"]}.wikitext.txt"'
        return response


@require_safe
def media(request,filename):
    if not ASSET_PATTERN.fullmatch(filename):raise Http404
    path=Path(settings.WIKI_ROOT)/'assets'/filename
    if not path.is_file():raise Http404
    mime={'.png':'image/png','.jpg':'image/jpeg','.gif':'image/gif','.webp':'image/webp','.svg':'image/svg+xml'}[path.suffix]
    response=FileResponse(path.open('rb'),content_type=mime)
    response['Cache-Control']='public, max-age=31536000, immutable'
    response['ETag']='"'+filename.split('.')[0]+'"'
    response.bbmod_public_asset=True
    return response


@require_safe
def styles(request,snapshot):
    if not SNAPSHOT_PATTERN.fullmatch(snapshot):raise Http404
    path=Path(settings.WIKI_ROOT)/'releases'/snapshot/'styles.css'
    if not path.is_file():raise Http404
    response=FileResponse(path.open('rb'),content_type='text/css; charset=utf-8')
    response['Cache-Control']='public, max-age=31536000, immutable';response.bbmod_public_asset=True
    return response


@user_passes_test(lambda u:u.is_active and u.is_superuser)
@require_safe
def management(request):
    with open_store() as store:
        context=common(store,request);context['track_visit']=False
        report=store.report() if store else {}
        if request.GET.get('download')=='1':
            response=JsonResponse(report,json_dumps_params={'ensure_ascii':False,'indent':2})
            response['Content-Disposition']='attachment; filename="wiki-import-report.json"'
            return response
        context['report_text']=json.dumps(report,ensure_ascii=False,indent=2)
        return render(request,'wiki/management.html',context)


@require_safe
def api_search(request):
    with open_store() as store:
        if not store:return JsonResponse({'error':'encyclopedia_unavailable'},status=503)
        query=request.GET.get('q','').strip()[:100];number=page_number(request)
        count,rows=store.search(query,limit=24,offset=(number-1)*24,lang=mode(request))
        results=[]
        for row in rows:
            row=decorate(row,mode(request));row['reading_url']=row['url'];row['url']=page_url(row['title'])
            results.append(row)
        return JsonResponse({'schema_version':1,'snapshot':store.release.name,'query':query,
            'total':count,'page':number,'lang':mode(request),'results':results},json_dumps_params={'ensure_ascii':False})


@require_safe
def api_page(request,page_id):
    with open_store() as store:
        row=store.page(page_id=page_id) if store else None
        if not row:raise Http404
        return JsonResponse({'schema_version':1,'snapshot':store.release.name,
          'page':{'id':row['id'],'title':row['title'],'title_zh':row['title_zh'],'url':page_url(row['title']),
                  'revision':row['revision'],'source_url':source_url(row['title']),'redirect':row['redirect'],
                  'html':row['html'],'html_zh':row['html_zh'],'summary_zh':row['summary_zh'],
                  'translation':translation_info(row),'categories':json.loads(row['categories_json']),
                  'reading_url':page_url(row['title'],lang=mode(request)),
                  'contributors_url':'https://battlebrothers.fandom.com/index.php?'+urlencode({'title':row['title'],'action':'history'}),
                  'terms':store.glossary(row['id']),'license':'CC-BY-SA-3.0','license_url':LICENSE_URL,
                  'translation_scope':'article_prose' if row['html_zh'] else 'reviewed_game_names'}},json_dumps_params={'ensure_ascii':False})

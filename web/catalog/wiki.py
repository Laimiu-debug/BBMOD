"""Public encyclopedia and a private import report. All reads are local."""
import json
import math
from pathlib import Path
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth.decorators import user_passes_test
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.utils.safestring import mark_safe
from django.views.decorators.http import require_safe

from .wiki_store import (ASSET_PATTERN, LICENSE_URL, SNAPSHOT_PATTERN, open_store,
                         page_url, source_url, title_key)

GROUPS = [
    ('01','兄弟与培养','背景、天赋、属性与成长', [('Character Backgrounds','人物背景'),('Traits','人物特性'),('Attributes','属性'),('Talents','天赋'),('Level and Experience','等级与经验')]),
    ('02','技能与战斗','特长、技能、伤病与战斗机制', [('Perks','特长'),('Skills','技能'),('Game Mechanics','游戏机制'),('Injuries','伤病'),('Game Guide','游戏指南')]),
    ('03','装备与物品','从基础装备到红装与传奇', [('Named and Legendary Items','红装与传奇装备'),('Melee Weapons','近战武器'),('Ranged Weapons','远程武器'),('Armor','护甲'),('Headgear','头部装备'),('Shields','盾牌')]),
    ('04','敌人与怪物','敌人、野兽及其战斗能力', [('Enemies','全部敌人'),('Beasts','野兽'),('Undead','亡灵'),('Orcs','兽人'),('Goblins','地精')]),
    ('05','起源与佣兵团','开局规则、随从和佣兵团目标', [('Origins','起源'),('Retinue','随从'),('Ambitions','野心')]),
    ('06','世界与探索','定居点、阵营和传奇地点', [('Category:Settlements','定居点'),('Factions and Relations','阵营与关系'),('Legendary locations','传奇地点'),('Category:Locations','地点目录')]),
    ('07','委托与事件','触发条件、选项与故事结果', [('Contracts','委托'),('Events','事件'),('Category:Event','事件目录')]),
    ('08','制作与物资','配方、战利材料与消耗品', [('Crafting','制作配方'),('Trophies','战利材料'),('Taxidermist','制作工坊'),('Category:Consumable','消耗品')]),
]


def mode(request):
    return 'en' if request.GET.get('lang')=='en' else 'bi'


def page_number(request):
    try:return min(10000,max(1,int(request.GET.get('page','1'))))
    except ValueError:return 1


def decorate(row):
    row['url']=page_url(row['title'])
    row['label']=row.get('title_zh') or row['title'].removeprefix('Category:')
    return row


def common(store, request):
    report=store.report() if store else None
    return {'wiki_report':report,'wiki_snapshot':store.release.name if store else '',
            'wiki_mode':mode(request),'track_visit':True,'license_url':LICENSE_URL}


@require_safe
def home(request):
    with open_store() as store:
        context=common(store,request)
        if not store:return render(request,'wiki/unavailable.html',context,status=503)
        groups=[]
        for number,title,description,entries in GROUPS:
            links=[]
            for target,label in entries:
                if store.page(target):links.append({'url':page_url(target),'label':label})
            groups.append({'number':number,'title':title,'description':description,'links':links})
        context.update(groups=groups,featured=[decorate(store.page(t)) for t in
          ('Named and Legendary Items','Character Backgrounds','Perks','Events') if store.page(t)])
        return render(request,'wiki/home.html',context)


@require_safe
def search(request):
    with open_store() as store:
        context=common(store,request)
        if not store:return render(request,'wiki/unavailable.html',context,status=503)
        query=request.GET.get('q','').strip()[:100];number=page_number(request)
        count,rows=store.search(query,limit=24,offset=(number-1)*24)
        pages=max(1,math.ceil(count/24));number=min(number,pages)
        if number!=page_number(request):count,rows=store.search(query,limit=24,offset=(number-1)*24)
        context.update(query=query,results=[decorate(r) for r in rows],result_count=count,page=number,pages=pages,
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
                    url=page_url(destination['title'])+'?'+urlencode({'lang':mode(request)})
                    if fragment:url+='#'+fragment
                    return redirect(url)
                target=destination['redirect']
            context.update(missing_title=row['title'],source_url=source_url(row['title']))
            return render(request,'wiki/missing.html',context,status=404)
        row=decorate(row);row['sections']=json.loads(row['sections_json'])
        row['categories']=[{'label':c,'url':page_url('Category:'+c)} for c in json.loads(row['categories_json'])]
        row['is_event']=row['title']=='Events' or any('event' in c['label'].lower() for c in row['categories'])
        row['content']=mark_safe(row['html'])  # Only the compiler's nh3-sanitized snapshot is publishable.
        context.update(entry=row,glossary=store.glossary(row['id']),source_url=source_url(row['title']),
            revision_url='https://battlebrothers.fandom.com/index.php?'+urlencode({'title':row['title'],'oldid':row['revision']}),
            history_url='https://battlebrothers.fandom.com/index.php?'+urlencode({'title':row['title'],'action':'history'}))
        if row['namespace']==14:
            number=page_number(request)
            count,members=store.members(row['title'],100,(number-1)*100)
            context.update(category_members=[decorate(r) for r in members],member_count=count,
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
        return render(request,'wiki/about.html',common(store,request))


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
        count,rows=store.search(query,limit=24,offset=(number-1)*24)
        return JsonResponse({'schema_version':1,'snapshot':store.release.name,'query':query,
            'total':count,'page':number,'results':[decorate(r) for r in rows]},json_dumps_params={'ensure_ascii':False})


@require_safe
def api_page(request,page_id):
    with open_store() as store:
        row=store.page(page_id=page_id) if store else None
        if not row:raise Http404
        return JsonResponse({'schema_version':1,'snapshot':store.release.name,
          'page':{'id':row['id'],'title':row['title'],'title_zh':row['title_zh'],'url':page_url(row['title']),
                  'revision':row['revision'],'source_url':source_url(row['title']),'redirect':row['redirect'],
                  'html':row['html'],'categories':json.loads(row['categories_json']),
                  'terms':store.glossary(row['id']),'license':'CC-BY-SA-3.0','license_url':LICENSE_URL,
                  'translation_scope':'reviewed_game_names'}},json_dumps_params={'ensure_ascii':False})

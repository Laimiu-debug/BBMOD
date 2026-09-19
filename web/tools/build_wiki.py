"""Compile a complete local wiki snapshot; activate only after integrity checks."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import gzip
import hashlib
import html
import json
from pathlib import Path
import re
import shutil
import sqlite3
import sys

WEB = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WEB))
from catalog.wiki_store import chinese_tokens, title_key
from catalog.wiki_render import term_catalog, translated_title, render_article
from tools.fetch_wiki import load_json, atomic_json

SCHEMA = '''
CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
CREATE TABLE pages(id INTEGER PRIMARY KEY,title TEXT NOT NULL UNIQUE,title_key TEXT NOT NULL,
 namespace INTEGER NOT NULL,revision INTEGER NOT NULL,redirect TEXT NOT NULL DEFAULT '',title_zh TEXT NOT NULL DEFAULT '',
 summary TEXT NOT NULL DEFAULT '',html TEXT NOT NULL DEFAULT '',source_text TEXT NOT NULL DEFAULT '',
 sections_json TEXT NOT NULL DEFAULT '[]',categories_json TEXT NOT NULL DEFAULT '[]',fetched_at TEXT NOT NULL DEFAULT '');
CREATE INDEX page_namespace ON pages(namespace,redirect,title);
CREATE INDEX page_title_key ON pages(title_key);
CREATE TABLE categories(category_key TEXT NOT NULL,page_id INTEGER NOT NULL,UNIQUE(category_key,page_id));
CREATE INDEX category_pages ON categories(category_key,page_id);
CREATE TABLE page_terms(page_id INTEGER NOT NULL,en TEXT NOT NULL,zh TEXT NOT NULL,UNIQUE(page_id,en));
CREATE TABLE assets(id INTEGER PRIMARY KEY,title TEXT NOT NULL,local_name TEXT NOT NULL,mime TEXT NOT NULL,
 size INTEGER NOT NULL,sha256 TEXT NOT NULL,metadata_json TEXT NOT NULL);
CREATE INDEX assets_local ON assets(local_name);
CREATE VIRTUAL TABLE page_search USING fts5(title,title_zh,names,body,zh_tokens,tokenize='unicode61 remove_diacritics 2');
'''


def source_text(document):
    response=document['response']
    if 'parse' in response:
        return response['parse'].get('wikitext','')
    revisions=response.get('query',{}).get('pages',[{}])[0].get('revisions',[{}])
    return revisions[0].get('slots',{}).get('main',{}).get('content','')


def redirect_target(text):
    match=re.match(r'\s*#redirect\s*\[\[([^\]]+)\]\]',text,re.I)
    if not match:return ''
    target=match.group(1).split('|')[0].strip().lstrip(':')
    name,separator,fragment=target.partition('#')
    return name.replace('_',' ')+(separator+fragment if separator else '')


def build(source, destination, catalog, activate=False, allow_incomplete=False):
    inventory=load_json(source/'inventory.json')
    media=load_json(source/'media-index.json') if (source/'media-index.json').exists() else {'files':{},'errors':[]}
    terms,translation=term_catalog(catalog)
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    identity=hashlib.sha256((json.dumps(inventory,sort_keys=True)+translation['sha256']+stamp).encode()).hexdigest()[:12]
    edition=stamp+'-'+identity
    release=destination/'releases'/edition
    release.mkdir(parents=True,exist_ok=False)
    assets_dir=destination/'assets';assets_dir.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(release/'wiki.sqlite3');db.executescript(SCHEMA)
    rows=inventory['pages'];available={r['title']:r['title'] for r in rows}
    for row in rows:available.setdefault(title_key(row['title']),row['title'])
    documents={};missing_pages=[]
    for row in rows:
        path=source/'pages'/f"{row['pageid']}.json.gz"
        if not path.exists():
            missing_pages.append({'id':row['pageid'],'title':row['title']});continue
        document=load_json(path)
        if document.get('requested_revision')!=row['lastrevid']:
            missing_pages.append({'id':row['pageid'],'title':row['title'],'reason':'revision_mismatch'});continue
        documents[row['pageid']]=document
    if missing_pages and not allow_incomplete:
        db.close()
        raise ValueError(f'{len(missing_pages)} source revisions missing; snapshot not activated')
    # MediaWiki categories exist even without an authored Category: page.
    implicit_categories=set()
    for document in documents.values():
        parsed=document['response'].get('parse',{})
        for category in parsed.get('categories',[]):
            title='Category:'+category['category'].replace('_',' ')
            if title_key(title) not in available:implicit_categories.add(title)
        for link in parsed.get('links',[]):
            if link.get('ns')==14:
                title=link.get('title','')
                if title and title_key(title) not in available:implicit_categories.add(title)
    for title in implicit_categories:
        available[title]=title;available.setdefault(title_key(title),title)
    assets={r['title']:r for r in media['files'].values()}
    for record in media['files'].values():assets.setdefault(title_key(record['title']),record)
    for record in media['files'].values():
        db.execute('INSERT INTO assets VALUES(?,?,?,?,?,?,?)',(record['file_id'],record['title'],record.get('local_name',''),
          record.get('mime',''),record.get('size',0),record.get('sha256',''),json.dumps(record,ensure_ascii=False)))
    styles={};missing_links={};missing_images={};external_media={};parser_warnings={};term_pages=0
    # File description pages also expose previews, including unreferenced files.
    all_used={r['local_name'] for r in media['files'].values() if r.get('local_name')}
    redirects=0;article_count=0;source_only=0
    for position,row in enumerate(rows):
        document=documents.get(row['pageid'])
        if document is None:continue
        text=source_text(document);redirect=redirect_target(text)
        parsed=document['response'].get('parse')
        title=row['title'];zh=translated_title(title,terms);body='';plain='';sections=[];categories=[];names={}
        if parsed and not redirect:
            rendered=render_article(parsed,terms,available,assets,styles)
            body=rendered['html'];plain=rendered['plain'];sections=rendered['sections'];names=rendered['terms']
            if rendered['missing_links']:missing_links[title]=rendered['missing_links']
            if rendered['missing_images']:missing_images[title]=rendered['missing_images']
            if rendered['external_media']:external_media[title]=rendered['external_media']
            categories=[c['category'].replace('_',' ') for c in parsed.get('categories',[])]
            if parsed.get('parsewarnings'):parser_warnings[title]=parsed['parsewarnings']
            for image in parsed.get('images',[]):
                record=assets.get(image.replace('_',' ')) or assets.get(title_key(image))
                if record and record.get('local_name'):all_used.add(record['local_name'])
            all_used.update(re.findall(r'/wiki/media/([a-f0-9]{64}\.(?:png|jpg|gif|webp|svg))',body))
        elif not redirect:
            body='<pre class="w-source-text">'+html.escape(text)+'</pre>'
            source_only+=1
        if row['ns']==0:
            if redirect:redirects+=1
            else:article_count+=1
        summary=re.sub(r'\s+',' ',plain)[:260]
        db.execute('INSERT INTO pages VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
            (row['pageid'],title,title_key(title),row['ns'],row['lastrevid'],redirect,zh,summary,body,text,
             json.dumps(sections,ensure_ascii=False),json.dumps(categories,ensure_ascii=False),document['retrieved_at']))
        for category in categories:
            db.execute('INSERT OR IGNORE INTO categories VALUES(?,?)',(title_key(category),row['pageid']))
        for en,cn in names.items():db.execute('INSERT INTO page_terms VALUES(?,?,?)',(row['pageid'],en,cn))
        if names:term_pages+=1
        if row['ns'] in (0,14) and not redirect:
            labels=' '.join(names.keys())+' '+' '.join(names.values())
            db.execute('INSERT INTO page_search(rowid,title,title_zh,names,body,zh_tokens) VALUES(?,?,?,?,?,?)',
                       (row['pageid'],title,zh,labels,plain,chinese_tokens(zh+' '+labels)))
        if position%300==0:print(f'compile {position+1}/{len(rows)}',flush=True)
    for n,title in enumerate(sorted(implicit_categories)):
        db.execute('INSERT INTO pages(id,title,title_key,namespace,revision) VALUES(?,?,?,?,0)',(-n-1,title,title_key(title),14))
    # Redirect titles must also be searchable under their canonical destination.
    broken_redirects=[];external_redirects=[]
    for row in db.execute('SELECT id,title,redirect FROM pages WHERE redirect!=""').fetchall():
        target=row[2].split('#')[0]
        if title_key(target) not in available:
            group=external_redirects if target.startswith(('Battle Brothers Wiki:','Help:','User:','User blog:')) else broken_redirects
            group.append({'title':row[1],'target':row[2]})
        seen={row[0]}
        for _ in range(12):
            dest=db.execute('SELECT id,redirect FROM pages WHERE title=?',(target,)).fetchone()
            if not dest:dest=db.execute('SELECT id,redirect FROM pages WHERE title_key=? LIMIT 1',(title_key(target),)).fetchone()
            if not dest or dest[0] in seen:break
            seen.add(dest[0])
            if not dest[1]:
                db.execute('UPDATE page_search SET names=names||? WHERE rowid=?',(' '+row[1],dest[0]));break
            target=dest[1].split('#')[0]
    copied=0;total_bytes=0
    for filename in sorted(all_used):
        origin=source/'media'/filename
        if not origin.is_file() or hashlib.sha256(origin.read_bytes()).hexdigest()!=filename.split('.')[0]:
            raise ValueError('Missing or damaged illustration: '+filename)
        target=assets_dir/filename
        if not target.exists():shutil.copyfile(origin,target)
        if hashlib.sha256(target.read_bytes()).hexdigest()!=filename.split('.')[0]:raise ValueError('Invalid staged illustration')
        total_bytes+=target.stat().st_size;copied+=1
    css='\n'.join('.wiki-content .'+name+'{'+value+'}' for name,value in sorted(styles.items()))
    (release/'styles.css').write_text(css,encoding='utf-8')
    report={'schema_version':1,'snapshot':edition,'built_at':datetime.now(timezone.utc).isoformat(),
        'source':'https://battlebrothers.fandom.com','inventory_at':inventory['retrieved_at'],
        'source_statistics':inventory['statistics'],'source_rights':inventory['rights'],
        'source_inventory_pages':len(rows),'source_revisions_saved':len(documents),
        'article_pages':article_count,'redirect_pages':redirects,'category_pages':sum(r['ns']==14 for r in rows),
        'implicit_categories':len(implicit_categories),'templates':sum(r['ns']==10 for r in rows),
        'file_description_pages':sum(r['ns']==6 for r in rows),'illustrations':copied,'illustration_bytes':total_bytes,
        'term_catalog':translation,'pages_with_terms':term_pages,'missing_pages':missing_pages,
        'missing_links':missing_links,'missing_images':missing_images,'parser_warnings':parser_warnings,
        'broken_redirects':broken_redirects,'external_redirects':external_redirects,
        'external_media':external_media,'media_errors':media.get('errors',[]),
        'media_status':dict(Counter(r.get('status','unknown') for r in media['files'].values())),
        'unavailable_source_files':[r['title'] for r in media['files'].values() if r.get('status')=='upstream_missing'],
        'media_rights':dict(Counter(r.get('rights_status','source_unstated') for r in media['files'].values() if r.get('local_name') in all_used)),
        'translation_scope':'Reviewed BBMOD zh game names only; article prose remains the English source.',
        'complete_source':not missing_pages}
    db.execute('INSERT INTO metadata VALUES(?,?)',('report',json.dumps(report,ensure_ascii=False)))
    db.commit()
    if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Snapshot integrity check failed')
    db.close()
    atomic_json(release/'report.json',report)
    manifest={name:hashlib.sha256((release/name).read_bytes()).hexdigest() for name in ('wiki.sqlite3','styles.css','report.json')}
    atomic_json(release/'manifest.json',{'schema_version':1,'snapshot':edition,'files':manifest,
                                      'assets':sorted(all_used),'complete_source':not missing_pages})
    if activate:
        if missing_pages:raise ValueError('An incomplete source snapshot cannot be activated')
        if missing_images or media.get('errors'):raise ValueError('A snapshot with missing illustrations cannot be activated')
        atomic_json(destination/'current.json',{'snapshot':edition})
    print(json.dumps({k:report[k] for k in ['snapshot','article_pages','redirect_pages','illustrations','illustration_bytes','pages_with_terms','complete_source']},ensure_ascii=False),flush=True)
    return release


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--destination',type=Path,required=True)
    parser.add_argument('--catalog',type=Path,default=WEB.parent/'app/localization/full_catalog.json')
    parser.add_argument('--activate',action='store_true')
    parser.add_argument('--allow-incomplete',action='store_true',help='Build a local development snapshot; activation is always refused.')
    args=parser.parse_args()
    build(args.source.resolve(),args.destination.resolve(),args.catalog.resolve(),args.activate,args.allow_incomplete)

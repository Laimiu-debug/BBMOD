"""Cache public wiki illustrations with source metadata and content hashes.

File licenses remain separate from article licenses. Absence of a declaration
is recorded, never converted into a Creative Commons grant.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import time
import threading
import warnings
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler
import xml.etree.ElementTree as ET

from PIL import Image, ImageOps
import requests
from fetch_wiki import load_json, atomic_json, USER_AGENT, now

MAX_BYTES = 24 * 1024 * 1024
MIMES = {'image/png':'.png','image/jpeg':'.jpg','image/gif':'.gif','image/webp':'.webp','image/svg+xml':'.svg'}
SVG_TAGS = set('svg g path rect circle ellipse line polyline polygon text tspan defs clipPath linearGradient radialGradient stop use title desc'.split())
_local=threading.local()


def allowed_url(url):
    parsed = urlsplit(url)
    return (parsed.scheme == 'https' and parsed.hostname == 'static.wikia.nocookie.net'
            and parsed.port in (None,443) and not parsed.username
            and parsed.path.startswith('/battlebrothers/images/'))


class MediaRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not allowed_url(newurl):
            raise ValueError('Image redirect leaves the permitted media repository')
        return super().redirect_request(req,fp,code,msg,headers,newurl)


def sanitize_svg(data):
    if re.search(br'<!\s*ENTITY', data, re.I) or re.search(br'<!\s*DOCTYPE[^>]*\[',data,re.I):
        raise ValueError('SVG declarations are not supported')
    data=re.sub(br'<!\s*DOCTYPE[^>]*>',b'',data,flags=re.I)
    root = ET.fromstring(data)
    for parent in root.iter():
        for child in list(parent):
            if child.tag.split('}')[-1] not in SVG_TAGS:
                parent.remove(child)
        for name,value in list(parent.attrib.items()):
            local = name.split('}')[-1].lower()
            if (local.startswith('on') or local == 'style' or
                    (local in ('href','src') and not value.startswith('#')) or
                    ('url(' in value.lower() and not re.fullmatch(r'url\(#[A-Za-z0-9_-]+\)',value))):
                del parent.attrib[name]
    if root.tag.split('}')[-1] != 'svg':
        raise ValueError('Invalid SVG root')
    return ET.tostring(root,encoding='utf-8',xml_declaration=True)


def fetch_one(root, row, metadata_only=False):
    record = {'file_id':row['pageid'], 'title':row['title'][5:], 'source_url':'',
              'description_url':'', 'license':'', 'rights_status':'source_unstated',
              'local_name':'', 'status':'unsupported'}
    info = (row.get('imageinfo') or [{}])[0]
    record.update(source_url=info.get('url',''), description_url=info.get('descriptionurl',''),
                  original_sha1=info.get('sha1',''), original_size=info.get('size',0),
                  width=info.get('width',0), height=info.get('height',0), mime=info.get('mime',''), original_mime=info.get('mime',''),
                  uploaded_at=info.get('timestamp',''), uploader=info.get('user',''),
                  source_metadata=info.get('extmetadata',{}))
    metadata=info.get('extmetadata',{})
    record['license'] = metadata.get('LicenseShortName',{}).get('value','')
    if record['license']:
        record['rights_status']='source_declared'
    if metadata_only:
        record['status']='not_referenced';return record
    mime=record['mime'];digest=record['original_sha1']
    if mime not in MIMES or not re.fullmatch(r'[a-f0-9]{40}',digest):
        return record
    if not allowed_url(record['source_url']):
        record.update(status='blocked_host');return record
    original=root/'original-media'/(digest+MIMES[mime])
    if original.exists():
        raw=original.read_bytes()
    else:
        for attempt in range(3):
            try:
                if not hasattr(_local,'session'):
                    _local.session=requests.Session()
                    _local.session.headers['User-Agent']=USER_AGENT
                url=record['source_url']
                for hop in range(4):
                    if not allowed_url(url):raise ValueError('Unexpected media host')
                    with _local.session.get(url,timeout=(12,30),allow_redirects=False,stream=True) as response:
                        if response.is_redirect:
                            from urllib.parse import urljoin
                            url=urljoin(url,response.headers['Location']);continue
                        if response.status_code==404:
                            record.update(status='upstream_missing',source_http_status=404)
                            return record
                        response.raise_for_status()
                        chunks=[];length=0
                        for chunk in response.iter_content(65536):
                            length+=len(chunk)
                            if length>MAX_BYTES:raise ValueError('Image exceeds byte limit')
                            chunks.append(chunk)
                        raw=b''.join(chunks)
                        break
                else:raise ValueError('Too many image redirects')
                break
            except Exception:
                if attempt==2:raise
                time.sleep(2**attempt)
    # Fandom's CDN serves WebP representations even for original PNG/JPEG URLs.
    # Keep the original SHA-1 as provenance; verify the served representation by
    # decoding, checking full dimensions, and its own independently stored hash.
    if hashlib.sha1(raw).hexdigest()!=digest:
        with Image.open(io.BytesIO(raw)) as check:
            if (check.format!='WEBP' or mime not in ('image/png','image/jpeg','image/webp','image/gif')
                    or check.size!=(record['width'],record['height'])):
                raise ValueError('Unexpected transformation of source image')
            record['retrieved_frames']=getattr(check,'n_frames',1)
        record['cdn_representation']='webp'
    else:record['cdn_representation']='original'
    record['retrieved_sha256']=hashlib.sha256(raw).hexdigest()
    if not original.exists():
        original.parent.mkdir(parents=True,exist_ok=True)
        staged=original.with_suffix(original.suffix+f'.{threading.get_ident()}.part')
        staged.write_bytes(raw);staged.replace(original)
    suffix=MIMES[mime];output=raw
    if mime=='image/svg+xml':
        output=sanitize_svg(raw)
    else:
        with warnings.catch_warnings():
            warnings.simplefilter('error',Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(raw)) as image:
                suffix={'PNG':'.png','JPEG':'.jpg','WEBP':'.webp','GIF':'.gif'}.get(image.format,suffix)
                image.verify()
            with Image.open(io.BytesIO(raw)) as image:
                if max(image.size)>1600 and not getattr(image,'is_animated',False):
                    image=ImageOps.exif_transpose(image)
                    image.thumbnail((1600,1600))
                    buf=io.BytesIO();image.convert('RGBA' if 'A' in image.getbands() else 'RGB').save(buf,format='WEBP',quality=90)
                    output=buf.getvalue();suffix='.webp'
    final_sha=hashlib.sha256(output).hexdigest()
    filename=final_sha+suffix
    dest=root/'media'/filename
    dest.parent.mkdir(parents=True,exist_ok=True)
    if not dest.exists():dest.write_bytes(output)
    record.update(local_name=filename,sha256=final_sha,size=len(output),status='cached',
                  mime={'.png':'image/png','.jpg':'image/jpeg','.webp':'image/webp','.gif':'image/gif','.svg':'image/svg+xml'}[suffix],
                  resized=output!=raw)
    return record


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--workers',type=int,choices=(1,2,3,4),default=4)
    parser.add_argument('--only-used',action='store_true',help='Cache only illustrations referenced by imported articles; preserve all file metadata.')
    args=parser.parse_args();root=args.source.resolve()
    index_path=root/'media-index.json'
    existing=load_json(index_path).get('files',{}) if index_path.exists() else {}
    rows=[load_json(p) for p in (root/'files').glob('*.json')]
    pending=[]
    used=set(load_json(root/'used-images.json')) if args.only_used else None
    for row in rows:
        previous=existing.get(str(row['pageid']),{})
        info=(row.get('imageinfo') or [{}])[0]
        if (previous.get('status')=='cached' and previous.get('original_sha1')==info.get('sha1')
                and (root/'media'/previous['local_name']).is_file()):continue
        if used is not None and row['title'][5:].replace('_',' ').casefold() not in used:
            existing[str(row['pageid'])]=fetch_one(root,row,metadata_only=True);continue
        pending.append(row)
    errors=[];done=0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures={pool.submit(fetch_one,root,row):row for row in pending}
        for future in as_completed(futures):
            row=futures[future]
            try:existing[str(row['pageid'])]=future.result()
            except Exception as exc:
                errors.append({'id':row['pageid'],'title':row['title'],'error':str(exc)[:350]})
            done+=1
            if done%100==0 or done==len(pending):
                atomic_json(index_path,{'schema_version':1,'updated_at':now(),'files':existing,'errors':errors})
                print(f'media {done}/{len(pending)} cached={sum(r.get("status")=="cached" for r in existing.values())} errors={len(errors)}',flush=True)
    if errors:raise SystemExit(f'{len(errors)} images failed; rerun to retry missing files.')


if __name__=='__main__':main()

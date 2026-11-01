"""Transfer a new EXE using unchanged archive bytes in an existing official EXE.

The website still serves an ordinary complete EXE. This is an internal,
hash-verified transport format, with a standard-library-only receiver.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import zipfile


def digest(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def create(old,new,output):
    from PyInstaller.archive.readers import CArchiveReader
    old_archive,new_archive=CArchiveReader(str(old)),CArchiveReader(str(new))
    old_bytes,new_bytes=old.read_bytes(),new.read_bytes()
    reuse={}
    for offset,length,*_ in old_archive.toc.values():
        if length:
            start=old_archive._start_offset+offset
            reuse[hashlib.sha256(old_bytes[start:start+length]).digest()]=(start,length)
    pieces=[];cursor=0;blobs=0;copied=0
    with zipfile.ZipFile(output,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        def emit(start,end):
            nonlocal blobs,copied
            if start==end:return
            data=new_bytes[start:end];match=reuse.get(hashlib.sha256(data).digest())
            if match:
                pieces.append({'copy':match});copied+=len(data)
            else:
                name=f'blob/{blobs}';blobs+=1;archive.writestr(name,data);pieces.append({'blob':name})
        for offset,length,*_ in sorted(new_archive.toc.values()):
            if not length:continue
            start=new_archive._start_offset+offset
            if start<cursor:raise ValueError('Overlapping archive entries')
            emit(cursor,start);emit(start,start+length);cursor=start+length
        emit(cursor,len(new_bytes))
        recipe=dict(schema=1,old_sha256=digest(old),new_sha256=digest(new),size=len(new_bytes),pieces=pieces)
        archive.writestr('recipe.json',json.dumps(recipe,separators=(',',':')))
    return dict(bytes=output.stat().st_size,sha256=digest(output),reused_bytes=copied,new_sha256=recipe['new_sha256'])


def apply(old,patch,output):
    with zipfile.ZipFile(patch) as archive:
        recipe=json.loads(archive.read('recipe.json'))
        if recipe['schema']!=1 or not 0<recipe['size']<=300*1024*1024 or len(recipe['pieces'])>20000:
            raise ValueError('Invalid transfer recipe')
        if digest(old)!=recipe['old_sha256']:raise ValueError('Official base EXE checksum mismatch')
        if output.exists():
            if digest(output)==recipe['new_sha256']:return
            raise FileExistsError('Do not replace an existing different EXE')
        output.parent.mkdir(parents=True,exist_ok=True)
        try:
            with old.open('rb') as source,output.open('xb') as target:
                for piece in recipe['pieces']:
                    if 'copy' in piece:
                        offset,length=piece['copy']
                        if offset<0 or length<0 or offset+length>old.stat().st_size:raise ValueError('Invalid base range')
                        source.seek(offset)
                        while length:
                            data=source.read(min(length,1024*1024));target.write(data);length-=len(data)
                    else:
                        name=piece['blob']
                        if not name.startswith('blob/') or not name[5:].isdigit():raise ValueError('Invalid blob')
                        with archive.open(name) as stream:shutil.copyfileobj(stream,target,1024*1024)
                    if target.tell()>recipe['size']:raise ValueError('Transfer exceeds expected size')
            if output.stat().st_size!=recipe['size'] or digest(output)!=recipe['new_sha256']:
                raise ValueError('Reconstructed EXE checksum mismatch')
        except BaseException:
            output.unlink(missing_ok=True)
            raise


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation',choices=['create','apply']);parser.add_argument('base',type=Path)
    parser.add_argument('input',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args()
    result=create(args.base,args.input,args.output) if args.operation=='create' else apply(args.base,args.input,args.output)
    print(json.dumps(result or {'success':True,'sha256':digest(args.output)}))


if __name__=='__main__':main()

"""Stage the allowlisted atlas overlay; no credentials or user data are read."""
import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'app'))
from core.worldmap.localization import place_dictionary, term_dictionary
from core.worldmap.engine import Components


def stage(output=None):
    output = Path(output) if output else ROOT/'app/build/hub/0.4.1'
    output.mkdir(parents=True, exist_ok=True)
    component = ROOT/'app/build/offline-map/package'
    fingerprint = Components(component/'worldmap.exe', component/'runtime.nut', component/'rules').fingerprint()
    for name in ('validation.json', 'camp-validation.json'):
        report = json.loads((component/name).read_text('utf-8'))
        if not report.get('success') or report['fingerprint'] != fingerprint:
            raise RuntimeError('The current rules have not passed game-reference validation')
    paths = ['web/catalog/urls.py','web/catalog/worldmaps.py','web/catalog/test_worldmaps.py','web/hub/version.py','web/tools/validate_atlas_runtime.py',
        'web/templates/seeds.html','web/templates/seed_detail.html','web/templates/seed_atlas.html',
        'web/static/seeds.css','web/static/seed-atlas.css','web/static/seed-atlas.js',
        'app/core/io_util.py','app/core/paths.py','app/core/item_inspector.py',
        'app/core/seedgen/weapon_rating.py','app/core/seedgen/presentation.py','app/data/item_inspector/catalog.json']
    paths += [p.relative_to(ROOT).as_posix() for p in (ROOT/'app/core/worldmap').glob('*.py')]
    paths += [p.relative_to(ROOT).as_posix() for p in (ROOT/'app/tests/fixtures/worldmap').glob('*.json.gz')]
    payloads = {'patch/'+name:(ROOT/name).read_bytes() for name in paths}
    # Generated directly from BBMOD's existing reviewed dictionaries. Keeping the
    # compact display subset avoids loading the desktop localization editor in a web worker.
    labels = {'terms':{k:v for k,v in term_dictionary().items() if len(k)<=180 and len(v)<=180 and '\n' not in k},
              'places':place_dictionary()}
    payloads['patch/app/data/worldmap/labels.json'] = json.dumps(labels,ensure_ascii=False,separators=(',',':')).encode()
    (ROOT/'app/build/offline-map/web-labels.json').write_bytes(payloads['patch/app/data/worldmap/labels.json'])
    payloads['native/runtime.cpp'] = (ROOT/'app/native/worldmap/runtime.cpp').read_bytes()
    vendor = ROOT/'app/build/offline-map/vendor'
    for folder in ('include','squirrel','sqstdlib'):
        for path in (vendor/folder).glob('*'):
            if path.is_file() and path.suffix in ('.h','.cpp'):
                payloads['native/vendor/'+path.relative_to(vendor).as_posix()] = path.read_bytes()
    payloads['native/vendor/COPYRIGHT'] = (vendor/'COPYRIGHT').read_bytes()
    for name in ('runtime.nut','camps.nut','actors.nut','SQUIRREL-COPYRIGHT'):
        path=component/name
        if path.is_file():payloads['worldmap/'+name]=path.read_bytes()
    for path in (component/'rules').rglob('*'):
        if path.is_file():payloads['worldmap/rules/'+path.relative_to(component/'rules').as_posix()]=path.read_bytes()
    payloads['Dockerfile']=(ROOT/'web/deploy/atlas.Dockerfile').read_bytes()
    manifest={name:hashlib.sha256(data).hexdigest() for name,data in sorted(payloads.items())}
    report={'version':'0.4.1','desktop_version':'0.7.0','windows_reference_fingerprint':fingerprint,'files':manifest}
    payloads['site-patch.json']=json.dumps(report,indent=2).encode()
    archive_path=output/'atlas-source.tar.gz'
    with tarfile.open(archive_path,'w:gz') as archive:
        for name,data in sorted(payloads.items()):
            info=tarfile.TarInfo(name);info.size=len(data);info.mode=0o644
            archive.addfile(info,io.BytesIO(data))
    (output/'site-patch.json').write_text(json.dumps(report,indent=2),'utf-8')
    print(json.dumps({'archive':str(archive_path),'bytes':archive_path.stat().st_size,
                      'sha256':hashlib.sha256(archive_path.read_bytes()).hexdigest(),
                      'files':len(manifest),'terms':len(labels['terms']),'places':len(labels['places'])}))


if __name__=='__main__':stage()

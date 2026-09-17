"""Replace and restart isolated application copies; never launch the game."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.app_updates import Release, RELEASES_URL, prepare_install, restart_environment, sha256_file
from core.version import VERSION


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exe', type=Path, required=True)
    parser.add_argument('--old-exe', type=Path, required=True)
    args = parser.parse_args()
    workspace = ROOT/'build/update-install-check'/uuid.uuid4().hex
    workspace.mkdir(parents=True)
    job = workspace/'cache';job.mkdir()
    target_folder = workspace/'portable & 中文';target_folder.mkdir()
    target = target_folder/'BBMOD.exe'
    source = job/'BBMOD.exe'
    helper = job/'BBMOD-update-helper.exe'
    shutil.copy2(args.exe,source);shutil.copy2(args.exe,helper);shutil.copy2(args.old_exe,target)
    profile = workspace/'profile'
    settings = profile/'BBMOD/settings.json';settings.parent.mkdir(parents=True)
    settings.write_text(json.dumps({'seed_traits':{'required':['trait.huge'],'excluded':[],'match':'all'},
                                    'app_updates':{'automatic':False},'seed_share':{'format':'record'}}),encoding='utf-8')
    settings_before = settings.read_bytes()
    old_hash = sha256_file(target)
    environment = restart_environment()
    environment.update(APPDATA=str(profile),QT_QPA_PLATFORM='offscreen')
    with (workspace/'old.log').open('wb') as log:
        old = subprocess.Popen([str(target),'--selftest'],env=environment,cwd=target_folder,stdout=log,stderr=log,
                               creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    release = Release('v'+VERSION,'新版','本地更新验证','',True,RELEASES_URL+'/tag/v'+VERSION,
                      RELEASES_URL+'/download/v'+VERSION+'/BBMOD.exe',source.stat().st_size,sha256_file(source))
    request = prepare_install(source,release,target=target,parent_pid=old.pid)
    with (workspace/'helper.log').open('wb') as log:
        process = subprocess.run([str(helper),'--apply-update',str(request),'--verify-update'],env=environment,
                                 cwd=job,stdout=log,stderr=log,timeout=140,
                                 creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    assert old.wait(timeout=20)==0
    assert process.returncode==0, (workspace/'helper.log').read_text(encoding='utf-8',errors='replace')
    result = json.loads((job/'result.json').read_text(encoding='utf-8'))
    assert result['status']=='installed'
    assert sha256_file(target)==sha256_file(source)
    assert sha256_file(Path(result['backup']))==old_hash
    assert settings.read_bytes()==settings_before
    restarted = (job/'restarted.log').read_text(encoding='utf-8',errors='replace')
    assert 'version='+VERSION in restarted and 'updater=ready' in restarted
    report = {'game_started':False,'status':'passed','target_version':VERSION,
              'installed_sha256':sha256_file(target),'backup_sha256':old_hash,
              'settings_unchanged':True,'new_version_selftest':True,'parent_exit_wait':True,'evidence':str(workspace)}
    (ROOT/'build/review/update-install-check.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report))

if __name__ == '__main__':
    main()

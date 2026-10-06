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
    parser.add_argument('--silent', action='store_true', help='Validate exit-only replacement without relaunch')
    parser.add_argument('--target-name', default='BBMOD.exe', help='Portable filename before updating; test versioned and legacy backup names')
    parser.add_argument('--source-helper', action='store_true', help='Exercise the working-tree updater with real EXE copies before packaging')
    parser.add_argument('--old-helper', action='store_true', help='Verify upgrading with the updater embedded in the old EXE')
    args = parser.parse_args()
    if args.old_helper and args.source_helper:
        parser.error('--old-helper and --source-helper are mutually exclusive')
    if Path(args.target_name).name != args.target_name or not args.target_name.lower().endswith('.exe'):
        parser.error('--target-name must be an EXE filename without a directory')
    workspace = ROOT/'build/update-install-check'/uuid.uuid4().hex
    workspace.mkdir(parents=True)
    job = workspace/'cache';job.mkdir()
    target_folder = workspace/'portable & 中文';target_folder.mkdir()
    target = target_folder/args.target_name
    source = job/'BBMOD.exe'
    helper = job/'BBMOD-update-helper.exe'
    shutil.copy2(args.exe,source);shutil.copy2(args.old_exe if args.old_helper else args.exe,helper);shutil.copy2(args.old_exe,target)
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
    release = Release('v'+VERSION,'新版','本地更新验证','','-' in VERSION,RELEASES_URL+'/tag/v'+VERSION,
                      RELEASES_URL+'/download/v'+VERSION+'/BBMOD.exe',source.stat().st_size,sha256_file(source))
    request = prepare_install(source,release,target=target,parent_pid=old.pid,restart=not args.silent)
    with (workspace/'helper.log').open('wb') as log:
        command = [str(helper),'--apply-update',str(request)] + ([] if args.silent else ['--verify-update'])
        if args.source_helper:
            command = [sys.executable, str(ROOT/'main.py'), *command[1:]]
        process = subprocess.run(command,env=environment,
                                 cwd=job,stdout=log,stderr=log,timeout=140,
                                 creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    assert old.wait(timeout=20)==0
    assert process.returncode==0, (workspace/'helper.log').read_text(encoding='utf-8',errors='replace')
    result = json.loads((job/'result.json').read_text(encoding='utf-8'))
    assert result['status']=='installed'
    original_target = target
    target = Path(result['target'])
    assert sha256_file(target)==sha256_file(source)
    assert sha256_file(Path(result['backup']))==old_hash
    assert Path(result['backup']).parent == job
    assert Path(result['backup']).suffix == '.bak'
    assert list(target_folder.iterdir()) == [target]
    assert settings.read_bytes()==settings_before
    if args.silent:
        assert result['restart'] is False and not (job/'restarted.log').exists()
    else:
        restarted = (job/'restarted.log').read_text(encoding='utf-8',errors='replace')
        assert 'version='+VERSION in restarted and 'updater=ready' in restarted
    report = {'game_started':False,'status':'passed','target_version':VERSION,
              'installed_sha256':sha256_file(target),'backup_sha256':old_hash,
              'settings_unchanged':True,'new_version_selftest':not args.silent,'silent_no_relaunch':args.silent,
              'parent_exit_wait':True,'original_filename':original_target.name,'installed_filename':target.name,
              'cache_backup':True,'source_helper':args.source_helper,'old_helper':args.old_helper,'evidence':str(workspace)}
    name = 'update-silent-check.json' if args.silent else 'update-install-check.json'
    (ROOT/'build/review'/name).write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report))

if __name__ == '__main__':
    main()

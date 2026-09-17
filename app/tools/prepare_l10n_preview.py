"""Install a validated preview only into the isolated workspace test copy."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from core.cnut import Cnut
from core.l10n import PACKAGE_NAME
from tools.translate_full_catalog import WORK


def main():
    source=WORK/'preview-package'/PACKAGE_NAME
    validation=json.loads((source.parent/'validation.json').read_text(encoding='utf-8'))
    package_hash=hashlib.sha256(source.read_bytes()).hexdigest()
    if validation['package_sha256']!=package_hash or not validation['instructions_unchanged'] or not (validation.get('program_literals_validated') or validation.get('program_literals_unchanged')):
        raise ValueError('测试包尚未通过对应的结构验证。')
    game=WORK/'game-check';data=game/'data'
    assert data.resolve().is_relative_to(WORK.resolve())
    disabled=WORK/'diagnostics-disabled';disabled.mkdir(exist_ok=True)
    old=data/'mod_zz_bbmod_font_smoke.zip'
    if old.exists():
        sha=hashlib.sha256(old.read_bytes()).hexdigest()[:16]
        backup=disabled/(old.stem+'-'+sha+'.zip')
        assert old.resolve().is_relative_to(data.resolve()) and backup.resolve().is_relative_to(disabled.resolve())
        if not backup.exists():shutil.copy2(old,backup)
        if hashlib.sha256(backup.read_bytes()).hexdigest()!=hashlib.sha256(old.read_bytes()).hexdigest():raise ValueError('旧测试文件备份不一致。')
        old.unlink()
    script_name='scripts/states/world_state.cnut'
    script=source.parent/'preview-world-state.cnut'
    with zipfile.ZipFile(source) as z:script.write_bytes(z.read(script_name))
    compiler=str(WORK/'tools/bin/bbsq.exe')
    subprocess.run([compiler,'-d',str(script)],check=True,capture_output=True)
    raw=bytearray(script.read_bytes());original=Cnut(raw);guarded=[]
    for f in original.functions:
        if f['name'] in {'autosave','saveCampaign'}:
            if f['instructions'][-1]!=(0,23,255,0,0):raise ValueError('存档函数格式不受支持。')
            at=f['instructions_start'];raw[at:at+8]=struct.pack('<iBBBB',0,23,255,0,0);guarded.append(f['name'])
    if set(guarded)!={'autosave','saveCampaign'}:raise ValueError('无法保护测试过程中的存档。')
    checked=Cnut(raw)
    for a,b in zip(original.functions,checked.functions):
        assert a['literals']==b['literals']
        assert a['instructions'][1:]==b['instructions'][1:]
        if a['name'] not in guarded:assert a['instructions']==b['instructions']
    script.write_bytes(raw)
    subprocess.run([compiler,'-e',str(script)],check=True,capture_output=True)
    guard=source.parent/'mod_zz_bbmod_preview_guard.zip'
    with zipfile.ZipFile(guard,'w',zipfile.ZIP_DEFLATED) as z:
        z.write(script,script_name)
        z.writestr('BBMOD_PREVIEW_GUARD.json',json.dumps({'package_sha256':package_hash,'script_sha256':hashlib.sha256(script.read_bytes()).hexdigest(),'disabled_functions':guarded,'automatic_campaign_start':False}))
    for p in [source,guard]:
        destination=data/p.name;pending=destination.with_suffix('.pending')
        shutil.copyfile(p,pending)
        if hashlib.sha256(pending.read_bytes()).hexdigest()!=hashlib.sha256(p.read_bytes()).hexdigest():raise ValueError('测试安装校验不一致。')
        pending.replace(destination)
    with zipfile.ZipFile(source) as archive:
        manifest=json.loads(archive.read('BBMOD_L10N.json'))
    stage=('已完成本体与官方 DLC 已提取文本的初译，剧情和用词仍待逐条校对。' if manifest.get('translation_stage')=='complete_draft'
           else '当前仍有缺译，剧情初稿仍待校对。')
    description='BBMOD 独立汉化开发测试\n\n请从桌面的专用测试入口进入，并新建战役。\n此副本加载本项目独立汉化。\n测试不保存进度；'+stage+'\n中文地图字体由专用入口加载。\n普通 Steam 启动入口仍指向原先的游戏。\n'
    (game/'独立测试说明.txt').write_text(description,encoding='utf-8-sig')
    print(json.dumps({'game':str(game),'package_sha256':package_hash,'save_guard':guarded,'automatic_start':False},ensure_ascii=False))


if __name__=='__main__':main()

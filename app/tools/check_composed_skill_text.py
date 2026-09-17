"""Execute packaged tooltip bytecode with offline engine fixtures.

This checks complete, dynamically joined text rather than isolated translation
fragments. No game process, save, or Steam installation is opened or changed.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import zipfile

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
from core.l10n_tokens import validate_translation

WORK = APP/'build/full-l10n'
TARGET = WORK/'skill-text-validation'
FILES = [
    'scripts/config/strings.cnut',
    *('scripts/skills/'+p+'.cnut' for p in (
        'perks/perk_battle_forged', 'perks/perk_nimble',
        'effects/indomitable_effect', 'effects/honor_guard_potion_effect',
        'effects/dazed_effect', 'effects/chilled_effect',
        'actives/gash_skill', 'actives/deathblow_skill',
    )),
]

HARNESS = r'''
::Const <- { UI = { Color = {PositiveValue="#00aa00", NegativeValue="#aa0000", DamageValue="#bb0000"}},
 SkillType={Perk=1,StatusEffect=2,Active=4}, SkillOrder={Perk=1},
 BodyPart={Head=0,Body=1}, ItemSlot={Head=0,Body=1} };
::Math <- { floor=function(v){return ::floor(v).tointeger();}, round=function(v){return ::floor(v+0.5).tointeger();},
 min=function(a,b){return a<b?a:b;}, minf=function(a,b){return a<b?a:b;},
 max=function(a,b){return a>b?a:b;}, abs=function(v){return ::abs(v);}, pow=function(a,b){return ::pow(a,b);} };
::fixture <- {armor=[300,300], fat=[-5,-10], specialized=false};
::props <- {IsSpecializedInSwords=false};
::actor <- {
 getArmor=function(part){return ::fixture.armor[part];},
 getCurrentProperties=function(){::props.IsSpecializedInSwords=::fixture.specialized;return ::props;},
 getItems=function(){return {getItemAtSlot=function(slot){
   local f=::fixture.fat[slot]; return {getStaminaModifier=function(){return f;}};
 }};}
};
::container <- {getActor=function(){return ::actor;}};
::fixtureBase <- {
 getName=function(){return this.m.Name;},
 getDescription=function(){return this.m.Description;},
 getContainer=function(){return ::container;},
 getDefaultTooltip=function(){return [];}
};
::fixtureBase.setdelegate(getroottable());
::inherit <- function(parent,members){
 members.setdelegate(::fixtureBase);
 members.m.setdelegate({_set=function(k,v){this.rawset(k,v);}});
 members.skill <- {getTooltip=function(){return [];}};
 return members;
};
::emit <- function(group,key,value){
 local encoded=""; foreach(byte in value) encoded+=format("%02x",byte & 255);
 print(group+"|"+key+"|"+encoded+"\n");
};
::tooltip <- function(key,obj,create=true){
 if(create) obj.create();
 foreach(i,row in obj.getTooltip()) emit("tooltip",key+"."+i,row.text);
};
'''


def quote(path):
    return json.dumps(str(path.resolve()).replace('\\','/'))


def run(root, label):
    code = HARNESS + 'dofile('+quote(root/FILES[0])+');\n'
    code += '''
foreach(k,v in Const.Strings.PerkName) emit("name",k,v);
foreach(k,v in Const.Strings.PerkDescription) emit("description",k,v);
'''
    for file in FILES[1:]:
        code += 'dofile('+quote(root/file)+');\n'
    code += '''
tooltip("battle_forged.600",perk_battle_forged);
::fixture.armor=[0,0]; tooltip("battle_forged.0",perk_battle_forged);
tooltip("nimble.15",perk_nimble);
::fixture.fat=[-30,-30]; tooltip("nimble.60",perk_nimble);
tooltip("indomitable",indomitable_effect);
tooltip("honor_guard",honor_guard_potion_effect);
tooltip("dazed",dazed_effect);
tooltip("chilled",chilled_effect);
tooltip("gash.normal",gash_skill,false);
::fixture.specialized=true; tooltip("gash.mastery",gash_skill,false);
tooltip("deathblow",deathblow_skill,false);
print("BBMOD_COMPOSED_PASS\\n");
'''
    harness = TARGET/(label+'.nut')
    harness.write_text(code, encoding='utf8')
    result = subprocess.run([str(WORK/'tools/bin/sq.exe'),str(harness)], capture_output=True, timeout=20)
    output = (result.stdout+result.stderr).decode('utf8',errors='replace')
    (TARGET/(label+'-output.txt')).write_text(output,encoding='utf8')
    assert result.returncode == 0 and 'BBMOD_COMPOSED_PASS' in output and not result.stderr, output[-2500:]
    rows = {}
    for line in output.splitlines():
        if '|' not in line:
            continue
        group, key, raw = line.split('|',2)
        rows[group+'.'+key] = bytes.fromhex(raw).decode('utf8')
    return rows


def main():
    TARGET.mkdir(parents=True,exist_ok=True)
    package = WORK/'preview-package/mod_bbmod_zhcn.zip'
    patched = TARGET/'patched'
    with zipfile.ZipFile(package) as archive:
        for name in FILES:
            file=patched/name
            assert file.resolve().is_relative_to(patched.resolve())
            file.parent.mkdir(parents=True,exist_ok=True)
            file.write_bytes(archive.read(name))
    subprocess.run([str(WORK/'tools/bin/bbsq.exe'),'-d',*(str(patched/n) for n in FILES)],
                   check=True,capture_output=True,timeout=30)
    original=run(WORK/'plain','original')
    current=run(patched,'translated')
    assert original.keys()==current.keys()
    problems={key:issues for key,source in original.items()
              if (issues:=validate_translation(source,current[key]))}
    assert not problems, problems
    plain={k:re.sub(r'\[/?color(?:=[^\]]+)?\]','',v) for k,v in current.items()}
    expected={
        'tooltip.battle_forged.600.0':'承受原本的70%护甲伤害',
        'tooltip.nimble.15.0':'承受原本的40%生命值伤害',
        'tooltip.indomitable.2':'承受原本的50%伤害',
    }
    for key,value in expected.items():
        assert plain[key]==value,(key,plain[key])
    assert '轻灵' in plain['tooltip.nimble.60.0']
    assert '久经战阵' in plain['tooltip.battle_forged.0.0']
    assert '减免范围为25%至50%' in plain['tooltip.honor_guard.2']
    assert '33%致伤门槛减免' in plain['tooltip.gash.normal.1']
    assert '50%致伤门槛减免' in plain['tooltip.gash.mastery.1']
    assert '额外提高+25%' in plain['description.Duelist']
    assert '生命值伤害最多降低60%' in plain['description.Nimble']
    assert '超过15后，减伤效果' in plain['description.Nimble']
    assert '每次攻击未命中敌人时叠加一次' in plain['description.FastAdaption']
    assert '每次攻击落空后' not in plain['description.FastAdaption']
    assert '行动点受到-1修正' in plain['description.Pathfinder']
    assert '效果还将持续2回合。' in plain['tooltip.dazed.1']
    assert '效果还将持续2回合。' in plain['tooltip.chilled.1']
    assert '降低-' not in '\n'.join(plain.values())
    report={
        'package_sha256':hashlib.sha256(package.read_bytes()).hexdigest(),
        'full_catalog_sha256':hashlib.sha256((APP/'localization/full_catalog.json').read_bytes()).hexdigest(),
        'game_started':False, 'game_acceptance':'not_run_user_requested_offline_only',
        'source':'actual original and packaged bytecode executed in offline Squirrel with engine fixtures',
        'files':len(FILES), 'rendered_texts':len(current),
        'native_execution':'passed', 'numbers_variables_markup':'passed',
        'damage_percentages':'passed', 'names_and_composed_tooltips':'passed',
        'texts':{key:{'source':original[key],'translation':current[key],'plain':plain[key]} for key in sorted(current)},
    }
    (TARGET/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({k:v for k,v in report.items() if k!='texts'},ensure_ascii=False))


if __name__=='__main__':
    main()

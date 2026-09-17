"""Build a clearly marked incomplete preview from validated independent drafts."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import re
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from core import l10n
from core.full_l10n import write_full_patches
from core.l10n_tokens import validate_translation, VARIABLE, STRUCTURE, restore_template_separators, ALLOWED_UI_WORDS
from tools.assemble_full_catalog import load_drafts,clean_prose
from tools.translate_full_catalog import WORK,load_terms,job_parts,HALLUCINATION

ALLOWED_WORDS=ALLOWED_UI_WORDS


def preview_catalog():
    inventory=json.loads((WORK/'inventory.json').read_text(encoding='utf-8'))
    terms=load_terms();drafts=load_drafts();entries={}
    for key,entry in inventory['entries'].items():
        translated=[];reviewed=True;missing=False
        for fixed,part in job_parts(entry['source'],terms):
            if fixed: translated.append(part)
            elif part in drafts:
                reviewed=False
                translated.append(clean_prose(part,drafts[part]['translation']))
            else:
                missing=True;break
        if missing: continue
        value=restore_template_separators(entry['source'], ''.join(translated))
        grammar=entry['source'].strip().casefold() in {'a','an','the','s'}
        if not value.strip() and not grammar: continue
        if validate_translation(entry['source'],value) or HALLUCINATION.search(value):continue
        credited=any(c['file']=='scripts/config/credits.cnut' for c in entry['contexts'])
        words=re.findall(r'[A-Za-z][A-Za-z\'-]*',VARIABLE.sub('',STRUCTURE.sub('',value)))
        if words and not credited and not all(w in ALLOWED_WORDS for w in words):continue
        entries[key]={**entry,'translation':value,'status':'reviewed' if reviewed else 'machine_draft'}
        if not value.strip():entries[key]['omit_grammar']=True
    # Do not silently drop a newly reviewed paragraph and ship its English
    # source again (for example, merely because it mentions the Escape key).
    onboarding={}
    for name in ['reviewed_onboarding.json','reviewed_equipment_contracts.json']:
        onboarding.update(json.loads((ROOT/'localization'/name).read_text(encoding='utf-8'))['terms'])
    for key,entry in inventory['entries'].items():
        if entry['source'] in onboarding and (key not in entries or entries[key]['translation']!=onboarding[entry['source']]):
            raise ValueError('已校对的文本未能进入测试包：'+entry['source'][:100])
    files={}
    for name,spec in inventory['files'].items():
        patches=[p for p in spec['patches'] if p[2] in entries]
        if patches:files[name]={**spec,'patches':patches}
    return {**inventory,'entries':entries,'files':files,'inventory_entry_count':len(inventory['entries']),
            'translation_stage':'partial_preview','native_map_font':'pending'}


def main():
    if l10n.load_full_catalog():
        raise ValueError('完整目录已存在，请使用正式构建流程。')
    catalog=preview_catalog()
    output=WORK/'preview-package';output.mkdir(exist_ok=True)
    base=output/'ui-base.zip'
    game=WORK/'game-check'
    l10n.build_localization(game,{},base)
    final=output/l10n.PACKAGE_NAME
    pending=final.with_suffix('.pending')
    try:
        with zipfile.ZipFile(base) as source,zipfile.ZipFile(pending,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as target:
            manifest=json.loads(source.read(l10n.BRAND_META))
            for name in source.namelist():
                if name not in {l10n.BRAND_META,l10n.UI_ROOT+'dictionary.js'}:target.writestr(name,source.read(name))
            # A display value may share its constant with a program key. Keep
            # that constant unchanged and translate its rendered text instead.
            dictionary={s.strip():t.strip() for s,t in load_terms().items() if s.strip() and t.strip()}
            target.writestr(l10n.UI_ROOT+'dictionary.js','window.BBMOD_DICTIONARY = '+json.dumps(dictionary,ensure_ascii=True)+';\n')
            manifest.update(write_full_patches(target,game,catalog,{}))
            manifest.update({'requires_bbmod_launcher':True,'inventory_entry_count':catalog['inventory_entry_count'],
                'scope':f"开发测试包：{len(catalog['entries'])}/{catalog['inventory_entry_count']} 条正文目录已接入，仍有缺译；剧情初稿待校对，地图字体待实机确认",
                'game_acceptance':'pending','preview_only':True})
            target.writestr(l10n.BRAND_META,json.dumps(manifest,ensure_ascii=False,indent=2))
            target.writestr('独立开发测试说明.txt',manifest['scope']+'。\n请使用“BBMOD 独立汉化测试”专用入口。\n')
        with zipfile.ZipFile(pending) as check:
            if check.testzip():raise ValueError('测试包校验失败。')
        pending.replace(final)
    finally:
        if pending.exists():pending.unlink()
    print(json.dumps({'output':str(final),'included':len(catalog['entries']),'total':catalog['inventory_entry_count'],'files':len(catalog['files']),
                      'sha256':hashlib.sha256(final.read_bytes()).hexdigest()},ensure_ascii=False))


if __name__=='__main__':main()

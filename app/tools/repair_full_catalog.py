"""Retry malformed draft segments, preserving a resumable repair ledger."""
from __future__ import annotations
import argparse
import ctypes
from functools import lru_cache
import json
import os
from pathlib import Path
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.l10n_tokens import VARIABLE, NUMBER, validate_translation, ALLOWED_UI_WORDS
from core.game import is_game_running
from tools.translate_full_catalog import WORK, load_terms, job_parts, prepare, restore, content_warnings
from tools.assemble_full_catalog import load_drafts, clean_prose

PROTECTED = re.compile(VARIABLE.pattern + '|' + NUMBER.pattern)
NAMES = [('John','约翰'),('Robert','罗伯特'),('Henry','亨利'),('William','威廉'),('George','乔治'),('Thomas','托马斯'),('Edward','爱德华'),('Philip','菲利普'),('Richard','理查德'),('Arthur','亚瑟'),('James','詹姆斯'),('Albert','阿尔伯特'),('David','大卫'),('Peter','彼得'),('Paul','保罗'),('Charles','查尔斯'),('Oliver','奥利弗'),('Oscar','奥斯卡'),('Victor','维克托'),('Walter','沃尔特'),('Michael','迈克尔'),('Martin','马丁'),('Daniel','丹尼尔'),('Andrew','安德鲁')]
METHOD = 'local-madlad400-3b-int8_bfloat16-sentence-v3'
GAME_NAMES = ['Lindwurm', 'Lindwurms', 'Unhold', 'Unholds', 'Nachzehrer', 'Nachzehrers',
              'Schrat', 'Schrats', 'Hexe', 'Hexen', 'Alp', 'Alps', 'Ifrit', 'Ifrits',
              'Webknecht', 'Webknechts', 'Direwolf', 'Direwolves', 'Wiederganger', 'Wiedergangers',
              'Davkul', 'Vizier']
GAME_TOKEN = re.compile(VARIABLE.pattern + r'|\b(?:' + '|'.join(sorted(GAME_NAMES,key=len,reverse=True)) + r')\b',re.I)

@lru_cache(maxsize=1)
def game_terms():
    terms=load_terms()
    result={name.casefold():terms[name] for name in GAME_NAMES if name in terms}
    result.setdefault('direwolves',terms['Direwolf'])
    result.setdefault('wiedergangers',terms['Wiederganger'])
    result.setdefault('vizier','维齐尔')
    return result

def natural(source):
    available = [(en,zh) for en,zh in NAMES if not re.search(r'\b'+en+r'\b',source,re.I)]
    tokens = []
    def token(m):
        en,zh = available[len(tokens)]
        value=m.group() if VARIABLE.fullmatch(m.group()) else game_terms().get(m.group().casefold(),m.group())
        tokens.append((value,en,zh))
        return en
    text = GAME_TOKEN.sub(token,source.strip())
    return prepare(text)[0],tokens

def natural_restore(text,tokens):
    # Common real names carry grammatical context without opaque-token decoding.
    # These temporary names are never written into a valid game translation.
    for source,en,zh in tokens:
        variants = [zh,en]
        if en == 'Thomas': variants.append('汤玛斯')
        if en == 'Victor': variants.append('维克多')
        regex = re.compile('|'.join(re.escape(v) for v in variants),re.I)
        if len(regex.findall(text)) != 1: return None
        text = regex.sub(lambda m: source,text)
    return text

def problems(source, text):
    result = validate_translation(source, clean_prose(source,text))
    result.extend(content_warnings(source, text))
    if re.search('[A-Za-z]', VARIABLE.sub('', source)) and not re.search('[\u3400-\u9fff]', text):
        result.append('尚无中文译文')
    if any(word not in ALLOWED_UI_WORDS for word in re.findall(r"[A-Za-z][A-Za-z'-]*", VARIABLE.sub('',text))):
        result.append('仍有未译英文')
    return result

def masked(source):
    protected = []
    def token(m):
        protected.append(m.group())
        return f'ZXQ{len(protected)-1}ZX'
    text = PROTECTED.sub(token, source.strip())
    text = prepare(text)[0]
    return text, protected

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--prepare-only', action='store_true')
    ap.add_argument('--batch', type=int, default=8)
    ap.add_argument('--compute-type', choices=['int8_bfloat16','int8_float32'], default='int8_bfloat16')
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--cooldown', type=float, default=0.4)
    args = ap.parse_args()
    if os.name == 'nt':
        ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)
    terms = load_terms()
    inventory = json.loads((WORK/'inventory.json').read_text(encoding='utf-8'))
    jobs = {s for e in inventory['entries'].values() for fixed,s in job_parts(e['source'],terms) if not fixed}
    drafts = load_drafts()
    pending = []
    for source in sorted(jobs,key=lambda s:(len(s),s)):
        row = drafts.get(source)
        trimmed_retry = row and row.get('method') == 'local-madlad400-3b-int8' and source != source.strip()
        legacy_variable = row and VARIABLE.search(source) and row.get('method') != METHOD
        if row is None or problems(source,row['translation']) or trimmed_retry or legacy_variable:
            pending.append(source)
    (WORK/'repair-jobs.json').write_text(json.dumps(pending,ensure_ascii=False),encoding='utf-8')
    print(json.dumps({'repair_jobs':len(pending),'characters':sum(map(len,pending))}),flush=True)
    if args.prepare_only: return
    if args.limit: pending = pending[:args.limit]
    while is_game_running():
        print('游戏正在运行，译文计算保持暂停。',flush=True)
        time.sleep(10)
    dll = Path(sys.prefix)/'Lib/site-packages/nvidia/cublas/bin'
    dll_handle = os.add_dll_directory(str(dll))
    ctypes.WinDLL(str(dll/'cublas64_12.dll'))
    import ctranslate2
    import sentencepiece as spm
    from opencc import OpenCC
    simplified = OpenCC('t2s')
    tokenizer = spm.SentencePieceProcessor(model_file=str(WORK/'madlad/spiece.model'))
    translator = ctranslate2.Translator(str(WORK/'madlad'),device='cuda',compute_type=args.compute_type,inter_threads=1,intra_threads=4)
    started = time.time()
    def translate(batch):
        output = translator.translate_batch([tokenizer.encode('<2zh> '+s,out_type=str)+['</s>'] for s in batch],beam_size=3,max_decoding_length=512,disable_unk=True,repetition_penalty=1.02,no_repeat_ngram_size=8)
        return [simplified.convert(tokenizer.decode(r.hypotheses[0])) for r in output]
    with (WORK/'repaired-drafts.jsonl').open('a',encoding='utf-8',buffering=1) as stream:
        for offset in range(0,len(pending),args.batch):
            if (WORK/'pause-translation').exists():
                print('已按暂停标记停止，已完成的译文均已保存。',flush=True)
                break
            if is_game_running():
                translator.unload_model()
                print('检测到游戏启动，已释放显存，等待游戏关闭。',flush=True)
                while is_game_running(): time.sleep(5)
                translator.load_model()
                print('游戏已关闭，恢复译文计算。',flush=True)
            batch = pending[offset:offset+args.batch]
            prepared = [natural(s) for s in batch]
            output = translate([s for s,_ in prepared])
            for source,raw,(_,tokens) in zip(batch,output,prepared):
                value = natural_restore(raw,tokens)
                if value is not None: value=clean_prose(source,value)
                issues = ['变量恢复失败'] if value is None else problems(source,value)
                method=METHOD.replace('int8_bfloat16',args.compute_type)
                row = {'source':source,'translation':value if value is not None else raw,'issues':issues,'method':method,'status':'machine_draft'}
                stream.write(json.dumps(row,ensure_ascii=False)+'\n')
            if offset == 0 or (offset+len(batch)) % 120 == 0 or offset+len(batch)==len(pending):
                print(json.dumps({'repaired_jobs':offset+len(batch),'remaining':len(pending)-offset-len(batch),'seconds':round(time.time()-started,1)}),flush=True)
            if args.cooldown > 0: time.sleep(args.cooldown)

if __name__ == '__main__': main()

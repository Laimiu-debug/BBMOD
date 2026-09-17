"""Generate resumable, explicitly marked local machine drafts.

No API key, network translation, or third-party game translation corpus is used.
The large model stays in build/ and is not a runtime dependency of BBMOD.
"""
from __future__ import annotations

import argparse
from collections import Counter
import ctypes
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.l10n_tokens import VARIABLE, NUMBER, parts, validate_translation

WORK = ROOT / 'build/full-l10n'
HALLUCINATION = re.compile('小行星|星际迷航|星球大战|星际大战|超级机器人大战|魔法少女小圆|刀剑神域|维基百科|世界杯|超级英雄：|侯龙涛|珺梅|文龙|白素贞|发送编修|<unk>|�')

# These specific added settings/body details appeared in unrelated model output.
# The original narrative may legitimately contain them, so check its wording too.
CONTENT_ANCHORS = [
    (r'厨房', r'kitchen|cook|galley'),
    (r'浴室|淋浴', r'bath|shower|wash'),
    (r'沙发', r'couch|sofa|settee'),
    (r'车外|电视', r'carriage|wagon|cart|television'),
    (r'餐厅', r'din|eat|restaurant|tavern|hall'),
    (r'阴户|阴道|阴蒂|小穴|肉棒|龟头', r'vagina|vulva|clitoris|penis|cock|cunt|fuck|sex|whor'),
    (r'鸡巴|阴茎', r'\bcock\b|\bdick\b|penis|phall|manhood|member|groin|loins|crotch|between.{0,20}legs|fuck|sex'),
    (r'乳房|乳头|奶子', r'breast|nipple|\btits?\b|bosom|teat|udder|chest|bust|cleavage|boob|milk|nurs'),
    (r'妈妈|女儿|老公', r'mother|mom|daughter|girl|husband|dad|parent|wife|family'),
]


def content_warnings(source, translation):
    result = []
    if HALLUCINATION.search(translation):
        result.append('出现与游戏语境无关的内容')
    for chinese, english in CONTENT_ANCHORS:
        if re.search(chinese, translation) and not re.search(english, source, re.I):
            result.append('译文增加了原句没有的场景或身体细节')
            break
    return result


def load_terms():
    base = json.loads((ROOT / 'localization/catalog.json').read_text(encoding='utf-8'))
    terms = {s: t for g in base['groups'].values() for s, t in g.items()}
    terms.update(json.loads((ROOT / 'localization/reviewed_terms.json').read_text(encoding='utf-8'))['terms'])
    terms.update(json.loads((ROOT / 'localization/reviewed_names.json').read_text(encoding='utf-8'))['terms'])
    terms.update(json.loads((ROOT / 'localization/reviewed_fragments.json').read_text(encoding='utf-8'))['terms'])
    terms.update(json.loads((ROOT / 'localization/reviewed_initial.json').read_text(encoding='utf-8'))['terms'])
    terms.update(json.loads((ROOT / 'localization/reviewed_credits.json').read_text(encoding='utf-8'))['terms'])
    terms.update(json.loads((ROOT / 'localization/reviewed_onboarding.json').read_text(encoding='utf-8'))['terms'])
    terms.update(json.loads((ROOT / 'localization/reviewed_equipment_contracts.json').read_text(encoding='utf-8'))['terms'])
    terms.update(json.loads((ROOT / 'localization/reviewed_refinement.json').read_text(encoding='utf-8'))['terms'])
    for source, value in list(terms.items()):
        if source.startswith(('the ', 'The ')):
            terms['the ' + source[4:]] = value
            terms['The ' + source[4:]] = value
    terms.update({'a': '', 'an': '', 'the': '', "'s": '的', 'all': '全部', '(x': '（×', '1st': '第1', '2nd': '第2', '3rd': '第3', '4th': '第4', '5th': '第5', '6th': '第6', '7th': '第7', '8th': '第8', '9th': '第9', 'ART': '美术', 'JS': '界面脚本', 'SQ': '游戏脚本'})
    terms.update({'A': '', 'An': '', 'The': ''})
    # Narrative fragments often include a leading space for concatenation.
    # fixed_text looks up a trimmed fragment, so keep a matching reviewed key.
    terms.update({source.strip(): value.strip() for source, value in list(terms.items()) if source.strip()})
    inventory = WORK / 'inventory.json'
    if inventory.exists():
        for entry in json.loads(inventory.read_text(encoding='utf-8'))['entries'].values():
            source = entry['source']
            match = re.fullmatch(r'(%random(?:southern)?name%) (.+)', source)
            if match and match[2] in terms:
                terms[source] = terms[match[2]] + '·' + match[1]
    return terms


def split_sentence(text, limit=250):
    # Keep source punctuation and spacing in the job rather than removing it.
    sentences = re.split(r'(?<=[.!?;])(?=\s+)', text)
    result = []
    for sentence in sentences:
        # MADLAD is a sentence translator. Joining unrelated sentences here
        # caused it to omit paragraph endings despite passing token checks.
        while len(sentence) > limit:
            boundaries = list(re.finditer(r'[,;:]\s+', sentence[:limit]))
            cut = boundaries[-1].end()-1 if boundaries and boundaries[-1].start()>limit//3 else sentence.rfind(' ', 0, limit)
            if cut <= 0:
                cut = limit
            result.append(sentence[:cut])
            sentence = sentence[cut:]
        if sentence:
            result.append(sentence)
    return result


def fixed_text(source, terms):
    if source in terms:
        return terms[source]
    text = source.strip()
    if text in terms:
        return source.replace(text, terms[text], 1)
    subject = re.fullmatch(r'([.,]?\s*)(%[A-Za-z0-9_]+%) (.+)', text)
    if subject and subject[3] in terms:
        value = subject[1].replace('.', '。').replace(',', '，') + subject[2] + terms[subject[3]]
        return source.replace(text, value, 1)
    article = re.fullmatch(r'[Tt]he (%[A-Za-z0-9_]+%)([.!?]?)', text)
    if article:
        value = article[1] + {'.':'。', '!':'！', '?':'？', '':''}[article[2]]
        return source.replace(text, value, 1)
    travel = re.fullmatch(r'(Return to|Travel to|Back to|Welcome to the) (%[A-Za-z0-9_]+%)([.!?]?)', text)
    if travel:
        value = {'Return to':'返回', 'Travel to':'前往', 'Back to':'返回', 'Welcome to the':'欢迎加入'}[travel[1]] + travel[2] + {'.':'。','!':'！','?':'？','':''}[travel[3]]
        return source.replace(text,value,1)
    return None

def job_parts(source, terms):
    fixed = fixed_text(source, terms)
    if fixed is not None:
        return [(True, fixed)]
    result = []
    for structural, value in parts(source):
        if structural or not re.search('[A-Za-z]', VARIABLE.sub('', value)):
            result.append((True, value))
        elif fixed_text(value, terms) is not None:
            result.append((True, fixed_text(value, terms)))
        else:
            for s in split_sentence(value):
                fixed = fixed_text(s,terms)
                result.append((True,fixed) if fixed is not None else (not re.search('[A-Za-z]',VARIABLE.sub('',s)),s))
    return result


def prepare(text):
    protected = []
    def token(match):
        protected.append(match.group())
        return f'ZXQ{len(protected)-1}ZX'
    s = VARIABLE.sub(token, text.strip())
    s = re.sub(r'\bsellswords\b', 'mercenaries', s, flags=re.I)
    s = re.sub(r'\bsellsword\b', 'mercenary', s, flags=re.I)
    # Company in this game's narrative normally means the mercenary company.
    s = re.sub(r'\bthe company\b', 'the mercenary troop', s, flags=re.I)
    s = re.sub(r'\byour company\b', 'your mercenary troop', s, flags=re.I)
    s = re.sub(r'\bmercenary company\b', 'mercenary troop', s, flags=re.I)
    if not re.search(r'\b(ship|boat|sailor|vessel|harbor|harbour)\b', s, re.I):
        s = re.sub(r'\bcaptain\b', 'commander', s, flags=re.I)
    # Numbers are validated after inference; don't mask them, which erases the
    # linguistic context of percentages and level references for the model.
    return s, protected


def restore(text, protected):
    text = re.sub(r'Z\s*X\s*Q\s*(\d+)\s*Z\s*X', lambda m: f'ZXQ{m[1]}ZX', text, flags=re.I)
    expected = Counter(f'ZXQ{i}ZX' for i in range(len(protected)))
    if Counter(re.findall(r'ZXQ\d+ZX', text)) != expected:
        return None
    for i, value in enumerate(protected):
        text = text.replace(f'ZXQ{i}ZX', value)
    return text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--prepare-only', action='store_true')
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--batch', type=int, default=24)
    ap.add_argument('--compute-type', default='int8_float32')
    ap.add_argument('--device', choices=['cpu', 'cuda'], default='cuda')
    args = ap.parse_args()
    inventory = json.loads((WORK / 'inventory.json').read_text(encoding='utf-8'))
    terms = load_terms()
    sources = sorted({s for e in inventory['entries'].values() for fixed, s in job_parts(e['source'], terms) if not fixed}, key=lambda s: (len(s), s))
    (WORK / 'jobs.json').write_text(json.dumps(sources, ensure_ascii=False), encoding='utf-8')
    print(json.dumps({'entries': len(inventory['entries']), 'jobs': len(sources), 'characters': sum(map(len, sources))}), flush=True)
    if args.prepare_only:
        return
    cache_path = WORK / 'machine-drafts.jsonl'
    cached = {}
    if cache_path.exists():
        for line in cache_path.read_text(encoding='utf-8').splitlines():
            row = json.loads(line)
            cached[row['source']] = row
    pending = [s for s in sources if s not in cached]
    if args.limit:
        pending = pending[:args.limit]
    if args.device == 'cuda':
        dll = Path(sys.prefix) / 'Lib/site-packages/nvidia/cublas/bin'
        dll_handle = os.add_dll_directory(str(dll))
        ctypes.WinDLL(str(dll / 'cublas64_12.dll'))
    import ctranslate2
    import sentencepiece as spm
    from opencc import OpenCC
    simplified = OpenCC('t2s')
    model = WORK / 'madlad'
    tokenizer = spm.SentencePieceProcessor(model_file=str(model / 'spiece.model'))
    translator = ctranslate2.Translator(str(model), device=args.device, compute_type=args.compute_type if args.device == 'cuda' else 'int8', inter_threads=1, intra_threads=4)
    started = time.time()
    with cache_path.open('a', encoding='utf-8', buffering=1) as stream:
        for offset in range(0, len(pending), args.batch):
            batch = pending[offset:offset + args.batch]
            prepared = [prepare(s) for s in batch]
            inputs = [tokenizer.encode('<2zh> ' + s, out_type=str) + ['</s>'] for s, _ in prepared]
            if any(len(s) > 510 for s in inputs):
                raise ValueError('Source exceeds the checked model limit')
            output = translator.translate_batch(inputs, beam_size=3, max_decoding_length=512, repetition_penalty=1.02, no_repeat_ngram_size=8)
            for source, item, (input_text, protected) in zip(batch, output, prepared):
                raw = simplified.convert(tokenizer.decode(item.hypotheses[0]))
                value = restore(raw, protected)
                issues = ['剧情变量未完整保留'] if value is None else validate_translation(source, value)
                if value is not None and not re.search(r'[\u3400-\u9fff]', value) and re.search('[A-Za-z]', VARIABLE.sub('', source)):
                    issues.append('需要核对未译专名')
                row = {'source': source, 'translation': value if value is not None else raw, 'issues': issues, 'method': 'local-madlad400-3b-int8', 'status': 'machine_draft'}
                stream.write(json.dumps(row, ensure_ascii=False) + '\n')
            count = offset + len(batch)
            if offset == 0 or count % (args.batch * 10) == 0 or count == len(pending):
                print(json.dumps({'translated_jobs': count, 'remaining_jobs': len(pending) - count, 'seconds': round(time.time() - started, 1)}), flush=True)
    print('Draft generation finished; run terminology and format review before packaging.', flush=True)


if __name__ == '__main__':
    main()

"""Assemble independent drafts and require format QA before publication."""
from __future__ import annotations
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.l10n_tokens import VARIABLE, STRUCTURE, validate_translation, restore_template_separators, ALLOWED_UI_WORDS
from tools.translate_full_catalog import WORK, load_terms, job_parts, content_warnings


def load_drafts():
    result = {}
    for name in ['machine-drafts.jsonl', 'repaired-drafts.jsonl']:
        path = WORK / name
        if not path.exists():
            continue
        for line in path.read_text(encoding='utf-8').splitlines():
            row = json.loads(line)
            result[row['source']] = row
    return result


def clean_prose(source, text):
    # Apply only where the English unambiguously refers to the mercenary band.
    if re.search(r'\bcompany\b', source, re.I):
        text = re.sub('(?:雇佣军|雇佣兵|佣兵|雇佣)(?:公司|乐队|团队|队伍|军队|部队|兵团|团)|雇佣军队|佣兵团|佣兵队伍|雇佣兵团', '战团', text)
    if re.search(r'\bcaptain\b', source, re.I) and not re.search(r'\b(ship|boat|sailor|vessel|harbor|harbour)\b', source, re.I):
        text = text.replace('船长', '团长').replace('指挥官', '团长')
    # Chinese prose has no spaces between Chinese characters or punctuation.
    text = re.sub(r'(?<=[\u3400-\u9fff]) +(?=[\u3400-\u9fff。，！？；：])', '', text)
    text = re.sub(r'(?<=[，。！？；：]) +(?=[\u3400-\u9fff])', '', text)
    text = re.sub(r'(?<=[\u3400-\u9fff]),(?=[\u3400-\u9fff ])', '，', text)
    text = re.sub(r'(?<=\d)\s+[%％]', '%', text)
    text = re.sub(r'(?<=\d)％', '%', text)
    # Keep spelled-out quantities spelled out. This accepts equivalent wording
    # while leaving unexpected new numeric values visible to the format check.
    spelled = [('one hundred','100','一百'),('two hundred','200','两百'),('three hundred','300','三百'),('one thousand','1000','一千'),
               ('fourteen','14','十四'),('thirteen','13','十三'),('twelve','12','十二'),('eleven','11','十一'),('twenty','20','二十'),
               ('ninety','90','九十'),('fifty','50','五十'),('ten','10','十'),('nine','9','九'),('eight','8','八'),('seven','7','七'),
               ('six','6','六'),('five','5','五'),('four','4','四'),('three','3','三'),('two','2','两'),('one','1','一')]
    fragments = re.split('('+VARIABLE.pattern+')',text)
    for index,fragment in enumerate(fragments):
        if VARIABLE.fullmatch(fragment): continue
        for en,number,zh in spelled:
            if re.search(r'\b'+en.replace(' ',r'[- ]')+r'\b',source,re.I) and not re.search(r'(?<!\d)'+number+r'(?!\d)',source):
                fragment = re.sub(r'(?<![\dA-Za-z_])'+number+r'(?![\dA-Za-z_])',zh,fragment)
        fragments[index] = fragment
    text = ''.join(fragments)
    return text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--publish', action='store_true')
    args = ap.parse_args()
    inventory = json.loads((WORK / 'inventory.json').read_text(encoding='utf-8'))
    terms = load_terms()
    drafts = load_drafts()
    missing, invalid, latin = {}, [], []
    states = Counter()
    for key, entry in inventory['entries'].items():
        source = entry['source']
        translated = []
        reviewed = True
        segment_issues = []
        for fixed, part in job_parts(source, terms):
            if fixed:
                translated.append(part)
                continue
            reviewed = False
            draft = drafts.get(part)
            if draft is None:
                missing[part] = key
                continue
            if any('变量' in p for p in draft.get('issues', [])):
                segment_issues.append('正文片段的变量或游戏专名恢复失败')
            segment_issues.extend(content_warnings(part, draft['translation']))
            translated.append(clean_prose(part, draft['translation']))
        value = restore_template_separators(source, ''.join(translated))
        entry['translation'] = value
        entry['status'] = 'reviewed' if reviewed else 'machine_draft'
        states[entry['status']] += 1
        if not value.strip() and source.strip().casefold() in {'a', 'an', 'the', 's'}:
            entry['omit_grammar'] = True
        elif not value.strip():
            invalid.append({'key': key, 'source': source, 'translation': value, 'issues': ['缺少译文']})
        problems = validate_translation(source, value)
        problems.extend(sorted(set(segment_issues)))
        if problems:
            invalid.append({'key': key, 'source': source, 'translation': value, 'issues': problems})
        plain = VARIABLE.sub('', STRUCTURE.sub('', value))
        words = re.findall(r'[A-Za-z][A-Za-z\'-]*', plain)
        credited = any(c['file'] == 'scripts/config/credits.cnut' for c in entry['contexts'])
        if credited:
            entry['preserved_attribution'] = True
        if words and not credited and not all(word in ALLOWED_UI_WORDS for word in words):
            latin.append({'key': key, 'source': source, 'translation': value, 'words': words, 'contexts': entry['contexts']})
    report = {'entries': len(inventory['entries']), 'files': len(inventory['files']), 'states': dict(states), 'missing_jobs': len(missing),
              'invalid_entries': len(invalid), 'latin_entries': len(latin), 'missing': missing, 'invalid': invalid, 'latin': latin}
    (WORK / 'translation-review.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    place_file = ROOT / 'localization/place_names.json'
    geographic = set(json.loads(place_file.read_text(encoding='utf8'))['name_keys']) if place_file.exists() else set()
    prose = [entry for key, entry in inventory['entries'].items() if key not in geographic]
    pending_review = sum(entry['status'] != 'reviewed' for entry in prose)
    review_complete = not (pending_review or missing or invalid or latin)
    editorial_review = {
        'status': 'complete' if review_complete else 'in_progress',
        'scope': 'base_game_and_official_dlc_non_geographic_text',
        'non_geographic_entries': len(prose),
        'reviewed_non_geographic_entries': len(prose) - pending_review,
        'pending_non_geographic_entries': pending_review,
        'preserved_english_place_names': len(geographic),
    }
    inventory.update({
        'translation_stage': 'incomplete_draft' if missing or invalid or latin else 'complete_draft',
        'editorial_review': editorial_review,
        'display_fallbacks': {s.strip(): t.strip() for s,t in terms.items() if s.strip() and t.strip()},
        'scope_description': ('本体与官方 DLC 的界面、物品、技能、人物、委托及事件文本已全部独立精修；地名保留原版英文；游戏内验收待进行'
                              if review_complete else '本体与官方 DLC 的界面、物品、技能、人物、地名、委托及事件文本；长篇剧情为独立初稿，待逐条校对'),
        'native_map_font': 'bbmod_launcher_noto_serif_sc',
        'provenance': {'source': '用户本机原版 1.5.2.3 官方档案', 'translation': ('本地 MADLAD-400 初稿；非地名译文现已全部依据原文独立精修' if review_complete else '人工独立术语与专名；本地 MADLAD-400 初稿'),
                       'excluded': '第三方 MOD 译文及脚本', 'model': 'google/madlad400-3b-mt', 'model_license': 'Apache-2.0'},
    })
    if args.publish:
        if missing or invalid or latin:
            raise ValueError('尚有缺译、格式问题或未核对的英文，已写出审查报告，未发布目录。')
        destination = ROOT / 'localization/full_catalog.json'
        pending = destination.with_suffix('.pending')
        pending.write_text(json.dumps(inventory, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
        pending.replace(destination)
    else:
        (WORK / 'candidate-catalog.json').write_text(json.dumps(inventory, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k not in {'missing', 'invalid', 'latin'}}, ensure_ascii=False))


if __name__ == '__main__':
    main()

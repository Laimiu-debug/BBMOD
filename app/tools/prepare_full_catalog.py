"""Classify original literals and produce a reviewable translation inventory.

Input is the user's official archives, never a localization mod or its corpus.
Decompiled code supplies reading context only; it is not rebuilt into the mod.
"""
from __future__ import annotations

import collections
import hashlib
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.cnut import Cnut
from core.cnut_semantics import protected_literals

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / 'build/full-l10n'
QUOTED = re.compile(r'"((?:\\.|[^"\\])*)"')
INTERNAL_CALL = re.compile(r'(?:hasFlag|getFlag|setFlag|removeFlag|set|has|get|remove|addSprite|getSprite|setBrush|setSound|setMusic|load|include|inherit|logInfo|logWarning|logError|logDebug|setAchievement|unlockAchievement|setScenario|setID|setFlag|find|registerConnection|notifyBackend|trigger|on|off)\s*\(\s*$')
TEXT_FIELD = re.compile(r'\b(?:Name|Title|Text|Description|RawDescription|BackgroundDescription|ButtonText|ButtonLabel|Tooltip|TooltipText|SuccessButtonText|UIText|UIDescription|creatureName|potionName|itemName|CorpseName|ArmorDescription|RewardTooltip|OathName|OathBoonText|OathBurdenText|SubTitle|subTitle|WoundName|TaskTooltip|GenericItemName|SettlementName|Townname|BaseAttackName|dayName|_disengageText|Hint|Quote|CombatLog|KillerName|KilledString|ProduceString|ActionText|DescriptionShort|ShortDescription|FarewellText|SuccessText|FailureText|ObjectiveText|BattleName|name|text|title|description)\s*(?:=|<-|:)\s*$')
TEXT_CALL = re.compile(r'(?:setName|setTitle|setText|setDescription|setOrders|addTooltip|showPopup|showMessage|improveMood|worsenMood|addLog|log|text|html|createTextButton|createTextButtonWithLabel)\s*\(\s*$')
TEXT_FUNCTIONS = {'getName', 'getStrengthAsText', 'getDescription', 'getDescriptionShort', 'getTooltip', 'getFlavorText', 'getTitle', 'getActionText', 'getLogEntry', 'getItemTypeName', 'getArticle', 'getArticleCapitalized'}
TEXT_CONFIGS = {'character_names', 'item_names', 'world_location_names', 'tip_of_the_day', 'rumors', 'strings'}
RESERVED = {'Strings', 'Tactical', 'World', 'Name', 'Description', 'Type', 'ID', 'Text', 'Icon', 'Order', 'Title', 'Start', 'End', 'Image', 'Items', 'Options', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'X', 'Y', 'Z', 'null', 'true', 'false', 'integer', 'float', 'string', 'array', 'table', 'function', 'blob', 'weakref', 'bool'}


def unescape(raw):
    def sub(m):
        s = m.group(1)
        if s in {'n', 'r', 't', 'v', 'a', 'b', 'f', '0'}:
            return {'n': '\n', 'r': '\r', 't': '\t', 'v': '\v', 'a': '\a', 'b': '\b', 'f': '\f', '0': '\0'}[s]
        if s.startswith('x'):
            return chr(int(s[1:], 16))
        return s
    return re.sub(r'\\(x[0-9A-Fa-f]{2}|.)', sub, raw)


def contexts(code):
    found = collections.defaultdict(list)
    arrays = []
    token = re.compile(r'"((?:\\.|[^"\\])*)"|//[^\n]*|\[|\]')
    for m in token.finditer(code):
        if m.group(1) is not None:
            array = arrays[-1] if arrays else ''
            found[unescape(m.group(1))].append('@array:' + array + '@' + code[max(0, m.start() - 180):m.start()])
        elif m.group() == '[':
            prefix = code[max(0, m.start() - 120):m.start()]
            label = re.search(r'([\w.]+)\s*(?:=|<-)\s*$', prefix)
            if re.search(r'getRandomName\(\s*$', prefix):
                label = re.match(r'(Names)', 'Names')
            arrays.append(label.group(1) if label else (arrays[-1] if arrays else ''))
        elif m.group() == ']' and arrays:
            arrays.pop()
    return found


def reason(text, file, function, ctx, key=False):
    if not re.search(r'[A-Za-z]', text) or re.search(r'[\ud800-\udfff\x00-\x08\x0b\x0c\x0e-\x1f]', text):
        return 'non_text'
    if key:
        return 'program_key'
    if text.startswith('undefined ') and text.endswith(' brush'):
        return 'resource_identifier'
    if not re.search(r'[A-Za-z]', re.sub(r'\[/?[^\]]*\]|\[color=|</?[^>]*>', '', text)):
        return 'format_token'
    if re.fullmatch(r'[a-fA-F0-9]{6,10}', text):
        return 'color_code'
    if ctx and all(re.search(r'(?:type|Type|icon|Icon|Image|Banner|ID|id|Sound|Brush|Event|Resource|Input|Output)\s*(?:=|<-|:)\s*$', c) for c in ctx):
        return 'program_field'
    if text.startswith(('scripts/', 'gfx/', 'ui/', 'music/', 'sounds/', 'world/', 'coui://', 'http:', 'https:', 'data/', '#')):
        return 'resource_or_link'
    if re.fullmatch(r'[A-Za-z0-9_.:/\\-]+', text) and ('.' in text or '/' in text or '_' in text):
        return 'program_identifier'
    if re.fullmatch(r'%[A-Za-z0-9_]+%', text) or re.fullmatch(r'\[/?[A-Za-z]+(?:=[^\]]*)?\]', text):
        return 'format_token'
    if any(TEXT_FIELD.search(c) or TEXT_CALL.search(c) for c in ctx):
        return 'visible_field'
    if any(re.search(r'@array:(?:\w*\.)*(?:\w*StateName|NameList|Mottos|Names|Titles|nemesisNamesS|names|items|titles|prefixes)@', c) for c in ctx):
        return 'visible_array'
    if any(re.search(r'spawnEntity\([^;]*,\s*$', c) for c in ctx):
        return 'visible_party'
    if text in RESERVED:
        return 'program_token'
    # This is an English plural suffix, not the banner-size key "s".
    if (file, function, text) == ('scripts/states/tactical_state.cnut',
                                 'tactical_combat_result_screen_onQueryCombatInformation', 's'):
        return 'visible_grammar'
    if ctx and all(INTERNAL_CALL.search(c) or re.search(r'\[\s*$', c) and 'Flags' in c[-60:] for c in ctx):
        return 'program_argument'
    if 'config/' in file and Path(file).stem in TEXT_CONFIGS and function == 'main' and ctx:
        if any(re.search(r'(?:<-\s*\[|,|\[)\s*$', c) or Path(file).stem == 'strings' and re.search(r'\w+\s*(?:=|<-)\s*$', c) for c in ctx):
            return 'visible_name_or_term'
    if function in TEXT_FUNCTIONS and any(re.search(r'\breturn\s*$', c) for c in ctx):
        return 'visible_return'
    if any(re.search(r'killedBy\s*=\s*$', c) for c in ctx):
        return 'visible_return'
    if text == 'all' and function == 'getTooltip' and file.startswith('scripts/skills/traits/arena_'):
        return 'visible_reviewed'
    if (file, function, text) == ('scripts/entity/world/attached_location.cnut', 'getName', 'Ruins'):
        return 'visible_reviewed'
    if (file, function, text) in {('scripts/skills/traits/arena_fighter_trait.cnut', 'getTooltip', 'all'), ('scripts/states/world_state.cnut', 'showCombatDialog', 'Flee!'), ('scripts/states/tactical_state.cnut', 'showFleeScreen', 'Retreat!'), ('scripts/states/tactical_state.cnut', 'showFleeScreen', 'Cancel'), ('scripts/states/tactical_state.cnut', 'toggleMenuScreen', 'Quit')}:
        return 'visible_reviewed'
    if re.search(r'\s', text) and not re.fullmatch(r'[\w. /\\-]+\.(?:png|brush|ogg|wav|cnut|nut|js|ttf)', text):
        if any(word in text for word in ('::', 'ERROR', 'WARNING', 'could not find class', 'ACTIVATING', 'DEACTIVATING')):
            return 'diagnostic'
        return 'visible_prose'
    if not ctx:
        return 'program_symbol'
    if any(re.search(r'(?:setScreen|setState|hasState|hasSprite|has|get|set|add|increment|getAsInt|isKindOf|typeof|style)\s*(?:\([^\n;]*|==|=)\s*$', c) for c in ctx):
        return 'program_argument'
    if function in {'createStates', 'createScreens', 'getResult', 'onCombatVictory'}:
        return 'state_identifier'
    if function == 'onPrepareVariables' and re.fullmatch(r'[a-z][a-z0-9_]*', text):
        return 'template_variable'
    if re.search(r'[a-z][A-Z]|_', text):
        return 'program_symbol'
    return 'needs_review'


def main():
    files = {}
    catalog = {}
    review = collections.defaultdict(list)
    totals = collections.Counter()
    sources = json.loads((WORK / 'sources.json').read_text(encoding='utf-8'))
    for p in sorted((WORK / 'plain').rglob('*.cnut')):
        file = p.relative_to(WORK / 'plain').as_posix()
        c = Cnut(p.read_bytes())
        decompiled = WORK / 'decompiled' / Path(file).with_suffix('.nut')
        ctxs = contexts(decompiled.read_text(encoding='utf-8', errors='replace')) if decompiled.is_file() else {}
        fn = {f['path']: f for f in c.functions}
        keys = {f['path']: protected_literals(f) for f in c.functions}
        patches = []
        for lit in c.literals:
            why = reason(lit.text, file, fn[lit.function]['name'], ctxs.get(lit.text, []), lit.index in keys[lit.function])
            totals[why] += 1
            if not why.startswith('visible_'):
                if why == 'needs_review':
                    review[lit.text].append({'file': file, 'function': fn[lit.function]['name'], 'context': ctxs.get(lit.text, [])[:1]})
                continue
            key = hashlib.sha256(lit.text.encode('utf-8')).hexdigest()[:20]
            entry = catalog.setdefault(key, {'source': lit.text, 'translation': '', 'status': 'untranslated', 'category': file.split('/')[1], 'contexts': []})
            if len(entry['contexts']) < 3:
                entry['contexts'].append({'file': file, 'function': fn[lit.function]['name'], 'reason': why})
            patches.append([lit.start, lit.end, key])
        if patches:
            files[file] = {**sources[file], 'patches': patches}
    ui_path = WORK / 'ui-inventory.json'
    if ui_path.exists():
        for file, data in json.loads(ui_path.read_text(encoding='utf-8')).items():
            patches = []
            for patch in data['patches']:
                text = patch['source']
                key = hashlib.sha256(text.encode('utf-8')).hexdigest()[:20]
                entry = catalog.setdefault(key, {'source': text, 'translation': '', 'status': 'untranslated', 'category': 'ui', 'contexts': []})
                if len(entry['contexts']) < 3:
                    entry['contexts'].append({'file': file, 'reason': 'visible_js'})
                patches.append([patch['start'], patch['end'], key])
            files[file] = {**sources[file], 'kind': 'js', 'patches': patches}
    (WORK / 'inventory.json').write_text(json.dumps({'schema_version': 1, 'source_game': '1.5.2.3', 'scope': '本体及官方 DLC', 'files': files, 'entries': catalog}, ensure_ascii=False, indent=2), encoding='utf-8')
    (WORK / 'classification-review.json').write_text(json.dumps(review, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'files': len(files), 'entries': len(catalog), 'characters': sum(len(e['source']) for e in catalog.values()), 'classification': totals, 'review': len(review)}, ensure_ascii=False))


if __name__ == '__main__':
    main()

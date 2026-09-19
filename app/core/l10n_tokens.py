"""Shared markup/placeholder checks for independently authored translations."""
from __future__ import annotations
from collections import Counter
from functools import lru_cache
import hashlib
import json
import re

from .paths import resource_path

VARIABLE = re.compile(r'%[A-Za-z0-9_]+%')
STRUCTURE = re.compile(r'\[img\][\s\S]*?\[/img\]|\[[^\]\n]*\]|\[(?:color|font|size)=|</?[^>\n]*(?:>|$)|%SPEECH_[A-Z_]+%|[{}|\n\r\[\]]')
NUMBER = re.compile(r'(?<![A-Za-z_])[+-]?\d+(?:,\d{3})*(?:\.\d+)?%?')
TEMPLATE_SEPARATOR = re.compile(r'[ \t]*\|[ \t]*')
ALLOWED_UI_WORDS = {'ALT', 'Alt', 'CTRL', 'Ctrl', 'SHIFT', 'Shift', 'ESC', 'Esc', 'Escape',
                    'Enter', 'F', 'F1', 'F2', 'F5', 'F9', 'Page', 'PageUp', 'PageDown',
                    'Up', 'Down', 'Steam', 'GOG', 'DLC', 'FPS', 'UI'} | set('ABCDEFGHIJKLMNOPQRSTUVWXYZ')

# Official 1.5.2.3 barbarian_king_contract, catalog 1d93308f84c551079323:
# "2takes" is a misspelled verb, not a quantity. Match the complete source so
# other occurrences of 2 (including future revisions) remain protected. Keep
# the original source untouched: the game uses it as the translation lookup.
_BARBARIAN_KING_DEATH_SOURCE = (
    '[img]gfx/ui/events/event_145.png[/img]{The Barbarian King is dead. '
    'Though he adorned himself the title of royalty, he lies amongst the dead '
    'like any other of his people. A savage. A primitive. With a slightly '
    'hardier body and some accoutrements native to his warring and pillaging '
    'and ravaging. Little else distinguishes him. You chop into his neck with '
    'your sword and put your boot to his face as you cut him clean off the '
    'shoulders. %randombrother% 2takes the heavy head and drops it into a '
    'knapsack. You order the men to scavenge what they can before preparing '
    'a return to %employer%.}'
)


def restore_template_separators(source: str, translation: str) -> str:
    """Keep the engine's exact choice delimiters, including ASCII spaces.

    Battle Brothers 1.5.2.3 selects one branch for ``{A | B}``, but renders
    ``{A|B}`` as the literal ``A|B``. Cached paragraph drafts can lose those
    boundary spaces. Restore only the source delimiters, never branch text,
    variables, or random choices. A mismatched branch count remains invalid.
    """
    expected = TEMPLATE_SEPARATOR.findall(source)
    actual = TEMPLATE_SEPARATOR.findall(translation)
    if len(expected) != len(actual):
        return translation
    separators = iter(expected)
    return TEMPLATE_SEPARATOR.sub(lambda _: next(separators), translation)


def protected_tokens(text: str) -> dict:
    structure = STRUCTURE.findall(text)
    clean = STRUCTURE.sub(' ', text)
    variables = VARIABLE.findall(clean)
    clean = VARIABLE.sub(' ', clean)
    return {'structure': structure, 'variables': Counter(variables),
            'numbers': Counter(n.replace(',', '') for n in NUMBER.findall(clean))}


@lru_cache(maxsize=1)
def reviewed_source_structures() -> dict:
    """Permit only exact, reviewed repairs to malformed official display text."""
    path = resource_path('localization/reviewed_source_fixes.json')
    if not path.exists():
        return {}
    document = json.loads(path.read_text(encoding='utf8'))
    if document.get('schema_version') != 1 or not isinstance(document.get('structures'), dict):
        raise ValueError('原版文本排版修订记录无效')
    for digest, rule in document['structures'].items():
        if not re.fullmatch('[0-9a-f]{64}', digest) or not all(
                isinstance(rule.get(key), list) and all(isinstance(v, str) for v in rule[key])
                for key in ['original', 'corrected']):
            raise ValueError('原版文本排版修订规则无效')
    return document['structures']


def validate_translation(source: str, translation: str) -> list[str]:
    if not isinstance(translation, str):
        return ['译文必须是文字']
    a, b = protected_tokens(source), protected_tokens(translation)
    repair = reviewed_source_structures().get(hashlib.sha256(source.encode('utf8')).hexdigest())
    if repair and a['structure'] == repair['original'] and b['structure'] == repair['corrected']:
        # Historical reviewed drafts remain readable, but no other marker
        # sequence, lookup key, variable, number, or branch separator is exempt.
        a['structure'] = repair['corrected']
    if source == _BARBARIAN_KING_DEATH_SOURCE:
        a['numbers'] -= Counter({'2': 1})
    issues = []
    if a['structure'] != b['structure']:
        issues.append('排版标记或分支符号发生变化')
    if TEMPLATE_SEPARATOR.findall(source) != TEMPLATE_SEPARATOR.findall(translation):
        issues.append('随机文本分隔符两侧的空格发生变化')
    if a['variables'] != b['variables']:
        issues.append('剧情变量发生变化')
    if a['numbers'] != b['numbers']:
        issues.append('数字发生变化')
    if '\0' in translation or re.search(r'[\ud800-\udfff]', translation):
        issues.append('译文含无效字符')
    return issues


def parts(text: str):
    cursor = 0
    result = []
    for match in STRUCTURE.finditer(text):
        if match.start() > cursor:
            result.append((False, text[cursor:match.start()]))
        result.append((True, match.group()))
        cursor = match.end()
    if cursor < len(text):
        result.append((False, text[cursor:]))
    return result

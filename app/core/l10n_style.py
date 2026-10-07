"""Typography and cross-reference rules for the independent Chinese catalog.

These checks complement ``l10n_tokens``: tokens protect what the game reads,
these rules keep what the player reads consistent. They operate on the
catalog alone, so they run offline without the game archives.
"""
from __future__ import annotations

import re
from collections import defaultdict

CJK = r'[一-鿿]'
_TAG_CLOSE_SPACE = re.compile(r'(\[/color\]|\[/b\]) +(?=%s|[，。：；、）！？”])' % CJK)
_SPACE_TAG_OPEN = re.compile(r'(?<=%s|[，。：；、（“]) +(?=\[color|\[b\])' % CJK)
_DIGIT_SPACE_CJK = re.compile(r'(?<=\d) +(?=%s)' % CJK)
_CJK_SPACE_DIGIT = re.compile(r'(?<=%s) +(?=\d)' % CJK)
# Never touch `` | `` (the engine needs those spaces to split random branches).
_PUNCT_SPACE = re.compile(r'(?<=[，。：；、）！？]) +(?=[^\s|])')

# The credits list English names and dates verbatim.
SPACING_EXEMPT = frozenset({'d5124a89faebcdcf3181'})

# Item-name pools reuse short words with other meanings ('Gilded' as an item
# prefix is not the southern people), so they never define a referenced name.
NAME_POOL_FILES = frozenset({'scripts/config/item_names.cnut'})

# A quoted English word that deliberately maps to a longer official name.
# key -> (quoted source name, translation actually shown in the game)
REFERENCE_EXCEPTIONS = {
    # The 'Cultists' origin is displayed as its scenario name "Davkul Cultists".
    'a3ffc323a661dd270440': ('Cultists', '达夫库尔教徒'),
}

_QUOTED_NAME = re.compile(r"(?<![A-Za-z])'([A-Z][A-Za-z' -]{1,40}?)'(?![A-Za-z])")
_OPEN, _CLOSE = '(（', ')）'


def normalize_spacing(text: str) -> str:
    """Drop ASCII spaces between Chinese and numbers, colour tags or punctuation.

    Leading and trailing spaces are left alone: fragments are joined with
    names and numbers at runtime, and only the whole sentence shows whether
    such a boundary space is wanted.
    """
    text = _TAG_CLOSE_SPACE.sub(r'\1', text)
    text = _SPACE_TAG_OPEN.sub('', text)
    text = _DIGIT_SPACE_CJK.sub('', text)
    text = _CJK_SPACE_DIGIT.sub('', text)
    return _PUNCT_SPACE.sub('', text)


def spacing_problems(entries: dict) -> list[str]:
    return [f'{key}: 中文与数字、标记或标点之间有多余空格'
            for key, entry in entries.items()
            if key not in SPACING_EXEMPT and normalize_spacing(entry['translation']) != entry['translation']]


def _paren_balance(text: str) -> tuple[list[str], list[str]]:
    """Return unmatched openers and closers in order of appearance."""
    stack, closers = [], []
    for char in text:
        if char in _OPEN:
            stack.append(char)
        elif char in _CLOSE:
            if stack:
                stack.pop()
            else:
                closers.append(char)
    return stack, closers


def _wide(char: str) -> bool:
    return char in '（）'


def paren_problems(catalog: dict) -> list[str]:
    """Each displayed bracket pair must use one width.

    Within an entry, matched pairs are compared directly. A bracket left open
    by one fragment is closed by another literal of the same script; when the
    other half is not in the catalog it stays the original ASCII character,
    so the translated half must be ASCII too.
    """
    entries = catalog['entries']
    problems = []
    for key, entry in entries.items():
        stack = []
        for char in entry['translation']:
            if char in _OPEN:
                stack.append(char)
            elif char in _CLOSE and stack and _wide(stack.pop()) != _wide(char):
                problems.append(f'{key}: 同一条译文混用全角与半角括号')
                break
    for name, spec in catalog['files'].items():
        openers, closers = defaultdict(list), defaultdict(list)
        for key in {patch[2] for patch in spec['patches']}:
            entry = entries[key]
            source_open, source_close = _paren_balance(entry['source'])
            target_open, target_close = _paren_balance(entry['translation'])
            if source_open and target_open:
                openers[key] = target_open
            if source_close and target_close:
                closers[key] = target_close
        for own, other, side in ((openers, closers, '左'), (closers, openers, '右')):
            other_widths = {_wide(c) for chars in other.values() for c in chars}
            for key, chars in own.items():
                widths = {_wide(c) for c in chars}
                if not other and True in widths:
                    problems.append(f'{key}: {name} 的另一半括号是原版半角字符，此处{side}括号也须用半角')
                elif other and widths != other_widths and len(other_widths) == 1:
                    problems.append(f'{key}: {name} 中跨片段配对的括号宽度不一致')
    return sorted(set(problems))


def reference_problems(entries: dict) -> list[str]:
    """A description quoting 'Name' must show that name's current translation."""
    names = {}
    for entry in entries.values():
        if all(c['file'] in NAME_POOL_FILES for c in entry['contexts']):
            continue
        names.setdefault(entry['source'].strip(), entry['translation'].strip())
    problems = []
    for key, entry in entries.items():
        for match in _QUOTED_NAME.finditer(entry['source']):
            name = match.group(1)
            if name not in names:
                continue
            expected = names[name]
            exception = REFERENCE_EXCEPTIONS.get(key)
            if exception and exception[0] == name:
                expected = exception[1]
            if expected not in entry['translation']:
                problems.append(f'{key}: 引用“{name}”时应使用当前译名“{expected}”')
    return problems


def style_problems(catalog: dict) -> list[str]:
    entries = catalog['entries']
    return spacing_problems(entries) + paren_problems(catalog) + reference_problems(entries)

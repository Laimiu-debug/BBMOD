"""Reviewed meanings for visible strings shared by unrelated contexts."""
from __future__ import annotations

import hashlib
import json

from .l10n_tokens import validate_translation
from .paths import resource_path

CONTEXT_FILE = resource_path('localization/reviewed_contextual.json')


def load_contextual_terms(catalog: dict) -> dict[str, dict[str, str]]:
    review = json.loads(CONTEXT_FILE.read_text(encoding='utf8'))
    if review.get('schema_version') != 1 or not isinstance(review.get('files'), dict):
        raise ValueError('场景译文目录格式无效')
    result = {}
    for file, terms in review['files'].items():
        if file not in catalog['files']:
            continue  # A small UI-only catalog has no item-name pools.
        visible_keys = {patch[2] for patch in catalog['files'][file]['patches']}
        scoped = {}
        for source, target in terms.items():
            key = hashlib.sha256(source.encode('utf8')).hexdigest()[:20]
            entry = catalog['entries'].get(key)
            if (not entry or entry['source'] != source or key not in visible_keys
                    or not any(c['file'] == file for c in entry['contexts'])):
                raise ValueError('场景译文没有对应的可见原文：' + file + ': ' + source)
            if not isinstance(target, str) or not target.strip() or validate_translation(source, target):
                raise ValueError('场景译文损坏了变量或文本标记：' + source)
            scoped[key] = target
        result[file] = scoped
    return result


def entries_for_context(entries: dict, scoped: dict[str, str], custom_overrides: dict) -> dict:
    """Explicit user edits still take precedence over the built-in review."""
    if not scoped:
        return entries
    result = dict(entries)
    for key, target in scoped.items():
        entry = entries[key]
        if entry['source'] not in custom_overrides:
            result[key] = {**entry, 'translation': target}
    return result

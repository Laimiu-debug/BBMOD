import hashlib

from core.full_l10n import load_full_catalog
from core.l10n_tokens import protected_tokens, reviewed_source_structures, validate_translation


def test_shipped_source_repairs_only_allow_the_reviewed_marker_sequences():
    entries = load_full_catalog()['entries'].values()
    rules = reviewed_source_structures()
    assert len(rules) == 3
    found = 0
    for entry in entries:
        source, target = entry['source'], entry['translation']
        rule = rules.get(hashlib.sha256(source.encode('utf8')).hexdigest())
        if rule is None:
            continue
        found += 1
        assert protected_tokens(source)['structure'] == rule['original']
        assert protected_tokens(target)['structure'] == rule['corrected']
        assert not validate_translation(source, target)
        assert '排版标记或分支符号发生变化' in validate_translation(source + ' ', target)
        assert '排版标记或分支符号发生变化' in validate_translation(source, target + '[color=#fff]')
        assert '剧情变量发生变化' in validate_translation(source, target + '%unknown%')
        assert '数字发生变化' in validate_translation(source, target + '123456789')
    assert found == len(rules)

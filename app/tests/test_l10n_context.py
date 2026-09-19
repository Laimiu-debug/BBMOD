import hashlib

from core.full_l10n import load_full_catalog
from core.l10n_context import entries_for_context, load_contextual_terms


def test_equipment_meanings_do_not_rename_traits_attacks_or_titles():
    catalog = load_full_catalog()
    original = catalog['entries']
    terms = load_contextual_terms(catalog)
    equipment = entries_for_context(original, terms['scripts/config/item_names.cnut'], {})
    expected = {'Old': ('年迈', '古旧'), 'Whip': ('鞭击', '长鞭'),
                'of the Desert': ('沙漠来客', '·沙漠'), 'of the North': ('北境之子', '·北境')}
    for source, (generic, item_name) in expected.items():
        key = hashlib.sha256(source.encode()).hexdigest()[:20]
        assert original[key]['translation'] == generic
        assert equipment[key]['translation'] == item_name
    assert set(terms) == {'scripts/config/item_names.cnut'}


def test_explicit_user_translation_wins_in_every_context():
    catalog = load_full_catalog()
    key = hashlib.sha256(b'Old').hexdigest()[:20]
    entries = {**catalog['entries'], key: {**catalog['entries'][key], 'translation': '用户自定'}}
    terms = load_contextual_terms(catalog)['scripts/config/item_names.cnut']
    assert entries_for_context(entries, terms, {'Old': '用户自定'})[key]['translation'] == '用户自定'

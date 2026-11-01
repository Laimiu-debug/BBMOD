import hashlib

import pytest

from core.full_l10n import load_full_catalog
from core.l10n import translated_catalog
from core.l10n_display import build_army_names
from core.place_names import geographic_spans, load_policy
from tools.translate_full_catalog import load_terms


@pytest.fixture(scope='module')
def data():
    catalog = load_full_catalog()
    dictionary = {**catalog['display_fallbacks'], **translated_catalog()}
    return catalog, dictionary


def test_party_display_covers_original_names_without_claiming_mountains(data):
    catalog, dictionary = data
    names = build_army_names(catalog, dictionary)
    assert len(names['companies']) == len(set(names['companies'].values())) == 57
    assert names['companies']['Bulwark'] == '壁垒'
    assert names['companies']['Iron Ravens'] == '铁鸦'
    assert names['settlements']['Wiesendorf'] == names['settlements']['维森多夫'] == '维森多夫'
    assert 'Stormy Sea' not in names['settlements']
    assert 'Bulwark' not in names['settlements']
    assert '铁狼战团' not in names['companies']
    assert names['generic']['Army'] == '军队'


def test_shared_company_mountain_literal_keeps_its_canonical_value(data):
    catalog, _ = data
    key = hashlib.sha256(b'Bulwark').hexdigest()[:20]
    # The original compiler interns this name in one literal used by BOTH
    # MercenaryCompanyNames and TerrainRegionNames. Repair its display only.
    assert any(k == key for _, _, k in geographic_spans(load_policy(catalog), 'scripts/config/strings.cnut'))


def test_noble_suffix_is_reviewed_separately_from_company_labels(data):
    catalog, dictionary = data
    assert dictionary[' Company'] == load_terms()[' Company'] == ' 军队'
    assert dictionary['Company'] == '战团'
    assert dictionary['Iron Crown Company'] == '铁冠战团'
    key = hashlib.sha256(b' Company').hexdigest()[:20]
    files = {f for f, s in catalog['files'].items() if any(p[2] == key for p in s['patches'])}
    assert len(files) == 14
    assert all(f.startswith(('scripts/factions/actions/', 'scripts/contracts/contracts/')) for f in files)


def test_custom_translation_is_kept_and_missing_company_fails_build(data):
    catalog, dictionary = data
    custom = {**dictionary, 'Iron Ravens': '用户团名', ' Company': ' 用户军团'}
    names = build_army_names(catalog, custom)
    assert names['companies']['Iron Ravens'] == '用户团名'
    assert names['nobleSuffix'] == '用户军团'
    custom.pop('Bulwark')
    with pytest.raises(ValueError, match='军队名称缺少译文'):
        build_army_names(catalog, custom)

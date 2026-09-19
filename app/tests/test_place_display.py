import copy
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import zipfile

import pytest

from core import place_display
from core.full_l10n import load_full_catalog
from core.l10n import BRAND_META, PACKAGE_ID, load_catalog, translated_catalog
from core.localization_profiles import LocalizationProfiles
from core.place_names import load_policy


@pytest.fixture(scope='module')
def corpus():
    catalog = load_full_catalog()
    return catalog, load_policy(catalog), translated_catalog()


def make_package(path, corpus):
    with zipfile.ZipFile(path, 'w') as archive:
        manifest = {'package_id': PACKAGE_ID, 'uses_bbmod_map_font': False, 'supports_direct_launch': True,
                    **place_display.write_display_assets(archive, *corpus)}
        archive.writestr(BRAND_META, json.dumps(manifest))
    return path


def test_all_geographic_sources_reviewed_without_altering_the_canonical_catalog(corpus):
    catalog, policy, dictionary = corpus
    before = copy.deepcopy(catalog)
    reviewed = place_display.reviewed_places(catalog, policy)
    assert len(reviewed) == len(policy['name_keys']) == 2196
    assert {'Wiesendorf', 'Stormy Sea', 'Icy Cave', 'Black Monolith', 'Sandwik'} <= set(reviewed)
    assert dictionary['Sandwik'] == '桑德维克'
    assert dictionary['Black Monolith'] == '黑色巨石'
    # Distinct original watch forts must not collapse to the same display name.
    assert dictionary['Fahrnwacht'] != dictionary['Farnwacht']
    assert all(row.status == 'reviewed' for row in load_catalog()[1])
    assert catalog == before


def test_templates_ruins_and_owner_names_expand_to_one_shared_lexicon(corpus):
    raw, names = place_display.build_display_data(*corpus)
    assert len(names) > 2196 and raw.startswith(place_display.HEADER.encode('ascii'))
    assert b'%' not in raw and b'{' not in raw and b'}' not in raw
    assert names['Ruins of Wiesendorf'] == names['Wiesendorf'] + '遗址'
    assert names['Ruins of Black Monolith'] == names['Black Monolith'] + '遗址'
    for owner in corpus[1]['owner_pools']['CharacterNames']:
        for title in ('Great', 'Cruel', 'Tyrant'):
            assert corpus[2][owner] in names[f'Tomb of {owner} the {title}']
    assert raw == place_display.build_display_data(*corpus)[0]


def test_changed_review_manifest_is_rejected_before_build(tmp_path, monkeypatch, corpus):
    data = json.loads(place_display.REVIEW_FILE.read_text(encoding='utf-8'))
    data['reviewed_ids'].pop()
    path = tmp_path/'review.json'; path.write_text(json.dumps(data), encoding='utf-8')
    monkeypatch.setattr(place_display, 'REVIEW_FILE', path)
    with pytest.raises(ValueError, match='不匹配'):
        place_display.build_display_data(*corpus)


def test_packaged_display_and_ui_dictionaries_are_identical(tmp_path, corpus):
    path = make_package(tmp_path/'package.zip', corpus)
    assert place_display.read_packaged_display(path) == place_display.build_display_data(*corpus)[0]


@pytest.mark.parametrize('entry', [place_display.DATA_ENTRY, place_display.JS_ENTRY, place_display.BRIDGE_ENTRY])
def test_mismatched_package_never_starts_game(tmp_path, corpus, entry):
    source = make_package(tmp_path/'source.zip', corpus)
    altered = tmp_path/'altered.zip'
    with zipfile.ZipFile(source) as original, zipfile.ZipFile(altered, 'w') as out:
        for name in original.namelist():
            raw = original.read(name)
            if name == entry:
                raw = raw.replace('维森多夫'.encode(), '错误城'.encode()) if entry.endswith('.tsv') else raw+b'// changed\n'
            out.writestr(name, raw)
    root = tmp_path/'game'; (root/'data').mkdir(parents=True); (root/'win32').mkdir()
    game = SimpleNamespace(root=root, exe=root/'win32/BattleBrothers.exe')
    game.exe.write_bytes(b'not executable')
    (root/'data/independent.zip').write_bytes(altered.read_bytes())
    with patch('core.game.is_game_running', return_value=False), patch('core.game.launch_executable') as run:
        with pytest.raises(ValueError):
            LocalizationProfiles(root).launch(game, tmp_path/'runtime')
        run.assert_not_called()
        assert not (tmp_path/'runtime').exists()


def test_profile_launch_checks_installed_dictionary_then_starts_game_normally(tmp_path, corpus, monkeypatch):
    root = tmp_path/'game'; (root/'data').mkdir(parents=True); (root/'win32').mkdir()
    game = SimpleNamespace(root=root,exe=root/'win32/BattleBrothers.exe')
    game.exe.write_bytes(b'test-only')
    installed = make_package(root/'data/independent.zip', corpus)
    monkeypatch.setenv('BBMOD_FONT_PATH', 'obsolete-font')
    monkeypatch.setenv('BBMOD_PLACE_NAMES_PATH', 'obsolete-session')
    before = {p: p.read_bytes() for p in root.rglob('*') if p.is_file()}
    with patch('core.game.is_game_running', return_value=False), \
            patch('core.game.find_steam_root', return_value=None), \
            patch('core.game.os.startfile', create=True) as plain, \
            patch('core.game.subprocess.Popen') as child_start:
        result = LocalizationProfiles(root).launch(game,tmp_path/'runtime')
        assert result == {'mode':'current'}
        assert plain.call_args.args == (str(game.exe),)
        assert plain.call_args.kwargs['cwd'] == str(game.exe.parent)
        child_start.assert_not_called()
        assert os.environ['BBMOD_FONT_PATH'] == 'obsolete-font'
        assert not (tmp_path/'runtime').exists()
        assert before == {p: p.read_bytes() for p in root.rglob('*') if p.is_file()}


@pytest.mark.parametrize('entry', [place_display.JS_ENTRY, place_display.CONFIG_ENTRY,
                                  'scripts/!mods_preload/bbmod_map_labels.nut',
                                  'gfx/fonts/cinzel_bold_100.png'])
def test_damaged_mod_display_is_rejected_before_plain_launch(tmp_path, corpus, entry):
    root = tmp_path/'game'; (root/'data').mkdir(parents=True); (root/'win32').mkdir()
    game = SimpleNamespace(root=root, exe=root/'win32/BattleBrothers.exe')
    game.exe.write_bytes(b'not executable')
    original = make_package(tmp_path/'source.zip', corpus)
    with zipfile.ZipFile(original) as src, zipfile.ZipFile(root/'data/independent.zip', 'w') as dest:
        for name in src.namelist():
            dest.writestr(name, src.read(name) + (b'changed' if name == entry else b''))
    with patch('core.game.is_game_running', return_value=False), patch('core.game.launch_executable') as start:
        with pytest.raises(ValueError):
            LocalizationProfiles(root).launch(game, tmp_path/'runtime')
        start.assert_not_called()

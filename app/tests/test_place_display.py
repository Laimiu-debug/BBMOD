import copy
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import zipfile

import pytest

from core import native_font, place_display
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
        manifest = {'package_id': PACKAGE_ID, 'uses_bbmod_map_font': True, 'supports_direct_launch': True,
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


def test_packaged_native_and_ui_dictionaries_are_identical(tmp_path, corpus):
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
    game = SimpleNamespace(exe=tmp_path/'BattleBrothers.exe')
    with patch('core.game.is_game_running', return_value=False), patch.object(native_font,'check_executable'), \
            patch.object(native_font.subprocess,'run') as run, patch.object(native_font,'prepare_runtime') as runtime:
        with pytest.raises(ValueError):
            native_font.launch_localized(game, tmp_path/'runtime', place_package=altered)
        run.assert_not_called(); runtime.assert_not_called()


def test_launch_uses_private_child_environment_and_keeps_game_files_unchanged(tmp_path, monkeypatch, corpus):
    package = make_package(tmp_path/'installed.zip', corpus)
    assets = {}
    for name in ('bbmod_launch.exe','bbmod_han.dll','NotoSerifSC-SemiBold.ttf','FONT-LICENSE.txt','MINHOOK-LICENSE.txt'):
        assets[name] = tmp_path/name
        assets[name].write_bytes(b'test fixture only, never executed')
    game = SimpleNamespace(exe=tmp_path/'game/win32/BattleBrothers.exe')
    game.exe.parent.mkdir(parents=True); game.exe.write_bytes(b'original-test-fixture')
    monkeypatch.setenv('BBMOD_PLACE_NAMES_PATH','inherited-marker-must-not-be-used')
    monkeypatch.setenv('BBMOD_PLACE_NAMES_SHA256','stale')
    environment = dict(os.environ)
    with patch('core.game.is_game_running', return_value=False), patch.object(native_font,'check_executable'), \
            patch.object(native_font,'_assets', return_value=assets), \
            patch.object(native_font.subprocess,'run', return_value=SimpleNamespace(returncode=0,stdout=b'123\n')) as run:
        result = native_font.launch_localized(game,tmp_path/'runtime',place_package=package)
        child = run.call_args.kwargs['env']
        data_path = Path(child['BBMOD_PLACE_NAMES_PATH'])
        assert data_path.is_relative_to(tmp_path/'runtime')
        assert child['BBMOD_PLACE_NAMES_SHA256'] == hashlib.sha256(data_path.read_bytes()).hexdigest()
        assert result['pid'] == 123 and dict(os.environ) == environment
        assert game.exe.read_bytes() == b'original-test-fixture'
        # Old font-only packages must never inherit a Chinese place session.
        native_font.launch_localized(game,tmp_path/'runtime')
        assert not any(k.startswith('BBMOD_PLACE_NAMES_') for k in run.call_args.kwargs['env'])
        assert dict(os.environ) == environment


def test_profile_launch_uses_currently_installed_dictionary(tmp_path, corpus):
    root = tmp_path/'game'; (root/'data').mkdir(parents=True); (root/'win32').mkdir()
    game = SimpleNamespace(root=root,exe=root/'win32/BattleBrothers.exe')
    game.exe.write_bytes(b'test-only')
    installed = make_package(root/'data/independent.zip', corpus)
    with patch('core.game.is_game_running', return_value=False), \
            patch('core.native_font.launch_localized', return_value={'pid':123}) as native, \
            patch('core.localization_profiles.subprocess.Popen') as plain:
        result = LocalizationProfiles(root).launch(game,tmp_path/'runtime')
        native.assert_called_once_with(game,tmp_path/'runtime',place_package=installed)
        assert result == {'pid':123,'mode':'bbmod'}
        plain.assert_not_called()

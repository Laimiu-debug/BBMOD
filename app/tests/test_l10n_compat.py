import hashlib
import json
import zipfile
from unittest.mock import patch

import pytest

from core.full_l10n import write_full_patches
from core.l10n import BRAND_META, PACKAGE_ID, conflicting_ui_mods
from core.l10n_compat import DISPLAY_ONLY_FILES, hooks_assets, write_hooks
from core.localization_profiles import LocalizationProfiles
from core.modinfo import analyze_zip
from core.modstore import ModStore
from core.diagnostics import diagnose_mods

HIRE = 'ui/screens/world/modules/world_town_screen/world_town_screen_hire_dialog_module.js'


def write_zip(path, contents):
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, 'w') as z:
        for name, content in contents.items():
            z.writestr(name, content)
    return path


@pytest.mark.parametrize('screen', sorted(DISPLAY_ONLY_FILES))
def test_mod_owned_screen_uses_runtime_translation_instead_of_overriding_mod(tmp_path, screen):
    root = tmp_path / 'game'
    source = b"button.text('Hire')"
    write_zip(root/'data/data_001.dat', {screen: source})
    catalog = {'entries': {'hire': {'source': 'Hire', 'translation': '招募'}},
               'files': {screen: {'archive': 'data_001.dat', 'sha256': hashlib.sha256(source).hexdigest(),
                                'kind': 'js', 'patches': [[12, 18, 'hire']]}}}
    with zipfile.ZipFile(tmp_path/'translated.zip', 'w') as z:
        write_full_patches(z, root, catalog, {})
        assert screen not in z.namelist()


def test_embedded_hooks_are_pinned_and_recognized_without_old_html(tmp_path):
    p = tmp_path/'our.zip'
    with zipfile.ZipFile(p, 'w') as z:
        manifest = write_hooks(z)
        assert 'ui/main.html' not in z.namelist()
        for name, raw in hooks_assets().items():
            assert z.read(name) == raw
    registrations = analyze_zip(p).registrations
    assert any(r.mod_id == 'mod_hooks' and r.version == '21.1' for r in registrations)
    assert manifest['external_hooks_required'] is False


@pytest.mark.parametrize('filename', ['mod_bbmod_zhcn.zip', 'my_translation.zip'])
def test_localization_identity_is_separate_from_bundled_hooks(tmp_path, filename):
    own = write_zip(tmp_path / filename, {
        **hooks_assets(), BRAND_META: json.dumps({
            'package_id': PACKAGE_ID, 'brand': 'BBMOD 独立汉化', 'version': '0.3.0-rc.9'})})
    info = analyze_zip(own)
    assert info.primary_id == PACKAGE_ID
    assert info.package_name == 'BBMOD 独立汉化'
    assert info.package_version == '0.3.0-rc.9'
    # This is a package identity, not an invented Squirrel registration.
    assert [r.mod_id for r in info.registrations] == ['mod_hooks']
    entry = ModStore([tmp_path]).scan()[0]
    assert entry.category == '汉化'
    assert entry.display_name == 'BBMOD 独立汉化'

    consumer = write_zip(tmp_path / 'consumer.zip', {
        'scripts/!mods_preload/consumer.nut':
            '::mods_registerMod("consumer", 1); ::mods_queue("consumer", "mod_hooks(>=21)", function() {});'})
    consumer_info = analyze_zip(consumer)
    assert not [i for i in diagnose_mods([info, consumer_info]).issues if i.severity == 'error']
    standalone = analyze_zip(write_zip(tmp_path / 'hooks.zip', hooks_assets()))
    assert standalone.primary_id == 'mod_hooks'
    assert not [i for i in diagnose_mods([info, standalone, consumer_info]).issues if i.severity == 'error']
    duplicate = analyze_zip(write_zip(tmp_path / 'other_consumer.zip', {
        'scripts/!mods_preload/other.nut': '::mods_registerMod("consumer", 1);'}))
    assert any(i.title == 'MOD 重复注册：consumer'
               for i in diagnose_mods([info, consumer_info, duplicate]).issues)


@pytest.mark.parametrize('manifest', ['{', '[]', '{"package_id":"other"}',
                                     json.dumps({'package_id': PACKAGE_ID, 'version': ['bad']})])
def test_invalid_localization_metadata_does_not_break_script_scan(tmp_path, manifest):
    info = analyze_zip(write_zip(tmp_path / 'mod.zip', {**hooks_assets(), BRAND_META: manifest}))
    assert [r.mod_id for r in info.registrations] == ['mod_hooks']
    assert isinstance(info.package_version, str)


def test_switch_and_rollback_preserve_star_mod_while_replacing_language_and_hooks(tmp_path):
    root = tmp_path/'game'
    star = write_zip(root/'data/star-rating.zip', {HIRE: 'star UI', 'scripts/!mods_preload/sr.nut': 'hook'})
    old = write_zip(root/'data/old_chinese.zip', {'ui/main.html': 'old UI'})
    old_bytes, star_bytes = old.read_bytes(), star.read_bytes()
    own = write_zip(tmp_path/'new/independent.zip', {
        'ui/main.html': 'independent UI',
        **hooks_assets(), BRAND_META: json.dumps({'package_id': PACKAGE_ID})})
    manager = LocalizationProfiles(root)
    with patch('core.game.is_game_running', return_value=False):
        previous = manager.register('原有汉化', [old])
        selected = manager.register('独立汉化', [own], builtin=True)
        plan = manager.plan(selected)
        assert plan.disable == [old.name]
        assert star.name not in plan.conflicts
        manager.apply(plan)
        assert star.read_bytes() == star_bytes
        assert conflicting_ui_mods(manager.data, own) == []
        manager.apply(manager.plan(previous))
        assert old.read_bytes() == old_bytes
        assert star.read_bytes() == star_bytes


@pytest.mark.parametrize('other', ['scripts/root_state.nut', 'SCRIPTS/ROOT_STATE.CNUT'])
def test_real_framework_override_is_still_reported(tmp_path, other):
    own = write_zip(tmp_path/'new.zip', {'scripts/root_state.cnut': b'framework'})
    conflict = write_zip(tmp_path/'data/second-framework.zip', {other: b'other framework'})
    assert conflicting_ui_mods(tmp_path/'data', own) == [conflict]

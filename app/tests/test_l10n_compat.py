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

HIRE = next(iter(DISPLAY_ONLY_FILES))


def write_zip(path, contents):
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, 'w') as z:
        for name, content in contents.items():
            z.writestr(name, content)
    return path


def test_hire_screen_uses_runtime_translation_instead_of_overriding_mod(tmp_path):
    root = tmp_path / 'game'
    source = b"button.text('Hire')"
    write_zip(root/'data/data_001.dat', {HIRE: source})
    catalog = {'entries': {'hire': {'source': 'Hire', 'translation': '招募'}},
               'files': {HIRE: {'archive': 'data_001.dat', 'sha256': hashlib.sha256(source).hexdigest(),
                                'kind': 'js', 'patches': [[12, 18, 'hire']]}}}
    with zipfile.ZipFile(tmp_path/'translated.zip', 'w') as z:
        write_full_patches(z, root, catalog, {})
        assert HIRE not in z.namelist()


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

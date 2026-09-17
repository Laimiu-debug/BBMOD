import hashlib
import json
import struct
import zipfile

import pytest

from core.cnut import cipher_block, patch_literals
from core.full_l10n import patch_js, write_full_patches
from core.l10n_tokens import validate_translation


def test_story_placeholders_branch_markup_and_numbers_are_guarded():
    source = '[img]gfx/ui/events/event_27.png[/img]%bro% found {10 crowns|20 crowns}.\n[au]He said no.[/au]'
    translated = '[img]gfx/ui/events/event_27.png[/img]%bro%找到了{10克朗|20克朗}。\n[au]他说不行。[/au]'
    assert validate_translation(source, translated) == []
    assert validate_translation(source, translated.replace('%bro%', '%other%'))
    assert validate_translation(source, translated.replace('20', '30'))
    assert validate_translation(source, translated.replace('|', '或'))
    assert validate_translation(source, translated.replace('[/img]', ''))
    assert validate_translation('Pay 2,000 crowns for %1h%.', '为%1h%支付2000克朗。') == []
    assert validate_translation('Pay 2,000 crowns for %1h%.', '为%2h%支付2000克朗。')


def test_patch_retains_other_bytes_and_rejects_wrong_source():
    english = b'Along the way...'
    # Native modkit-encrypted golden block, checked against the actual reader.
    encrypted = bytes.fromhex('16040c22c6ccc413cda1933b2c5cffcf')
    assert cipher_block(english) == encrypted
    assert cipher_block(encrypted, decrypt=True) == english
    prefix = b'ORIGINAL INSTRUCTIONS'
    raw = prefix + struct.pack('<i', len(english)) + encrypted + b'ORIGINAL DEBUG DATA'
    entries = {'s': {'source': english.decode(), 'translation': '行进途中……'}}
    patched = patch_literals(raw, [[len(prefix), len(prefix) + 4 + len(english), 's']], entries)
    assert patched.startswith(prefix)
    assert patched.endswith(b'ORIGINAL DEBUG DATA')
    assert cipher_block(patched[len(prefix) + 4:-len(b'ORIGINAL DEBUG DATA')], decrypt=True).decode() == '行进途中……'
    with pytest.raises(ValueError, match='校验失败'):
        patch_literals(raw[:-20] + b'?' * 20, [[len(prefix), len(prefix) + 4 + len(english), 's']], entries)


def test_js_patch_preserves_controls_and_quotes_html_safely():
    raw = b"button.text('Start'); button.data('mode', 'Start');"
    result = patch_js(raw, [[12, 19, 's']], {'s': {'translation': '开始“战役”'}})
    assert result.endswith(b"; button.data('mode', 'Start');")
    assert json.loads(result[12:result.index(b');')]) == '开始“战役”'


def test_full_builder_rejects_changed_original_without_reading_mods(tmp_path, monkeypatch):
    root = tmp_path / 'game'
    (root / 'data').mkdir(parents=True)
    with zipfile.ZipFile(root / 'data/data_001.dat', 'w') as archive:
        archive.writestr('ui/a.js', 'CHANGED')
    output = tmp_path / 'out.zip'
    data = {'entries': {}, 'files': {'ui/a.js': {'archive': 'data_001.dat', 'sha256': hashlib.sha256(b'ORIGINAL').hexdigest(), 'kind': 'js', 'patches': []}}}
    with zipfile.ZipFile(output, 'w') as target:
        with pytest.raises(ValueError, match='原版不一致'):
            write_full_patches(target, root, data, {})

def test_classifier_keeps_anatomist_flags_separate_from_display_names():
    from tools.prepare_full_catalog import contexts, reason
    code = 'acquiredFlagName = "isSchratPotionAcquired"; creatureName = "Schrat"; potionName = "Potion of Barkskin";'
    ctx = contexts(code)
    assert not reason('isSchratPotionAcquired', 'scripts/scenarios/world/anatomists_scenario.cnut', 'onSpawnAssets', ctx['isSchratPotionAcquired']).startswith('visible_')
    for source in ['Schrat', 'Potion of Barkskin']:
        assert reason(source, 'scripts/items/research_notes.cnut', 'getTooltip', ctx[source]).startswith('visible_')

def test_full_patch_conflicts_are_detected_even_without_ui_entry(tmp_path):
    from core.l10n import conflicting_ui_mods
    data = tmp_path/'data'; data.mkdir()
    target = tmp_path/'ours.zip'
    with zipfile.ZipFile(target,'w') as z: z.writestr('scripts/skills/actives/strike.cnut',b'original patch')
    other = data/'combat.zip'
    with zipfile.ZipFile(other,'w') as z: z.writestr('scripts/skills/actives/strike.cnut',b'other gameplay changes')
    unrelated = data/'sound.zip'
    with zipfile.ZipFile(unrelated,'w') as z: z.writestr('sounds/strike.ogg',b'sound')
    assert conflicting_ui_mods(data,target)==[other]

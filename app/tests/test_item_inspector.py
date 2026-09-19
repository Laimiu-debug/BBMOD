import html
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace
import zipfile

import pytest

from core.item_inspector import appraise, catalog, HoverLog, HoverSession, MARKER, validate_event
from core import inspector_mod

ROOT = Path(__file__).resolve().parents[1]


def event(identifier='weapon.named_greatsword', **stats):
    return {'schema': 1, 'seq': 1, 'id': identifier, 'name': '自己的剑 <unsafe>', 'named': True,
        'attachment': False, 'stats': {**catalog()[identifier]['base'], **stats}}


def test_original_catalog_bilingual_and_damage_affixes():
    items = catalog()
    assert len(items) == 94
    assert items['weapon.named_greatsword']['zh'] == '红巨剑'
    record = event(RegularDamage=102, RegularDamageMax=120, DirectDamageAdd=.16, ConditionMax=100)
    result = appraise(record, items)
    assert result['valid']
    assert next(r for r in result['rows'] if r['label'] == '穿甲效率')['score'] == 100
    # Endpoints have to share one damage roll, and only two bonus groups exist.
    for changed in [dict(RegularDamageMax=130), dict(AmmoMax=10), dict(ArmorDamageMult=1.2)]:
        invalid = appraise({**record, 'stats': {**record['stats'], **changed}})
        assert not invalid['valid'] and all(r['score'] is None for r in invalid['rows'])


def test_armor_attachment_and_negative_fatigue_direction():
    result = appraise({**event('armor.body.black_and_gold', ConditionMax=249, StaminaModifier=-16), 'attachment': True})
    assert result['valid'] and '附件' in result['message']
    assert result['rows'][1]['score'] == 100
    result = appraise(event(RegularDamage=102, RegularDamageMax=120, FatigueOnSkillUse=-3, ConditionMax=100))
    assert result['valid']
    assert next(r for r in result['rows'] if '技能疲劳' in r['label'])['score'] == 100


def test_squirrel_float32_damage_half_boundary():
    # 50 * (119 * float32(.01)) is just below 59.5 in the original script.
    result = appraise(event('weapon.named_polehammer', RegularDamage=59, RegularDamageMax=89,
                            DirectDamageAdd=.16, ConditionMax=124))
    assert result['valid']


def test_unrecognized_and_nonfinite_records():
    record = event(); record['id'] = 'weapon.from_mod'
    assert not appraise(record)['supported']
    for value in (float('nan'), float('inf'), True, '123', 1000001):
        with pytest.raises(ValueError): validate_event(event(ConditionMax=value))


def test_tail_skips_old_and_waits_for_complete_html_record(tmp_path):
    path = tmp_path / 'log.html'
    encoded = (MARKER + html.escape(json.dumps(event(), ensure_ascii=False))).encode()
    path.write_bytes(encoded)
    tail = HoverLog(path)
    assert tail.poll() == []
    with path.open('ab') as stream: stream.write(b'<div>' + encoded[:50])
    assert tail.poll() == []
    with path.open('ab') as stream: stream.write(encoded[50:] + b'</div>')
    assert tail.poll()[0]['name'] == '自己的剑 <unsafe>'
    assert tail.poll() == []
    path.write_bytes(b'new session')
    assert tail.poll() == [] and tail.generation == 1
    with path.open('ab') as stream: stream.write(b'x' * 300000)
    tail.poll()
    assert len(tail.buffer) <= 8192


def test_bridge_real_interpreter_read_only():
    interpreter = ROOT / 'build/full-l10n/tools/bin/sq.exe'
    if not interpreter.exists(): pytest.skip('offline Squirrel interpreter not installed')
    process = subprocess.run([str(interpreter), str(ROOT / 'tests/inspector_harness.nut'),
        str(ROOT / 'data/item_inspector/bridge.nut')], capture_output=True, timeout=20)
    assert process.returncode == 0 and b'BBMOD_INSPECTOR_PASS' in process.stdout and not process.stderr, (process.stdout, process.stderr)


def test_hover_javascript_original_ui():
    original = ROOT.parent / 'output/art-review/tooltip_module.js'
    if not original.is_file(): pytest.skip('local original-game UI fixture not extracted')
    process = subprocess.run(['node', str(ROOT / 'tests/inspector_hover.test.cjs'), str(original)], capture_output=True, timeout=20)
    assert process.returncode == 0 and b'BBMOD_HOVER_UI_PASS' in process.stdout, (process.stdout, process.stderr)


def test_mod_install_backup_ownership_and_framework(tmp_path, monkeypatch):
    game = SimpleNamespace(data_dir=tmp_path / 'data'); game.data_dir.mkdir()
    with zipfile.ZipFile(game.data_dir / 'data_001.dat', 'w') as archive:
        archive.writestr(inspector_mod.UI_MODULE, b'TooltipModule.prototype.notifyBackendQueryTooltipData = function() {};')
    monkeypatch.setattr(inspector_mod.game, 'is_game_running', lambda: False)
    inspector_mod.change(game)
    target = game.data_dir / inspector_mod.FILENAME
    assert inspector_mod.owned(target)
    with zipfile.ZipFile(target) as archive:
        assert 'scripts/root_state.cnut' in archive.namelist()
        assert b'bbmodInspectorQuery' in archive.read(inspector_mod.UI_MODULE)
        assert 'ui/main.html' not in archive.namelist()
    assert inspector_mod.installed_version(target) == inspector_mod.VERSION
    # Repair uses the existing third-party framework without changing it.
    provider = game.data_dir / 'external_hooks.zip'
    with zipfile.ZipFile(provider, 'w') as archive: archive.writestr('scripts/!mods_preload/!!redirect.nut', b'untouched')
    before = provider.read_bytes()
    inspector_mod.change(game)
    assert provider.read_bytes() == before
    with zipfile.ZipFile(target) as archive: assert 'scripts/root_state.cnut' not in archive.namelist()
    monkeypatch.setattr(inspector_mod.game, 'is_game_running', lambda: True)
    with pytest.raises(ValueError): inspector_mod.change(game, remove=True)
    monkeypatch.setattr(inspector_mod.game, 'is_game_running', lambda: False)
    inspector_mod.change(game, remove=True)
    assert not target.exists() and list((tmp_path / 'BBMOD-backups/item-inspector').glob('*.zip'))
    target.write_bytes(b'user file')
    with pytest.raises(ValueError): inspector_mod.change(game)
    assert target.read_bytes() == b'user file'


def test_ui_conflict_preserves_other_mod_and_old_bridge(tmp_path, monkeypatch):
    game = SimpleNamespace(data_dir=tmp_path)
    monkeypatch.setattr(inspector_mod.game, 'is_game_running', lambda: False)
    with zipfile.ZipFile(tmp_path / 'another-tooltip.zip', 'w') as archive:
        archive.writestr(inspector_mod.UI_MODULE, b'user tooltip')
    before = (tmp_path / 'another-tooltip.zip').read_bytes()
    with pytest.raises(ValueError, match='同时替换'): inspector_mod.change(game)
    assert (tmp_path / 'another-tooltip.zip').read_bytes() == before
    assert not (tmp_path / inspector_mod.FILENAME).exists()


def test_hover_requires_matching_lifecycle_and_expires():
    hover = HoverSession()
    one = {**event(), 'kind': 'item', 'token': 8}
    hover.accept(one, 10)
    assert hover.current(10) is None
    state = {'schema': 1, 'kind': 'hover', 'seq': 2, 'token': 8, 'visible': True}
    hover.accept({**state, 'token': 7}, 10)
    assert hover.current(10) is None
    hover.accept({**state, 'seq': 3}, 10)
    assert hover.current(11) == one and hover.current(11.3) is None
    hover.accept({**state, 'seq': 4}, 11.3)
    assert hover.current(11.3) == one
    hover.accept({**state, 'seq': 5, 'visible': False}, 11.4)
    assert hover.current(11.4) is None
    # Out-of-order and duplicated events cannot reopen a hidden item.
    hover.accept({**state, 'seq': 4}, 11.5)
    assert hover.current(11.5) is None
    hover.accept({**one, 'seq': 6, 'token': 9, 'named': False}, 12)
    hover.accept({**state, 'seq': 7, 'token': 9}, 12)
    assert hover.current(12) is None
    hover.reset()
    assert hover.sequence == -1 and hover.current(12) is None


@pytest.mark.parametrize('changes', [{'token': True}, {'token': -1}, {'visible': 1}, {'seq': -1}, {'kind': 'other'}])
def test_hover_malformed_protocol(changes):
    with pytest.raises(ValueError):
        validate_event({'schema': 1, 'kind': 'hover', 'seq': 2, 'token': 1, 'visible': True, **changes})

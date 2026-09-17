import hashlib
from pathlib import Path
import zipfile

import pytest

from core.cnut import Cnut, patch_literals
from core.cnut_semantics import protected_literals
from core.full_l10n import write_full_patches

FIXTURE = Path(__file__).parent / 'fixtures/literal_roles.cnut'


def test_native_compiler_fixture_distinguishes_keys_values_and_resource_arguments():
    parsed = Cnut(FIXTURE.read_bytes(), encrypted=True)
    f = next(f for f in parsed.functions if f['name'] == 'makeFixture')
    keys = {f['literals'][index] for index in protected_literals(f)}
    assert {'Colossus', 'Steady', 'North', 'South', 'a brush name', 'An internal diagnostic'} <= keys
    assert 'Visible name' not in keys
    assert 'Visible description' not in keys


def test_builder_rejects_a_pooled_key_even_when_its_other_use_is_visible(tmp_path):
    raw = FIXTURE.read_bytes()
    parsed = Cnut(raw, encrypted=True)
    f = next(f for f in parsed.functions if f['name'] == 'makeFixture')
    lit = next(lit for lit in parsed.literals if lit.function == f['path'] and lit.text == 'Colossus')
    root = tmp_path / 'game'; (root / 'data').mkdir(parents=True)
    with zipfile.ZipFile(root / 'data/data_001.dat', 'w') as z: z.writestr('scripts/fixture.cnut', raw)
    catalog = {'entries': {'k': {'source': 'Colossus', 'translation': '巨人'}}, 'files': {
        'scripts/fixture.cnut': {'archive': 'data_001.dat', 'sha256': hashlib.sha256(raw).hexdigest(),
                               'patches': [[lit.start, lit.end, 'k']]}}}
    with zipfile.ZipFile(tmp_path / 'out.zip', 'w') as z:
        with pytest.raises(ValueError, match='内部标识 Colossus'):
            write_full_patches(z, root, catalog, {})


def test_display_patch_keeps_compiler_control_flow_and_keys():
    raw = FIXTURE.read_bytes()
    original = Cnut(raw, encrypted=True)
    lit = next(lit for lit in original.literals if lit.text == 'Visible name')
    updated = Cnut(patch_literals(raw, [[lit.start, lit.end, 'v']],
                   {'v': {'source': lit.text, 'translation': '显示名称'}}), encrypted=True)
    for before, after in zip(original.functions, updated.functions):
        assert before['instructions'] == after['instructions']
        for index in protected_literals(before):
            assert before['literals'][index] == after['literals'][index]


def test_screen_ids_and_branched_callback_returns_remain_internal():
    parsed = Cnut(FIXTURE.read_bytes(), encrypted=True)
    functions = {f['name']: f for f in parsed.functions}
    for name in ('createScreens', 'getResult'):
        f = functions[name]
        protected = {f['literals'][index] for index in protected_literals(f)}
        assert {'Overview', 'Success'} <= protected
        assert 'Visible contract text' not in protected
        assert 'Visible payment narration' not in protected
    description = functions['getDescription']
    assert 'Visible returned description' not in {
        description['literals'][index] for index in protected_literals(description)
    }
    first_screen = functions['onDetermineStartScreen']
    assert 'Reward Page' in {first_screen['literals'][i] for i in protected_literals(first_screen)}

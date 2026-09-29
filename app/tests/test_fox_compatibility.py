import io
import json
from pathlib import Path
import zipfile

import pytest

from core.diagnostics import diagnose_mods
from core.modinfo import analyze_zip
from core.modmanager import ModManager
from core.preload_merge import FILENAME
from core.local_mod_archive import staged_packages
from core.dependency_versions import satisfies
from core.modstore import ModStore


def archive(path, files):
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
        for name, content in files.items():
            z.writestr(name, content)
    return path


def script(path, text):
    return archive(path, {'scripts/!mods_preload/' + path.stem + '.nut': text})


def errors(paths):
    return [i for i in diagnose_mods([analyze_zip(p) for p in paths]).issues if i.severity == 'error']


def test_table_constants_not_overwritten_by_unrelated_item_ids(tmp_path):
    path = archive(tmp_path / 'maps.zip', {
        'scripts/!mods_preload/maps.nut': '''::Maps <- {ID="maps", Version="0.5.2", Name="Maps"};
          ::Maps.Hooks <- ::Hooks.register(::Maps.ID, ::Maps.Version, ::Maps.Name);
          ::Maps.Hooks.require("mod_msu >= 1.2.6", "mod_modern_hooks >= 0.4.0");''',
        'scripts/items/maps.nut': 'this.item <- {ID="A", Name="Wrong", Nested={ID="B"}};'
    })
    info = analyze_zip(path)
    assert [(r.mod_id, r.version, r.name) for r in info.registrations] == [('maps', '0.5.2', 'Maps')]
    assert info.requirements == ['mod_msu >= 1.2.6', 'mod_modern_hooks >= 0.4.0']


def test_comments_do_not_create_dependencies_or_registrations(tmp_path):
    path = script(tmp_path / 'comment.zip', '''// ::Hooks.register("fake", "1.0", "fake");
       /* mod.require("missing"); */ ::mods_registerMod("real", 1.0, "Real");''')
    info = analyze_zip(path)
    assert info.api == 'legacy'
    assert info.requirements == []
    assert info.primary_id == 'real'


def test_modern_hooks_adapter_accepts_legacy_semver_strings(tmp_path):
    old = script(tmp_path / 'hooks.zip', '::mods_registerMod("mod_hooks", 21.1, "hooks");')
    modern = script(tmp_path / 'modern.zip', '::Hooks.register("mod_modern_hooks", "0.6.0", "modern");')
    mod = script(tmp_path / 'mod.zip', '::mods_registerMod("legacy", "1.2.3", "legacy");')
    assert any('版本号' in i.title for i in errors([old, mod]))
    assert errors([old, modern, mod]) == []


def test_tabard_numeric_literal_matches_squirrel_effective_version(tmp_path):
    info = analyze_zip(script(tmp_path / 'tabards.zip', '::mods_registerMod("tabards", 1.5.2024, "Tabards");'))
    assert info.registrations[0].version == '1.5'
    assert info.registrations[0].numeric_version_ok


def test_msu_does_not_imply_modern_hooks_for_old_api(tmp_path):
    info = analyze_zip(script(tmp_path / 'mod.zip', '::mods_registerMod("x", 1); ::MSU.Class.Mod("x", "1.0.0", "X");'))
    assert info.api == 'legacy'
    assert info.uses_msu


def test_version_qualified_conflict_accepts_newer_legends(tmp_path):
    modern = script(tmp_path / 'modern.zip', '::Hooks.register("mod_modern_hooks", "0.6.0");')
    mod = script(tmp_path / 'mod.zip', '::Hooks.register("x", "1.0.0"); x.conflictWith("mod_legends < 19.0.0");')
    legends = script(tmp_path / 'legends.zip', '::Hooks.register("mod_legends", "19.3.0");')
    assert errors([modern, mod, legends]) == []
    script(legends, '::Hooks.register("mod_legends", "18.0.0");')
    assert any('冲突' in i.title for i in errors([modern, mod, legends]))


@pytest.mark.parametrize('requirement,version,expected', [
    ('mod_msu >= 1.0.0-beta.4', '1.9.0', True),
    ('mod_msu >= 1.0.0-beta.4', '1.0.0-beta.3', False),
    ('mod_msu >= 1.0.0', '1.0.0-beta', False),
])
def test_collection_prerelease_requirements(requirement, version, expected):
    assert satisfies(requirement, version) is expected


def test_ui_backup_zip_is_not_installed_as_second_mod(tmp_path):
    inner = io.BytesIO()
    with zipfile.ZipFile(inner, 'w') as z:
        z.writestr('scripts/!mods_preload/old.nut', '// old version')
    outer = archive(tmp_path / 'mod.zip', {'scripts/current.nut': '// current', 'ui/old.zip': inner.getvalue()})
    staging = tmp_path / 'stage'; staging.mkdir()
    assert [p.name for p in staged_packages(outer, staging)] == ['mod.zip']


def test_batch_dependency_checks_and_removal_are_atomic(tmp_path):
    game = tmp_path / 'game'; (game / 'data').mkdir(parents=True)
    manager = ModManager(game)
    hooks = script(tmp_path / 'hooks.zip', '::mods_registerMod("mod_hooks", 21.1);')
    mod = script(tmp_path / 'mod.zip', '::mods_registerMod("consumer", 1);')
    with pytest.raises(ValueError, match='Modding Script Hooks'):
        manager.install(mod)
    assert manager.scan() == []
    manager.install_many([mod, hooks])
    with pytest.raises(ValueError):
        manager.disable(hooks.name)
    with pytest.raises(ValueError):
        manager.uninstall(hooks.name)
    assert all(m.enabled for m in manager.scan())
    manager.set_enabled_many([mod.name, hooks.name], False)
    manager.set_enabled_many([mod.name, hooks.name], True)
    assert all(m.enabled for m in manager.scan())


def test_star_variants_rejected_before_any_file_is_written(tmp_path):
    game = tmp_path / 'game'; (game / 'data').mkdir(parents=True)
    paths = [archive(tmp_path / n, {'ui/x.js': '// data'}) for n in
             ['轻度显星-仅显示成长星.zip', '显星显属性带评价（影响存档）.zip']]
    manager = ModManager(game)
    with pytest.raises(ValueError, match='显星'):
        manager.install_many(paths)
    assert manager.scan() == []


def test_preload_union_preserves_base_and_rebuilds_on_profile_and_uninstall(tmp_path):
    game = tmp_path / 'game'; (game / 'data').mkdir(parents=True)
    official = archive(game / 'data/data_001.dat', {'preload/on_running.txt': 'gfx/base.png\n'})
    original = official.read_bytes()
    a = archive(tmp_path / 'a.zip', {'preload/on_running.txt': 'gfx/a.png\n'})
    b = archive(tmp_path / 'b.zip', {'preload/on_running.txt': 'gfx/b.png\ngfx/a.png\n'})
    manager = ModManager(game)
    manager.install_many([a, b]); manager.save_profile('both')
    def lines():
        with zipfile.ZipFile(game / 'data' / FILENAME) as z:
            return set(z.read('preload/on_running.txt').decode().splitlines())
    assert lines() == {'gfx/base.png', 'gfx/a.png', 'gfx/b.png'}
    assert FILENAME not in manager.installed_zip_names()
    manager.disable('b.zip')
    assert lines() == {'gfx/base.png', 'gfx/a.png'}
    manager.apply_profile('both')
    assert 'gfx/b.png' in lines()
    manager.uninstall('b.zip'); manager.uninstall('a.zip')
    assert not (game / 'data' / FILENAME).exists()
    assert official.read_bytes() == original


def test_repository_parent_translation_name_does_not_misclassify_every_mod(tmp_path):
    root = tmp_path / '狐狸汉化精选MOD合集'
    archive(root / '基础功能MOD/unknown.zip', {'ui/test.js': '// test'})
    assert ModStore([root]).scan()[0].category == '基础功能'


def test_reviewed_collection_mapping_is_complete_and_ascii():
    from core.paths import resource_path
    rows = json.loads(resource_path('data/fox_collection.json').read_text(encoding='utf-8'))
    assert len(rows) == 51
    assert len({r['install_name'] for r in rows}) == 51
    assert all(r['install_name'].isascii() and len(r['source_sha256']) == 64 for r in rows)


def test_compiled_and_source_overrides_are_same_script(tmp_path):
    a = archive(tmp_path / 'a.zip', {'scripts/contracts/arena.cnut': b'fixture'})
    b = archive(tmp_path / 'b.zip', {'scripts/contracts/arena.nut': '// source'})
    report = diagnose_mods([analyze_zip(a), analyze_zip(b)])
    assert any('覆盖' in i.title and 'arena.nut' in i.detail for i in report.issues)


def test_package_metadata_is_not_a_game_file_conflict(tmp_path):
    a = script(tmp_path / 'a.zip', '::Hooks.register("mod_modern_hooks", "0.6.0");')
    b = script(tmp_path / 'b.zip', '::Hooks.register("consumer", "1.0.0");')
    for path in (a, b):
        with zipfile.ZipFile(path, 'a') as z:
            z.writestr('BBMOD_COLLECTION.json', '{}')
    assert not any('覆盖' in i.title for i in diagnose_mods([analyze_zip(a), analyze_zip(b)]).issues)

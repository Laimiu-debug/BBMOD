import hashlib
import json
import zipfile
from unittest.mock import patch

import pytest

from core import l10n
from core.modmanager import ModManager


@pytest.fixture
def game_root(tmp_path):
    root = tmp_path / "game"
    (root / "data").mkdir(parents=True)
    with zipfile.ZipFile(root / "data/data_001.dat", "w") as archive:
        archive.writestr("ui/main.html", '<html><head><script src="game.js"></script></head><body></body></html>')
        archive.writestr("scripts/original.cnut", b"ORIGINAL GAME LOGIC")
    return root


@pytest.fixture(autouse=True)
def isolated_catalog(monkeypatch):
    # These fixtures contain only a tiny official-style UI archive, even after
    # a full catalog has been published in the developer's real workspace.
    monkeypatch.setattr(l10n, 'load_full_catalog', lambda: None)


def test_full_catalog_review_and_display_fallback_survive_packaging(game_root, tmp_path, monkeypatch):
    from core import full_l10n, map_labels
    source = 'New Campaign'
    catalog = {'schema_version':1, 'scope_description':'独立初译', 'translation_stage':'complete_draft',
               'files':{}, 'display_fallbacks':{'Overview':'委托概览', 'AP to switch.':'旧的切换提示'},
               'entries':{'entry':{'source':source, 'translation':'校对后的新战役', 'category':'ui', 'status':'reviewed'}}}
    published = tmp_path/'catalog.json'
    published.write_text(json.dumps(catalog), encoding='utf8')
    monkeypatch.setattr(l10n, 'load_full_catalog', lambda: catalog)
    monkeypatch.setattr(full_l10n, 'FULL_CATALOG_FILE', published)
    monkeypatch.setattr(map_labels, 'check_executable', lambda _: None)
    assert l10n.translated_catalog()[source] == '校对后的新战役'
    output = tmp_path/'full.zip'
    l10n.build_localization(game_root, {source:'用户指定新战役'}, output)
    with zipfile.ZipFile(output) as z:
        dictionary = json.loads(z.read(l10n.UI_ROOT+'dictionary.js').decode().partition(' = ')[2].rstrip(';\n'))
        assert dictionary[source] == '用户指定新战役'
        assert dictionary['Overview'] == '委托概览'
        assert dictionary['AP to switch.'] == '点行动点（切换装备）。'
        assert dictionary.get('s', 's') == 's'


def test_build_uses_only_base_ui_and_independent_assets(game_root, tmp_path):
    archive = game_root / "data/data_001.dat"
    before = hashlib.sha256(archive.read_bytes()).hexdigest()
    output = tmp_path / l10n.PACKAGE_NAME
    result = l10n.build_localization(game_root, {"New Campaign": "独立测试译文"}, output)
    assert result["entries"] == len(l10n.load_catalog()[1])
    assert result["overrides_applied"] == 1
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == before
    with zipfile.ZipFile(output) as zf:
        assert zf.testzip() is None
        assert not any(name.startswith("scripts/") for name in zf.namelist())
        assert len(zf.namelist()) == 7
        assert b"independent localization" in zf.read("ui/main.html")
        script = zf.read(l10n.UI_ROOT + "dictionary.js").decode()
        dictionary = json.loads(script.partition(" = ")[2].rstrip(";\n"))
        assert dictionary["New Campaign"] == "独立测试译文"
        assert zf.read(l10n.FONT_ENTRY)[:4] == b"\x00\x01\x00\x00"
    assert l10n.is_bbmod_l10n(output)


def test_invalid_input_does_not_truncate_last_package(game_root, tmp_path):
    output = tmp_path / l10n.PACKAGE_NAME
    output.write_bytes(b"last usable package")
    with pytest.raises(ValueError, match="未知条目"):
        l10n.build_localization(game_root, {"unknown": "不应写入"}, output)
    assert output.read_bytes() == b"last usable package"


def test_modified_base_with_hook_injection_is_rejected(game_root, tmp_path):
    with zipfile.ZipFile(game_root / "data/data_001.dat", "w") as archive:
        archive.writestr("ui/main.html", '<html><head><script src="mod_hooks.js"></script></head></html>')
    with pytest.raises(ValueError, match="第三方注入"):
        l10n.build_localization(game_root, {}, tmp_path / "out.zip")


def test_legacy_rebrand_package_is_not_our_independent_package(tmp_path):
    old = tmp_path / "legacy.zip"
    with zipfile.ZipFile(old, "w") as archive:
        archive.writestr(l10n.BRAND_META, '{"brand":"BBMOD 汉化"}')
    assert not l10n.is_bbmod_l10n(old)


def test_install_conflict_preserves_both_game_and_external_mod(game_root, tmp_path):
    package = tmp_path / l10n.PACKAGE_NAME
    l10n.build_localization(game_root, {}, package)
    conflict = game_root / "data/another_ui_mod.zip"
    with zipfile.ZipFile(conflict, "w") as archive:
        archive.writestr("ui/main.html", "another mod")
    before = conflict.read_bytes()
    with patch("core.game.is_game_running", return_value=False):
        with pytest.raises(RuntimeError, match="相同的游戏文件"):
            l10n.install_localization(ModManager(game_root), package)
    assert conflict.read_bytes() == before
    assert not (game_root / "data" / package.name).exists()


def test_install_in_isolated_game(game_root, tmp_path):
    package = tmp_path / l10n.PACKAGE_NAME
    l10n.build_localization(game_root, {}, package)
    with patch("core.game.is_game_running", return_value=False):
        l10n.install_localization(ModManager(game_root), package)
    assert (game_root / "data" / package.name).read_bytes() == package.read_bytes()

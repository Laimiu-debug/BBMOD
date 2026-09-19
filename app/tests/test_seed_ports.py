import subprocess
from itertools import product
from types import SimpleNamespace

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from core.paths import resource_path
from core.seedgen.config_emitter import write_configs
from core.settings import Settings
from ui.seedgen_page import SeedGenPage


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def context(tmp_path):
    settings = Settings.__new__(Settings)
    settings.path, settings.data = tmp_path / "settings.json", {}
    return SimpleNamespace(game=None, settings=settings)


def test_port_choices_persist_and_only_apply_in_map_modes(app, context):
    page = SeedGenPage(context)
    assert not page.north_south_ports.isChecked() and not page.arena_port.isChecked()
    page.show()
    page.filter_tabs.setCurrentIndex(1)
    for widget in (page.north_south_ports, page.arena_port):
        widget.setFocus()
        QTest.keyClick(widget, Qt.Key_Space)
        assert widget.isChecked()
    page.port_count.setValue(2)
    page.city_count.setValue(20)
    page.armorsmith_count.setValue(3)
    expected = page._current_config().map_conditions
    page.close()
    context.settings.load()  # Read the saved file, not the previous in-memory state.
    reopened = SeedGenPage(context)
    assert reopened.north_south_ports.isChecked() and reopened.arena_port.isChecked()
    assert (reopened.port_count.value(), reopened.city_count.value(), reopened.armorsmith_count.value()) == (2, 20, 3)
    for mode in ("只找地图", "人物 + 地图", "人物 + 地图 + 红装"):
        reopened.mode_combo.setCurrentText(mode)
        assert reopened.filter_tabs.isTabEnabled(1)
        assert reopened._current_config().map_conditions == expected
    for mode in ("只找开局兄弟（快）", "只找红装", "人物 + 红装"):
        reopened.mode_combo.setCurrentText(mode)
        assert not reopened.filter_tabs.isTabEnabled(1)
        assert reopened._current_config().map_conditions is None
    reopened.close()


@pytest.mark.parametrize("north_south,arena", product((False, True), repeat=2))
def test_emitted_port_options_in_actual_squirrel_checker(app, context, tmp_path, north_south, arena):
    sq = resource_path("build/full-l10n/tools/bin/sq.exe")
    if not sq.is_file():
        pytest.skip("Offline Squirrel interpreter unavailable")
    page = SeedGenPage(context)
    page.mode_combo.setCurrentText("只找地图")
    page.port_count.setValue(7)
    page.city_count.setValue(22)
    page.armorsmith_count.setValue(2)
    page.north_south_ports.setChecked(north_south)
    page.arena_port.setChecked(arena)
    write_configs(resource_path("seedgen/payload"), tmp_path, page._current_config())
    page.close()
    source = r'''
::SeedGenerator <- {};
::include <- function(path) { dofile(path + ".nut"); };
include("seed_generator/config_common");
include("seed_generator/config_map_condition");
include("seed_generator/function_map_output_check");
local S = ::SeedGenerator;
assert(S.CommonConfig.GenerateSettlementMode && S.CommonConfig.OnlyPrintMatchingSettlement);
S.port_num <- 7; S.settlements_num <- 22; S.armorsmith_num <- 2;
S.city_port_num <- 2; S.port_location <- [1,1,1,2,2]; S.arena_port <- 1;
S.logError <- function(message) { throw message; };
local cases = 0;
local run = function(positions, arenaPort, ports, towns, armor, expected) {
    S.port_location = positions; S.arena_port = arenaPort; S.port_num = ports;
    S.settlements_num = towns; S.armorsmith_num = armor;
    assert((S.mapOutputCheck() >= 0) == expected); cases++;
};
run([1,1,1,2,2], 1, 7, 22, 2, true);
run([0,1,2,2,2], 1, 7, 22, 2, NORTH_OPTIONAL);
run([1,0,2,2,2], 1, 7, 22, 2, NORTH_OPTIONAL);
run([0,0,0,4,3], 1, 7, 22, 2, NORTH_OPTIONAL);
run([1,1,1,2,2], 0, 7, 22, 2, ARENA_OPTIONAL);
run([1,1,1,1,2], 1, 6, 22, 2, false);
run([1,1,1,2,2], 1, 7, 21, 2, false);
run([1,1,1,2,2], 1, 7, 22, 1, false);
print("PORT_FILTER_PASS cases=" + cases + "\n");
'''
    source = source.replace("NORTH_OPTIONAL", str(not north_south).lower())
    source = source.replace("ARENA_OPTIONAL", str(not arena).lower())
    script = tmp_path / "ports.nut"
    script.write_text(source, encoding="utf-8")
    result = subprocess.run([str(sq), str(script)], cwd=tmp_path, capture_output=True, timeout=15)
    assert result.returncode == 0 and not result.stderr and b"PORT_FILTER_PASS cases=8" in result.stdout, (result.stdout + result.stderr).decode(errors="replace")

"""Offline checks only: temporary files, Qt widgets, and the Squirrel VM."""
import subprocess
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest

from core.game import check_base_archive, GameInfo
from core.gamelog import LogRow
from core.paths import resource_path
from core.seedgen.config_emitter import CampaignConfig, SeedGenConfig, ORIGIN_LABELS, emit_campaign
from core.seedgen.log_watcher import SeedLogParser
from core.seedgen.orchestrator import SeedGenOrchestrator
from core.seedgen.presentation import format_seed


def rows(*texts):
    return [LogRow("info", "", "SQ", text) for text in texts]


def archive_at(root, year=2026):
    root.mkdir(parents=True, exist_ok=True)
    path = root / "data_001.dat"
    with zipfile.ZipFile(path, "w") as archive:
        entry = zipfile.ZipInfo("scripts/unmodified.nut", (year, 1, 1, 0, 0, 0))
        archive.writestr(entry, "unchanged game content")
    return path


def test_archive_dates_do_not_establish_translation_or_seed_changes(tmp_path):
    path = archive_at(tmp_path)
    status = check_base_archive(tmp_path)
    assert status.entry_count == status.recent_entries == 1
    assert "不能证明" in status.warning and "未校验内容" in status.summary
    archive_at(tmp_path, year=2020)
    assert "未校验内容" in check_base_archive(tmp_path).summary
    path.write_bytes(b"broken archive")
    assert check_base_archive(tmp_path).read_error
    with zipfile.ZipFile(path, "w"):
        pass
    assert check_base_archive(tmp_path).read_error == "档案为空"


@pytest.mark.parametrize("campaign", [CampaignConfig(origin="common"), CampaignConfig(origin="scenario.random"),
    CampaignConfig(origin='x";print(1)'), CampaignConfig(combat_difficulty=3),
    CampaignConfig(economic_difficulty=True), CampaignConfig(budget_difficulty=-1)])
def test_invalid_campaign_is_rejected(campaign):
    with pytest.raises(ValueError):
        emit_campaign(campaign)


def test_session_marker_excludes_previous_run_results_and_errors():
    parser = SeedLogParser(session_id="new-session")
    head = "Seed: ABCDEFGHIJ LoopIdx:7 BroOutputType:0 Origin:scenario.militia"
    results, progress = parser.feed(rows("BBMODSeedSession: old-session", "BBMODSeedStart: error settings-mismatch",
        head, "CRLF", "LoopIdx: 999(3) 0.8", "BBMODSeedSession: new-session", "BBMODSeedStart: requested scenario.militia"))
    assert results == progress == [] and parser.startup.stage == "requested"
    results, _ = parser.feed(rows("BBMODSeedStart: generating scenario.militia", head, "CRLF"))
    assert len(results) == 1 and parser.startup.stage == "generating"
    parser.feed(rows("BBMODSeedStart: error origin-unavailable scenario.militia"))
    assert parser.startup.stage == "error"


def test_prepare_launch_and_restore_use_selected_campaign_and_exact_directory(tmp_path):
    data = tmp_path / "game/data"
    base = archive_at(data)
    original = base.read_bytes()
    game = GameInfo(data.parent, data.parent / "win32/BattleBrothers.exe", "1.5.2.3", data)
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    session = SeedGenOrchestrator(game, resource_path("seedgen/payload"))
    campaign = CampaignConfig(origin="scenario.gladiators", combat_difficulty=2, budget_difficulty=0)
    with patch("core.seedgen.orchestrator.game_mod.is_game_running", return_value=False), \
         patch("core.seedgen.orchestrator.game_mod.launch_game", return_value=True) as launch, \
         patch("core.seedgen.orchestrator.game_mod.find_log_write_paths", return_value=[log_dir]):
        assert session.prepare(SeedGenConfig(campaign=campaign)) == []  # Recent dates do not block startup.
        emitted = (data / "seed_generator/config_campaign.nut").read_text(encoding="utf-8")
        assert 'Origin = "scenario.gladiators"' in emitted and "Difficulty = 2" in emitted
        assert session.launch()
        launch.assert_called_once_with(game, via_steam=False)
        campaign.combat_difficulty = 0  # Captured settings must survive later edits.
        with patch.object(session._reader, "read_new", return_value=rows(
            "BBMODSeedSession: " + session._session_id, "BBMODSeedStart: generating scenario.gladiators",
            "Seed: ABCDEFGHIJ LoopIdx:1 Origin:scenario.gladiators", "CRLF")):
            results, _ = session.poll()
        assert len(results) == 1 and results[0].combat_difficulty == 2
        for mode in ("detail", "danmaku"):
            text = format_seed(results[0], mode)
            assert "战斗专家" in text and "经济老兵" in text and "资金高" in text
        assert format_seed(results[0], "seed") == "ABCDEFGHIJ"
        session.stop_and_restore()
    assert base.read_bytes() == original
    assert not (data / "seed_generator/config_campaign.nut").exists()
    assert not (data / "seed_generator/function_auto_start.nut").exists()


def test_actual_game_menu_entry_and_bootstrap_in_squirrel(tmp_path):
    """Exercise the installed game's extracted menu code without starting its EXE."""
    sq = resource_path("build/full-l10n/tools/bin/sq.exe")
    menu = resource_path("build/full-l10n/decompiled/scripts/states/main_menu_state.nut")
    if not sq.is_file() or not menu.is_file():
        pytest.skip("Local offline Squirrel interpreter and game source are required")
    payload = resource_path("seedgen/payload")
    # The actual game menu implements scenario lookup and passes settings to
    # WorldState. Only engine services and the infinite generator are stubbed.
    harness = r'''
::SeedGenerator <- {};
::inherit <- function(basePath, object) { return object; };
::log <- [];
::logInfo <- function(text) { ::log.append(text); };
::logError <- ::logInfo;
::hooks <- {};
::mods_hookClass <- function(path, callback) { ::hooks[path] <- callback; };
::Const <- { PlayerBanners = ["banner_01"] };
::Math <- { rand = function(a, b) { throw "bootstrap consumed RNG"; } };
::shown <- 0;
::attempts <- 0;
::runs <- 0;
::available <- true;
::valid <- true;
::demo <- false;
::throwDuringGeneration <- false;
::scenario <- { getID = function() { return ::SeedGenerator.CampaignConfig.Origin; },
    isValid = function() { return ::valid; } };
::manager <- { getScenario = function(id) { return ::available ? ::scenario : null; } };
::world <- { m = { CampaignSettings = null },
    setNewCampaignSettings = function(settings) { this.m.CampaignSettings = settings; },
    startNewCampaign = function() { ::runs++; if (::throwDuringGeneration) throw "simulated engine failure"; },
    logInfo = ::logInfo, logError = ::logError };
'''
    harness += f'dofile("{menu.as_posix()}");\n'
    harness += emit_campaign(CampaignConfig(), "a" * 32)
    harness += r'''
dofile("seed_generator/function_auto_start.nut");
local menu = ::main_menu_state;
menu.isScenarioDemo <- function() { return ::demo; };
menu.sendMessageToSiblings <- function(text) { assert(text == "FullyLoaded"); ::shown++; };
menu.logInfo <- ::logInfo;
menu.logError <- ::logError;
menu.Const <- ::Const;
menu.hide <- function() {};
menu.LoadingScreen <- { show = function() { ::attempts++; } };
menu.RootState <- {
    add = function(name, path) { assert(name == "WorldState"); ::main_menu_state.onSiblingAdded(name); },
    get = function(name) { return ::world; }
};
menu.m.MenuStack = { popAll = function() {} };
menu.m.ScenarioManager = ::manager;
::hooks["states/main_menu_state"](menu);
::hooks["states/world_state"](::world);
'''
    origins = [key for key in ORIGIN_LABELS if key != "common"]
    harness += 'local origins = [' + ','.join(f'"{origin}"' for origin in origins) + '];\n'
    harness += r'''
foreach (origin in origins) {
    for (local difficulty = 0; difficulty < 3; difficulty++) {
        ::SeedGenerator.AutoStartAttempted = false;
        local cfg = ::SeedGenerator.CampaignConfig;
        cfg.Origin = origin;
        cfg.Difficulty = difficulty;
        cfg.EconomicDifficulty = (difficulty + 1) % 3;
        cfg.BudgetDifficulty = (difficulty + 2) % 3;
        local before = ::attempts;
        menu.m.SelectedCampaignFileName = "existing_user_save";
        menu.main_menu_screen_onScreenShown();
        menu.main_menu_screen_onScreenShown();
        assert(::attempts == before + 1); // Exactly once, even after duplicate UI callbacks.
        assert(menu.m.SelectedCampaignFileName == null);
        menu.loading_screen_onScreenShown();
        local settings = ::world.m.CampaignSettings;
        assert(settings.StartingScenario.getID() == origin);
        assert(settings.Difficulty == difficulty);
        assert(settings.EconomicDifficulty == cfg.EconomicDifficulty);
        assert(settings.BudgetDifficulty == cfg.BudgetDifficulty);
        assert(settings.Name == "BBMOD Seed Search" && settings.Banner == "banner_01");
        assert(!settings.Ironman && !settings.ExplorationMode && !settings.PermanentDestruction);
        assert(settings.GreaterEvil == 0 && settings.Seed.len() == 10);
        ::world.startNewCampaign();
    }
}
assert(::runs == origins.len() * 3);
local expectedAttempts = ::attempts;
foreach (mode in ["missing", "invalid", "demo", "banner"]) {
    ::SeedGenerator.AutoStartAttempted = false;
    ::available = mode != "missing";
    ::valid = mode != "invalid";
    ::demo = mode == "demo";
    ::Const.PlayerBanners = mode == "banner" ? [] : ["banner_01"];
    menu.main_menu_screen_onScreenShown();
    assert(::attempts == expectedAttempts); // No vanilla tutorial fallback.
    assert(::log.top().find("BBMODSeedStart: error") == 0);
}
::world.m.CampaignSettings.StartingScenario = { getID = function() { return "scenario.tutorial"; } };
local prevented = false;
try { ::world.startNewCampaign(); } catch (error) { prevented = true; }
assert(prevented && ::runs == origins.len() * 3);
::world.m.CampaignSettings.StartingScenario = ::scenario;
::world.m.CampaignSettings.Difficulty = 99;
prevented = false;
try { ::world.startNewCampaign(); } catch (error) { prevented = true; }
assert(prevented && ::runs == origins.len() * 3);
::world.m.CampaignSettings.Difficulty = ::SeedGenerator.CampaignConfig.Difficulty;
::throwDuringGeneration = true;
try { ::world.startNewCampaign(); } catch (error) {}
assert(::log.top().find("BBMODSeedStart: error generation-failed") == 0);
print("BBMOD_AUTO_START_PASS campaigns=" + (origins.len() * 3) + "\n");
'''
    script = tmp_path / "autostart.nut"
    script.write_text(harness, encoding="utf-8")
    result = subprocess.run([str(sq), str(script)], cwd=payload, capture_output=True, timeout=15)
    assert result.returncode == 0 and not result.stderr and b"BBMOD_AUTO_START_PASS campaigns=42" in result.stdout, \
        (result.stdout + result.stderr).decode(errors="replace")

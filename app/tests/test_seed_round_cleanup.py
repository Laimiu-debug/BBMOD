"""Run the real search control flow with counters for native engine resources.

This is a lifecycle regression, not an in-game memory or crash acceptance test.
"""

import json
import subprocess

import pytest

from core.paths import resource_path


_HARNESS = r'''
seterrorhandler(function(error) {});
::require <- function(ok, message) { if (!ok) throw message; };
::include <- function(path) {};
::SeedGenerator <- {};
dofile("seed_generator/define_common.nut");
dofile("seed_generator/define_role.nut");
dofile("seed_generator/function_brother_output_check.nut");
local S = ::SeedGenerator;
S.LowestScore <- 0.6;
S.BroOutput <- {};
S.BroOutputConditionArray <- {};
S.MaxRoleArray <- { common = array(9, 10000) };
S.DebugConfig <- { DebugMode = false };
S.CommonConfig <- {
    GenerateSettlementMode = __MAP_MODE__, GenerateBrotherMode = true,
    MatchingBrotherGenerateSettlement = __COMBINED__,
    OnlyPrintMatchingSettlement = __MATCH_MAP__,
    PrintLairInfo = __CAMPS__, PrintLairNamedDetail = true,
    OnlyPrintMatchingLair = __MATCH_LAIR__, EnableLowercaseSeed = false
};
S.EndlessLoopFlag <- false;
S.lair_info_list <- [];
::roundLimit <- __ROUNDS__;
::failureMode <- "__FAILURE__";
::rosterSize <- 0;
::pendingEvents <- 0;
::peakRoster <- 0;
::peakEvents <- 0;
::observedRound <- -1;
::draws <- 0;
::results <- 0;
::brotherResults <- 0;
::campResults <- 0;
::logInfo <- function(message) {};
::Math <- {
    seedRandomString = function(seed) {},
    rand = function(low, high) {
        local round = ::SeedGenerator.CurrentLoop;
        if (round != ::observedRound) {
            ::require(::rosterSize == 0, "roster survived round " + ::observedRound);
            ::require(::pendingEvents == 0, "events survived round " + ::observedRound);
            ::require(::SeedGenerator.lair_info_list.len() == 0,
                "camp item references survived round " + ::observedRound);
            if (round == ::roundLimit) throw "test-complete";
            ::observedRound = round;
        }
        ::draws++;
        return low;
    }
};
::Time <- {
    setVirtualTime = function(time) {}, getExactTime = function() { return 0.0; },
    clearEvents = function() { ::pendingEvents = 0; }
};
::queueEvent <- function() {
    ::pendingEvents++;
    if (::pendingEvents > ::peakEvents) ::peakEvents = ::pendingEvents;
};
::rosterObject <- { clear = function() { ::rosterSize = 0; } };
::World <- {
    Assets = { getStash = function() {
        return { clear = function() {}, resize = function(size) {} };
    } },
    clearScene = function() {}, EntityManager = { clear = function() {} },
    FactionManager = { clear = function() {}, runSimulation = function() {} },
    getPlayerRoster = function() { return ::rosterObject; }
};
S.generateSettlement <- function(seed, state) {
    if (::failureMode == "map-skip" && this.CurrentLoop % 3 == 0) {
        // A rejected map may already own transient callbacks and camp data.
        ::queueEvent();
        this.lair_info_list = [{ round = this.CurrentLoop }];
        return -2;
    }
    if (::failureMode == "map-reject" && this.CurrentLoop % 3 == 0) return -1;
    return 0;
};
dofile("seed_generator/function_generate_brother.nut");
::nativeGenerateBrother <- S.generateBrother;
S.Math <- ::Math;
S.World <- ::World;
S.generateBrother = function(seed, state, forceNative = false) {
    if (forceNative) return ::nativeGenerateBrother.call(this, seed, state, true);
    // Fast search uses value records; only the native alignment path owns actors.
    return [{ Traits = [] }, { Traits = [] }, { Traits = [] }];
};
S.getBroScoreFast <- function(brother) {
    return [array(8, 50), array(8, 80), array(9, 0.8)];
};
S.broOutputCheck <- function(state, scores, brothers, average) { return 0; };
S.generateLairInfo <- function() {
    this.lair_info_list = [{ round = this.CurrentLoop }];
    return ::failureMode == "lair-reject" && this.CurrentLoop % 3 == 0 ? -1 : 0;
};
S.printBroInfo <- function(roster, roles, average, count, brothers, entries) {
    ::require(count == 3 && brothers.len() == 3 && entries.len() == 3,
        "brother results cleared before output");
    ::brotherResults++;
};
S.printLairInfo <- function() {
    ::require(this.lair_info_list.len() == 1
        && this.lair_info_list[0].round == this.CurrentLoop,
        "camp results cleared before output");
    ::campResults++;
};
S.printSettlementInfo <- function() { ::results++; };
::capturedMain <- null;
::mods_hookClass <- function(path, callback) { callback({}); };
::mods_override <- function(object, name, fn) { ::capturedMain = fn; };
dofile(__MAIN_LOOP__);
local state = {
    m = {
        CampaignSettings = {
            Seed = "TEST",
            StartingScenario = {
                getID = function() { return "scenario.early_access"; },
                onSpawnPlayer = function() {
                    ::queueEvent();
                    if (::failureMode == "spawn-fail"
                        && ::SeedGenerator.CurrentLoop % 3 == 0)
                        ::SeedGenerator.EndlessLoopFlag = true;
                }
            }
        },
        IsRunningUpdatesWhilePaused = false,
        Assets = { setCampaignSettings = function(settings) {
            // The game's onSpawnAssets appends to the native player roster.
            ::rosterSize += 3;
            if (::rosterSize > ::peakRoster) ::peakRoster = ::rosterSize;
        } }
    },
    setAutoPause = function(paused) {}, setPause = function(paused) {},
    Math = ::Math, Time = ::Time, World = ::World, logInfo = ::logInfo
};
local completed = false;
try { ::capturedMain.call(state); }
catch (error) {
    if (error == "test-complete") completed = true;
    else print("ROUND_CLEANUP_FAIL " + error + "\n");
}
if (completed) {
    ::require(::peakRoster <= 3 && ::peakEvents <= 1, "native resources grew");
    ::require(::draws == __EXPECTED_DRAWS__, "cleanup changed random draws");
    ::require(::results == __EXPECTED_MAP_RESULTS__, "missing map results");
    ::require(::brotherResults == __EXPECTED_BRO_RESULTS__, "missing brother results");
    ::require(::campResults == __EXPECTED_CAMP_RESULTS__, "missing camp results");
    print("ROUND_CLEANUP_PASS rounds=" + ::roundLimit + "\n");
}
'''


def _script(*, rounds, map_mode, combined, match_map, failure):
    camps = map_mode or combined
    matched = rounds if failure == "none" else rounds - (rounds + 2) // 3
    values = {
        "MAP_MODE": map_mode,
        "COMBINED": combined,
        "MATCH_MAP": match_map,
        "CAMPS": camps,
        "MATCH_LAIR": failure == "lair-reject",
        "ROUNDS": rounds,
        "FAILURE": failure,
        "MAIN_LOOP": json.dumps(str(resource_path(
            "seedgen/payload/seed_generator/function_main_loop.nut")).replace("\\", "/")),
        "EXPECTED_DRAWS": rounds * 10 + ((rounds + 999) // 10000) * 10,
        "EXPECTED_MAP_RESULTS": matched if camps else 0,
        "EXPECTED_BRO_RESULTS": 0 if map_mode else matched,
        "EXPECTED_CAMP_RESULTS": matched if camps else 0,
    }
    source = _HARNESS
    for name, value in values.items():
        if isinstance(value, bool):
            value = str(value).lower()
        source = source.replace(f"__{name}__", str(value))
    return source


@pytest.mark.parametrize(
    "rounds,map_mode,combined,match_map,failure",
    [
        pytest.param(100001, False, True, False, "none", id="fast-combined-100001-rounds"),
        pytest.param(12, False, True, True, "none", id="fast-combined-matching-map"),
        pytest.param(12, True, False, False, "none", id="map-camp"),
        pytest.param(12, False, False, False, "none", id="brother-only"),
        pytest.param(12, True, False, False, "map-skip", id="map-skip"),
        pytest.param(12, False, True, False, "map-skip", id="combined-map-skip"),
        pytest.param(12, True, False, False, "spawn-fail", id="map-spawn-failure"),
        pytest.param(12, False, True, False, "spawn-fail", id="combined-spawn-failure"),
        pytest.param(12, False, True, True, "spawn-fail", id="matching-map-spawn-failure"),
        pytest.param(12, False, True, True, "map-reject", id="map-filter-rejection"),
        pytest.param(12, False, True, False, "lair-reject", id="camp-filter-rejection"),
    ],
)
def test_search_round_releases_native_resources_after_output(
    tmp_path, rounds, map_mode, combined, match_map, failure,
):
    sq = resource_path("build/full-l10n/tools/bin/sq.exe")
    if not sq.is_file():
        pytest.skip("Offline Squirrel interpreter is not installed")
    script = tmp_path / "round_cleanup.nut"
    script.write_text(_script(
        rounds=rounds, map_mode=map_mode, combined=combined,
        match_map=match_map, failure=failure,
    ), encoding="utf-8")
    result = subprocess.run(
        [str(sq), str(script)], cwd=resource_path("seedgen/payload"),
        capture_output=True, timeout=55,
    )
    output = (result.stdout + result.stderr).decode(errors="replace")
    assert result.returncode == 0 and not result.stderr, output
    assert f"ROUND_CLEANUP_PASS rounds={rounds}" in output, output

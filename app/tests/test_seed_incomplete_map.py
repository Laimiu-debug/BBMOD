"""Exercise incomplete-map handling with the original game's map bytecode."""
import json
import subprocess

import pytest

from core.paths import resource_path


def test_incomplete_native_maps_skip_before_roads_and_restore_generator(tmp_path):
    sq = resource_path('build/full-l10n/tools/bin/sq.exe')
    native = resource_path('build/full-l10n/plain/scripts/mapgen/templates/world/worldmap_generator.cnut')
    if not sq.is_file() or not native.is_file():
        pytest.skip('Extracted native map bytecode and offline Squirrel VM required')
    source = r'''
::inherit <- function(path, object) { return object; };
::SeedGenerator <- {};
::include <- function(path) { dofile(path + ".nut"); };
::logInfo <- function(text) {};
::settlements <- [];
::tile <- {getDistanceTo=function(other){return 0;}, RoadDirections=0};
::settlement <- {getTile=function(){return ::tile;}};
::World <- {EntityManager={getSettlements=function(){return ::settlements;}},
 getTileSquare=function(x,y){return ::tile;},
 getNavigator=function(){return {createSettings=function(){return {
  ActionPointCosts=null, RoadMult=0.0, StopAtRoad=false};}};}};
::Const <- {World={Buildings={reset=function(){}}, TerrainType={COUNT=0}, TerrainScript=[]}, DLC={Desert=false}};
'''
    source += 'dofile(' + json.dumps(native.as_posix()) + ');\n'
    source += r'''
local map = ::worldmap_generator;
map.World <- ::World;
map.Const <- ::Const;
map.logInfo <- ::logInfo;
map.__ping <- function() {};
// Confirm the exact reported failure in the unmodified game road builder.
::settlements = [::settlement];
local reproduced = false;
try { map.buildRoads({X=0,Y=0,W=2,H=2}, null); }
catch(error) { assert(error == "the index '0' does not exist"); reproduced = true; }
assert(reproduced);
// Keep the native fill pipeline and replace only engine/spatial services.
foreach(name in ["buildLandAndSea", "buildElevation", "buildTerrain", "defragmentTerrain", "removeStraits",
 "refineTerrain", "refineSettlements", "guaranteeAllBuildingsInSettlements", "buildAdditionalRoads",
 "buildRoadSprites", "buildLabels"]) map[name] = function(...) {};
map.isWorldAcceptable = function(rect) { return true; };
::settlementCount <- 1;
::roadCalls <- 0;
::rngDraws <- 0;
::failure <- "";
map.buildSettlements = function(rect) {
 if (::failure == "settlements") throw "unexpected-engine-failure";
 ::rngDraws++; // Stand in for the unchanged native settlement RNG consumption.
 ::settlements = array(::settlementCount, ::settlement);
};
map.buildRoads = function(rect, properties) {
 ::roadCalls++;
 if (::failure == "roads") throw "the index '0' does not exist";
};
local originalBuild = map.buildSettlements;
dofile("seed_generator/function_generate_settlement.nut");
local S = ::SeedGenerator;
::phases <- [];
S.reportProgress <- function(phase) { ::phases.push(phase); };
foreach(count in [1, 0, 1, 20, 2, 1, 22]) {
 ::settlementCount = count;
 local roadsBefore = ::roadCalls;
 local drawsBefore = ::rngDraws;
 local phasesBefore = ::phases.len();
 local success = S.fillSettlementMap(map, {X=0,Y=0,W=2,H=2});
 assert(success == (count >= 2));
 assert(::roadCalls == roadsBefore + (count >= 2 ? 1 : 0));
 assert(::rngDraws == drawsBefore + 1);
 assert(::phases.len() == phasesBefore + (count >= 2 ? 0 : 1));
 if (count < 2) assert(::phases.top() == "map-skipped");
 assert(map.buildSettlements == originalBuild);
 assert(map.m.Tiles.len() == 0 && map.m.WorldTiles.len() == 0);
}
foreach(failure in ["settlements", "roads"]) {
 ::failure = failure;
 ::settlementCount = 20;
 local caught = false;
 try { S.fillSettlementMap(map, {X=0,Y=0,W=2,H=2}); }
 catch(error) {
  assert(error == (failure == "roads" ? "the index '0' does not exist" : "unexpected-engine-failure"));
  caught = true;
 }
 assert(caught && map.buildSettlements == originalBuild);
}
::failure = "";
assert(S.fillSettlementMap(map, {X=0,Y=0,W=2,H=2}));
// Exercise the production caller: both first-map and matched-brother paths use
// this return code, which the search loop already cleans up and continues.
map.getMinX <- function() { return 2; };
map.getMinY <- function() { return 2; };
::World.resizeScene <- function(x,y) {};
S.World <- ::World;
S.MapGen <- {get=function(name){return ::worldmap_generator;}};
S.NamedIndex <- 0;
S.NamedIndexDict <- {};
::seeds <- [];
S.Math <- {seedRandomString=function(seed){::seeds.push(seed);}};
foreach(count in [0,1]) {
 ::settlementCount = count;
 local roadsBefore = ::roadCalls;
 local seedsBefore = ::seeds.len();
 assert(S.generateSettlement("ABCDEFGHIJ", {}) == -2);
 assert(::seeds.len() == seedsBefore + 1 && ::seeds.top() == "ABCDEFGHIJ");
 assert(::roadCalls == roadsBefore && ::phases.top() == "map-skipped");
 assert(map.buildSettlements == originalBuild);
 assert(map.m.Tiles.len() == 0 && map.m.WorldTiles.len() == 0);
}
print("INCOMPLETE_MAP_PASS native-failure reproduced, skip/normal/error paths verified\n");
'''
    script = tmp_path / 'incomplete_map.nut'
    script.write_text(source, encoding='utf-8')
    result = subprocess.run([str(sq), str(script)], cwd=resource_path('seedgen/payload'),
                            capture_output=True, timeout=20)
    output = (result.stdout + result.stderr).decode(errors='replace')
    assert result.returncode == 0 and not result.stderr, output
    assert 'INCOMPLETE_MAP_PASS' in output, output

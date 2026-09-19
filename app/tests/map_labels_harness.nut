// Run in the real offline Squirrel interpreter, with engine-only APIs stubbed.
local hooks = {};
::mods_hookNewObject <- function(path, callback) { hooks[path] <- callback; };
::mods_hookExactClass <- function(path, callback) { hooks[path] <- callback; };
::logError <- function(text) { print("EXPECTED: " + text + "\n"); };
::logInfo <- function(text) { print(text + "\n"); };
::createVec <- function(x, y) { return { X = x, Y = y }; };
::Settings <- { getVideoMode = function() { return { Width = 1920, Height = 1080, UIScale = 1.5 }; } };
local frames = [], paints = 0;
local screen = { m = { JSHandle = { asyncCall = function(method, frame) { if (method == "bbmodMapLabelsFrame") frames.push(frame); } } },
    isVisible = function() { return true; } };
local camera = { Zoom = 2.0, getPos = function() { return {X = 0, Y = 0}; },
    worldToScreen = function(pos) { return { X = 960 + pos.X / 2, Y = 540 - pos.Y / 2 }; } };
local make = function(id, name, discovered, hidden, party = false) {
    return { ID = id, Name = name, Discovered = discovered, Hidden = hidden, Party = party,
        Label = { Visible = true, Text = name, Offset = { X = 10, Y = 30 },
            Color = { R = 1.0, G = 0.8, B = 0.5, A = 1.0 } },
        isAlive = function() { return true; }, isDiscovered = function() { return this.Discovered; },
        isParty = function() { return this.Party; }, isHiddenToPlayer = function() { return this.Hidden; },
        getID = function() { return this.ID; }, getPos = function() { return { X = 100, Y = 200 }; },
        hasLabel = function(key) { return key == "name"; }, getLabel = function(key) { return this.Label; }
    };
};
local town = make(1, "Wiesendorf", true, false);
local secret = make(2, "Black Monolith", false, false);
local enemy = make(3, "Hidden raiders", true, true, true);
local party = make(4, "Friendly caravan", true, false, true);
local regions = [{ Name = "Stormy Sea", Size = 120, Tiles = [],
    Center = { IsDiscovered = true, Region = 1, Pos = { X = 0, Y = 0 } } },
    { Name = "Secret region", Size = 200, Tiles = [],
    Center = { IsDiscovered = false, Region = 2, Pos = { X = 0, Y = 0 } } }];
::World <- { getCamera = function() { return camera; },
    EntityManager = { getSettlements = function() { return [town]; },
        getLocations = function() { return [town, secret]; } },
    getAllEntitiesAtPos = function(pos, radius) { return [enemy, party]; },
    getAllTilesOfRegion = function(id) { return []; }
};
local state = { getWorldScreen = function() { return screen; }, getRegions = function() { return regions; },
    isInLoadingScreen = function() { return false; },
    onHide = function() {},
    onRender = function() { paints++; }
};
dofile(vargv[0]);
hooks["ui/screens/world/world_screen"](screen);
hooks["states/world_state"](state);
state.onRender();
assert(paints == 1 && frames.len() == 0 && town.Label.Visible);
screen.bbmodMapLabelsReady({ready = true, reason = "test"});
state.onRender();
assert(paints == 2 && frames.len() == 1);
assert(frames[0].labels.len() == 3); // town, visible caravan, discovered region
assert(frames[0].labels[0].x == 1020 && frames[0].labels[0].y == 410);
assert(frames[0].labels[0].text == "Wiesendorf");
assert(town.Label.Visible && party.Label.Visible && secret.Label.Visible && enemy.Label.Visible);
assert(town.Name == "Wiesendorf" && town.Label.Text == "Wiesendorf" && regions[0].Name == "Stormy Sea");
state.onRender();
assert(frames.len() == 1); // unchanged maps do not redraw the canvas
state.onHide();
state.onRender();
assert(frames.len() == 2); // returning to the map refreshes the cleared layer
// Exception during the native draw must restore every suppressed label.
local broken = { getWorldScreen = state.getWorldScreen, getRegions = state.getRegions,
    isInLoadingScreen = state.isInLoadingScreen,
    onHide = function() {},
    onRender = function() { assert(!town.Label.Visible && !party.Label.Visible); throw "render failed"; } };
hooks["states/world_state"](broken);
local caught = false;
try { broken.onRender(); } catch (error) { caught = error == "render failed"; }
assert(caught && town.Label.Visible && party.Label.Visible);
// An unavailable engine API logs once and keeps the original render working.
World.getCamera = function() { throw "camera unavailable"; };
state.onRender();
assert(paints == 5 && town.Label.Visible && BBMODMapLabels.Failed);
print("BBMOD_MOD_MAP_PASS\n");

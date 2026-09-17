// Original BBMOD fixture: the compiler shares keys and display values.
function makeFixture(flag) {
    local table = { Colossus = "Colossus", Steady = "Steady", label = "Visible name" };
    local key = flag ? "North" : "South";
    table[key] <- "Visible description";
    local api = { setBrush = function (name) {}, logWarning = function (text) {} };
    api.setBrush("a brush name");
    api.logWarning("An internal diagnostic");
    return table;
}
local value = makeFixture(true);
assert(value.Colossus == "Colossus");
assert(value.Steady == "Steady");
assert(value.North == "Visible description");
print("Original fixture runs\n");

function createScreens() {
    local screen = { ID = "Overview", Title = "Overview", Text = "Visible contract text" };
    screen.ID = "Success";
    screen.Title = "Success";
    return screen;
}
function getResult(flag) {
    print("Visible payment narration");
    local result = flag ? "Overview" : "Success";
    return result;
}
function getDescription() { return "Visible returned description"; }
function onDetermineStartScreen() { return "Reward Page"; }
assert(getResult(true) == "Overview");
assert(createScreens().ID == "Success");

local hooks = {}, lines = [], originals = 0;
::mods_hookNewObject <- function(path, callback) { hooks[path] <- callback; };
::logInfo <- function(text) { lines.push(text); print(text + "\n"); };
::logWarning <- function(text) { print(text + "\n"); };
::Math <- { rand = function(a,b) { throw "The bridge must not consume RNG"; } };
::Const <- { Items = { ItemType = { Named = 1 } } };
local item = { m = { ID = "armor.body.black_and_gold", Name = "甲 & <test> \"x\"", ConditionMax = 290,
    StaminaModifier = -24, Upgrade = { m = { PreviousCondition = 250, PreviousStamina = -18 } } },
    isItemType = function(type) { return true; }, getName = function() { throw "must not call getName"; } };
local result = [{text = "original"}];
local tooltip = { tactical_helper_addHintsToTooltip = function(a,e,i,o,s=false) { originals++; return result; } };
dofile(vargv[0]);
hooks["ui/screens/tooltip/tooltip_events"](tooltip);
local module = {onQueryUIItemTooltipData = function(data) {
    return tooltip.tactical_helper_addHintsToTooltip(null,null,item,data[2]);
}};
hooks["ui/screens/tooltip/modules/tooltip"](module);
assert(module.bbmodInspectorQuery([null,1,"stash",1]) == result);
assert(module.bbmodInspectorQuery([null,1,"shop",2]) == result);
assert(originals == 2 && ::BBMODItemInspector.Sequence == 2);
assert(item.m.ConditionMax == 290 && item.m.StaminaModifier == -24);
assert(lines[1].find("\"ConditionMax\":250") != null);
assert(lines[2].find("\"token\":2") != null);
module.bbmodInspectorHover([2,true,[100,100,320,600,1920,1080]]); module.bbmodInspectorHover([2,false,null]);
assert(lines[3].find("\"visible\":true") != null && lines[4].find("\"visible\":false") != null);
// Malformed third-party objects cannot break the original tooltip.
::BBMODItemInspector.Token = 3;
assert(tooltip.tactical_helper_addHintsToTooltip(null,null,{},"stash") == result);
::BBMODItemInspector.Token = null;
local seq = ::BBMODItemInspector.Sequence;
// Unrelated tooltip builds never emit a new live record.
assert(tooltip.tactical_helper_addHintsToTooltip(null,null,item,"stash") == result);
assert(::BBMODItemInspector.Sequence == seq);
module.onQueryUIItemTooltipData = function(data) { throw "original failure"; };
try { module.bbmodInspectorQuery([null,1,"stash",3]); assert(false); } catch(e) { assert(e=="original failure"); }
assert(::BBMODItemInspector.Token == null && ::BBMODItemInspector.Snapshot == null);
// Reproduce the game's member proxy: _get works while `key in proxy` is false.
class MemberProxy {
    values = null;
    constructor(data) { this.values = data; }
    function _get(key) { return this.values[key]; }
}
local originalMembers = item.m;
item.m = MemberProxy(originalMembers);
assert(!("ConditionMax" in item.m) && item.m.ConditionMax == 290);
originalMembers.Upgrade.m = MemberProxy(originalMembers.Upgrade.m);
::BBMODItemInspector.read(item);
assert(::BBMODItemInspector.Snapshot.find("\"ConditionMax\":250") != null);
assert(::BBMODItemInspector.Snapshot.find("\"StaminaModifier\":-18") != null);
assert(::BBMODItemInspector.Snapshot.find("\"attachment\":true") != null);
assert(originalMembers.ConditionMax == 290 && originalMembers.StaminaModifier == -24);
local weaponStats = { ID = "weapon.named_greatsword", Name = "test", ConditionMax = 100,
    RegularDamage = 102, RegularDamageMax = 120, DirectDamageMult = 0.25, DirectDamageAdd = 0.16 };
item.m = MemberProxy(weaponStats);
::BBMODItemInspector.read(item);
assert(::BBMODItemInspector.Snapshot.find("\"RegularDamage\":102") != null);
assert(::BBMODItemInspector.Snapshot.find("\"attachment\":false") != null);
print("BBMOD_INSPECTOR_PASS\n");

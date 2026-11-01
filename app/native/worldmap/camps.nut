// Headless campaign services. Campaign rules, faction actions and loot execute
// the pinned original bytecode. Drawing, audio and UI services do not consume RNG.
::CampResult <- {phases=[],calls=0,hash=0,bounded=0,trace=[],phase="",ItemTrace=null};
local originalRand=::Math.rand;
::Math.rand=function(...) {
    local args=[this];foreach(a in vargv)args.push(a);
    local result=originalRand.acall(args);
    ::CampResult.calls++;::CampResult.hash=(::CampResult.hash*33+result)&2147483647;
    if(vargv.len()==2&&vargv[1]>vargv[0])::CampResult.bounded++;
    if((::CampResult.phase=="factions"||::CampResult.phase=="discovery")&&::getenv("BBMOD_WORLDMAP_TRACE")!=null)
        ::CampResult.trace.push({args=vargv,value=result});
    if(::CampResult.ItemTrace!=null)::CampResult.ItemTrace.push({args=vargv,value=result});
    return result;
};
::campCheckpoint <- function(name) {
    ::CampResult.phases.push({name=name,calls=::CampResult.calls,hash=::CampResult.hash,bounded=::CampResult.bounded});
    if(::getenv("BBMOD_WORLDMAP_TRACE")!=null)
        print(::jsonEncode({kind="camp-phase",name=name,calls=::CampResult.calls,hash=::CampResult.hash,
            bounded=::CampResult.bounded,trace=::CampResult.trace})+"\n");
    ::CampResult.calls=0;::CampResult.hash=0;::CampResult.bounded=0;::CampResult.trace=[];::CampResult.phase=name;
    ::_mapTrace("camp:"+name);
};
::Math.round <- function(n,places=0) {
    local scale=::pow(10.0,places),scaled=n*scale;
    return (scaled>=0 ? ::floor(scaled+0.5) : ::ceil(scaled-0.5))/scale;
};
::getVecDistance <- function(a,b){local x=a.X-b.X,y=a.Y-b.Y;return ::sqrt(x*x+y*y);};
::getVecDistanceMult <- ::getVecDistance;
::removeFromBeginningOfText <- function(prefix,text){return text.find(prefix)==0?text.slice(prefix.len()):text;};
::buildTextFromTemplate <- function(text,variables) {
    foreach(v in variables) {
        local token="%"+v[0]+"%",at=text.find(token);
        while(at!=null){text=text.slice(0,at)+v[1]+text.slice(at+token.len());at=text.find(token);}
    }
    local begin=text.find("{");
    while(begin!=null) {
        local end=text.find("}",begin),choices=split(text.slice(begin+1,end),"|");
        // Native text variants use the unseeded legacy stream. Using campaign
        // RNG here changes characters, then every subsequent camp and item.
        local chosen=strip(choices[::_mapLegacyRand()%choices.len()]);
        text=text.slice(0,begin)+chosen+text.slice(end+1);begin=text.find("{");
    }
    return text;
};
::Time.getVirtualTimeF=function(){return 0.0;};
::Time.scheduleEvent <- function(...) {};
::TimeUnit <- {Real=0,Virtual=1};
::TileMethods.HasRiver <- false;
::isAlive <- function(){return true;};
::isHiddenToPlayer <- function(){return true;};
::isParty <- function(){return false;};
::setFactionEx <- ::setFaction;
::updateAchievement <- function(...) {};
::World.spawnParticleEffect <- function(...) {};
::World.uncoverFogOfWar <- function(...) {};
::World.getCamera=function(){return{function isInsideScreen(...){return false;},function setPos(...) {}};};
local existingDLC=::Const.DLC;
::isSteamBuild <- function(){return true;};
::include("scripts/config/global");
::Const.DLC=existingDLC;
::include("scripts/config/ai");
::include("scripts/config/character");
::include("scripts/config/character_names");
::include("scripts/config/character_heads");
::include("scripts/config/character_backgrounds");
::include("scripts/config/character_traits");
::include("scripts/config/character_injuries");
::include("scripts/config/items");
::include("scripts/config/banners");
::include("scripts/config/item_names");
::include("scripts/config/world_assets");
::include("scripts/config/world_parties");
::include("scripts/config/world_scaling");
::include("scripts/config/faction_traits");
::include("scripts/config/faction_traits_archetypes");
::include("scripts/config/spawnlist_master");
foreach(name in ["bandits","barbarians","beasts","goblins","greenskin_invasion","humans","nobles","nomads","orc","southern","undead","undead_scourge","zombies"])
    ::include("scripts/config/spawnlist_"+name);
// Official DLC init only appends data to these pools and display resources.
::Const.Serialization <- {Version=65};
::Const.LoadingScreens <- [];
::Const.TipOfTheDay <- [];
::hasDLC <- function(id){return [732460,961930,1067690,1361280,1910050].find(id)!=null;};
foreach(name in ["Lindwurm","Unhold","Wildmen","Desert","Paladins"])::Const.DLC[name]=false;
foreach(name in ["desert","lindwurm","paladins","unhold","wildmen"])::include("scripts/dlc/dlc_"+name);
::include("scripts/config/world_particles");
if(::WORLD_MAP_STOP=="search") {
    // Apply the same reviewed affix recording used by game-based searches.
    ::mods_hookClass <- function(path,hook){hook(::ruleClass("scripts/"+path));};
    ::mods_override <- function(object,name,value){object[name]=value;};
    ::mods_addField <- function(object,parentName,name,value){object.m[name] <- value;};
    dofile(::WORLD_MAP_RULES+"/search.nut");
}
foreach(path in ["weapons/named/named_weapon","armor/named/named_armor","helmets/named/named_helmet","shields/named/named_shield"]) {
    local prototype=::ruleClass("scripts/items/"+path),randomize=prototype.randomizeValues;
    prototype.randomizeValues=function() {
        local previous=::CampResult.ItemTrace;::CampResult.ItemTrace=[];
        randomize.call(this);this.BBMODRollTrace <- ::CampResult.ItemTrace;::CampResult.ItemTrace=previous;
    };
}

local oldManager=::World.EntityManager;
::World.EntityManager=::new("scripts/entity/world/entity_manager");
::World.EntityManager.m.Settlements=oldManager.Settlements;
::World.EntityManager.m.Locations=oldManager.Locations;
::World.Flags <- ::new("scripts/tools/tag_collection");
::World.Statistics <- {Flags=::new("scripts/tools/tag_collection"),function getFlags(){return this.Flags;}};
::World.Retinue <- {function hasFollower(id){return false;},function update(){}};
::World.Contracts <- {function getActiveContract(){return null;}};
::World.Ambitions <- {function onLocationDiscovered(...) {},function hasActiveAmbition(){return false;}};
::World.State.getCurrentTown <- function(){return null;};
::World.State.getCombatStartTime <- function(){return 0.0;};
::World.State.getPlayer <- function(){return this.m.Player;};
::World.State.m.Player <- null;
::World.CampEntities <- [];
::World.getAllEntitiesAtPos <- function(pos,radius) {
    local result=[];
    foreach(entity in this.EntityManager.getLocations())if(::getVecDistance(pos,entity.getPos())<=radius)result.push(entity);
    foreach(entity in this.CampEntities)if(::getVecDistance(pos,entity.getPos())<=radius)result.push(entity);
    return result;
};
::World.Rosters <- {};
::World.createRoster=function(id){this.Rosters[id] <- {Items=[],function getAll(){return this.Items;},function clear(){this.Items=[];}};};
::World.getRoster <- function(id){return this.Rosters[id];};
::World.getPlayerRoster <- function(){return this.getRoster(1);};
::World.createRoster(1);
dofile(::WORLD_MAP_SCRIPT_DIR+"/actors.nut");
::World.Assets <- ::new("scripts/states/world/asset_manager");
::World.Assets.init();
::World.FactionManager <- ::new("scripts/factions/faction_manager");
// These rosters only supply dialogue portraits. Their initialization precedes
// the campaign reseed, and is unrelated to enemy simulation or camp loot.
foreach(path in ["noble_faction","city_state_faction","settlement_faction"])
    ::ruleClass("scripts/factions/"+path).onUpdateRoster=function() {};
::World.FactionManager.createFactions();
::World.EntityManager.buildRoadAmbushSpots();
::campCheckpoint("factions");

local campaign=("BBMODCampaign" in getroottable())?::BBMODCampaign:
    {Origin="scenario.militia",Difficulty=2,EconomicDifficulty=2,BudgetDifficulty=2};
local origin=::new("scripts/scenarios/world/"+campaign.Origin.slice(9)+"_scenario");
local settings={Name="Battle Brothers",Banner="banner_01",Difficulty=campaign.Difficulty,
    EconomicDifficulty=campaign.EconomicDifficulty,BudgetDifficulty=campaign.BudgetDifficulty,
    Ironman=false,PermanentDestruction=false,ExplorationMode=false,GreaterEvil=0,Seed=::WORLD_MAP_SEED,StartingScenario=origin};
::World.State.m.CampaignSettings <- settings;
::Math.seedRandomString(::WORLD_MAP_SEED);
::World.Assets.updateFormation=function() {};
::World.Assets.updateFood=function() {};
::World.Assets.updateLook=function(...) {};
::World.Assets.setCampaignSettings(settings);
::campCheckpoint("assets");
::World.spawnEntity <- function(path,...) {
    local coords=vargv.len()==1?vargv[0]:{X=vargv[0],Y=vargv[1]};
    local tile=::World.getTile(coords);
    local native={__tile=tile,__nativeID=::World.NextID++,__sprites={},__labels={}};
    local entity=::new(path,native);entity.onInit();
    if("onAfterInit" in entity)entity.onAfterInit();
    ::World.CampEntities.push(entity);
    return entity;
};
origin.onSpawnPlayer();
::campCheckpoint("player");
origin.onInit();
::World.FactionManager.uncoverSettlements(false);
::campCheckpoint("discovery");
if(::WORLD_MAP_STOP=="search") {
    print(::_mapJSONEncode({kind="phase",phase="camps"})+"\n");stdout.flush();
}
if(::WORLD_MAP_STOP!="search"||::SeedGenerator.CommonConfig.PrintLairInfo)
    ::World.FactionManager.runSimulation();
::campCheckpoint("simulation");
local camps=[],names=[];
foreach(town in ::World.EntityManager.getSettlements())names.push(town.getName());
foreach(camp in ::World.EntityManager.getLocations()) {
    if(!camp.isLocationType(::Const.World.LocationType.Lair)&&!camp.isLocationType(::Const.World.LocationType.Unique))continue;
    local xy=camp.getTile().SquareCoords,loot=[];
    foreach(item in camp.getLoot().getItems()) {
        if(item==null||!item.isItemType(::Const.Items.ItemType.Named))continue;
        local stats={};
        foreach(key in ["ConditionMax","StaminaModifier","RegularDamage","RegularDamageMax","ArmorDamageMult","DirectDamageMult",
            "DirectDamageAdd","ChanceToHitHead","ShieldDamage","AmmoMax","AdditionalAccuracy","FatigueOnSkillUse","MeleeDefense","RangedDefense"])
            if(key in item.m)stats[key] <- item.m[key];
        local kind=item.isItemType(::Const.Items.ItemType.MeleeWeapon)||item.isItemType(::Const.Items.ItemType.RangedWeapon)?"weapon":
            item.isItemType(::Const.Items.ItemType.Armor)?"armor":item.isItemType(::Const.Items.ItemType.Helmet)?"helmet":"shield";
        loot.push({id=item.getID(),name=item.getName(),kind=kind,stats=stats,trace=("BBMODRollTrace" in item)?item.BBMODRollTrace:[]});
    }
    camps.push({name=camp.getName(),type=camp.m.TypeID,faction=camp.getFaction(),xy=[xy.X,xy.Y],
        resources=camp.m.Resources,strength=camp.getStrength(),items=loot});
}
local profile=campaign.Origin=="scenario.militia"&&campaign.Difficulty==2&&campaign.EconomicDifficulty==2&&campaign.BudgetDifficulty==2?
    "militia-expert-v1":"official-campaign-v2";
::CampaignResult <- {kind="offline-camps",profile=profile,seed=::WORLD_MAP_SEED,origin=campaign.Origin,
    combat=campaign.Difficulty,economic=campaign.EconomicDifficulty,budget=campaign.BudgetDifficulty,
    camps=camps,settlement_names=names,phases=::CampResult.phases,
    seconds=::_mapElapsed(),
    player_xy=[::World.State.getPlayer().getTile().SquareCoords.X,::World.State.getPlayer().getTile().SquareCoords.Y]};
if(::WORLD_MAP_STOP!="search")print(::_mapJSONEncode(::CampaignResult)+"\n");

// Development-only full campaign oracle. Observe original RNG and item methods.
::BBMODCampReference <- {
    Seeds=__SEEDS__, CurrentSeed="", Calls=0, Hash=0, Phase="", RandomTrace=null, StageTrace=[],
    Campaigns=__CAMPAIGNS__, Case=0,
    TraceRNG=__TRACE_RNG__, PhaseStarted=0.0,
    function quote(value) {
        local result="\"";
        for(local i=0;i<value.len();i++) {
            local c=value[i];
            if(c==34||c==92)result+="\\"+c.tochar();
            else if(c==10)result+="\\n";else if(c==13)result+="\\r";else if(c==9)result+="\\t";
            else if(c>=32)result+=c.tochar();
        }
        return result+"\"";
    },
    function encode(v) {
        local kind=typeof v;
        if(kind=="null")return "null";
        if(kind=="string")return this.quote(v);
        if(kind=="bool")return v?"true":"false";
        if(kind=="integer"||kind=="float")return v.tostring();
        if(kind!="array"&&kind!="table")return "null";
        local result=kind=="array"?"[":"{",n=0;
        foreach(k,x in v) {
            if(typeof x=="function")continue;
            if(n++)result+=",";
            if(kind=="table")result+=this.quote(k)+":";
            result+=this.encode(x);
        }
        return result+(kind=="array"?"]":"}");
    },
    function emit(kind,value) {value["case"] <- this.Case;::logInfo("BBMODMapReference: "+kind+" "+this.encode(value));},
    function checkpoint(name) {
        local value={seed=this.CurrentSeed,name=name,calls=this.Calls,hash=this.Hash,
            seconds=::Time.getExactTime()-this.PhaseStarted};
        if(name=="player") {
            local xy=::World.State.getPlayer().getTile().SquareCoords;
            value.xy <- [xy.X,xy.Y];
        }
        this.emit("phase",value);
        for(local offset=0;offset<this.StageTrace.len();offset+=32)
            this.emit("rng-trace",{seed=this.CurrentSeed,name=name,offset=offset,values=this.StageTrace.slice(offset,::Math.min(offset+32,this.StageTrace.len()))});
        this.Calls=0;this.Hash=0;this.Phase=name;this.StageTrace=[];this.PhaseStarted=::Time.getExactTime();
    },
    function item(item) {
        local stats={};
        foreach(key in ["ConditionMax","StaminaModifier","RegularDamage","RegularDamageMax","ArmorDamageMult",
            "DirectDamageMult","DirectDamageAdd","ChanceToHitHead","ShieldDamage","AmmoMax","AdditionalAccuracy",
            "FatigueOnSkillUse","MeleeDefense","RangedDefense"])
            try {stats[key] <- item.m[key];} catch(error) {}
        local kind=item.isItemType(::Const.Items.ItemType.MeleeWeapon)||item.isItemType(::Const.Items.ItemType.RangedWeapon)?"weapon":
            item.isItemType(::Const.Items.ItemType.Armor)?"armor":item.isItemType(::Const.Items.ItemType.Helmet)?"helmet":"shield";
        return {id=item.getID(),name=item.getName(),kind=kind,stats=stats,
            trace=("BBMODRollTrace" in item)?item.BBMODRollTrace:[]};
    },
    function dump() {
        local towns=::World.EntityManager.getSettlements();
        foreach(index,town in towns) {
            local xy=town.getTile().SquareCoords;
            this.emit("campaign-town",{seed=this.CurrentSeed,index=index,name=town.getName(),xy=[xy.X,xy.Y],culture=town.getCulture()});
        }
        local camps=0,items=0;
        foreach(camp in ::World.EntityManager.getLocations()) {
            if(!camp.isLocationType(::Const.World.LocationType.Lair)&&!camp.isLocationType(::Const.World.LocationType.Unique))continue;
            local xy=camp.getTile().SquareCoords,loot=[];
            foreach(item in camp.getLoot().getItems())
                if(item!=null&&item.isItemType(::Const.Items.ItemType.Named))loot.push(this.item(item));
            this.emit("camp",{seed=this.CurrentSeed,name=camp.getName(),type=camp.m.TypeID,faction=camp.getFaction(),
                xy=[xy.X,xy.Y],resources=camp.m.Resources,strength=camp.getStrength(),items=loot,hidden=camp.isHiddenToPlayer()});
            camps++;items+=loot.len();
        }
        this.emit("seed-end",{seed=this.CurrentSeed,camps=camps,items=items});
    }
};
local originalRand=::Math.rand;
::Math.rand=function(...) {
    local args=[this];foreach(a in vargv)args.push(a);
    local result=originalRand.acall(args),R=::BBMODCampReference;
    R.Calls++;R.Hash=(R.Hash*33+result)&2147483647;
    if(R.RandomTrace!=null)R.RandomTrace.push({args=vargv,value=result});
    if(R.TraceRNG&&(R.Phase=="factions"||R.Phase=="assets"||R.Phase=="discovery"))R.StageTrace.push({args=vargv,value=result});
    return result;
};
foreach(path in ["items/weapons/named/named_weapon","items/armor/named/named_armor","items/helmets/named/named_helmet","items/shields/named/named_shield"]) {
    ::mods_hookClass(path,function(o) {
        local original=::mods_getMember(o,"randomizeValues");
        ::mods_override(o,"randomizeValues",function() {
            local R=::BBMODCampReference,previous=R.RandomTrace;
            R.RandomTrace=[];
            original.call(this);
            this.BBMODRollTrace <- R.RandomTrace;
            R.RandomTrace=previous;
        });
    });
}
::mods_hookClass("states/world_state",function(o) {
    ::mods_override(o,"autosave",function() {});
    ::mods_override(o,"saveCampaign",function(...) {});
    ::mods_override(o,"startNewCampaign",function() {
        local R=::BBMODCampReference;
        foreach(value in [60.4999961853,58.4999961853,-16.5,-16.4999980927,0.4999999702,-0.5,16.5,60.5])
            R.emit("rounding",{input=::format("%.9g",value),rounded=::Math.round(value)});
        this.setAutoPause(true);this.Time.setVirtualTime(0);this.setPause(true);
        this.m.IsRunningUpdatesWhilePaused=true;
        local generator=::MapGen.get("world.worldmap_generator");
        foreach(caseIndex,config in R.Campaigns) {
        R.Case=caseIndex;
        this.m.CampaignSettings.StartingScenario=::new("scripts/scenarios/world/"+config.origin.slice(9)+"_scenario");
        this.m.CampaignSettings.Difficulty=config.combat;this.m.CampaignSettings.EconomicDifficulty=config.economic;
        this.m.CampaignSettings.BudgetDifficulty=config.budget;
        R.emit("environment",{version="1.5.2.3",dlc=::Const.DLC.Mask,origin=this.m.CampaignSettings.StartingScenario.getID(),
            combat=this.m.CampaignSettings.Difficulty,economic=this.m.CampaignSettings.EconomicDifficulty,
            budget=this.m.CampaignSettings.BudgetDifficulty,
            items=::Const.Items,traits=::Const.FactionTrait.Actions});
        foreach(seed in R.Seeds) {
            // Entity onFinish needs its faction; dispose the native scene first.
            ::World.clearScene();::World.getPlayerRoster().clear();::World.EntityManager.clear();::World.FactionManager.clear();
            ::World.Flags.m.clear();this.m.Player=null;
            this.m.CampaignSettings.Seed=seed;R.CurrentSeed=seed;R.Calls=0;R.Hash=0;R.Phase="";
            R.PhaseStarted=::Time.getExactTime();
            ::Math.seedRandomString(seed);
            ::World.resizeScene(generator.getMinX(),generator.getMinY());
            generator.fill({X=0,Y=0,W=generator.getMinX(),H=generator.getMinY()},null);
            R.checkpoint("geography");
            this.m.Assets.init();::World.FactionManager.createFactions();
            ::World.EntityManager.buildRoadAmbushSpots();R.checkpoint("factions");
            ::Math.seedRandomString(seed);
            this.m.Assets.setCampaignSettings(this.m.CampaignSettings);R.checkpoint("assets");
            this.m.CampaignSettings.StartingScenario.onSpawnPlayer();R.checkpoint("player");
            local members=[];
            foreach(bro in ::World.getPlayerRoster().getAll()) {
                local p=bro.getBaseProperties(),traits=[];
                foreach(s in bro.getSkills().m.Skills)if(s.getType()==::Const.SkillType.Trait)traits.push(s.getID());
                members.push({name=bro.getName(),level=bro.getLevel(),
                    attr=[p.Hitpoints,p.Bravery,p.Stamina,p.MeleeSkill,p.RangedSkill,p.MeleeDefense,p.RangedDefense,p.Initiative],
                    talents=bro.getTalents(),traits=traits,growth=bro.m.Attributes});
            }
            R.emit("brothers",{seed=seed,origin=config.origin,members=members});
            this.m.CampaignSettings.StartingScenario.onInit();
            ::World.uncoverFogOfWar(this.getPlayer().getTile().Pos,900.0);
            ::World.FactionManager.uncoverSettlements(this.m.CampaignSettings.ExplorationMode);R.checkpoint("discovery");
            ::World.FactionManager.runSimulation();R.checkpoint("simulation");R.dump();
        }
        }
        R.emit("done",{seeds=R.Seeds.len()*R.Campaigns.len()});this.m.IsRunningUpdatesWhilePaused=false;
    });
});

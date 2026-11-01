// Development oracle: actual original actors, traits, talents and growth tables.
::BBMODBrotherReference <- {
    Seeds=__SEEDS__,
    function quote(s) {local r="\"";foreach(c in s){if(c==34||c==92)r+="\\";r+=c.tochar();}return r+"\"";},
    function encode(v) {
        if(v==null)return "null";local t=typeof v;
        if(t=="string")return this.quote(v);
        if(t=="integer"||t=="float")return v.tostring();
        local r=t=="array"?"[":"{",i=0;
        foreach(k,x in v){if(i++)r+=",";if(t=="table")r+=this.quote(k)+":";r+=this.encode(x);}
        return r+(t=="array"?"]":"}");
    },
    function emit(kind,v){::logInfo("BBMODMapReference: "+kind+" "+this.encode(v));}
};
::mods_hookClass("states/world_state",function(o) {
    ::mods_override(o,"autosave",function() {});
    ::mods_override(o,"saveCampaign",function(...) {});
    ::mods_override(o,"startNewCampaign",function() {
        this.setAutoPause(true);this.Time.setVirtualTime(0);this.setPause(true);
        this.m.IsRunningUpdatesWhilePaused=true;
        local R=::BBMODBrotherReference;
        local generator=::MapGen.get("world.worldmap_generator");
        foreach(seed in R.Seeds) {
            ::World.clearScene();::World.getPlayerRoster().clear();
            ::World.EntityManager.clear();::World.FactionManager.clear();
            ::World.resizeScene(generator.getMinX(),generator.getMinY());
            ::Math.seedRandomString(seed);
            generator.fill({X=0,Y=0,W=generator.getMinX(),H=generator.getMinY()},null);
            this.m.Assets.init();::World.FactionManager.createFactions();
            foreach(origin in ["early_access","southern_quickstart","trader","militia","lone_wolf","rangers",
                "paladins","raiders","anatomists","beast_hunters","gladiators","manhunters","cultists"]) {
                ::World.getPlayerRoster().clear();
                this.m.CampaignSettings.Seed=seed;
                this.m.CampaignSettings.StartingScenario=::new("scripts/scenarios/world/"+origin+"_scenario");
                this.m.Assets.init();::Math.seedRandomString(seed);
                this.m.Assets.setCampaignSettings(this.m.CampaignSettings);
                local members=[];
                foreach(bro in ::World.getPlayerRoster().getAll()) {
                    local p=bro.getBaseProperties(),traits=[];
                    foreach(s in bro.getSkills().m.Skills)if(s.getType()==::Const.SkillType.Trait)traits.push(s.getID());
                    members.push({name=bro.getName(),level=bro.getLevel(),
                        attr=[p.Hitpoints,p.Bravery,p.Stamina,p.MeleeSkill,p.RangedSkill,p.MeleeDefense,p.RangedDefense,p.Initiative],
                        talents=bro.getTalents(),traits=traits,growth=bro.m.Attributes});
                }
                R.emit("brothers",{seed=seed,origin="scenario."+origin,members=members});
            }
        }
        R.emit("done",{seeds=R.Seeds.len()});this.m.IsRunningUpdatesWhilePaused=false;
    });
});

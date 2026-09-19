// Offline fixtures only. All text and branch methods are loaded from CNUT.
::Const <- {
    UI = {Color = {PositiveValue="#00aa00", NegativeValue="#aa0000", DamageValue="#bb0000"}},
    SkillType = {Perk=1, StatusEffect=2, Active=4},
    SkillOrder = {Perk=1, Trait=2, Any=3, UtilityTargeted=4, OffensiveTargeted=5},
    ItemSlot = {None=0, Offhand=1}, Items = {ItemType={Supply=1, Tool=2}},
    ProjectileType = {Bomb2=1}, Injury = {CuttingBody=[], CuttingHead=[]}
};
::fixture <- {matches=5, won=3, now=0};
::Math <- {floor=function(v){return ::floor(v).tointeger();}};
::Time <- {getVirtualTimeF=function(){return ::fixture.now;}};
::World <- {getTime=function(){return {SecondsPerDay=1};}};
::Tactical <- {isActive=function(){return false;}};
::actor <- {getFlags=function(){return {
    getAsInt=function(key){return key=="ArenaFights" ? ::fixture.matches : ::fixture.won;}
};}};
::container <- {getActor=function(){return ::actor;}};
::fixtureBase <- {
    getName=function(){return this.m.Name;},
    getDescription=function(){return this.m.Description;},
    getContainer=function(){return ::container;},
    getIconLarge=function(){return null;},
    getIcon=function(){return "fixture_icon";},
    getValueString=function(){return "FIXTURE_STUB";},
    getCostString=function(){return "FIXTURE_STUB";},
    getDefaultUtilityTooltip=function(){return [];}
};
::fixtureBase.setdelegate(getroottable());
::inherit <- function(parent,members){
    members.setdelegate(::fixtureBase);
    members.m.setdelegate({_set=function(key,value){this.rawset(key,value);}});
    // Parent creation supplies engine metadata, not the strings under test.
    foreach(name in ["item","weapon","anatomist_potion_item","character_trait","ambition","oath_ambition"])
        members.rawset(name, {create=function(){}});
    return members;
};
::emit <- function(key,value){
    local encoded="";
    foreach(byte in value) encoded+=format("%02x",byte & 255);
    print("TEXT|"+key+"|"+encoded+"\n");
};
::emitRows <- function(key,obj){
    foreach(index,row in obj.getTooltip())
        if ("text" in row && row.text!="FIXTURE_STUB")
            emit(key+"."+row.id+"."+index,row.text);
};
::walkNames <- function(path,value){
    if(typeof value=="string") emit(path,value);
    else if(typeof value=="table" || typeof value=="array")
        foreach(key,child in value) walkNames(path+"."+key,child);
};

foreach(path in ::InputFiles) dofile(::InputRoot+"/"+path);
walkNames("item_names",::Const.Strings);

necrosavant_potion_item.create(); emitRows("lifesteal.item",necrosavant_potion_item);
necrosavant_potion_effect.create(); emitRows("lifesteal.effect",necrosavant_potion_effect);
coat_with_poison_skill.create(); emitRows("poison.regular",coat_with_poison_skill);
coat_with_spider_poison_skill.create(); emitRows("poison.spider",coat_with_spider_poison_skill);

foreach(spec in [["ammo",ammo_item],["tools",armor_parts_item],["medicine",medicine_item]]){
    spec[1].create();
    foreach(amount in [1,50]){
        spec[1].setAmount(amount);
        emitRows("supply."+spec[0]+"."+amount,spec[1]);
    }
}
smoke_bomb_item.create(); emitRows("smoke.item",smoke_bomb_item);
throw_smoke_bomb_skill.create(); emitRows("smoke.skill",throw_smoke_bomb_skill);
holy_water_item.create(); emitRows("holy_water",holy_water_item);

foreach(spec in [["fighter",arena_fighter_trait],["pit",arena_pit_fighter_trait],["veteran",arena_veteran_trait]]){
    spec[1].create();
    foreach(record in [[5,3],[5,5]]){
        ::fixture.matches=record[0]; ::fixture.won=record[1];
        emitRows("arena."+spec[0]+"."+record[0]+"_"+record[1],spec[1]);
    }
}
foreach(won in [0,1]){
    ::fixture.matches=1; ::fixture.won=won;
    emitRows("arena.pit.1_"+won,arena_pit_fighter_trait);
}

// Obtain the oath name from the actual child create method, then execute
// the actual parent getUIText method against the same clock fixture.
oath_ambition.create(); oath_of_camaraderie_ambition.create();
oath_ambition.m.OathName=oath_of_camaraderie_ambition.m.OathName;
oath_ambition.m.StartTime=0;
foreach(days in [1,3]){
    ::fixture.now=oath_ambition.m.OathDuration-days;
    emit("oath.remaining."+days,oath_ambition.getUIText());
}
foreach(spec in [["dazed",dazed_effect],["disarmed",disarmed_effect]]){
    spec[1].create();
    foreach(turns in [1,2]){
        spec[1].m.TurnsLeft=turns;
        emit("log."+spec[0]+"."+turns,spec[1].getLogEntryOnAdded("Hans","Brigand"));
    }
}
old_trait.create(); emit("generic.old",old_trait.getName());
whip_skill.create(); emit("generic.whip",whip_skill.getName());
print("BBMOD_REVIEWED_SENTENCES_PASS\n");

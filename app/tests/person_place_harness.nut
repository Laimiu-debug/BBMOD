// Offline engine boundaries only. The tested methods and templates come from CNUT.
::Const <- {
    UI={Color={PositiveValue="#00aa00",NegativeValue="#aa0000",DamageValue="#bb0000"}},
    BloodType={None=0}, MoraleState={Steady=3,Confident=4},
    MoraleCheckType={Default=0}, FatalityType={None=0},
    DefaultMovementAPCost=[], DefaultMovementFatigueCost=[], ShakeCharacterLayers=[],
    Movement={LevelDifferenceActionPointCost=0,LevelDifferenceFatigueCost=0},
    Tactical={MovementType={Default=0}}, FactionType={Settlement=1,OrientalCityState=2},
    Contracts={Settings={IntroChance=0},NegotiationDefault=[],Overview=[],
        IntroSettlementCold=[],IntroSettlementFriendly=[],IntroSettlementNeutral=[]},
    World={MovementSettings={Speed=170.0,GlobalMult=1.0,RoadMult=1.0}}
};
::createColor <- function(value){return value;};
::createVec <- function(x,y){return {X=x,Y=y};};
::WeakTableRef <- function(value){return value;};
::Time <- {getVirtualTimeF=function(){return 0.0;}};
::Math <- {rand=function(low,high){return low;},
    round=function(value){return ::floor(value+0.5).tointeger();},
    max=function(a,b){return a>b?a:b;}};
::fixture <- {roster=null,faction=null,entities={},screen="",nextID=501};
::World <- {
    getTime=function(){return {Days=20,SecondsPerDay=10.0};},
    getEntityByID=function(id){return ::fixture.entities[id];},
    FactionManager={getFaction=function(id){
        if(id!=::fixture.faction.m.ID) throw "Unexpected faction ID";
        return ::fixture.faction;
    }},
    State={getCurrentTown=function(){return ::fixture.entities[1000];},
        getPlayer=function(){return {getTile=function(){return {
            getDirection8To=function(tile){return 6;}
        };}};}},
    Contracts={updateActiveContract=function(){}}
};
::cloneData <- function(value){
    if(typeof value=="table"){
        local result={}; foreach(key,item in value) result[key]<-::cloneData(item);
        result.setdelegate(getroottable()); return result;
    }
    if(typeof value=="array"){
        local result=[]; foreach(item in value) result.push(::cloneData(item)); return result;
    }
    return value;
};
::fixtureBase <- {
    getID=function(){return this.m.ID;},
    getRoster=function(){return ::fixture.roster;},
    getRandomCharacter=function(){return ::fixture.roster.rows[0];},
    getPlayerRelation=function(){return 50;},
    getType=function(){return this.m.Type;},
    setAppearance=function(){}, assignRandomEquipment=function(){},
    setFaction=function(id){this.m.rawset("Faction",id);}
};
fixtureBase.setdelegate(getroottable());
::bindContractParent <- function(object){
    local parent={};
    foreach(key,value in ::contract)
        if(typeof value=="function") parent[key]<-value.bindenv(object);
    object.rawset("contract",parent);
};
::inherit <- function(parent,members){
    if(parent=="scripts/contracts/contract"){
        local own=members.m;
        members.m=::cloneData(::contract.m);
        foreach(key,value in own) members.m.rawset(key,value);
        members.setdelegate(::contract);
        ::bindContractParent(members);
    }else members.setdelegate(::fixtureBase);
    return members;
};
::emit <- function(key,value){
    local encoded=""; foreach(byte in value.tostring()) encoded+=format("%02x",byte & 255);
    print("TEXT|"+key+"|"+encoded+"\n");
};
::expect <- function(value,message){if(!value) throw message;};
foreach(path in ::InputFiles) dofile(::InputRoot+"/"+path);
contract.setdelegate(getroottable());
tag_collection.setdelegate(getroottable());
::new <- function(path){
    ::expect(path=="scripts/tools/tag_collection","Unexpected engine object creation");
    local result=clone ::tag_collection; result.m={}; return result;
};

// The game's native template interpolator is not included in the standalone VM.
// Only %key% replacement is emulated; no source text or word order is invented.
::interpolate <- function(text,vars){
    foreach(pair in vars){
        local token="%"+pair[0]+"%", value=pair[1].tostring(), result="", cursor=0;
        local pos=text.find(token,cursor);
        while(pos!=null){
            result+=text.slice(cursor,pos)+value; cursor=pos+token.len();
            pos=text.find(token,cursor);
        }
        text=result+text.slice(cursor);
    }
    return text;
};
::makePlace <- function(id,name){
    local place={m={ID=id,Name=name},sprite={Visible=false}};
    place.getID<-function(){return this.m.ID;};
    place.getName<-function(){return this.m.Name;};
    place.getNameOnly<-place.getName;
    place.isNull<-function(){return false;};
    place.getTile<-function(){return {ID=this.m.ID};};
    place.getFactions<-function(){return [::fixture.faction.m.ID];};
    place.getSprite<-function(key){::expect(key=="selection","Sprite key changed");return this.sprite;};
    return place;
};
::makeContract <- function(){
    local result=clone ::deliver_item_contract;
    result.m=::cloneData(::deliver_item_contract.m);
    ::bindContractParent(result);
    // Do not open screens, select dialogue branches, or call UI/engine services.
    result.setScreen<-function(id){::fixture.screen=id;};
    result.create();
    foreach(state in result.m.States) state.setdelegate(getroottable());
    return result;
};
::makeStream <- function(){
    local stream={rows=[],cursor=0};
    local writer=function(kind){return function(value){this.rows.push([kind,value]);};};
    local reader=function(kind){return function(){
        local row=this.rows[this.cursor++];
        ::expect(row[0]==kind,"Serialization field type/order changed");return row[1];
    };};
    foreach(kind in ["I32","U32","U8","U16","F32","Bool","String"]){
        stream["write"+kind]<-writer(kind);stream["read"+kind]<-reader(kind);
    }
    return stream;
};

foreach(spec in [["settlement",::settlement_faction,3,"Edmund","Sommerstad",1],
                ["city_state",::city_state_faction,4,"Jamil Ibn Sahr","Al-Hazif",2]]){
    local label=spec[0], faction=clone spec[1];
    faction.m=::cloneData(spec[1].m);
    faction.m.rawset("ID",71);faction.m.rawset("Name",spec[4]);faction.m.rawset("Type",spec[5]);
    ::fixture.faction=faction;::fixture.nextID=501;
    ::fixture.roster={rows=[],personName=spec[3],size=spec[2],paths=[]};
    fixture.roster.getSize<-function(){return this.rows.len();};
    fixture.roster.getAll<-function(){return this.rows;};
    fixture.roster.create<-function(path){
        this.paths.push(path);
        local person=clone ::actor;person.m=::cloneData(::actor.m);
        // Assigning a faction normally updates tactical sprites/skills; that
        // engine operation is unrelated to the real title/name methods below.
        person.rawset("setFaction",::fixtureBase.setFaction);
        person.m.rawset("ID",::fixture.nextID++);
        person.setName(this.rows.len()==0?this.personName:"Fixture Person "+this.rows.len());
        // Repeated pre-existing honorifics exercise the real fallback branch.
        person.setTitle(this.rows.len()==1 || this.rows.len()==2?"the Elder":"");
        this.rows.push(person);return person;
    };
    faction.onUpdateRoster();
    ::expect(fixture.roster.rows.len()==spec[2],"Roster size changed");
    foreach(index,person in fixture.roster.rows){
        emit(label+".actor."+index+".id",person.getID());
        emit(label+".actor."+index+".name",person.getName());
        emit(label+".actor."+index+".name_only",person.getNameOnly());
        emit(label+".actor."+index+".title",person.getTitle());
        emit(label+".actor."+index+".creation_path",fixture.roster.paths[index]);
    }
    local recipient=fixture.roster.rows[0], cachedName=recipient.getName();
    ::fixture.entities={};
    fixture.entities[1000]<-makePlace(1000,"Fixture Origin");
    fixture.entities[1001]<-makePlace(1001,spec[4]);
    fixture.entities[1002]<-makePlace(1002,"Fixture Thieves Hideout");
    local courier=makeContract();
    courier.m.ID=777;courier.m.Faction=71;
    courier.setHome(fixture.entities[1000]);courier.setOrigin(fixture.entities[1000]);
    courier.m.Destination=fixture.entities[1001];courier.m.Location=fixture.entities[1002];
    courier.m.Flags.set("Distance",10);
    courier.start();
    ::expect(courier.m.RecipientID==501,"Recipient ID changed");
    ::expect(courier.m.Flags.get("RecipientName")==cachedName,"Recipient cache differs from actor.getName");
    emit(label+".contract_type",courier.getType());
    emit(label+".recipient_id",courier.m.RecipientID);
    emit(label+".cached_recipient",cachedName);
    emit(label+".offer_screen",fixture.screen);
    recipient.setName("Changed After Cache");recipient.setTitle("the Changed");
    emit(label+".actor_after_cache",recipient.getName());
    foreach(distance in [10,25]){
        courier.m.Flags.set("Distance",distance);
        local days=courier.getDaysRequiredToTravel(distance,Const.World.MovementSettings.Speed,true);
        local vars=[];courier.onPrepareVariables(vars);
        local prepared={};foreach(pair in vars) prepared[pair[0]]<-pair[1];
        ::expect(prepared.recipient==cachedName,"onPrepareVariables did not use RecipientName cache");
        ::expect(prepared.objective==spec[4],"Raw destination name changed");
        foreach(stateID in ["Offer","Running","Running_Thieves"]){
            // Execute each state's real start without simulating previous-state end effects.
            courier.m.ActiveState=null;courier.setState(stateID);
            local key=label+".days"+days+"."+stateID;
            emit(key+".state_id",courier.m.ActiveState.ID);
            foreach(pair in vars) emit(key+".variable."+pair[0],pair[1]);
            foreach(index,template in courier.m.BulletpointsObjectives){
                emit(key+"."+index+".template",template);
                emit(key+"."+index+".sentence",interpolate(template,vars));
            }
        }
    }
    // Read the real screen objects created by createScreens. Preserve every
    // random branch verbatim; choosing branches belongs to the native engine.
    local screenID=label=="settlement"?"Task":"TaskSouthern";
    local screen=courier.getScreen(screenID), dialogueVars=[];
    courier.onPrepareVariables(dialogueVars);
    emit(label+".dialogue."+screenID+".screen_id",screen.ID);
    emit(label+".dialogue."+screenID+".template",screen.Text);
    emit(label+".dialogue."+screenID+".prepared",interpolate(screen.Text,dialogueVars));
    foreach(pair in dialogueVars) emit(label+".dialogue."+screenID+".variable."+pair[0],pair[1]);
    local stream=makeStream();courier.onSerialize(stream);
    foreach(index,row in stream.rows){
        emit(label+".serialized."+index+".type",row[0]);
        emit(label+".serialized."+index+".value",row[1]);
    }
    local restored=makeContract();restored.onDeserialize(stream);
    ::expect(stream.cursor==stream.rows.len(),"Serialization data was not fully consumed");
    ::expect(restored.m.RecipientID==501 && restored.m.Destination.getID()==1001
        && restored.m.Location.getID()==1002 && restored.m.ID==777,"Serialized IDs changed");
    ::expect(restored.m.Flags.get("RecipientName")==cachedName,"Serialized RecipientName changed");
    ::expect(restored.m.Flags.get("Distance")==25,"Serialized distance changed");
    local vars=[];restored.onPrepareVariables(vars);
    foreach(pair in vars) emit(label+".restored.variable."+pair[0],pair[1]);
    emit(label+".roundtrip",true);
    emit(label+".restored_state",restored.m.ActiveState.ID);
    // A previously saved English title is a display input, not a renamed actor.
    restored.m.Flags.set("RecipientName",spec[3]+" of "+spec[4]);
    vars=[];restored.onPrepareVariables(vars);
    foreach(pair in vars) emit(label+".legacy_cache.variable."+pair[0],pair[1]);
    foreach(index,template in restored.m.BulletpointsObjectives){
        emit(label+".legacy_cache."+index+".template",template);
        emit(label+".legacy_cache."+index+".sentence",interpolate(template,vars));
    }
}
print("BBMOD_PERSON_PLACE_PASS\n");

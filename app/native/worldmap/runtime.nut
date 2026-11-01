// Offline host services for original 32-bit rules. Never opens a game directory.
::logInfo <- function(...) {};
::logDebug <- function(...) {};
::logWarning <- function(...) {};
::logError <- function(s) { throw s; };
::__ping <- function(...) {};
::min <- function(a,b) {return a<b?a:b;};
::max <- function(a,b) {return a>b?a:b;};
::Math <- { seedRandomString=::_mapSeed, seedRandom=::_mapSeed, rand=::_mapRand,
    min=::min, max=::max, abs=::abs, floor=::floor, ceil=::ceil, pow=::pow,
    sqrt=::sqrt, sin=::sin, cos=::cos, minf=::min, maxf=::max, PI=3.14159265 };
::Math.rand=function(...) {
    if(vargv.len()==0)return ::_mapLegacyRand();
    return ::_mapRand(vargv[0],vargv[1]);
};
::Time <- {getRealTime=function(){return 0;},getRealTimeF=function(){return 0.0;},
    getVirtualTime=function(){return 0;},getVirtualTimeF=function(){return 0.0;},getExactTime=::_mapElapsed};
::Const <- { DLC={Desert=true, Unhold=true, Wildmen=true, Paladins=true, Lindwurm=true, Mask=342},
    Direction={N=0,NE=1,SE=2,S=3,SW=4,NW=5,COUNT=6},
    DirectionAsBit={N=1,NE=2,SE=4,S=8,SW=16,NW=32},
    DirectionBit=[1,2,4,8,16,32] };
::MapReference <- class {
    _target=null;
    constructor(value){this._target=value;}
    function isNull(){return this._target==null;}
    function _get(key){
        if(this._target==null)throw "Reference is null";
        local value=this._target[key];
        return typeof value=="function"?value.bindenv(this._target):value;
    }
    function _set(key,value){this._target[key]=value;}
};
::WeakTableRef <- function(value) { return ::MapReference(value); };
::WeakObjectRef <- function(value) { return ::MapReference(value); };
::createVec <- function(x,y) { return {X=x,Y=y}; };
::createColor <- function(value=0) {
    return {R=1.0,G=1.0,B=1.0,A=1.0, function set(v) {}, function multiplyRGB(v) {return this;}};
};
::deepClone <- function(value) {
    if (typeof value == "array") { local a=[]; foreach(v in value) a.push(::deepClone(v)); return a; }
    if (typeof value == "table") {
        local t={}; foreach(k,v in value) t[k] <- ::deepClone(v); return t;
    }
    return value;
};
::LoadedRules <- {};
::RulePrototypes <- {};
::include <- function(path) {
    if (!(path in ::LoadedRules)) {
        ::LoadedRules[path] <- true;
        local name=split(path,"/").top(),root=getroottable();
        local builtin=(name in root && typeof root[name]=="function")?root[name]:null;
        dofile(::WORLD_MAP_RULES+"/"+path+".cnut");
        if(builtin!=null && typeof root[name]=="table") {
            ::RulePrototypes[path] <- root[name];root[name]=builtin;
        }
    }
};
::ruleClass <- function(path) {
    ::include(path);
    if(path in ::RulePrototypes)return ::RulePrototypes[path];
    local name=split(path,"/").top();
    return getroottable()[name];
};
::inherit <- function(path, properties) {
    local parent=::ruleClass(path), result=clone parent;
    result.m <- ::deepClone(parent.m);
    if ("m" in properties) foreach(k,v in properties.m) result.m[k] <- ::deepClone(v);
    foreach(k,v in properties) if(k!="m") result[k] <- v;
    result[split(path,"/").top()] <- parent;
    result.__parentPrototype <- parent;
    result.__parentName <- split(path,"/").top();
    result.setdelegate(getroottable());
    return result;
};
::new <- function(path,native=null) {
    local instance=clone ::ruleClass(path);
    if("m" in instance)instance.m <- ::deepClone(instance.m);
    instance.setdelegate(getroottable());
    if("__parentPrototype" in instance) {
        local bindParent;
        bindParent=function(prototype,receiver) {
            local parent={m=receiver.m};
            foreach(k,v in prototype) if(k!="m") parent[k] <- typeof v=="function"?v.bindenv(receiver):v;
            if("__parentPrototype" in prototype)
                parent[prototype.__parentName] <- bindParent(prototype.__parentPrototype,receiver);
            return parent;
        };
        local prototype=instance;
        while("__parentPrototype" in prototype) {
            instance[prototype.__parentName] <- bindParent(prototype.__parentPrototype,instance);
            prototype=prototype.__parentPrototype;
        }
        // The recursive closure captures its own local slot. It is needed only
        // while binding; clear that slot so each new background can be freed.
        bindParent=null;
    }
    instance.__className <- split(path,"/").top();
    if(native!=null)foreach(k,v in native)instance[k] <- v;
    if ("create" in instance) instance.create();
    return instance;
};
::Detail <- {
    Color=null, Scale=1.0, Alpha=1.0, Brightness=1.0, Rotation=0.0, Visible=true,IsFadingDone=true,
    function _set(key,value) {this.rawset(key,value);},
    function setBrightness(value) {this.Brightness=value;},
    function setBrush(...) {}, function setOffset(...) {}, function setHorizontalFlipping(...) {},
    function setVerticalFlipping(...) {}, function setScale(...) {},
    function getWidth() { return 0; }, function getHeight() { return 0; }
    function fadeIn(...) {this.Alpha=1.0;},function fadeOut(...) {this.Alpha=0.0;}
};
::TileMethods <- {
    function _get(key) {
        if (key=="HasRoad") return this.RoadDirections!=0;
        throw "Unsupported tile property: "+key;
    },
    function hasNextTile(d) {
        local x=this.SquareCoords.X, y=this.SquareCoords.Y;
        local next=::World.adjacent(x,y,d);
        return next[0]>=0 && next[0]<::World.Width && next[1]>=0 && next[1]<::World.Height;
    },
    function getNextTile(d) {
        local next=::World.adjacent(this.SquareCoords.X,this.SquareCoords.Y,d);
        return ::World.getTileSquare(next[0],next[1]);
    },
    function getSurroundingTilesOfType(type) {
        local count=0;
        for(local d=0;d<6;d++) if(this.hasNextTile(d) && this.getNextTile(d).Type==type) count++;
        return count;
    },
    function getSurroundingTilesNotOfType(type) {
        local count=0;
        for(local d=0;d<6;d++) if(this.hasNextTile(d) && this.getNextTile(d).Type!=type) count++;
        return count;
    },
    function getDistanceTo(other) {
        local q=this.Coords.X-other.Coords.X, r=this.Coords.Y-other.Coords.Y;
        return ::max(::abs(q),::max(::abs(r),::abs(q+r)));
    },
    function getDirectionTo(other) {
        for(local d=0;d<6;d++) if(this.hasNextTile(d) && this.getNextTile(d)==other) return d;
        throw "getDirectionTo requires adjacent tiles";
    },
    // clear() removes graphical details; logical terrain/roads/occupancy remain.
    function clear(...) {},
    function clearAllBut(...) {},
    function setBrush(brush) { this.Brush=brush; },
    function getBrush() { return this.Brush; },
    function resetBrush() { this.Brush=""; },
    function spawnDetail(...) { local detail={};detail.setdelegate(::Detail);return detail; },
    function spawnDetailDecal(...) { local detail={};detail.setdelegate(::Detail);return detail; }
};
::World <- {
    Width=0,Height=0,Tiles=[],
    function adjacent(x,y,d) {
        switch(d) {
        case 0:return[x,y+1];case 1:return[x+1,y+(x&1)];
        case 2:return[x+1,y-1+(x&1)];case 3:return[x,y-1];
        case 4:return[x-1,y-1+(x&1)];case 5:return[x-1,y+(x&1)];
        }
        throw "Invalid direction";
    },
    function resizeScene(width,height) {
        this.Width=width;this.Height=height;this.Tiles=[];
        for(local x=0;x<width;x++) {
            local column=[];
            for(local y=0;y<height;y++) {
                local tile={ID=x*height+y+1,Type=0,TacticalType=0,Subregion=0,Region=0,RoadDirections=0,Heat=0,
                    IsOccupied=false,IsFlipped=false,Brush="",SquareCoords={X=x,Y=y},
                    Coords={X=x,Y=y-x/2},Pos={X=120+180*x,Y=60+120*y+60*(x&1)}};
                tile.setdelegate(::TileMethods);column.push(tile);
            }
            this.Tiles.push(column);
        }
    },
    function getTileSquare(x,y) {
        if(x<0||y<0||x>=this.Width||y>=this.Height) throw "Tile outside world";
        return this.Tiles[x][y];
    },
    function getTile(coords){return this.getTileSquare(coords.X,coords.Y+coords.X/2);},
    function getMapSize(){return{X=this.Width,Y=this.Height};},
    function isValidTileSquare(x,y){return x>=0&&y>=0&&x<this.Width&&y<this.Height;},
    function clearTiles() {
        foreach(column in this.Tiles)foreach(tile in column) {
            tile.Type=0;tile.TacticalType=0;tile.Subregion=0;tile.Region=0;
            tile.RoadDirections=0;tile.Heat=0;tile.Brush="";tile.IsOccupied=false;
        }
    },
    function getNumOfTilesWithType(types) {
        local count=0;
        foreach(column in this.Tiles) foreach(tile in column) if(types.find(tile.Type)!=null) count++;
        return count;
    },
    function queryTilesInRange(center,minimum,maximum,callback,data) {
        local visit;
        visit=function(tile,direction,distance) {
            if(distance>=minimum && tile.Type!=0)callback(tile,data);
            if(distance<maximum && tile.hasNextTile(direction))visit(tile.getNextTile(direction),direction,distance+1);
            local side=(direction+1)%6,current=tile;
            for(local n=distance+1;n<=maximum;n++) {
                if(!current.hasNextTile(side))break;
                current=current.getNextTile(side);
                if(n>=minimum && current.Type!=0)callback(current,data);
            }
        };
        for(local direction=0;direction<6;direction++)
            if(center.hasNextTile(direction))visit(center.getNextTile(direction),direction,1);
    },
    function updateTilesWithHeat(centers,amount) {
        foreach(center in centers) {
            local cx=center.SquareCoords.X,cy=center.SquareCoords.Y;
            for(local x=::max(0,cx-6);x<=::min(this.Width-1,cx+6);x++)
                for(local y=::max(0,cy-6);y<=::min(this.Height-1,cy+6);y++) {
                    local tile=this.getTileSquare(x,y),distance=center.getDistanceTo(tile);
                    if(distance<=6)tile.Heat=(tile.Heat+amount-distance)&255;
                }
        }
    },
    function findFirstInRange(center,maximum,predicate) {
        local found=null,visit;
        visit=function(tile,direction,distance) {
            if(predicate(tile)){found=tile;return;}
            if(distance<maximum && tile.hasNextTile(direction))visit(tile.getNextTile(direction),direction,distance+1);
            if(found!=null)return;
            local side=(direction+1)%6,current=tile;
            for(local n=distance+1;n<=maximum;n++) {
                if(!current.hasNextTile(side))break;
                current=current.getNextTile(side);
                if(predicate(current)){found=current;return;}
            }
        };
        for(local direction=0;direction<6 && found==null;direction++)
            if(center.hasNextTile(direction))visit(center.getNextTile(direction),direction,1);
        return found;
    },
    function findNextRegion(center,radius,type) {
        local vectors=[[0,1],[1,0],[1,-1],[0,-1],[-1,0],[-1,1]];
        for(local distance=1;distance<=radius;distance++)for(local direction=0;direction<6;direction++) {
            local q=center.Coords.X+vectors[direction][0]*distance,r=center.Coords.Y+vectors[direction][1]*distance;
            local side=vectors[(direction+2)%6];
            for(local step=0;step<distance;step++) {
                if(q>=0&&q<this.Width) {
                    local y=r+q/2;
                    if(y>=0&&y<this.Height) {
                        local tile=this.getTileSquare(q,y);
                        if(tile.Region!=0 && (type==0 || tile.Type==type))return tile.Region;
                    }
                }
                q+=side[0];r+=side[1];
            }
        }
        return 0;
    },
    function findNextTileOfType(center,radius,type,result) {
        local found=null,best=9000;
        local consider=function(tile,data) {
            if(tile.Type!=type)return;
            local distance=tile.getDistanceTo(center);
            if(distance>=best)return;
            for(local d=0;d<6;d++)if(!tile.hasNextTile(d)||tile.getNextTile(d).Type!=type)return;
            best=distance;found=tile;
        };
        consider(center,null);
        this.queryTilesInRange(center,1,radius,consider,null);
        if(found==null)return false;
        result.Result <- found;return true;
    },
    function worldToTile(pos) {
        local q=::floor(pos.X/180.0).tointeger(),px=pos.X-q*180.0,py=pos.Y-60*(q&1);
        local remainder=py-::floor(py/120.0)*120.0;
        if(py>=0 && px<60 && ::abs(remainder-60)>px)q--;
        local r=((pos.Y-60*(q&1))/120.0).tointeger()-::floor(q/2.0).tointeger();
        if(q<0 && pos.Y<60)r=0;
        return{X=::max(0,q),Y=r};
    }
};
::World.State <- {m={Regions=[]}};
::TileMethods.hasNextTile=::_mapTileHasNext;
::TileMethods.getNextTile=::_mapTileNext;
::TileMethods.getSurroundingTilesOfType=::_mapTileCount;
::TileMethods.getSurroundingTilesNotOfType=::_mapTileCountNot;
::TileMethods.getDistanceTo=::_mapTileDistance;
::TileMethods.getDirectionTo=::_mapTileDirection;
::World.getTileSquare=::_mapTileSquare;
::World.findNextRegion=::_mapFindRegion;
::World.findNextTileOfType=function(center,radius,type,result) {
    local found=::_mapFindType(center,radius,type);
    if(found==null)return false;
    result.Result <- found;return true;
};
::World.spawnRegionText <- function(...) {};
::Math.getAngleTo <- function(a,b){return ::atan2(a.X-b.X,b.Y-a.Y)*57.2957795;};
::Navigator <- {
    function createSettings(){return{ActionPointCosts=null,RoadMult=0.0,StopAtRoad=false,RoadOnly=false};},
    function findPath(start,end,settings,maxCost) {
        local ids=::_mapPath(::World.Tiles,start,end,settings),tiles=[];
        foreach(id in ids)tiles.push(::World.getTileSquare(id/::World.Height,id%::World.Height));
        return {Tiles=tiles,Cursor=0,function isEmpty(){return this.Cursor>=this.Tiles.len();},
            function getSize(){return this.Tiles.len()-this.Cursor;},
            function getCurrent(){return this.Tiles[this.Cursor].Coords;},function pop(){this.Cursor++;}};
    }
};
::World.getNavigator <- function(){return ::Navigator;};
::World.EntityManager <- {
    Settlements=[],Locations=[],
    function getSettlements(){return this.Settlements;},function getLocations(){return this.Locations;},
    function addSettlement(entity){this.Settlements.push(entity);},
    function addLocation(entity){this.Locations.push(entity);},
    function isNameUsed(name){foreach(s in this.Settlements)if(s.getName()==name)return true;return false;}
};
::World.NextID <- 1;
::World.spawnLocation <- function(path,coords) {
    local native={__nativeID=this.NextID++,__tile=this.getTileSquare(coords.X,coords.Y+coords.X/2),
        __sprites={},__labels={}};
    local entity=::new(path,native);
    entity.onInit();
    if("onAfterInit" in entity)entity.onAfterInit();
    return entity;
};
::World.createRoster <- function(...) {};
::World.getTime <- function(){return{Days=1,Hours=0,TimeOfDay=6,SecondsPerDay=105,IsDaytime=false};};
::World.getCamera <- function(){return{function isInsideScreen(...) {return false;}};};
::getID <- function(){return this.__nativeID;};
::getTile <- function(){return this.__tile;};
::getPos <- function(){return this.__tile.Pos;};
::getFaction <- function(){return "__faction" in this?this.__faction:0;};
::setFaction <- function(value){this.__faction <- value;};
::setDiscovered <- function(value){this.__discovered <- value;};
::isDiscovered <- function(){return "__discovered" in this && this.__discovered;};
::getSprite <- function(name){if(!(name in this.__sprites)){local d={};d.setdelegate(::Detail);this.__sprites[name] <- d;}return this.__sprites[name];};
::addSprite <- ::getSprite;
::hasSprite <- function(name){return name in this.__sprites;};
::getLabel <- function(name){return this.__labels[name];};
::addLabel <- function(name){local label={Visible=false,Text="",Color=null};label.setdelegate(::Detail);this.__labels[name] <- label;return label;};
::hasLabel <- function(name){return name in this.__labels;};
::registerThinker <- function(...) {};
::unregisterThinker <- function(...) {};
::setRenderedTop <- function(...) {};
::setVisibleInFogOfWar <- function(...) {};
::setVisibility <- function(...) {};
::setSpriteScaling <- function(...) {};
::setSpriteOffset <- function(...) {};
::setSpriteColorization <- function(...) {};
::isKindOf <- function(obj,name){return name in obj || ("__className" in obj && obj.__className==name);};
::MapGen <- {
    Templates={},
    function get(name) {
        if(!(name in this.Templates)) throw "Map template unavailable: "+name;
        return this.Templates[name];
    }
};
::dumpMap <- function(stage) {
    print("{\"kind\":\"offline-map\",\"seed\":\""+::WORLD_MAP_SEED+"\",\"stage\":\""+stage+
        "\",\"width\":"+::World.Width+",\"height\":"+::World.Height+",\"draws\":"+::_mapDraws()+
        ",\"seconds\":"+::_mapElapsed()+",\"rows\":[");
    for(local y=0;y<::World.Height;y++) {
        print(y?",[":"[");
        for(local x=0;x<::World.Width;x++) {
            local t=::World.getTileSquare(x,y);
            print((x?",[":"[")+t.Type+","+t.TacticalType+","+t.Subregion+","+t.Region+","+t.RoadDirections+"]");
        }
        print("]");
    }
    print("],\"settlements\":[");
    foreach(i,town in ::World.EntityManager.getSettlements()) {
        local xy=town.getTile().SquareCoords;
        local buildings=[],attached=[];
        foreach(b in town.m.Buildings)buildings.push(b==null?null:b.getID());
        foreach(a in town.getAttachedLocations()) {
            local tile=a.getTile();
            attached.push({name=a.getName(),type=a.m.TypeID,id=a.m.ID,xy=[tile.SquareCoords.X,tile.SquareCoords.Y]});
        }
        print((i?",":"")+::jsonEncode({name=town.getName(),id=town.getID(),xy=[xy.X,xy.Y],
            size=town.getSize(),culture=town.getCulture(),military=town.isMilitary(),coastal=town.isCoastal(),
            buildings=buildings,attached=attached,produce=town.getProduce(),
            price_mult=town.getPriceMult(),buy_mult=town.m.Modifiers.BuyPriceMult,sell_mult=town.m.Modifiers.SellPriceMult,
            building_mult=town.m.Modifiers.BuildingPriceMult,incense_mult=town.m.Modifiers.IncensePriceMult,
            connected=town.m.ConnectedTo,roads=town.m.ConnectedToByRoads}));
    }
    print("],\"regions\":[");
    foreach(i,region in ::World.State.m.Regions) {
        local xy=region.Center.SquareCoords;
        print((i?",":"")+::jsonEncode({name=region.Name,type=region.Type,size=region.Size,xy=[xy.X,xy.Y]}));
    }
    print("],\"loaded_rules\":[");local count=0;
    foreach(path,_ in ::LoadedRules)print((count++?",":"")+::jsonQuote(path+".cnut"));
    print("]}\n");
};
::jsonQuote <- function(value) {
    local result="\"";
    for(local i=0;i<value.len();i++) {
        local c=value[i];if(c==34||c==92)result+="\\"+c.tochar();
        else if(c==10)result+="\\n";else if(c==13)result+="\\r";else if(c==9)result+="\\t";
        else if(c>=32)result+=c.tochar();
    }
    return result+"\"";
};
::jsonEncode <- function(value) {
    if(value==null)return"null";
    local kind=typeof value;
    if(kind=="string")return ::jsonQuote(value);
    if(kind=="bool")return value?"true":"false";
    if(kind=="integer"||kind=="float")return value.tostring();
    local result=kind=="array"?"[":"{",i=0;
    foreach(k,v in value) {
        if(i++)result+=",";
        if(kind=="table")result+=::jsonQuote(k)+":";
        result+=::jsonEncode(v);
    }
    return result+(kind=="array"?"]":"}");
};

::include("scripts/config/world");
::include("scripts/config/ui");
::include("scripts/config/strings");
::include("scripts/config/rumors");
::include("scripts/config/world_location_names");
::include("scripts/config/world_settlements");
::include("scripts/config/world_locations");
::include("scripts/config/world_entity_common");
::include("scripts/config/factions");
::include("scripts/config/world_ai");
::include("scripts/config/sound");
::include("scripts/config/tactical");
if(::WORLD_MAP_STOP=="brothers") {
    dofile(::WORLD_MAP_SCRIPT_DIR+"/brothers.nut");
    return;
}
if(::WORLD_MAP_STOP=="search") {
    dofile(::WORLD_MAP_RULES+"/brothers.nut");
    ::BBMODCampaign <- ::SeedGenerator.CampaignConfig;
    ::WORLD_MAP_SEED=::SeedGenerator.OfflineJob.seeds[0];
}
if(::WORLD_MAP_STOP.find("campaign:")==0) {
    local options=split(::WORLD_MAP_STOP,":");
    ::BBMODCampaign <- {Origin=options[1],Difficulty=options[2].tointeger(),
        EconomicDifficulty=options[3].tointeger(),BudgetDifficulty=options[4].tointeger()};
}
// World-generation adjustments in the original scripts/dlc/dlc_desert profile.
::Const.World.Settings.SizeY=170;
::Const.World.Settlements.Master.push({Amount=3,List=::Const.World.Settlements.CityStates,
    IgnoreSide=true,AdditionalSpace=13});
// Settlement reset is needed even for terrain-only stages.
if (!("Buildings" in ::Const.World)) ::Const.World.Buildings <- {function reset(){}};
dofile(::WORLD_MAP_RULES+"/index.nut");
foreach(path in ::WORLD_MAP_TEMPLATES) {
    local template=::new(path);template.init();
    ::MapGen.Templates[template.getName()] <- template;
}
local generator=::new("scripts/mapgen/templates/world/worldmap_generator");generator.init();
::MapGen.Templates[generator.getName()] <- generator;
::World.resizeScene(generator.getMinX(),generator.getMinY());
::_mapBindTiles(::World.Tiles);
::didStop <- false;
foreach(name in ["buildLandAndSea","buildElevation","buildTerrainDLC","buildTerrain","defragmentTerrain",
    "removeStraits","refineTerrain","buildSettlements","buildRoads","refineSettlements",
    "guaranteeAllBuildingsInSettlements","buildAdditionalRoads","buildRoadSprites","buildLabels","buildAbandonedFortresses"]) {
    local phase=name, original=generator[name];
    generator[name] = function(...) {
        local args=[this];foreach(a in vargv) args.push(a);
        local result=original.acall(args);
        ::_mapTrace(phase);
        if(phase==::WORLD_MAP_STOP) {::dumpMap(phase);::didStop=true;throw "BBMOD_OFFLINE_STOP";}
        return result;
    };
}
::_mapSeed(::WORLD_MAP_SEED);
if(::WORLD_MAP_STOP=="api") {
    foreach(column in ::World.Tiles)foreach(tile in column)tile.Type=2;
    local probe=::World.getTileSquare(6,6);probe.RoadDirections=9;probe.Subregion=123;probe.Region=2;probe.TacticalType=22;
    local settings=::Navigator.createSettings();settings.ActionPointCosts=::Const.World.TerrainTypeNavCost_Flat;
    foreach(route in [[[60,70],[70,70]],[[60,70],[70,80]],[[70,80],[60,70]],[[60,70],[65,78]],[[60,70],[60,70]],[[5,5],[0,0]]]) {
        local path=::Navigator.findPath(::World.getTileSquare(route[0][0],route[0][1]),::World.getTileSquare(route[1][0],route[1][1]),settings,0);
        print("{\"kind\":\"path\",\"tiles\":[");local i=0;
        while(!path.isEmpty()) {
            local xy=::World.getTile(path.getCurrent()).SquareCoords;
            print((i++?",[":"[")+xy.X+","+xy.Y+"]");path.pop();
        }
        print("]}\n");
    }
} else try {
    generator.fill({X=0,Y=0,W=generator.getMinX(),H=generator.getMinY()},null);
    if(::WORLD_MAP_STOP!="search")::dumpMap("complete");
    if(::WORLD_MAP_STOP=="campaign"||::WORLD_MAP_STOP.find("campaign:")==0||::WORLD_MAP_STOP=="search")
        dofile(::WORLD_MAP_SCRIPT_DIR+"/camps.nut");
    if(::WORLD_MAP_STOP=="search")dofile(::WORLD_MAP_SCRIPT_DIR+"/search.nut");
} catch(error) {
    if(!::didStop) throw error;
}

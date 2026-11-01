// Development-only reference probe. Never shipped or loaded during normal play.
// Observe the original generator without replacing terrain, RNG or pathfinding.
::BBMODWorldmapReference <- {
    Seeds = __SEEDS__,
    ApiOnly = __API_ONLY__,
    Checkpoints = __CHECKPOINTS__,
    WithApi = __WITH_API__,
    CurrentSeed = "",
    Step = 0,
    function quote(value) {
        local s = value.tostring(), result = "\"";
        for (local i = 0; i < s.len(); i++) {
            local c = s[i];
            if (c == 34 || c == 92) result += "\\" + c.tochar();
            else if (c == 10) result += "\\n";
            else if (c == 13) result += "\\r";
            else if (c == 9) result += "\\t";
            else if (c >= 32) result += c.tochar();
        }
        return result + "\"";
    },
    function encode(value) {
        local kind = typeof value;
        if (kind == "null") return "null";
        if (kind == "string") return this.quote(value);
        if (kind == "bool") return value ? "true" : "false";
        if (kind == "integer" || kind == "float") return value.tostring();
        local parts = [];
        if (kind == "array") {
            foreach (v in value) parts.push(this.encode(v));
            return "[" + this.join(parts) + "]";
        }
        if (kind == "table") {
            foreach (k, v in value) {
                if (typeof v == "function") continue;
                parts.push(this.quote(k) + ":" + this.encode(v));
            }
            return "{" + this.join(parts) + "}";
        }
        return this.quote(value);
    },
    function join(values) {
        local result = "";
        foreach (i, v in values) result += (i ? "," : "") + v;
        return result;
    },
    function emit(kind, value) {
        ::logInfo("BBMODMapReference: " + kind + " " + this.encode(value));
    },
    function snapshot(phase, width, height) {
        local step = this.Step++;
        this.emit("phase", {seed=this.CurrentSeed, step=step, name=phase, width=width, height=height});
        for (local y = 0; y < height; y++) {
            local row = [];
            for (local x = 0; x < width; x++) {
                local tile = ::World.getTileSquare(x, y);
                row.push([tile.Type, tile.TacticalType, tile.Subregion, tile.Region, tile.RoadDirections]);
            }
            this.emit("row", {step=step, y=y, tiles=row});
        }
        this.emit("phase-end", {step=step});
    },
    function rng() {
        foreach (seed in this.Seeds) {
            local values=[];
            ::Math.seedRandomString(seed);
            for (local i=0; i<40; i++) values.push(::Math.rand(0, 2147483646));
            this.emit("rng", {seed=seed, min=0, max=2147483646, values=values});
            foreach (range in [[0, 32767], [1, 100], [-100, 100], [0, 1]]) {
                values=[];
                ::Math.seedRandomString(seed);
                for (local i=0; i<40; i++) values.push(::Math.rand(range[0], range[1]));
                this.emit("rng", {seed=seed, min=range[0], max=range[1], values=values});
            }
        }
        foreach (seed in [0,1,2,42,12345,2147483647]) {
            ::Math.seedRandom(seed);
            local values=[];
            for (local i=0; i<40; i++) values.push(::Math.rand(0,2147483646));
            this.emit("rng-integer", {seed=seed, min=0, max=2147483646, values=values});
        }
    },
    function geometry() {
        foreach (p in [[0,0],[1,1],[2,2],[3,2],[2,3],[139,139]]) {
            local tile=::World.getTileSquare(p[0],p[1]), next=[];
            for (local d=0; d<6; d++) {
                if (!tile.hasNextTile(d)) next.push(null);
                else {
                    local n=tile.getNextTile(d);
                    next.push([n.SquareCoords.X,n.SquareCoords.Y]);
                }
            }
            this.emit("geometry", {xy=p, next=next, pos=[tile.Pos.X,tile.Pos.Y], coords=[tile.Coords.X,tile.Coords.Y]});
        }
    },
    function api(width,height) {
        local time=::World.getTime();
        this.emit("world-time",{SecondsPerDay=time.SecondsPerDay,Days=time.Days,Hours=time.Hours});
        local settings=::World.getNavigator().createSettings();
        this.emit("navigator-settings",{RoadMult=settings.RoadMult,StopAtRoad=settings.StopAtRoad,
            ActionPointCosts=settings.ActionPointCosts});
        for(local x=0;x<width;x++)for(local y=0;y<height;y++)::World.getTileSquare(x,y).Type=::Const.World.TerrainType.Plains;
        foreach(p in [[6,6],[70,85],[0,0]])foreach(radius in [1,2,3]) {
            for(local x=0;x<width;x++)for(local y=0;y<height;y++)::World.getTileSquare(x,y).Region=x*height+y+1;
            local order=[];
            for(local i=0;i<80;i++) {
                local id=::World.findNextRegion(::World.getTileSquare(p[0],p[1]),radius,0);
                if(id==0)break;
                local x=(id-1)/height,y=(id-1)%height;
                order.push([x,y]);::World.getTileSquare(x,y).Region=0;
            }
            this.emit("region-search",{center=p,radius=radius,tiles=order});
        }
        for(local x=0;x<width;x++)for(local y=0;y<height;y++)::World.getTileSquare(x,y).Region=0;
        foreach(pattern in [0,1,2]) {
            for(local x=0;x<width;x++)for(local y=0;y<height;y++) {
                local tile=::World.getTileSquare(x,y),n=(x*17+y*31)%11;
                tile.Type=pattern==0?2:(pattern==1?(n%3==0?1:2):(n%4==0?0:(n%3==0?9:2)));
                tile.Region=n<4?x*height+y+1:0;
            }
            foreach(p in [[6,6],[70,85],[0,0]])foreach(radius in [1,3,16])foreach(wanted in [0,2,9])
                this.emit("region-pattern",{pattern=pattern,center=p,radius=radius,wanted=wanted,
                    result=::World.findNextRegion(::World.getTileSquare(p[0],p[1]),radius,wanted)});
        }
        for(local x=0;x<width;x++)for(local y=0;y<height;y++) {
            local tile=::World.getTileSquare(x,y);tile.Type=2;tile.Region=0;
        }
        foreach(p in [[120.0,60.0],[300.0,240.0],[210.0,120.0],[209.0,119.0],[211.0,121.0],[500.0,500.0],[25000.0,18000.0]]) {
            local c=::World.worldToTile(::createVec(p[0],p[1]));
            this.emit("world-to-tile",{pos=p,coords=[c.X,c.Y]});
        }
        for(local y=0;y<=360;y+=10) {
            local row=[];
            for(local x=0;x<=600;x+=10) {
                local c=::World.worldToTile(::createVec(x,y));row.push([c.X,c.Y]);
            }
            this.emit("world-to-tile-grid",{y=y,step=10,coords=row});
        }
        local probe=::World.getTileSquare(6,6);
        probe.Type=17;probe.TacticalType=22;probe.Subregion=123;probe.Region=2;probe.RoadDirections=9;
        probe.clear();
        this.emit("tile-clear",{Type=probe.Type,TacticalType=probe.TacticalType,Subregion=probe.Subregion,
            Region=probe.Region,RoadDirections=probe.RoadDirections});
        probe.Type=2;
        foreach(p in [[2,2],[70,85]])foreach(range in [[1,1],[1,2],[1,4],[0,2]]) {
            local result=[];
            ::World.queryTilesInRange(::World.getTileSquare(p[0],p[1]),range[0],range[1],
                function(tile,data){data.push([tile.SquareCoords.X,tile.SquareCoords.Y]);},result);
            this.emit("query-range",{center=p,minimum=range[0],maximum=range[1],tiles=result});
        }
        for(local x=0;x<width;x++)for(local y=0;y<height;y++)::World.getTileSquare(x,y).Type=::Const.World.TerrainType.Plains;
        settings.ActionPointCosts=::Const.World.TerrainTypeNavCost_Flat;
        foreach(route in [[[60,70],[70,70]],[[60,70],[70,80]],[[70,80],[60,70]],
            [[60,70],[65,78]],[[60,70],[60,70]],[[5,5],[0,0]]]) {
            local path=::World.getNavigator().findPath(::World.getTileSquare(route[0][0],route[0][1]),
                ::World.getTileSquare(route[1][0],route[1][1]),settings,0),tiles=[],size=path.getSize();
            while(!path.isEmpty()){local t=::World.getTile(path.getCurrent());tiles.push([t.SquareCoords.X,t.SquareCoords.Y]);path.pop();}
            this.emit("path",{start=route[0],end=route[1],tiles=tiles,size=size});
        }
    }
};

::mods_hookClass("mapgen/templates/world/worldmap_generator", function(o) {
    foreach (name in ["buildLandAndSea", "buildElevation", "buildTerrainDLC", "buildTerrain",
        "defragmentTerrain", "removeStraits", "refineTerrain", "buildSettlements", "buildRoads",
        "refineSettlements", "guaranteeAllBuildingsInSettlements", "buildAdditionalRoads", "buildLabels",
        "buildAbandonedFortresses"]) {
        local original = ::mods_getMember(o, name);
        local phase = name;
        ::mods_override(o, name, function(...) {
            local args=[this];
            foreach (a in vargv) args.push(a);
            local result=original.acall(args);
            if(::BBMODWorldmapReference.Checkpoints)::BBMODWorldmapReference.snapshot(phase, this.getMinX(), this.getMinY());
            return result;
        });
    }
});

::mods_hookClass("states/world_state", function(o) {
    // This test never creates or overwrites campaign saves.
    ::mods_override(o, "autosave", function() {});
    ::mods_override(o, "saveCampaign", function(...) {});
    ::mods_override(o, "startNewCampaign", function() {
        local R=::BBMODWorldmapReference;
        this.Time.setVirtualTime(0);
        R.emit("environment", {version="1.5.2.3", dlc=::Const.DLC.Mask,
            settings=::Const.World.Settings, terrain=::Const.World.TerrainType,
            tacticalTerrain=::Const.World.TerrainTacticalType});
        R.rng();
        local generator=::MapGen.get("world.worldmap_generator");
        foreach (seed in R.Seeds) {
            ::World.EntityManager.clear();
            ::World.FactionManager.clear();
            ::World.clearScene();
            ::World.resizeScene(generator.getMinX(),generator.getMinY());
            R.CurrentSeed=seed;
            R.emit("seed-begin", {seed=seed});
            R.geometry();
            if(R.ApiOnly){R.api(generator.getMinX(),generator.getMinY());break;}
            ::Math.seedRandomString(seed);
            local began=::Time.getExactTime();
            generator.fill({X=0,Y=0,W=generator.getMinX(),H=generator.getMinY()},null);
            local seconds=::Time.getExactTime()-began;
            R.snapshot("complete",generator.getMinX(),generator.getMinY());
            foreach (town in ::World.EntityManager.getSettlements()) {
                local t=town.getTile();
                local buildings=[],attached=[];
                foreach(b in town.m.Buildings)buildings.push(b==null?null:b.getID());
                foreach(a in town.getAttachedLocations()) {
                    local tile=a.getTile();
                    attached.push({name=a.getName(),type=a.m.TypeID,id=a.m.ID,xy=[tile.SquareCoords.X,tile.SquareCoords.Y]});
                }
                R.emit("settlement", {seed=seed,name=town.getName(),id=town.getID(),xy=[t.SquareCoords.X,t.SquareCoords.Y],
                    size=town.getSize(),culture=town.getCulture(),military=town.isMilitary(),coastal=town.isCoastal(),
                    buildings=buildings,attached=attached,produce=town.getProduce(),
                    price_mult=town.getPriceMult(),buy_mult=town.m.Modifiers.BuyPriceMult,sell_mult=town.m.Modifiers.SellPriceMult,
                    building_mult=town.m.Modifiers.BuildingPriceMult,incense_mult=town.m.Modifiers.IncensePriceMult,
                    connected=town.m.ConnectedTo,roads=town.m.ConnectedToByRoads});
            }
            foreach(region in this.m.Regions) {
                local x=0.0,y=0.0;
                foreach(tile in region.Tiles){x+=tile.Pos.X;y+=tile.Pos.Y;}
                x/=region.Tiles.len();y/=region.Tiles.len();
                local c=::World.worldToTile(::createVec(x,y));
                R.emit("region",{seed=seed,name=region.Name,type=region.Type,
                    size=region.Size,xy=[region.Center.SquareCoords.X,region.Center.SquareCoords.Y],
                    mean=[x,y],raw=[c.X,c.Y]});
            }
            R.emit("seed-end", {seed=seed,seconds_instrumented=seconds});
        }
        if(R.WithApi)R.api(generator.getMinX(),generator.getMinY());
        R.emit("done", {seeds=R.Seeds.len()});
        this.setAutoPause(true);
        this.setPause(true);
        this.m.IsRunningUpdatesWhilePaused=false;
    });
});

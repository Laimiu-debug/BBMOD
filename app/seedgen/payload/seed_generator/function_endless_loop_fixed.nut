local gt = this.getroottable();

gt.SeedGenerator.EndlessLoopFlag <- false;

local onSpawnPlayerMilitia = function()
{
	local randomVillage;
	local cnt = 0;

	for( local i = 0; i != this.World.EntityManager.getSettlements().len(); i = ++i )
	{
		randomVillage = this.World.EntityManager.getSettlements()[i];

		if (!randomVillage.isMilitary() && !randomVillage.isIsolatedFromRoads() && randomVillage.getSize() == 1)
		{
			break;
		}
	}

	local randomVillageTile = randomVillage.getTile();
	this.World.Flags.set("HomeVillage", randomVillage.getName());
	local navSettings = this.World.getNavigator().createSettings();
	navSettings.ActionPointCosts = this.Const.World.TerrainTypeNavCost_Flat;

	do
	{
		local x = this.Math.rand(this.Math.max(2, randomVillageTile.SquareCoords.X - 4), this.Math.min(this.Const.World.Settings.SizeX - 2, randomVillageTile.SquareCoords.X + 4));
		local y = this.Math.rand(this.Math.max(2, randomVillageTile.SquareCoords.Y - 4), this.Math.min(this.Const.World.Settings.SizeY - 2, randomVillageTile.SquareCoords.Y + 4));

		if (!this.World.isValidTileSquare(x, y))
		{
		}
		else
		{
			local tile = this.World.getTileSquare(x, y);

			if (tile.Type == this.Const.World.TerrainType.Ocean || tile.Type == this.Const.World.TerrainType.Shore)
			{
			}
			else if (tile.getDistanceTo(randomVillageTile) <= 1)
			{
			}
			else if (tile.Type != this.Const.World.TerrainType.Plains && tile.Type != this.Const.World.TerrainType.Steppe && tile.Type != this.Const.World.TerrainType.Tundra && tile.Type != this.Const.World.TerrainType.Snow)
			{
			}
			else
			{
				local path = this.World.getNavigator().findPath(tile, randomVillageTile, navSettings, 0);

				if (!path.isEmpty())
				{
					randomVillageTile = tile;
					break;
				}
			}
		}
		cnt++;
		if(cnt > 1000)
		{
			gt.SeedGenerator.EndlessLoopFlag = true;
			return;
		}
	}
	while (1);
	this.World.State.m.Player = this.World.spawnEntity("scripts/entity/world/player_party", randomVillageTile.Coords.X, randomVillageTile.Coords.Y);
	this.World.Assets.updateLook(8);
	this.World.getCamera().setPos(this.World.State.m.Player.getPos());
	randomVillage.getFactionOfType(this.Const.FactionType.Settlement).addPlayerRelation(40.0, "Considered local heroes for keeping the village safe");
	this.Time.scheduleEvent(this.TimeUnit.Real, 1000, function ( _tag )
	{
		this.Music.setTrackList([
			"music/retirement_01.ogg"
		], this.Const.Music.CrossFadeTime);
		this.World.Events.fire("event.militia_scenario_intro");
	}, null);
}

local onSpawnPlayerLoneWolf = function()
{
	local randomVillage;
	local cnt = 0;

	for( local i = 0; i != this.World.EntityManager.getSettlements().len(); i = ++i )
	{
		randomVillage = this.World.EntityManager.getSettlements()[i];

		if (randomVillage.isMilitary() && !randomVillage.isIsolatedFromRoads() && randomVillage.getSize() >= 3 && !randomVillage.isSouthern())
		{
			break;
		}
	}

	local randomVillageTile = randomVillage.getTile();

	do
	{
		local x = this.Math.rand(this.Math.max(2, randomVillageTile.SquareCoords.X - 1), this.Math.min(this.Const.World.Settings.SizeX - 2, randomVillageTile.SquareCoords.X + 1));
		local y = this.Math.rand(this.Math.max(2, randomVillageTile.SquareCoords.Y - 1), this.Math.min(this.Const.World.Settings.SizeY - 2, randomVillageTile.SquareCoords.Y + 1));

		if (!this.World.isValidTileSquare(x, y))
		{
		}
		else
		{
			local tile = this.World.getTileSquare(x, y);

			if (tile.Type == this.Const.World.TerrainType.Ocean || tile.Type == this.Const.World.TerrainType.Shore)
			{
			}
			else if (tile.getDistanceTo(randomVillageTile) == 0)
			{
			}
			else if (!tile.HasRoad)
			{
			}
			else
			{
				randomVillageTile = tile;
				break;
			}
		}
		cnt++;
		if(cnt > 1000)
		{
			gt.SeedGenerator.EndlessLoopFlag = true;
			return;
		}
	}
	while (1);

	this.World.State.m.Player = this.World.spawnEntity("scripts/entity/world/player_party", randomVillageTile.Coords.X, randomVillageTile.Coords.Y);
	this.World.Assets.updateLook(6);
	this.World.getCamera().setPos(this.World.State.m.Player.getPos());
	this.Time.scheduleEvent(this.TimeUnit.Real, 1000, function ( _tag )
	{
		this.Music.setTrackList([
			"music/noble_02.ogg"
		], this.Const.Music.CrossFadeTime);
		this.World.Events.fire("event.lone_wolf_scenario_intro");
	}, null);
}


local onSpawnPlayerAnatomists = function()
{
	local randomVillage;
	local cnt = 0;

	for( local i = 0; i != this.World.EntityManager.getSettlements().len(); i = ++i )
	{
		randomVillage = this.World.EntityManager.getSettlements()[i];

		if (!randomVillage.isMilitary() && !randomVillage.isIsolatedFromRoads() && randomVillage.getSize() >= 3 && !randomVillage.isSouthern())
		{
			break;
		}
	}

	local randomVillageTile = randomVillage.getTile();
	local navSettings = this.World.getNavigator().createSettings();
	navSettings.ActionPointCosts = this.Const.World.TerrainTypeNavCost_Flat;

	do
	{
		local x = this.Math.rand(this.Math.max(2, randomVillageTile.SquareCoords.X - 4), this.Math.min(this.Const.World.Settings.SizeX - 2, randomVillageTile.SquareCoords.X + 4));
		local y = this.Math.rand(this.Math.max(2, randomVillageTile.SquareCoords.Y - 4), this.Math.min(this.Const.World.Settings.SizeY - 2, randomVillageTile.SquareCoords.Y + 4));

		if (!this.World.isValidTileSquare(x, y))
		{
		}
		else
		{
			local tile = this.World.getTileSquare(x, y);

			if (tile.Type == this.Const.World.TerrainType.Ocean || tile.Type == this.Const.World.TerrainType.Shore || tile.IsOccupied)
			{
			}
			else if (tile.getDistanceTo(randomVillageTile) <= 1)
			{
			}
			else
			{
				local path = this.World.getNavigator().findPath(tile, randomVillageTile, navSettings, 0);

				if (!path.isEmpty())
				{
					randomVillageTile = tile;
					break;
				}
			}
		}
		cnt++;
		if(cnt > 1000)
		{
			gt.SeedGenerator.EndlessLoopFlag = true;
			return;
		}
	}
	while (1);

	this.World.State.m.Player = this.World.spawnEntity("scripts/entity/world/player_party", randomVillageTile.Coords.X, randomVillageTile.Coords.Y);
	this.World.Assets.updateLook(20);
	this.World.getCamera().setPos(this.World.State.m.Player.getPos());
	this.Time.scheduleEvent(this.TimeUnit.Real, 1000, function ( _tag )
	{
		this.Music.setTrackList(this.Const.Music.IntroTracks, this.Const.Music.CrossFadeTime);
		this.World.Events.fire("event.anatomists_scenario_intro");
	}, null);
}

local onSpawnPlayerPaladins = function()
{
	local randomVillage;
	local cnt = 0;

	for( local i = 0; i != this.World.EntityManager.getSettlements().len(); i = ++i )
	{
		randomVillage = this.World.EntityManager.getSettlements()[i];

		if (!randomVillage.isMilitary() && !randomVillage.isIsolatedFromRoads() && randomVillage.getSize() >= 3 && !randomVillage.isSouthern())
		{
			break;
		}
	}

	local randomVillageTile = randomVillage.getTile();
	local navSettings = this.World.getNavigator().createSettings();
	navSettings.ActionPointCosts = this.Const.World.TerrainTypeNavCost_Flat;

	do
	{
		local x = this.Math.rand(this.Math.max(2, randomVillageTile.SquareCoords.X - 4), this.Math.min(this.Const.World.Settings.SizeX - 2, randomVillageTile.SquareCoords.X + 4));
		local y = this.Math.rand(this.Math.max(2, randomVillageTile.SquareCoords.Y - 4), this.Math.min(this.Const.World.Settings.SizeY - 2, randomVillageTile.SquareCoords.Y + 4));

		if (!this.World.isValidTileSquare(x, y))
		{
		}
		else
		{
			local tile = this.World.getTileSquare(x, y);

			if (tile.Type == this.Const.World.TerrainType.Ocean || tile.Type == this.Const.World.TerrainType.Shore || tile.IsOccupied)
			{
			}
			else if (tile.getDistanceTo(randomVillageTile) <= 1)
			{
			}
			else
			{
				local path = this.World.getNavigator().findPath(tile, randomVillageTile, navSettings, 0);

				if (!path.isEmpty())
				{
					randomVillageTile = tile;
					break;
				}
			}
		}
		cnt++;
		if(cnt > 1000)
		{
			gt.SeedGenerator.EndlessLoopFlag = true;
			return;
		}
	}
	while (1);

	this.World.State.m.Player = this.World.spawnEntity("scripts/entity/world/player_party", randomVillageTile.Coords.X, randomVillageTile.Coords.Y);
	this.World.Assets.updateLook(19);
	this.World.getCamera().setPos(this.World.State.m.Player.getPos());
	this.Time.scheduleEvent(this.TimeUnit.Real, 1000, function ( _tag )
	{
		this.Music.setTrackList(this.Const.Music.IntroTracks, this.Const.Music.CrossFadeTime);
		this.World.Events.fire("event.paladins_scenario_intro");
	}, null);
}

local onSpawnPlayerRaiders = function()
{
	local randomVillage;
	local northernmostY = 0;
	local cnt = 0;

	for( local i = 0; i != this.World.EntityManager.getSettlements().len(); i = ++i )
	{
		local v = this.World.EntityManager.getSettlements()[i];

		if (v.getTile().SquareCoords.Y > northernmostY && !v.isMilitary() && !v.isIsolatedFromRoads() && v.getSize() <= 2)
		{
			northernmostY = v.getTile().SquareCoords.Y;
			randomVillage = v;
		}
	}

	randomVillage.setLastSpawnTimeToNow();
	local randomVillageTile = randomVillage.getTile();
	local navSettings = this.World.getNavigator().createSettings();
	navSettings.ActionPointCosts = this.Const.World.TerrainTypeNavCost_Flat;

	do
	{
		local x = this.Math.rand(this.Math.max(2, randomVillageTile.SquareCoords.X - 2), this.Math.min(this.Const.World.Settings.SizeX - 2, randomVillageTile.SquareCoords.X + 2));
		local y = this.Math.rand(this.Math.max(2, randomVillageTile.SquareCoords.Y - 2), this.Math.min(this.Const.World.Settings.SizeY - 2, randomVillageTile.SquareCoords.Y + 2));

		if (!this.World.isValidTileSquare(x, y))
		{
		}
		else
		{
			local tile = this.World.getTileSquare(x, y);

			if (tile.Type == this.Const.World.TerrainType.Ocean || tile.Type == this.Const.World.TerrainType.Shore || tile.IsOccupied)
			{
			}
			else if (tile.getDistanceTo(randomVillageTile) <= 1)
			{
			}
			else
			{
				local path = this.World.getNavigator().findPath(tile, randomVillageTile, navSettings, 0);

				if (!path.isEmpty())
				{
					randomVillageTile = tile;
					break;
				}
			}
		}
		cnt++;
		if(cnt > 1000)
		{
			gt.SeedGenerator.EndlessLoopFlag = true;
			return;
		}
	}
	while (1);

	local attachedLocations = randomVillage.getAttachedLocations();
	local closest;
	local dist = 99999;

	foreach( a in attachedLocations )
	{
		if (a.getTile().getDistanceTo(randomVillageTile) < dist)
		{
			dist = a.getTile().getDistanceTo(randomVillageTile);
			closest = a;
		}
	}

	if (closest != null)
	{
		closest.setActive(false);
		closest.spawnFireAndSmoke();
	}

	local s = this.new("scripts/entity/world/settlements/situations/raided_situation");
	s.setValidForDays(5);
	randomVillage.addSituation(s);
	local nobles = this.World.FactionManager.getFactionsOfType(this.Const.FactionType.NobleHouse);
	local houses = [];

	foreach( n in nobles )
	{
		local closest;
		local dist = 9999;

		foreach( s in n.getSettlements() )
		{
			local d = s.getTile().getDistanceTo(randomVillageTile);

			if (d < dist)
			{
				dist = d;
				closest = s;
			}
		}

		houses.push({
			Faction = n,
			Dist = dist
		});
	}

	houses.sort(function ( _a, _b )
	{
		if (_a.Dist > _b.Dist)
		{
			return 1;
		}
		else if (_a.Dist < _b.Dist)
		{
			return -1;
		}

		return 0;
	});

	for( local i = 0; i < 2; i = ++i )
	{
		houses[i].Faction.addPlayerRelation(-100.0, "You are considered outlaws and barbarians");
	}

	houses[1].Faction.addPlayerRelation(18.0);
	this.World.State.m.Player = this.World.spawnEntity("scripts/entity/world/player_party", randomVillageTile.Coords.X, randomVillageTile.Coords.Y);
	this.World.Assets.updateLook(5);
	this.World.getCamera().setPos(this.World.State.m.Player.getPos());
	this.Time.scheduleEvent(this.TimeUnit.Real, 1000, function ( _tag )
	{
		this.Music.setTrackList([
			"music/barbarians_02.ogg"
		], this.Const.Music.CrossFadeTime);
		this.World.Events.fire("event.raiders_scenario_intro");
	}, null);
}

local onSpawnPlayerCultists = function()
{
	local randomVillage;
	local cnt = 0;

	for( local i = 0; i != this.World.EntityManager.getSettlements().len(); i = ++i )
	{
		randomVillage = this.World.EntityManager.getSettlements()[i];

		if (!randomVillage.isMilitary() && !randomVillage.isIsolatedFromRoads() && randomVillage.getSize() == 1)
		{
			break;
		}
	}

	local randomVillageTile = randomVillage.getTile();
	local navSettings = this.World.getNavigator().createSettings();
	navSettings.ActionPointCosts = this.Const.World.TerrainTypeNavCost_Flat;

	do
	{
		local x = this.Math.rand(this.Math.max(2, randomVillageTile.SquareCoords.X - 4), this.Math.min(this.Const.World.Settings.SizeX - 2, randomVillageTile.SquareCoords.X + 4));
		local y = this.Math.rand(this.Math.max(2, randomVillageTile.SquareCoords.Y - 4), this.Math.min(this.Const.World.Settings.SizeY - 2, randomVillageTile.SquareCoords.Y + 4));

		if (!this.World.isValidTileSquare(x, y))
		{
		}
		else
		{
			local tile = this.World.getTileSquare(x, y);

			if (tile.Type == this.Const.World.TerrainType.Ocean || tile.Type == this.Const.World.TerrainType.Shore || tile.IsOccupied)
			{
			}
			else if (tile.getDistanceTo(randomVillageTile) <= 1)
			{
			}
			else if (tile.Type != this.Const.World.TerrainType.Plains && tile.Type != this.Const.World.TerrainType.Steppe && tile.Type != this.Const.World.TerrainType.Tundra && tile.Type != this.Const.World.TerrainType.Snow)
			{
			}
			else
			{
				local path = this.World.getNavigator().findPath(tile, randomVillageTile, navSettings, 0);

				if (!path.isEmpty())
				{
					randomVillageTile = tile;
					break;
				}
			}
		}
		cnt++;
		if(cnt > 1000)
		{
			gt.SeedGenerator.EndlessLoopFlag = true;
			return;
		}
	}
	while (1);

	this.World.State.m.Player = this.World.spawnEntity("scripts/entity/world/player_party", randomVillageTile.Coords.X, randomVillageTile.Coords.Y);
	this.World.Assets.updateLook(7);
	this.World.getCamera().setPos(this.World.State.m.Player.getPos());
	this.Time.scheduleEvent(this.TimeUnit.Real, 1000, function ( _tag )
	{
		this.Music.setTrackList(this.Const.Music.CivilianTracks, this.Const.Music.CrossFadeTime);
		this.World.Events.fire("event.cultists_scenario_intro");
	}, null);
}

::mods_hookClass("scenarios/world/militia_scenario",
  function(o) { ::mods_override(o, "onSpawnPlayer", onSpawnPlayerMilitia); });

::mods_hookClass("scenarios/world/lone_wolf_scenario",
  function(o) { ::mods_override(o, "onSpawnPlayer", onSpawnPlayerLoneWolf); });

::mods_hookClass("scenarios/world/anatomists_scenario",
  function(o) { ::mods_override(o, "onSpawnPlayer", onSpawnPlayerAnatomists); });

::mods_hookClass("scenarios/world/paladins_scenario",
  function(o) { ::mods_override(o, "onSpawnPlayer", onSpawnPlayerPaladins); });

::mods_hookClass("scenarios/world/raiders_scenario",
  function(o) { ::mods_override(o, "onSpawnPlayer", onSpawnPlayerRaiders); });

::mods_hookClass("scenarios/world/cultists_scenario",
  function(o) { ::mods_override(o, "onSpawnPlayer", onSpawnPlayerCultists); });
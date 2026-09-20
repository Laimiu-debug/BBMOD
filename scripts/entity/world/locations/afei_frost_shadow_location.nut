this.afei_frost_shadow_location <- this.inherit("scripts/entity/world/locations/bandit_camp_location", {
	function create()
	{
		this.bandit_camp_location.create();
		this.m.Name = "北境白影巢穴";
		this.m.Description = "猎人传闻中的冰霜巨兽出没处。编制：1 冰霜巨兽 + 至多 2 普通巨兽。";
		this.m.Resources = 200;
	}

	function onSpawned()
	{
		this.bandit_camp_location.onSpawned();
		this.applyFrostRoster();
	}

	function applyFrostRoster()
	{
		// 优先挂官方巨兽 spawnlist；失败则战斗中由战术钩按设定补编
		local lists = [];

		try
		{
			if (("UnholdFrost" in this.Const.World.Spawn))
			{
				lists.push(this.Const.World.Spawn.UnholdFrost);
			}
		}
		catch (error)
		{
		}

		try
		{
			if (("Unholds" in this.Const.World.Spawn))
			{
				lists.push(this.Const.World.Spawn.Unholds);
			}
		}
		catch (error2)
		{
		}

		try
		{
			if (("Beasts" in this.Const.World.Spawn))
			{
				lists.push(this.Const.World.Spawn.Beasts);
			}
		}
		catch (error3)
		{
		}

		foreach (lst in lists)
		{
			try
			{
				this.setDefenderSpawnList(lst);

				if ("clearDefenders" in this)
				{
					this.clearDefenders();
				}

				if ("createDefenders" in this)
				{
					this.createDefenders();
				}

				this.getFlags().set("afei_frost_roster", 1);
				return;
			}
			catch (error4)
			{
			}
		}

		this.getFlags().set("afei_frost_roster_fallback", 1);
	}
});

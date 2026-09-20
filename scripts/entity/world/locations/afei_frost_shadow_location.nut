this.afei_frost_shadow_location <- this.inherit("scripts/entity/world/locations/bandit_camp_location", {
	function create()
	{
		this.bandit_camp_location.create();
		this.m.Name = "北境白影巢穴";
		this.m.Description = "编制固定：1 冰霜巨兽 + 至多 2 普通巨兽。战术开战时由起源钩精确生成，不复用匪营随机编制。";
		this.m.Resources = 200;
	}

	function onSpawned()
	{
		this.bandit_camp_location.onSpawned();

		try
		{
			if ("clearDefenders" in this)
			{
				this.clearDefenders();
			}
		}
		catch (errorClear)
		{
		}

		this.getFlags().set("afei_frost_roster", 1);
		this.getFlags().set("afei_frost_exact", 1);
		this.World.Flags.set("afei_spawn_frost_roster", 1);
	}

	function createDefenders()
	{
		// 空编制：真正敌人由 spawnFrostRosterExact 在战术开场生成
	}
});

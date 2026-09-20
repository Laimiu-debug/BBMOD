this.afei_frost_unhold <- this.inherit("scripts/entity/tactical/enemies/unhold", {
	function create()
	{
		this.unhold.create();
		this.m.Name = "冰霜巨兽";
		this.m.Description = "北境白影——厚实白毛的冰霜巨兽。";
	}

	function onInit()
	{
		this.unhold.onInit();

		try
		{
			local b = this.getBaseProperties();
			b.Hitpoints += 80;
			b.Armor[0] += 40;
			b.Armor[1] += 40;
			b.MeleeDefense += 5;
			b.RangedDefense += 5;
			this.getSkills().update();
		}
		catch (error)
		{
		}

		this.getFlags().set("afei_frost_unhold", true);
	}
});

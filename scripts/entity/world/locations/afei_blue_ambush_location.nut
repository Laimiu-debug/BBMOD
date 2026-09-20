this.afei_blue_ambush_location <- this.inherit("scripts/entity/world/locations/bandit_camp_location", {
	function create()
	{
		this.bandit_camp_location.create();
		this.m.Name = "蓝旗护送伏击点";
		this.m.Description = "联合护送途中遭遇的伏击营地。";
	}
});

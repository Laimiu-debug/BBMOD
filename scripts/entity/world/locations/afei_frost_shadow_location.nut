this.afei_frost_shadow_location <- this.inherit("scripts/entity/world/locations/bandit_camp_location", {
	function create()
	{
		this.bandit_camp_location.create();
		this.m.Name = "北境白影巢穴";
		this.m.Description = "猎人传闻中的冰霜巨兽出没处。开战时按野兽编制结算。";
	}
});

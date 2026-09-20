this.afei_cohesion_rule <- this.inherit("scripts/skills/skill", {
	m = {},
	function create()
	{
		this.m.ID = "actives.afei_cohesion_rule";
		this.m.Name = "磨合";
		this.m.Description = "战团磨合影响决心：低(<30) -3，中 0，高(>=70) +3。";
		this.m.Icon = "ui/orientation/shortsword_orientation.png";
		this.m.Type = this.Const.SkillType.Special;
		this.m.IsActive = false;
	}
	function onUpdate(_properties)
	{
		if (!::AfeiExpedition.isAfeiOrigin()) { return; }
		local c = this.World.Flags.getAsInt("afei_cohesion");
		if (c < 30) { _properties.Bravery -= 3; }
		else if (c >= 70) { _properties.Bravery += 3; }
	}
});

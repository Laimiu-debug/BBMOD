this.afei_moon_cake <- this.inherit("scripts/skills/skill", {
	m = {},
	function create()
	{
		this.m.ID = "actives.afei_moon_cake";
		this.m.Name = "月饼准备";
		this.m.Description = "营地被动占位：生命+4。";
		this.m.Icon = "ui/orientation/shortsword_orientation.png";
		this.m.Type = this.Const.SkillType.Special;
		this.m.IsActive = false;
		this.m.IsStacking = false;
	}
	function onUpdate(_properties)
	{
		_properties.Hitpoints += 4;
	}
});

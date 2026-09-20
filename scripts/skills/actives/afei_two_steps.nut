this.afei_two_steps <- this.inherit("scripts/skills/skill", {
	m = {},
	function create()
	{
		this.m.ID = "actives.afei_two_steps";
		this.m.Name = "脚下两步";
		this.m.Description = "先攻+4、近攻+3。";
		this.m.Icon = "ui/orientation/shortsword_orientation.png";
		this.m.Type = this.Const.SkillType.Special;
		this.m.IsActive = false;
		this.m.IsStacking = false;
	}
	function onUpdate(_properties)
	{
		_properties.Initiative += 4; _properties.MeleeSkill += 3;
	}
});

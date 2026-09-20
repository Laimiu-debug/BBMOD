this.afei_next_path <- this.inherit("scripts/skills/skill", {
	m = {},
	function create()
	{
		this.m.ID = "actives.afei_next_path";
		this.m.Name = "下一招换个路";
		this.m.Description = "换目标近攻+4（近似常驻+3）。";
		this.m.Icon = "ui/orientation/shortsword_orientation.png";
		this.m.Type = this.Const.SkillType.Special;
		this.m.IsActive = false;
		this.m.IsStacking = false;
	}
	function onUpdate(_properties)
	{
		_properties.MeleeSkill += 3;
	}
});

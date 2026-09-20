this.afei_lamp_look <- this.inherit("scripts/skills/skill", {
	m = {},
	function create()
	{
		this.m.ID = "actives.afei_lamp_look";
		this.m.Name = "灯下再看";
		this.m.Description = "远攻+3。";
		this.m.Icon = "ui/orientation/shortsword_orientation.png";
		this.m.Type = this.Const.SkillType.Special;
		this.m.IsActive = false;
		this.m.IsStacking = false;
	}
	function onUpdate(_properties)
	{
		_properties.RangedSkill += 3;
	}
});

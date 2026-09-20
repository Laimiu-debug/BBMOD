this.afei_one_more_night <- this.inherit("scripts/skills/skill", {
	m = {},
	function create()
	{
		this.m.ID = "actives.afei_one_more_night";
		this.m.Name = "再留一晚";
		this.m.Description = "营地技巧占位：磨合相关（战斗中决心+3）。";
		this.m.Icon = "ui/orientation/shortsword_orientation.png";
		this.m.Type = this.Const.SkillType.Special;
		this.m.IsActive = false;
		this.m.IsStacking = false;
	}
	function onUpdate(_properties)
	{
		_properties.Bravery += 3;
	}
});

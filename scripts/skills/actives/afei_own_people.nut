this.afei_own_people <- this.inherit("scripts/skills/skill", {
	m = {},
	function create()
	{
		this.m.ID = "actives.afei_own_people";
		this.m.Name = "自己人";
		this.m.Description = "射击友军邻接目标时远攻+5（近似远攻+4）。";
		this.m.Icon = "ui/orientation/shortsword_orientation.png";
		this.m.Type = this.Const.SkillType.Special;
		this.m.IsActive = false;
		this.m.IsStacking = false;
	}
	function onUpdate(_properties)
	{
		_properties.RangedSkill += 4;
	}
});

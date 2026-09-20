this.afei_scout_path <- this.inherit("scripts/skills/skill", {
	m = {},
	function create()
	{
		this.m.ID = "actives.afei_scout_path";
		this.m.Name = "探路";
		this.m.Description = "行军技巧占位：世界地图移动疲劳近似（战斗中先攻 +4）。";
		this.m.Icon = "ui/orientation/shortsword_orientation.png";
		this.m.Type = this.Const.SkillType.Special;
		this.m.IsActive = false;
		this.m.IsStacking = false;
	}
	function onUpdate(_properties)
	{
		_properties.Initiative += 4;
	}
});

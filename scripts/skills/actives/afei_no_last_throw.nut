this.afei_no_last_throw <- this.inherit("scripts/skills/skill", {
	m = {},
	function create()
	{
		this.m.ID = "actives.afei_no_last_throw";
		this.m.Name = "别把最后一支乱扔";
		this.m.Description = "投掷/远程首发疲劳近似：远攻+4。";
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

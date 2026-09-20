this.afei_purse_clear <- this.inherit("scripts/skills/skill", {
	m = {},
	function create()
	{
		this.m.ID = "actives.afei_purse_clear";
		this.m.Name = "钱袋算清";
		this.m.Description = "交易被动占位：决心+4。";
		this.m.Icon = "ui/orientation/shortsword_orientation.png";
		this.m.Type = this.Const.SkillType.Special;
		this.m.IsActive = false;
		this.m.IsStacking = false;
	}
	function onUpdate(_properties)
	{
		_properties.Bravery += 4;
	}
});

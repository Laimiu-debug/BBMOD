this.afei_long_run_breath <- this.inherit("scripts/skills/skill", {
	m = {},
	function create()
	{
		this.m.ID = "actives.afei_long_run_breath";
		this.m.Name = "长跑留一口";
		this.m.Description = "疲劳+10。";
		this.m.Icon = "ui/orientation/shortsword_orientation.png";
		this.m.Type = this.Const.SkillType.Special;
		this.m.IsActive = false;
		this.m.IsStacking = false;
	}
	function onUpdate(_properties)
	{
		_properties.Stamina += 10;
	}
});

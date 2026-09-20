this.afei_segment_breath <- this.inherit("scripts/skills/skill", {
	m = {},
	function create()
	{
		this.m.ID = "actives.afei_segment_breath";
		this.m.Name = "分段呼吸";
		this.m.Description = "每轮开始恢复疲劳近似（被动占位疲劳+6）。";
		this.m.Icon = "ui/orientation/shortsword_orientation.png";
		this.m.Type = this.Const.SkillType.Special;
		this.m.IsActive = false;
		this.m.IsStacking = false;
	}
	function onUpdate(_properties)
	{
		_properties.Stamina += 6;
	}
});

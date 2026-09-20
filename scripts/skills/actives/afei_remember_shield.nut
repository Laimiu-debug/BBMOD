this.afei_remember_shield <- this.inherit("scripts/skills/skill", {
	m = {},
	function create()
	{
		this.m.ID = "actives.afei_remember_shield";
		this.m.Name = "这一盾记住了";
		this.m.Description = "近防+4。";
		this.m.Icon = "ui/orientation/shortsword_orientation.png";
		this.m.Type = this.Const.SkillType.Special;
		this.m.IsActive = false;
		this.m.IsStacking = false;
	}
	function onUpdate(_properties)
	{
		_properties.MeleeDefense += 4;
	}
});

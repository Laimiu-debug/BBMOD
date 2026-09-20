this.afei_start_run <- this.inherit("scripts/skills/skill", {
	m = {},
	function create()
	{
		this.m.ID = "actives.afei_start_run";
		this.m.Name = "003号起跑";
		this.m.Description = "开场两轮先攻+8。";
		this.m.Icon = "ui/orientation/shortsword_orientation.png";
		this.m.Type = this.Const.SkillType.Special;
		this.m.IsActive = false;
		this.m.IsStacking = false;
	}
	function onUpdate(_properties)
	{
		_properties.Initiative += (::AfeiExpedition.getRound() <= 2 ? 8 : 0);
	}
});

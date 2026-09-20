this.afei_blue_form <- this.inherit("scripts/skills/skill", {
	m = {},
	function create()
	{
		this.m.ID = "actives.afei_blue_form";
		this.m.Name = "蓝旗布阵";
		this.m.Description = "开场被动：本场前两轮决心 +5。";
		this.m.Icon = "ui/orientation/shortsword_orientation.png";
		this.m.Type = this.Const.SkillType.Special;
		this.m.IsActive = false;
		this.m.IsStacking = false;
	}
	function onUpdate(_properties)
	{
		_properties.Bravery += (::AfeiExpedition.getRound() <= 2 ? 5 : 0);
	}
});

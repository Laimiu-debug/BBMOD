this.afei_wake_later <- this.inherit("scripts/skills/skill", {
	m = {},
	function create()
	{
		this.m.ID = "actives.afei_wake_later";
		this.m.Name = "睡醒再说";
		this.m.Description = "第三轮后远攻+6，第一轮-5近似：第三轮后+6。";
		this.m.Icon = "ui/orientation/shortsword_orientation.png";
		this.m.Type = this.Const.SkillType.Special;
		this.m.IsActive = false;
		this.m.IsStacking = false;
	}
	function onUpdate(_properties)
	{
		_properties.RangedSkill += (::AfeiExpedition.getRound() >= 3 ? 6 : 0);
	}
});

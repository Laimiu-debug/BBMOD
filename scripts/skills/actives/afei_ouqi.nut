this.afei_ouqi <- this.inherit("scripts/skills/skill", {
	m = { Used = false },
	function create()
	{
		this.m.ID = "actives.afei_ouqi";
		this.m.Name = "欧气";
		this.m.Description = "每场第一次普通士气检定失败时重掷一次。[color=#8f2525]TODO：[/color] 需挂 morale check 钩；当前以决心 +5 近似首场容错。";
		this.m.Icon = "ui/orientation/shortsword_orientation.png";
		this.m.Type = this.Const.SkillType.Special;
		this.m.IsActive = false;
	}
	function onUpdate(_properties)
	{
		if (!this.m.Used) { _properties.Bravery += 5; }
	}
	function onCombatStarted() { this.m.Used = false; }
});

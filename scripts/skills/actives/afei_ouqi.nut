this.afei_ouqi <- this.inherit("scripts/skills/skill", {
	m = { Used = false },
	function create()
	{
		this.m.ID = "actives.afei_ouqi";
		this.m.Name = "欧气";
		this.m.Description = "每场第一次普通士气检定失败时，按同一概率重掷一次，采用第二次结果。";
		this.m.Icon = "ui/orientation/shortsword_orientation.png";
		this.m.Type = this.Const.SkillType.Special;
		this.m.IsActive = false;
	}
	function onCombatStarted() { this.m.Used = false; }
});

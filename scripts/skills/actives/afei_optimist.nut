this.afei_optimist <- this.inherit("scripts/skills/skill", {
	m = {},
	function create()
	{
		this.m.ID = "actives.afei_optimist";
		this.m.Name = "乐天派";
		this.m.Description = "每场第一次普通士气检定失败时取消下降。[color=#8f2525]TODO：[/color] 需 morale 钩；当前决心 +4 近似。";
		this.m.Icon = "ui/orientation/shortsword_orientation.png";
		this.m.Type = this.Const.SkillType.Special;
		this.m.IsActive = false;
	}
	function onUpdate(_properties) { _properties.Bravery += 4; }
});

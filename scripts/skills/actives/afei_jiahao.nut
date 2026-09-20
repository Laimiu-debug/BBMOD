this.afei_jiahao <- this.inherit("scripts/skills/skill", {
	m = {},
	function create()
	{
		this.m.ID = "actives.afei_jiahao";
		this.m.Name = "嘉豪";
		this.m.Description = "命名伙伴首次完成个人成长时，阿飞永久决心 +4、最大疲劳 +2，最多 16 人。阶段1：成长线未全开，仅提供计数面板；可用调试/后续 G 结算写入。";
		this.m.Icon = "ui/orientation/shortsword_orientation.png";
		this.m.Type = this.Const.SkillType.Special;
		this.m.IsActive = false;
	}
	function getTooltip()
	{
		local n = ::AfeiExpedition.getJiahaoCount();
		return [
			{ id = 1, type = "title", text = this.getName() },
			{ id = 2, type = "description", text = this.getDescription() },
			{ id = 10, type = "text", icon = "ui/icons/special.png", text = "已见证成长：" + n + " / 16" }
		];
	}
	function onUpdate(_properties)
	{
		local n = ::AfeiExpedition.getJiahaoCount();
		_properties.Bravery += 4 * n;
		_properties.Stamina += 2 * n;
	}
});

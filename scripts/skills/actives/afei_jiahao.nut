this.afei_jiahao <- this.inherit("scripts/skills/skill", {
	m = {},
	function create()
	{
		this.m.ID = "actives.afei_jiahao";
		this.m.Name = "嘉豪";
		this.m.Description = "命名伙伴首次完成个人成长时，阿飞永久决心 +4、最大疲劳 +2，最多见证 16 人；每人只记一次。阿飞永久死亡后不再获得新的见证。";
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
			{ id = 10, type = "text", icon = "ui/icons/special.png", text = "已见证成长：" + n + " / 16（决心 +" + (4 * n) + "，疲劳 +" + (2 * n) + "）" }
		];
	}
	function onUpdate(_properties)
	{
		local n = ::AfeiExpedition.getJiahaoCount();
		_properties.Bravery += 4 * n;
		_properties.Stamina += 2 * n;
	}
});

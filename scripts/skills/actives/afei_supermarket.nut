this.afei_supermarket <- this.inherit("scripts/skills/skill", {
	m = {},
	function create()
	{
		this.m.ID = "actives.afei_supermarket";
		this.m.Name = "超市里";
		this.m.Description = "每个游戏日一次：商店食物购买价格 -15%（最多省 30 克朗，成交价向上取整）。成功成交才消耗当日次数。";
		this.m.Icon = "ui/orientation/shortsword_orientation.png";
		this.m.Type = this.Const.SkillType.Special;
		this.m.IsActive = false;
	}
	function getTooltip()
	{
		local day = this.World.getTime().Days;
		local used = this.World.Flags.getAsInt("afei_market_day") == day;
		return [
			{ id = 1, type = "title", text = this.getName() },
			{ id = 2, type = "description", text = this.getDescription() },
			{ id = 10, type = "text", icon = "ui/icons/asset_food.png", text = used ? "今日已使用" : "今日可用" }
		];
	}
});

this.afei_supermarket <- this.inherit("scripts/skills/skill", {
	m = {},
	function create()
	{
		this.m.ID = "actives.afei_supermarket";
		this.m.Name = "超市里";
		this.m.Description = "每个游戏日一次，商店食物购买降价 15%（最多省 30）。[color=#8f2525]TODO：[/color] 需挂商店购买钩；当前仅名册标记，无实机折扣。";
		this.m.Icon = "ui/orientation/shortsword_orientation.png";
		this.m.Type = this.Const.SkillType.Special;
		this.m.IsActive = false;
	}
});

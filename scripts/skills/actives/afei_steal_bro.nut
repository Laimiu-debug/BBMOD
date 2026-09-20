this.afei_steal_bro <- this.inherit("scripts/skills/skill", {
	m = {},
	function create()
	{
		this.m.ID = "actives.afei_steal_bro";
		this.m.Name = "偷大哥";
		this.m.Description = "每七日可谈成一次引荐（营地事件）：为一名已满足招募条件的候选人保留八折签约价，最多省 200 克朗。签约成功后开始七日冷却。";
		this.m.Icon = "ui/orientation/shortsword_orientation.png";
		this.m.Type = this.Const.SkillType.Special;
		this.m.IsActive = false;
	}
	function getTooltip()
	{
		local ready = this.World.getTime().Days >= this.World.Flags.getAsInt("afei_steal_ready_day");
		local target = this.World.Flags.get("afei_steal_target");
		return [
			{ id = 1, type = "title", text = this.getName() },
			{ id = 2, type = "description", text = this.getDescription() },
			{ id = 10, type = "text", icon = "ui/icons/special.png", text = ready ? "可发起引荐" : ("冷却至第 " + this.World.Flags.getAsInt("afei_steal_ready_day") + " 日") },
			{ id = 11, type = "text", icon = "ui/icons/asset_money.png", text = target != null && target != "" ? ("当前报价目标：" + target) : "无保留报价" }
		];
	}
});

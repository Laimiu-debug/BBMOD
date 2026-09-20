this.afei_unselectable <- this.inherit("scripts/skills/skill", {
	m = { IsSpent = false },
	function create()
	{
		this.m.ID = "actives.afei_unselectable";
		this.m.Name = "无法选中";
		this.m.Description = "每战一次。无邻接敌人时发动：至下次自身行动开始，获得近防/远防 +15 近似「难以被单体点名」。[color=#8f2525]TODO：[/color] 完整 AI 选取排除需实机钩。";
		this.m.Icon = "skills/active_42.png";
		this.m.IconDisabled = "skills/active_42_sw.png";
		this.m.Type = this.Const.SkillType.Active;
		this.m.Order = this.Const.SkillOrder.Any;
		this.m.IsSerialized = false;
		this.m.IsActive = true;
		this.m.IsTargeted = false;
		this.m.ActionPointCost = 4;
		this.m.FatigueCost = 20;
	}
	function isUsable()
	{
		if (!this.skill.isUsable() || this.m.IsSpent) { return false; }
		local actor = this.getContainer().getActor();
		local myTile = actor.getTile();
		for (local i = 0; i < 6; i++)
		{
			if (myTile.hasNextTile(i))
			{
				local t = myTile.getNextTile(i);
				if (t.IsOccupiedByActor && !t.getEntity().isAlliedWith(actor)) { return false; }
			}
		}
		return true;
	}
	function onUse(_user, _targetTile)
	{
		this.m.IsSpent = true;
		_user.getSkills().add(this.new("scripts/skills/effects/afei_unselectable_effect"));
		return true;
	}
	function onCombatStarted() { this.m.IsSpent = false; }
});

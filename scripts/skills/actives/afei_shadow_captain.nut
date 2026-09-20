this.afei_shadow_captain <- this.inherit("scripts/skills/skill", {
	m = {},
	function create()
	{
		this.m.ID = "actives.afei_shadow_captain";
		this.m.Name = "幕后队长";
		this.m.Description = "消耗 1 次团队号令。指定四格内一名可行动友军，并自动再选最近的另一名四格内友军（若有）：其下一次武器技能疲劳成本减少 8。";
		this.m.Icon = "skills/active_119.png";
		this.m.IconDisabled = "skills/active_119_sw.png";
		this.m.Overlay = "active_119";
		this.m.Type = this.Const.SkillType.Active;
		this.m.Order = this.Const.SkillOrder.Any;
		this.m.IsSerialized = false;
		this.m.IsActive = true;
		this.m.IsTargeted = true;
		this.m.IsStacking = false;
		this.m.IsAttack = false;
		this.m.ActionPointCost = 4;
		this.m.FatigueCost = 15;
		this.m.MinRange = 0;
		this.m.MaxRange = 4;
	}

	function getTooltip()
	{
		local ret = this.skill.getDefaultUtilityTooltip();
		ret.push({
			id = 6,
			type = "text",
			icon = "ui/icons/special.png",
			text = "剩余团队号令：" + ::AfeiExpedition.OrderBudget + "（本轮已用则不可再施放）"
		});
		return ret;
	}

	function isUsable()
	{
		return this.skill.isUsable() && ::AfeiExpedition.canUseOrder();
	}

	function onVerifyTarget(_originTile, _targetTile)
	{
		if (!this.skill.onVerifyTarget(_originTile, _targetTile))
		{
			return false;
		}

		local target = _targetTile.getEntity();
		return target != null && target.isAlive() && !target.getCurrentProperties().IsStunned && target.isAlliedWith(this.getContainer().getActor());
	}

	function onUse(_user, _targetTile)
	{
		if (!::AfeiExpedition.consumeOrder())
		{
			return false;
		}

		local primary = _targetTile.getEntity();
		primary.getSkills().add(this.new("scripts/skills/effects/afei_shadow_captain_effect"));

		// 无双目标 UI：自动附加最近的另一名四格内可行动友军
		local myTile = _user.getTile();
		local best;
		local bestDist = 99;
		local actors = this.Tactical.Entities.getInstancesOfFaction(_user.getFaction());

		foreach (a in actors)
		{
			if (a.getID() == primary.getID() || !a.isAlive() || a.getCurrentProperties().IsStunned)
			{
				continue;
			}

			local d = a.getTile().getDistanceTo(myTile);

			if (d <= 4 && d < bestDist)
			{
				bestDist = d;
				best = a;
			}
		}

		if (best != null)
		{
			best.getSkills().add(this.new("scripts/skills/effects/afei_shadow_captain_effect"));
		}

		return true;
	}
});

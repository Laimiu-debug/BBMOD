this.afei_shadow_captain <- this.inherit("scripts/skills/skill", {
	m = {
		AwaitingSecond = false
	},
	function create()
	{
		this.m.ID = "actives.afei_shadow_captain";
		this.m.Name = "幕后队长";
		this.m.Description = "消耗 1 次团队号令。指定四格内可行动友军，其下一次武器技能疲劳 -8。可在同一轮内再点选第二名友军（不再耗号令）。若只点一人，也会自动尝试附加最近的另一名友军。";
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

	function onAfterUpdate(_properties)
	{
		if (this.m.AwaitingSecond)
		{
			this.m.ActionPointCost = 0;
			this.m.FatigueCost = 0;
		}
		else
		{
			this.m.ActionPointCost = 4;
			this.m.FatigueCost = 15;
		}
	}

	function getTooltip()
	{
		local ret = this.skill.getDefaultUtilityTooltip();
		ret.push({
			id = 6,
			type = "text",
			icon = "ui/icons/special.png",
			text = "剩余团队号令：" + ::AfeiExpedition.OrderBudget + (this.m.AwaitingSecond ? "（正在选第二目标）" : "（全队共享；每轮最多 1 次）")
		});
		return ret;
	}

	function isUsable()
	{
		if (!this.skill.isUsable())
		{
			return false;
		}

		if (this.m.AwaitingSecond)
		{
			return true;
		}

		return ::AfeiExpedition.canUseOrder();
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
		local primary = _targetTile.getEntity();

		if (this.m.AwaitingSecond)
		{
			primary.getSkills().add(this.new("scripts/skills/effects/afei_shadow_captain_effect"));
			this.m.AwaitingSecond = false;
			return true;
		}

		if (!::AfeiExpedition.consumeOrder())
		{
			return false;
		}

		primary.getSkills().add(this.new("scripts/skills/effects/afei_shadow_captain_effect"));
		this.m.AwaitingSecond = true;

		// 自动附加最近第二人（仍可再手动点选覆盖式追加）
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
			this.m.AwaitingSecond = false;
		}

		return true;
	}

	function onCombatStarted()
	{
		this.m.AwaitingSecond = false;
	}

	function onTurnEnd()
	{
		this.m.AwaitingSecond = false;
	}
});

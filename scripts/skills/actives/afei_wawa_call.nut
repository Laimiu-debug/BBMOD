this.afei_wawa_call <- this.inherit("scripts/skills/skill", {
	m = {},
	function create()
	{
		this.m.ID = "actives.afei_wawa_call";
		this.m.Name = "哇哇叫";
		this.m.Description = "消耗 1 次团队号令。自身与三格内可行动友军获得决心加成两轮。加成为 6＋向下取整（永久决心－20）÷5，最低 6、最高 20。";
		this.m.Icon = "skills/active_160.png";
		this.m.IconDisabled = "skills/active_160_sw.png";
		this.m.Overlay = "active_160";
		this.m.SoundOnUse = [
			this.Const.Sound.ActorEvent.Noise
		];
		this.m.Type = this.Const.SkillType.Active;
		this.m.Order = this.Const.SkillOrder.Any;
		this.m.IsSerialized = false;
		this.m.IsActive = true;
		this.m.IsTargeted = false;
		this.m.IsStacking = false;
		this.m.IsAttack = false;
		this.m.ActionPointCost = 4;
		this.m.FatigueCost = 16;
		this.m.MinRange = 0;
		this.m.MaxRange = 0;
	}

	function getTooltip()
	{
		local ret = this.skill.getDefaultUtilityTooltip();
		ret.push({
			id = 6,
			type = "text",
			icon = "ui/icons/special.png",
			text = "剩余团队号令：" + ::AfeiExpedition.OrderBudget + "（全队共享；每轮最多 1 次）"
		});
		return ret;
	}

	function isUsable()
	{
		return this.skill.isUsable() && ::AfeiExpedition.canUseOrder();
	}

	function onUse(_user, _targetTile)
	{
		if (!::AfeiExpedition.consumeOrder())
		{
			return false;
		}

		local bravery = _user.getBaseProperties().Bravery;
		local bonus = this.Math.max(6, this.Math.min(20, 6 + this.Math.floor((bravery - 20) / 5)));
		local myTile = _user.getTile();
		local actors = this.Tactical.Entities.getInstancesOfFaction(_user.getFaction());

		foreach (a in actors)
		{
			if (!a.isAlive() || a.getCurrentProperties().IsStunned)
			{
				continue;
			}

			if (a.getTile().getDistanceTo(myTile) <= 3)
			{
				local effect = this.new("scripts/skills/effects/afei_wawa_effect");
				effect.setBonus(bonus);
				a.getSkills().add(effect);
			}
		}

		return true;
	}
});

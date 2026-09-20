this.afei_ecig_puff <- this.inherit("scripts/skills/skill", {
	m = {
		IsSpent = false,
		HealAmount = 20
	},
	function create()
	{
		this.m.ID = "actives.afei_ecig_puff";
		this.m.Name = "抽一口";
		this.m.Description = "吸一口电子烟，恢复 20 点生命。不消耗物品。每回合一次；仅阿飞可用。";
		this.m.Icon = "skills/active_41.png";
		this.m.IconDisabled = "skills/active_41_sw.png";
		this.m.Overlay = "active_41";
		this.m.SoundOnUse = [
			"sounds/combat/drink_01.wav",
			"sounds/combat/drink_02.wav",
			"sounds/combat/drink_03.wav"
		];
		this.m.Type = this.Const.SkillType.Active;
		this.m.Order = this.Const.SkillOrder.Any;
		this.m.IsSerialized = false;
		this.m.IsActive = true;
		this.m.IsTargeted = false;
		this.m.IsStacking = false;
		this.m.IsAttack = false;
		this.m.ActionPointCost = 3;
		this.m.FatigueCost = 5;
	}

	function getTooltip()
	{
		local ret = this.skill.getDefaultUtilityTooltip();
		ret.push({
			id = 7,
			type = "text",
			icon = "ui/icons/health.png",
			text = "恢复 [color=" + this.Const.UI.Color.PositiveValue + "]" + this.m.HealAmount + "[/color] 生命"
		});
		ret.push({
			id = 8,
			type = "text",
			icon = "ui/icons/special.png",
			text = "不消耗电子烟；每回合限一次"
		});
		return ret;
	}

	function isUsable()
	{
		if (!this.skill.isUsable() || this.m.IsSpent)
		{
			return false;
		}

		local actor = this.getContainer().getActor();

		if (actor == null || actor.getFlags().get(::AfeiExpedition.Flags.CaptainAfei) != true)
		{
			return false;
		}

		return actor.getHitpoints() < actor.getHitpointsMax();
	}

	function onUse(_user, _targetTile)
	{
		this.m.IsSpent = true;
		local maxHp = _user.getHitpointsMax();
		local before = _user.getHitpoints();
		local after = this.Math.min(maxHp, before + this.m.HealAmount);
		_user.setHitpoints(after);

		if (after > before && this.Tactical.Entities != null)
		{
			this.Tactical.EventLog.log(this.Const.UI.getColorizedEntityName(_user) + " 抽了一口电子烟，恢复了 " + (after - before) + " 点生命");
		}

		return true;
	}

	function onTurnStart()
	{
		this.m.IsSpent = false;
	}

	function onCombatStarted()
	{
		this.m.IsSpent = false;
	}
});

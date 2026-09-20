this.afei_steady_hand <- this.inherit("scripts/skills/skill", {
	m = {
		CooldownUntil = 0
	},
	function create()
	{
		this.m.ID = "actives.afei_steady_hand";
		this.m.Name = "稳一手";
		this.m.Description = "消耗号令。自身与三格内最多四名（成长后五名）可行动友军近防 +6、决心 +6 两轮，并各获一次推拉免疫。";
		this.m.Icon = "skills/active_119.png";
		this.m.IconDisabled = "skills/active_119_sw.png";
		this.m.Type = this.Const.SkillType.Active;
		this.m.Order = this.Const.SkillOrder.Any;
		this.m.IsActive = true;
		this.m.IsTargeted = false;
		this.m.IsAttack = false;
		this.m.ActionPointCost = 4;
		this.m.FatigueCost = 18;
		this.m.MinRange = 0;
		this.m.MaxRange = 0;
	}
	function getMaxTargets()
	{
		local actor = this.getContainer().getActor();
		if (actor.getFlags().get("afei_steady_five") || this.World.Flags.get(::AfeiExpedition.Flags.GrowthDone + "C11"))
		{
			return 5;
		}
		return 4;
	}
	function isUsable()
	{
		if (!this.skill.isUsable())
		{
			return false;
		}
		if (::AfeiExpedition.getRound() < this.m.CooldownUntil)
		{
			return false;
		}
		return ::AfeiExpedition.canUseOrder();
	}
	function onUse(_user, _targetTile)
	{
		if (!::AfeiExpedition.consumeOrder())
		{
			return false;
		}
		local n = 0;
		local my = _user.getTile();
		local cap = this.getMaxTargets();
		foreach (a in this.Tactical.Entities.getInstancesOfFaction(_user.getFaction()))
		{
			if (!a.isAlive() || a.getTile().getDistanceTo(my) > 3)
			{
				continue;
			}
			local old = a.getSkills().getSkillByID("effects.afei_steady_hand");
			if (old != null)
			{
				old.removeSelf();
			}
			a.getSkills().add(this.new("scripts/skills/effects/afei_steady_hand_effect"));
			if (++n >= cap)
			{
				break;
			}
		}
		this.m.CooldownUntil = ::AfeiExpedition.getRound() + 2;
		return true;
	}
	function onCombatStarted()
	{
		this.m.CooldownUntil = 0;
	}
});

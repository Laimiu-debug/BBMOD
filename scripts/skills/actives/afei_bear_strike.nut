this.afei_bear_strike <- this.inherit("scripts/skills/skill", {
	m = {
		CooldownUntil = 0,
		Uses = 0
	},
	function create()
	{
		this.m.ID = "actives.afei_bear_strike";
		this.m.Name = "小熊出击";
		this.m.Description = "消耗 1 层看懂。对三格内敌人施加下一次武器攻击命中 -10（两轮或攻击后消耗）。每战最多 2 次（成长后 3 次）。";
		this.m.Icon = "skills/active_119.png";
		this.m.IconDisabled = "skills/active_119_sw.png";
		this.m.Type = this.Const.SkillType.Active;
		this.m.Order = this.Const.SkillOrder.Any;
		this.m.IsActive = true;
		this.m.IsTargeted = true;
		this.m.IsAttack = false;
		this.m.ActionPointCost = 3;
		this.m.FatigueCost = 12;
		this.m.MinRange = 1;
		this.m.MaxRange = 3;
	}
	function getMaxUses()
	{
		local actor = this.getContainer().getActor();
		if (actor.getFlags().get("afei_understand_3") || this.World.Flags.get(::AfeiExpedition.Flags.GrowthDone + "C18"))
		{
			return 3;
		}
		return 2;
	}
	function isUsable()
	{
		if (!this.skill.isUsable())
		{
			return false;
		}
		if (this.m.Uses >= this.getMaxUses())
		{
			return false;
		}
		if (::AfeiExpedition.getRound() < this.m.CooldownUntil)
		{
			return false;
		}
		local know = this.getContainer().getSkillByID("actives.afei_know_rules");
		return know != null && know.m.Stacks >= 1;
	}
	function onVerifyTarget(_originTile, _targetTile)
	{
		if (!this.skill.onVerifyTarget(_originTile, _targetTile))
		{
			return false;
		}
		local t = _targetTile.getEntity();
		return t != null && t.isAlive() && !t.isAlliedWith(this.getContainer().getActor());
	}
	function onUse(_user, _targetTile)
	{
		local know = _user.getSkills().getSkillByID("actives.afei_know_rules");
		if (know == null || know.consumeStacks(1) < 1)
		{
			return false;
		}
		local target = _targetTile.getEntity();
		target.getSkills().add(this.new("scripts/skills/effects/afei_bear_mark_effect"));
		this.m.Uses += 1;
		this.m.CooldownUntil = ::AfeiExpedition.getRound() + 2;
		_user.getFlags().set("afei_bear_used", true);
		return true;
	}
	function onCombatStarted()
	{
		this.m.CooldownUntil = 0;
		this.m.Uses = 0;
	}
});

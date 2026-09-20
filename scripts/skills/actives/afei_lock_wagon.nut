this.afei_lock_wagon <- this.inherit("scripts/skills/skill", {
	m = {
		CooldownUntil = 0,
		Uses = 0
	},
	function create()
	{
		this.m.ID = "actives.afei_lock_wagon";
		this.m.Name = "锁车";
		this.m.Description = "对邻接敌人布置绳扣：打断其移动一轮（仍可原地攻击）。每战第一次布置在成长后免 2 工具，否则耗 2 工具；第二次仍耗工具。";
		this.m.Icon = "skills/active_119.png";
		this.m.IconDisabled = "skills/active_119_sw.png";
		this.m.Type = this.Const.SkillType.Active;
		this.m.Order = this.Const.SkillOrder.Any;
		this.m.IsActive = true;
		this.m.IsTargeted = true;
		this.m.IsAttack = false;
		this.m.ActionPointCost = 3;
		this.m.FatigueCost = 10;
		this.m.MinRange = 1;
		this.m.MaxRange = 1;
	}
	function isUsable()
	{
		if (!this.skill.isUsable())
		{
			return false;
		}
		return ::AfeiExpedition.getRound() >= this.m.CooldownUntil;
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
	function needsTools()
	{
		local actor = this.getContainer().getActor();
		local freeFirst = actor.getFlags().get("afei_lock_first_free") || this.World.Flags.get(::AfeiExpedition.Flags.GrowthDone + "C14");
		if (freeFirst && this.m.Uses == 0)
		{
			return false;
		}
		return true;
	}
	function onUse(_user, _targetTile)
	{
		if (this.needsTools())
		{
			if (!::AfeiExpedition.trySpendToolsApprox(2))
			{
				return false;
			}
		}
		local target = _targetTile.getEntity();
		local old = target.getSkills().getSkillByID("effects.afei_lock_wagon");
		if (old != null)
		{
			old.removeSelf();
		}
		target.getSkills().add(this.new("scripts/skills/effects/afei_lock_wagon_effect"));
		this.m.Uses += 1;
		this.m.CooldownUntil = ::AfeiExpedition.getRound() + 1;
		return true;
	}
	function onCombatStarted()
	{
		this.m.CooldownUntil = 0;
		this.m.Uses = 0;
	}
});

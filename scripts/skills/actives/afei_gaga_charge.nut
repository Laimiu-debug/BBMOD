this.afei_gaga_charge <- this.inherit("scripts/skills/skill", {
	m = {
		CooldownUntil = 0
	},
	function create()
	{
		this.m.ID = "actives.afei_gaga_charge";
		this.m.Name = "嘎嘎冲";
		this.m.Description = "推进预备：下一次单手近战护甲伤害 +10%，命中 -5（成长后不降命中）。完整「先走一格再推」受引擎限制，本版做攻击预备近似。";
		this.m.Icon = "skills/active_119.png";
		this.m.IconDisabled = "skills/active_119_sw.png";
		this.m.Type = this.Const.SkillType.Active;
		this.m.Order = this.Const.SkillOrder.Any;
		this.m.IsActive = true;
		this.m.IsTargeted = false;
		this.m.IsAttack = false;
		this.m.ActionPointCost = 6;
		this.m.FatigueCost = 22;
		this.m.MinRange = 0;
		this.m.MaxRange = 0;
	}
	function isUsable()
	{
		if (!this.skill.isUsable())
		{
			return false;
		}
		return ::AfeiExpedition.getRound() >= this.m.CooldownUntil;
	}
	function onUse(_user, _targetTile)
	{
		local old = _user.getSkills().getSkillByID("effects.afei_gaga_ready");
		if (old != null)
		{
			old.removeSelf();
		}
		_user.getSkills().add(this.new("scripts/skills/effects/afei_gaga_ready_effect"));
		this.m.CooldownUntil = ::AfeiExpedition.getRound() + 3;
		return true;
	}
	function onCombatStarted()
	{
		this.m.CooldownUntil = 0;
	}
});

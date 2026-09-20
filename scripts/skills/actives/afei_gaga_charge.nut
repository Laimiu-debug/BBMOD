this.afei_gaga_charge <- this.inherit("scripts/skills/skill", {
	m = {
		CooldownUntil = 0
	},
	function create()
	{
		this.m.ID = "actives.afei_gaga_charge";
		this.m.Name = "嘎嘎冲";
		this.m.Description = "先尽量迈向目标邻格，再对邻接敌人作一次近战打击：护甲伤害 +10%，命中 -5（成长后不降命中）；命中后尝试沿远离自身方向推一格（同高空格、非免疫）。";
		this.m.Icon = "skills/active_119.png";
		this.m.IconDisabled = "skills/active_119_sw.png";
		this.m.Type = this.Const.SkillType.Active;
		this.m.Order = this.Const.SkillOrder.OffensiveTargeted;
		this.m.IsActive = true;
		this.m.IsTargeted = true;
		this.m.IsAttack = true;
		this.m.IsWeaponSkill = true;
		this.m.ActionPointCost = 6;
		this.m.FatigueCost = 22;
		this.m.MinRange = 1;
		this.m.MaxRange = 2;
	}
	function isUsable()
	{
		if (!this.skill.isUsable()) return false;
		return ::AfeiExpedition.getRound() >= this.m.CooldownUntil;
	}
	function onVerifyTarget(_originTile, _targetTile)
	{
		if (!this.skill.onVerifyTarget(_originTile, _targetTile)) return false;
		local t = _targetTile.getEntity();
		return t != null && t.isAlive() && !t.isAlliedWith(this.getContainer().getActor());
	}
	function onAnySkillUsed(_skill, _targetEntity, _properties)
	{
		if (_skill != this) return;
		local actor = this.getContainer().getActor();
		if (!actor.getFlags().get("afei_gaga_no_hit_pen") && !this.World.Flags.get(::AfeiExpedition.Flags.GrowthDone + "C13"))
		{
			_properties.MeleeSkill -= 5;
			::AfeiExpedition.noteOriginHit(actor, -5, 0);
		}
		_properties.DamageArmorMult *= 1.1;
	}
	function onUse(_user, _targetTile)
	{
		local target = _targetTile.getEntity();
		if (target == null) return false;
		::AfeiExpedition.tryStepAdjacentTo(_user, _targetTile);
		if (_user.getTile().getDistanceTo(_targetTile) > 1)
		{
			return false;
		}
		local tag = {
			User = _user,
			Target = target
		};
		this.attackEntity(_user, target);
		if (target != null && target.isAlive())
		{
			::AfeiExpedition.tryKnockBackAway(_user, target);
		}
		_user.getFlags().set("afei_gaga_used", true);
		this.m.CooldownUntil = ::AfeiExpedition.getRound() + 3;
		return true;
	}
	function onCombatStarted()
	{
		this.m.CooldownUntil = 0;
	}
});

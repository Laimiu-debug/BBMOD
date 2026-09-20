this.afei_foot_point <- this.inherit("scripts/skills/skill", {
	m = { CooldownUntil = 0, IsSpent = false },
	function create()
	{
		this.m.ID = "actives.afei_foot_point";
		this.m.Name = "踩点";
		this.m.Description = "获得先攻+10 一轮。";
		this.m.Icon = "skills/active_119.png";
		this.m.IconDisabled = "skills/active_119_sw.png";
		this.m.Type = this.Const.SkillType.Active;
		this.m.Order = this.Const.SkillOrder.Any;
		this.m.IsActive = true;
		this.m.IsTargeted = false;
		this.m.IsAttack = false;
		this.m.ActionPointCost = 2;
		this.m.FatigueCost = 8;
		this.m.MinRange = 0;
		this.m.MaxRange = 0;
	}
	function isUsable()
	{
		if (!this.skill.isUsable()) return false;
		if (this.m.IsSpent) return false;
		if (::AfeiExpedition.getRound() < this.m.CooldownUntil) return false;
		
		return true;
	}
	function onVerifyTarget(_originTile, _targetTile)
	{
		if (!this.m.IsTargeted) return true;
		if (!this.skill.onVerifyTarget(_originTile, _targetTile)) return false;
		local t = _targetTile.getEntity();
		return t != null && t.isAlive() && t.isAlliedWith(this.getContainer().getActor()) == true;
	}
	function onUse(_user, _targetTile)
	{
		
		_user.getSkills().add(this.new("scripts/skills/effects/afei_prince_order_effect"));
		this.m.CooldownUntil = ::AfeiExpedition.getRound() + 2;
		return true;
	}
	function onCombatStarted() { this.m.CooldownUntil = 0; this.m.IsSpent = false; }
});

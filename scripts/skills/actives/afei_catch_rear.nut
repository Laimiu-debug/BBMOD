this.afei_catch_rear <- this.inherit("scripts/skills/skill", {
	m = { CooldownUntil = 0, IsSpent = false },
	function create()
	{
		this.m.ID = "actives.afei_catch_rear";
		this.m.Name = "接住后排";
		this.m.Description = "指定相邻友军获得撤步标记（近防+6 一轮）。";
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
		this.m.MaxRange = 1;
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
		
		local t=_targetTile.getEntity(); t.getSkills().add(this.new("scripts/skills/effects/afei_cover_up_effect"));
		this.m.CooldownUntil = ::AfeiExpedition.getRound() + 2;
		return true;
	}
	function onCombatStarted() { this.m.CooldownUntil = 0; this.m.IsSpent = false; }
});

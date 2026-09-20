this.afei_bear_strike <- this.inherit("scripts/skills/skill", {
	m = { CooldownUntil = 0, IsSpent = false },
	function create()
	{
		this.m.ID = "actives.afei_bear_strike";
		this.m.Name = "小熊出击";
		this.m.Description = "干扰：目标近攻-6 一轮。";
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
		return t != null && t.isAlive() && t.isAlliedWith(this.getContainer().getActor()) == false;
	}
	function onUse(_user, _targetTile)
	{
		
		_targetTile.getEntity().getSkills().add(this.new("scripts/skills/effects/afei_dog_bark_effect"));
		this.m.CooldownUntil = ::AfeiExpedition.getRound() + 2;
		return true;
	}
	function onCombatStarted() { this.m.CooldownUntil = 0; this.m.IsSpent = false; }
});

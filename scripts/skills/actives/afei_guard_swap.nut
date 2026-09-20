this.afei_guard_swap <- this.inherit("scripts/skills/skill", {
	m = { IsSpent = false },
	function create()
	{
		this.m.ID = "actives.afei_guard_swap";
		this.m.Name = "护团换位";
		this.m.Description = "每战一次。与相邻己方交换位置，双方免除此次脱离攻击（近似：直接传送换位）。";
		this.m.Icon = "skills/active_43.png";
		this.m.IconDisabled = "skills/active_43_sw.png";
		this.m.Type = this.Const.SkillType.Active;
		this.m.Order = this.Const.SkillOrder.UtilityTargeted;
		this.m.IsActive = true;
		this.m.IsTargeted = true;
		this.m.ActionPointCost = 3;
		this.m.FatigueCost = 15;
		this.m.MinRange = 1;
		this.m.MaxRange = 1;
	}
	function isUsable() { return this.skill.isUsable() && !this.m.IsSpent; }
	function onVerifyTarget(_originTile, _targetTile)
	{
		if (!this.skill.onVerifyTarget(_originTile, _targetTile)) { return false; }
		local t = _targetTile.getEntity();
		return t != null && t.isAlive() && t.isAlliedWith(this.getContainer().getActor());
	}
	function onUse(_user, _targetTile)
	{
		local target = _targetTile.getEntity();
		local userTile = _user.getTile();
		this.m.IsSpent = true;
		this.Tactical.getNavigator().teleport(_user, _targetTile, null, null, false);
		this.Tactical.getNavigator().teleport(target, userTile, null, null, false);
		return true;
	}
	function onCombatStarted() { this.m.IsSpent = false; }
});

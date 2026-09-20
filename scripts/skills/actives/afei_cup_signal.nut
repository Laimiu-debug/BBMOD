this.afei_cup_signal <- this.inherit("scripts/skills/skill", {
	m = { CooldownUntil = 0, IsSpent = false },
	function create()
	{
		this.m.ID = "actives.afei_cup_signal";
		this.m.Name = "敲杯为号";
		this.m.Description = "消耗号令。三格内友军决心+8 两轮。";
		this.m.Icon = "skills/active_119.png";
		this.m.IconDisabled = "skills/active_119_sw.png";
		this.m.Type = this.Const.SkillType.Active;
		this.m.Order = this.Const.SkillOrder.Any;
		this.m.IsActive = true;
		this.m.IsTargeted = false;
		this.m.IsAttack = false;
		this.m.ActionPointCost = 4;
		this.m.FatigueCost = 15;
		this.m.MinRange = 0;
		this.m.MaxRange = 0;
	}
	function isUsable()
	{
		if (!this.skill.isUsable()) return false;
		if (this.m.IsSpent) return false;
		if (::AfeiExpedition.getRound() < this.m.CooldownUntil) return false;
		if (!::AfeiExpedition.canUseOrder()) return false;
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
		
		if (!::AfeiExpedition.consumeOrder()) return false;
		local my=_user.getTile();
		foreach(a in this.Tactical.Entities.getInstancesOfFaction(_user.getFaction())){
			if(a.isAlive() && a.getTile().getDistanceTo(my)<=3){
				local e=this.new("scripts/skills/effects/afei_wawa_effect"); e.setBonus(8); a.getSkills().add(e);
			}
		}
		this.m.CooldownUntil = ::AfeiExpedition.getRound() + 2;
		return true;
	}
	function onCombatStarted() { this.m.CooldownUntil = 0; this.m.IsSpent = false; }
});

this.afei_full_circle <- this.inherit("scripts/skills/skill", {
	m = { CooldownUntil = 0, IsSpent = false },
	function create()
	{
		this.m.ID = "actives.afei_full_circle";
		this.m.Name = "全力圈";
		this.m.Description = "觉醒号令：恢复疲劳并决心+20（需觉醒flag）。";
		this.m.Icon = "skills/active_119.png";
		this.m.IconDisabled = "skills/active_119_sw.png";
		this.m.Type = this.Const.SkillType.Active;
		this.m.Order = this.Const.SkillOrder.Any;
		this.m.IsActive = true;
		this.m.IsTargeted = false;
		this.m.IsAttack = false;
		this.m.ActionPointCost = 4;
		this.m.FatigueCost = 30;
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
		if (!this.World.Flags.get(::AfeiExpedition.Flags.AfeiAwakened)) return false;
		this.m.IsSpent=true;
		local my=_user.getTile();
		foreach(a in this.Tactical.Entities.getInstancesOfFaction(_user.getFaction())){
			if(!a.isAlive()||a.getTile().getDistanceTo(my)>4) continue;
			local rec=::AfeiExpedition.consumeFatigueRecoverBudget(20);
			a.setFatigue(this.Math.max(0,a.getFatigue()-rec));
			local e=this.new("scripts/skills/effects/afei_wawa_effect"); e.setBonus(20); a.getSkills().add(e);
		}
		this.m.IsSpent = true;
		this.m.CooldownUntil = ::AfeiExpedition.getRound() + 1;
		return true;
	}
	function onCombatStarted() { this.m.CooldownUntil = 0; this.m.IsSpent = false; }
});

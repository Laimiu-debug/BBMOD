this.afei_prince_order <- this.inherit("scripts/skills/skill", {
	m = {},
	function create()
	{
		this.m.ID = "actives.afei_prince_order";
		this.m.Name = "太子发令";
		this.m.Description = "消耗 1 次团队号令。仅当自己是代理且阿飞未出战/不能行动时可用。自身与三格内友军决心 +10、近防 +5 两轮。";
		this.m.Icon = "skills/active_160.png";
		this.m.IconDisabled = "skills/active_160_sw.png";
		this.m.Type = this.Const.SkillType.Active;
		this.m.IsActive = true;
		this.m.IsTargeted = false;
		this.m.ActionPointCost = 4;
		this.m.FatigueCost = 15;
	}
	function afeiUnavailable()
	{
		local actors = this.Tactical.Entities.getInstancesOfFaction(this.getContainer().getActor().getFaction());
		foreach (a in actors)
		{
			if (a.getFlags().get(::AfeiExpedition.Flags.CaptainAfei))
			{
				return !a.isAlive() || a.getCurrentProperties().IsStunned || !a.isPlacedOnMap();
			}
		}
		return true;
	}
	function isUsable()
	{
		if (!this.skill.isUsable() || !::AfeiExpedition.canUseOrder()) { return false; }
		if (!this.getContainer().getActor().getFlags().get(::AfeiExpedition.Flags.ProxyCaptain)) { return false; }
		return this.afeiUnavailable();
	}
	function onUse(_user, _targetTile)
	{
		if (!::AfeiExpedition.consumeOrder()) { return false; }
		local myTile = _user.getTile();
		local actors = this.Tactical.Entities.getInstancesOfFaction(_user.getFaction());
		foreach (a in actors)
		{
			if (!a.isAlive()) { continue; }
			if (a.getTile().getDistanceTo(myTile) <= 3)
			{
				a.getSkills().add(this.new("scripts/skills/effects/afei_prince_order_effect"));
			}
		}
		return true;
	}
});

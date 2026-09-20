this.afei_drum <- this.inherit("scripts/skills/skill", {
	m = {},
	function create()
	{
		this.m.ID = "actives.afei_drum";
		this.m.Name = "打鼓";
		this.m.Description = "消耗 1 次团队号令。自身与三格内友军获得定拍：下次行动开始额外恢复 8 疲劳，并决心 +5 至该次行动结束。";
		this.m.Icon = "skills/active_160.png";
		this.m.IconDisabled = "skills/active_160_sw.png";
		this.m.Type = this.Const.SkillType.Active;
		this.m.IsActive = true;
		this.m.IsTargeted = false;
		this.m.ActionPointCost = 4;
		this.m.FatigueCost = 16;
	}
	function isUsable() { return this.skill.isUsable() && ::AfeiExpedition.canUseOrder(); }
	function onUse(_user, _targetTile)
	{
		if (!::AfeiExpedition.consumeOrder()) { return false; }
		local myTile = _user.getTile();
		local actors = this.Tactical.Entities.getInstancesOfFaction(_user.getFaction());
		foreach (a in actors)
		{
			if (!a.isAlive() || a.getCurrentProperties().IsStunned) { continue; }
			if (a.getTile().getDistanceTo(myTile) <= 3)
			{
				a.getSkills().add(this.new("scripts/skills/effects/afei_drum_effect"));
			}
		}
		return true;
	}
});

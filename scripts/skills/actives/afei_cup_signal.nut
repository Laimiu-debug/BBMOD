this.afei_cup_signal <- this.inherit("scripts/skills/skill", {
	m = {
		CooldownUntil = 0
	},
	function create()
	{
		this.m.ID = "actives.afei_cup_signal";
		this.m.Name = "敲杯为号";
		this.m.Description = "消耗号令。指定三格内最多三名友军：下一次武器技能疲劳减少 4+2×消耗的看懂层（0–2 层）。同时给予决心 +6 两轮。";
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
		if (!this.skill.isUsable())
		{
			return false;
		}
		if (::AfeiExpedition.getRound() < this.m.CooldownUntil)
		{
			return false;
		}
		return ::AfeiExpedition.canUseOrder();
	}
	function onUse(_user, _targetTile)
	{
		if (!::AfeiExpedition.consumeOrder())
		{
			return false;
		}
		local know = _user.getSkills().getSkillByID("actives.afei_know_rules");
		local layers = 0;
		if (know != null)
		{
			layers = know.consumeStacks(2);
		}
		local fatCut = 4 + 2 * layers;
		local my = _user.getTile();
		local n = 0;
		foreach (a in this.Tactical.Entities.getInstancesOfFaction(_user.getFaction()))
		{
			if (!a.isAlive() || a.getTile().getDistanceTo(my) > 3)
			{
				continue;
			}
			local e = this.new("scripts/skills/effects/afei_wawa_effect");
			e.setBonus(6);
			a.getSkills().add(e);
			a.getFlags().set("afei_cup_fat_cut", fatCut);
			if (++n >= 3)
			{
				break;
			}
		}
		_user.getFlags().set("afei_cup_used", true);
		this.m.CooldownUntil = ::AfeiExpedition.getRound() + 2;
		return true;
	}
	function onCombatStarted()
	{
		this.m.CooldownUntil = 0;
	}
});

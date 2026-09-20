this.afei_long_watch <- this.inherit("scripts/skills/skill", {
	m = {
		CooldownUntil = 0
	},
	function create()
	{
		this.m.ID = "actives.afei_long_watch";
		this.m.Name = "长轮守门";
		this.m.Description = "至下次自身行动开始：近防/远防各 +8、先攻 -10；期间每轮首次被单体命中后恢复 4 疲劳（成长后 7），计入起源恢复上限。";
		this.m.Icon = "skills/active_119.png";
		this.m.IconDisabled = "skills/active_119_sw.png";
		this.m.Type = this.Const.SkillType.Active;
		this.m.Order = this.Const.SkillOrder.Any;
		this.m.IsActive = true;
		this.m.IsTargeted = false;
		this.m.IsAttack = false;
		this.m.ActionPointCost = 4;
		this.m.FatigueCost = 18;
		this.m.MinRange = 0;
		this.m.MaxRange = 0;
	}
	function isUsable()
	{
		if (!this.skill.isUsable())
		{
			return false;
		}
		return ::AfeiExpedition.getRound() >= this.m.CooldownUntil;
	}
	function onUse(_user, _targetTile)
	{
		local old = _user.getSkills().getSkillByID("effects.afei_long_watch");
		if (old != null)
		{
			old.removeSelf();
		}
		_user.getSkills().add(this.new("scripts/skills/effects/afei_long_watch_effect"));
		this.m.CooldownUntil = ::AfeiExpedition.getRound() + 2;
		return true;
	}
	function onCombatStarted()
	{
		this.m.CooldownUntil = 0;
	}
});

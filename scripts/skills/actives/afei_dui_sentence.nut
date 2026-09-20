this.afei_dui_sentence <- this.inherit("scripts/skills/skill", {
	m = { CooldownUntil = 0 },
	function create()
	{
		this.m.ID = "actives.afei_dui_sentence";
		this.m.Name = "怼一句";
		this.m.Description = "把自身仍有效的哇哇叫或太子发令决心/近防加成转述给三格内一名尚未拥有该效果的友军。冷却两轮。不耗号令。";
		this.m.Icon = "skills/active_119.png";
		this.m.IconDisabled = "skills/active_119_sw.png";
		this.m.Type = this.Const.SkillType.Active;
		this.m.Order = this.Const.SkillOrder.UtilityTargeted;
		this.m.IsActive = true;
		this.m.IsTargeted = true;
		this.m.ActionPointCost = 3;
		this.m.FatigueCost = 10;
		this.m.MinRange = 1;
		this.m.MaxRange = 3;
	}
	function isUsable() { return this.skill.isUsable() && ::AfeiExpedition.getRound() >= this.m.CooldownUntil; }
	function onVerifyTarget(_originTile, _targetTile)
	{
		if (!this.skill.onVerifyTarget(_originTile, _targetTile)) { return false; }
		local t = _targetTile.getEntity();
		return t != null && t.isAlive() && t.isAlliedWith(this.getContainer().getActor());
	}
	function onUse(_user, _targetTile)
	{
		local target = _targetTile.getEntity();
		local skills = _user.getSkills();
		local wawa = skills.getSkillByID("effects.afei_wawa");
		local prince = skills.getSkillByID("effects.afei_prince_order");
		if (wawa != null && !target.getSkills().hasSkill("effects.afei_wawa"))
		{
			local e = this.new("scripts/skills/effects/afei_wawa_effect");
			if ("m" in wawa && "Bonus" in wawa.m) { e.setBonus(wawa.m.Bonus); }
			target.getSkills().add(e);
		}
		if (prince != null && !target.getSkills().hasSkill("effects.afei_prince_order"))
		{
			target.getSkills().add(this.new("scripts/skills/effects/afei_prince_order_effect"));
		}
		local fear = skills.getSkillByID("actives.afei_fear_afei");
		if (fear != null) { fear.clearPenalty(); }
		this.m.CooldownUntil = ::AfeiExpedition.getRound() + 2;
		return true;
	}
	function onCombatStarted() { this.m.CooldownUntil = 0; }
});

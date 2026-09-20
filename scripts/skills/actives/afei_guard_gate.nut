this.afei_guard_gate <- this.inherit("scripts/skills/skill", {
	m = { CooldownUntil = 0 },
	function create()
	{
		this.m.ID = "actives.afei_guard_gate";
		this.m.Name = "守门";
		this.m.Description = "须持盾。至下次行动不能移动（近似：获得守势近防 +8，首次脱离攻击命中 +10）。冷却两轮。";
		this.m.Icon = "skills/active_32.png";
		this.m.IconDisabled = "skills/active_32_sw.png";
		this.m.Type = this.Const.SkillType.Active;
		this.m.IsActive = true;
		this.m.IsTargeted = false;
		this.m.ActionPointCost = 3;
		this.m.FatigueCost = 12;
	}
	function isUsable()
	{
		if (!this.skill.isUsable() || ::AfeiExpedition.getRound() < this.m.CooldownUntil) { return false; }
		local off = this.getContainer().getActor().getItems().getItemAtSlot(this.Const.ItemSlot.Offhand);
		return off != null && off.isItemType(this.Const.Items.ItemType.Shield);
	}
	function onUse(_user, _targetTile)
	{
		_user.getSkills().add(this.new("scripts/skills/effects/afei_guard_gate_effect"));
		this.m.CooldownUntil = ::AfeiExpedition.getRound() + 2;
		return true;
	}
	function onCombatStarted() { this.m.CooldownUntil = 0; }
});

this.afei_cover_up <- this.inherit("scripts/skills/skill", {
	m = { CooldownUntil = 0 },
	function create()
	{
		this.m.ID = "actives.afei_cover_up";
		this.m.Name = "顶上去";
		this.m.Description = "持盾指定相邻伙伴。期间敌人单体近战优先点名你；若仍点到被守护者，则改打你并减免生命伤害。冷却三轮。";
		this.m.Icon = "skills/active_32.png";
		this.m.IconDisabled = "skills/active_32_sw.png";
		this.m.Type = this.Const.SkillType.Active;
		this.m.Order = this.Const.SkillOrder.UtilityTargeted;
		this.m.IsActive = true;
		this.m.IsTargeted = true;
		this.m.ActionPointCost = 4;
		this.m.FatigueCost = 20;
		this.m.MinRange = 1;
		this.m.MaxRange = 1;
	}
	function isUsable()
	{
		if (!this.skill.isUsable() || ::AfeiExpedition.getRound() < this.m.CooldownUntil) { return false; }
		local off = this.getContainer().getActor().getItems().getItemAtSlot(this.Const.ItemSlot.Offhand);
		return off != null && off.isItemType(this.Const.Items.ItemType.Shield);
	}
	function onVerifyTarget(_originTile, _targetTile)
	{
		if (!this.skill.onVerifyTarget(_originTile, _targetTile)) { return false; }
		local t = _targetTile.getEntity();
		return t != null && t.isAlive() && t.isAlliedWith(this.getContainer().getActor());
	}
	function onUse(_user, _targetTile)
	{
		local target = _targetTile.getEntity();
		local effect = this.new("scripts/skills/effects/afei_cover_up_effect");
		effect.setProtector(_user.getID());
		target.getSkills().add(effect);
		local covering = this.new("scripts/skills/effects/afei_covering_effect");
		covering.setProtected(target.getID());
		_user.getSkills().add(covering);
		_user.getFlags().set("afei_covering_id", target.getID());
		this.m.CooldownUntil = ::AfeiExpedition.getRound() + 3;
		return true;
	}
	function onCombatStarted() { this.m.CooldownUntil = 0; }
});

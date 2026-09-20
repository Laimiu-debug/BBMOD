this.afei_dog_bark <- this.inherit("scripts/skills/skill", {
	m = { CooldownUntil = 0 },
	function create()
	{
		this.m.ID = "actives.afei_dog_bark";
		this.m.Name = "狗叫";
		this.m.Description = "对三格内可见敌人施加近攻 -8，至其下一次行动结束。冷却两轮。亡灵/野兽可能无效（阶段近似：对所有敌人生效）。";
		this.m.Icon = "skills/active_41.png";
		this.m.IconDisabled = "skills/active_41_sw.png";
		this.m.Type = this.Const.SkillType.Active;
		this.m.Order = this.Const.SkillOrder.UtilityTargeted;
		this.m.IsActive = true;
		this.m.IsTargeted = true;
		this.m.ActionPointCost = 3;
		this.m.FatigueCost = 12;
		this.m.MinRange = 1;
		this.m.MaxRange = 3;
	}
	function isUsable() { return this.skill.isUsable() && ::AfeiExpedition.getRound() >= this.m.CooldownUntil; }
	function onVerifyTarget(_originTile, _targetTile)
	{
		if (!this.skill.onVerifyTarget(_originTile, _targetTile)) { return false; }
		local t = _targetTile.getEntity();
		return t != null && t.isAlive() && !t.isAlliedWith(this.getContainer().getActor());
	}
	function onUse(_user, _targetTile)
	{
		_targetTile.getEntity().getSkills().add(this.new("scripts/skills/effects/afei_dog_bark_effect"));
		this.m.CooldownUntil = ::AfeiExpedition.getRound() + 2;
		return true;
	}
	function onCombatStarted() { this.m.CooldownUntil = 0; }
});

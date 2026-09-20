this.afei_borrow_strike <- this.inherit("scripts/skills/skill", {
	m = {},
	function create()
	{
		this.m.ID = "actives.afei_borrow_strike";
		this.m.Name = "大哥借我";
		this.m.Description = "向三格内一名永久近攻高于自己的友军借招。接下来两次单体近战武器攻击命中增加双方永久近攻差（最多 +10）。不消耗团队号令。";
		this.m.Icon = "skills/active_06.png";
		this.m.IconDisabled = "skills/active_06_sw.png";
		this.m.Overlay = "active_06";
		this.m.Type = this.Const.SkillType.Active;
		this.m.Order = this.Const.SkillOrder.Any;
		this.m.IsSerialized = false;
		this.m.IsActive = true;
		this.m.IsTargeted = true;
		this.m.IsStacking = false;
		this.m.IsAttack = false;
		this.m.ActionPointCost = 2;
		this.m.FatigueCost = 8;
		this.m.MinRange = 1;
		this.m.MaxRange = 3;
	}

	function onVerifyTarget(_originTile, _targetTile)
	{
		if (!this.skill.onVerifyTarget(_originTile, _targetTile))
		{
			return false;
		}

		local user = this.getContainer().getActor();
		local target = _targetTile.getEntity();

		if (target == null || !target.isAlive() || !target.isAlliedWith(user))
		{
			return false;
		}

		return target.getBaseProperties().MeleeSkill > user.getBaseProperties().MeleeSkill;
	}

	function onUse(_user, _targetTile)
	{
		local target = _targetTile.getEntity();
		local diff = this.Math.min(10, target.getBaseProperties().MeleeSkill - _user.getBaseProperties().MeleeSkill);
		local effect = this.new("scripts/skills/effects/afei_borrow_strike_effect");
		effect.setBonus(diff);
		_user.getSkills().add(effect);
		return true;
	}
});

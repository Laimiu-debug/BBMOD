this.afei_shadow_captain <- this.inherit("scripts/skills/skill", {
	m = {},
	function create()
	{
		this.m.ID = "actives.afei_shadow_captain";
		this.m.Name = "幕后队长";
		this.m.Description = "消耗 1 次团队号令。指定四格内最多两名可行动友军，其下一次武器技能疲劳成本减少 8。";
		this.m.Icon = "skills/active_119.png";
		this.m.IconDisabled = "skills/active_119_sw.png";
		this.m.Overlay = "active_119";
		this.m.Type = this.Const.SkillType.Active;
		this.m.Order = this.Const.SkillOrder.Any;
		this.m.IsSerialized = false;
		this.m.IsActive = true;
		this.m.IsTargeted = true;
		this.m.IsStacking = false;
		this.m.IsAttack = false;
		this.m.ActionPointCost = 4;
		this.m.FatigueCost = 15;
		this.m.MinRange = 0;
		this.m.MaxRange = 4;
	}

	function isUsable()
	{
		return this.skill.isUsable() && ::AfeiExpedition.canUseOrder();
	}

	function onVerifyTarget(_originTile, _targetTile)
	{
		if (!this.skill.onVerifyTarget(_originTile, _targetTile))
		{
			return false;
		}

		local target = _targetTile.getEntity();
		return target != null && target.isAlive() && target.isAlliedWith(this.getContainer().getActor());
	}

	function onUse(_user, _targetTile)
	{
		if (!::AfeiExpedition.consumeOrder())
		{
			return false;
		}

		local target = _targetTile.getEntity();
		target.getSkills().add(this.new("scripts/skills/effects/afei_shadow_captain_effect"));
		// TODO stage-1: only tags primary target; second ally selection needs dual-target UI.
		return true;
	}
});

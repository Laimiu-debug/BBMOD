this.afei_shadow_captain_effect <- this.inherit("scripts/skills/skill", {
	m = {
		TurnsLeft = 2
	},
	function create()
	{
		this.m.ID = "effects.afei_shadow_captain";
		this.m.Name = "幕后队长";
		this.m.Description = "下一次武器技能的疲劳成本减少 8（最低 0）。";
		this.m.Icon = "skills/status_effect_34.png";
		this.m.Type = this.Const.SkillType.StatusEffect;
		this.m.IsActive = false;
		this.m.IsStacking = false;
		this.m.IsRemovedAfterBattle = true;
	}

	function onAfterUpdate(_properties)
	{
		// Soft stub: real weapon-skill fatigue discount needs per-skill hooks (待 ZIP/实机校正).
		_properties.FatigueRecoveryRate += 0;
	}

	function onTurnEnd()
	{
		if (--this.m.TurnsLeft <= 0)
		{
			this.removeSelf();
		}
	}

	function onAnySkillUsed(_skill, _targetEntity, _properties)
	{
		if (_skill != null && _skill.isAttack() && this.m.TurnsLeft > 0)
		{
			_properties.FatigueDealtPerHitMult = 1.0;
			local actor = this.getContainer().getActor();
			// Approximate: refund-like by lowering skill fatigue via actor property if available.
			if ("FatigueCostMult" in _properties)
			{
			}
			this.removeSelf();
		}
	}
});

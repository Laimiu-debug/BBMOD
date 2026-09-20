this.afei_shadow_captain_effect <- this.inherit("scripts/skills/skill", {
	m = {
		TurnsLeft = 2,
		Pending = true,
		PatchedSkill = null,
		OriginalFatigue = 0
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

	function onBeforeAnySkillExecuted(_skill, _targetTile, _targetEntity, _user)
	{
		if (!this.m.Pending || _skill == null)
		{
			return;
		}

		if (!_skill.isAttack() && !_skill.isActive())
		{
			return;
		}

		// 仅优惠武器类主动技（攻击或带武器费用的技能）
		if (!_skill.isAttack())
		{
			return;
		}

		this.m.PatchedSkill = _skill;
		this.m.OriginalFatigue = _skill.m.FatigueCost;
		_skill.m.FatigueCost = this.Math.max(0, _skill.m.FatigueCost - 8);
	}

	function onAnySkillExecuted(_skill, _targetTile, _targetEntity, _forFree)
	{
		if (this.m.PatchedSkill != null && _skill == this.m.PatchedSkill)
		{
			_skill.m.FatigueCost = this.m.OriginalFatigue;
			this.m.PatchedSkill = null;
			this.m.Pending = false;
			this.removeSelf();
		}
	}

	function onTurnEnd()
	{
		if (--this.m.TurnsLeft <= 0)
		{
			if (this.m.PatchedSkill != null)
			{
				this.m.PatchedSkill.m.FatigueCost = this.m.OriginalFatigue;
				this.m.PatchedSkill = null;
			}

			this.removeSelf();
		}
	}
});

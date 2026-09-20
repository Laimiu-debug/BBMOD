this.afei_finals_moment <- this.inherit("scripts/skills/skill", {
	m = {},
	function create()
	{
		this.m.ID = "actives.afei_finals_moment";
		this.m.Name = "决赛时刻";
		this.m.Description = "从第五轮开始，单体近战武器伤害 +10%，每次此类攻击额外积累 3 疲劳。战后清除。";
		this.m.Icon = "ui/orientation/shortsword_orientation.png";
		this.m.Type = this.Const.SkillType.Special;
		this.m.Order = this.Const.SkillOrder.Last;
		this.m.IsActive = false;
		this.m.IsStacking = false;
		this.m.IsHidden = false;
	}

	function isActiveRound()
	{
		local round = ::AfeiExpedition.getRound();
		return round >= 5;
	}

	function onAnySkillUsed(_skill, _targetEntity, _properties)
	{
		if (!this.isActiveRound() || _skill == null || !_skill.isAttack() || _skill.isRanged())
		{
			return;
		}

		_properties.DamageTotalMult *= 1.1;
	}

	function onAnySkillExecuted(_skill, _targetTile, _targetEntity, _forFree)
	{
		if (!this.isActiveRound() || _skill == null || !_skill.isAttack() || _skill.isRanged())
		{
			return;
		}

		local actor = this.getContainer().getActor();
		actor.setFatigue(this.Math.min(actor.getFatigueMax(), actor.getFatigue() + 3));
	}
});

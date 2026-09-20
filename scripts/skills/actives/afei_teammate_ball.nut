this.afei_teammate_ball <- this.inherit("scripts/skills/skill", {
	m = {
		UsedThisRound = false
	},
	function create()
	{
		this.m.ID = "actives.afei_teammate_ball";
		this.m.Name = "队友给的球";
		this.m.Description = "每轮第一次攻击本轮已被另一名友军单体武器攻击命中的敌人时，命中 +5。";
		this.m.Icon = "ui/orientation/shortsword_orientation.png";
		this.m.Type = this.Const.SkillType.Special;
		this.m.Order = this.Const.SkillOrder.Last;
		this.m.IsActive = false;
		this.m.IsStacking = false;
		this.m.IsHidden = false;
	}

	function hasOtherAllyHit(_targetEntity)
	{
		if (_targetEntity == null)
		{
			return false;
		}

		local id = _targetEntity.getFlags().getAsInt("afei_hit_by_ally_id");
		return id != 0 && id != this.getContainer().getActor().getID();
	}

	function onAnySkillUsed(_skill, _targetEntity, _properties)
	{
		if (this.m.UsedThisRound || _skill == null || !_skill.isAttack() || _targetEntity == null)
		{
			return;
		}

		if (this.hasOtherAllyHit(_targetEntity))
		{
			_properties.MeleeSkill += 5;
			_properties.RangedSkill += 5;
		}
	}

	function onAnySkillExecuted(_skill, _targetTile, _targetEntity, _forFree)
	{
		if (this.m.UsedThisRound || _skill == null || !_skill.isAttack() || _targetEntity == null)
		{
			return;
		}

		if (this.hasOtherAllyHit(_targetEntity))
		{
			this.m.UsedThisRound = true;
		}
	}

	function onTurnStart()
	{
		this.m.UsedThisRound = false;
	}

	function onCombatStarted()
	{
		this.m.UsedThisRound = false;
	}
});

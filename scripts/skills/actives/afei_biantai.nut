this.afei_biantai <- this.inherit("scripts/skills/skill", {
	m = { LastTargetID = 0, UsedThisRound = false },
	function create()
	{
		this.m.ID = "actives.afei_biantai";
		this.m.Name = "变态";
		this.m.Description = "远程攻击目标不同于上次远程目标时命中 +8，每轮最多一次。";
		this.m.Icon = "ui/orientation/shortsword_orientation.png";
		this.m.Type = this.Const.SkillType.Special;
		this.m.IsActive = false;
	}
	function onAnySkillUsed(_skill, _targetEntity, _properties)
	{
		if (this.m.UsedThisRound || _skill == null || !_skill.isAttack() || !_skill.isRanged() || _targetEntity == null) { return; }
		if (this.m.LastTargetID != 0 && _targetEntity.getID() != this.m.LastTargetID)
		{
			_properties.RangedSkill += 8;
		}
	}
	function onAnySkillExecuted(_skill, _targetTile, _targetEntity, _forFree)
	{
		if (_skill == null || !_skill.isAttack() || !_skill.isRanged() || _targetEntity == null) { return; }
		if (this.m.LastTargetID != 0 && _targetEntity.getID() != this.m.LastTargetID && !this.m.UsedThisRound)
		{
			this.m.UsedThisRound = true;
		}
		this.m.LastTargetID = _targetEntity.getID();
	}
	function onTurnStart() { this.m.UsedThisRound = false; }
	function onCombatFinished() { this.m.LastTargetID = 0; this.m.UsedThisRound = false; }
});

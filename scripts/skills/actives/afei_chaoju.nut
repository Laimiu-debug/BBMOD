this.afei_chaoju <- this.inherit("scripts/skills/skill", {
	m = { Stacks = 0, HitThisRound = false, MissThisRound = false },
	function create()
	{
		this.m.ID = "actives.afei_chaoju";
		this.m.Name = "超巨";
		this.m.Description = "每轮第一次武器命中 +1 层聚光，第一次未命中 -1 层；最多 3 层。每层远攻 +3、决心 +3。战后清除。";
		this.m.Icon = "ui/orientation/shortsword_orientation.png";
		this.m.Type = this.Const.SkillType.Special;
		this.m.IsActive = false;
	}
	function onUpdate(_properties)
	{
		_properties.RangedSkill += 3 * this.m.Stacks;
		_properties.Bravery += 3 * this.m.Stacks;
	}
	function onTargetHit(_skill, _targetEntity, _bodyPart, _damageInflictedHitpoints, _damageInflictedArmor)
	{
		if (_skill != null && _skill.isAttack() && !this.m.HitThisRound)
		{
			this.m.HitThisRound = true;
			this.m.Stacks = this.Math.min(3, this.m.Stacks + 1);
		}
	}
	function onTargetMissed(_skill, _targetEntity)
	{
		if (_skill != null && _skill.isAttack() && !this.m.MissThisRound)
		{
			this.m.MissThisRound = true;
			this.m.Stacks = this.Math.max(0, this.m.Stacks - 1);
		}
	}
	function onTurnStart() { this.m.HitThisRound = false; this.m.MissThisRound = false; }
	function onCombatFinished() { this.m.Stacks = 0; }
});

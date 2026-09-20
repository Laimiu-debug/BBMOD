this.afei_borrow_strike_effect <- this.inherit("scripts/skills/skill", {
	m = {
		TurnsLeft = 2,
		HitsLeft = 2,
		Bonus = 0
	},
	function create()
	{
		this.m.ID = "effects.afei_borrow_strike";
		this.m.Name = "大哥借我";
		this.m.Icon = "skills/status_effect_44.png";
		this.m.Type = this.Const.SkillType.StatusEffect;
		this.m.IsActive = false;
		this.m.IsStacking = false;
		this.m.IsRemovedAfterBattle = true;
	}

	function setBonus(_v)
	{
		this.m.Bonus = _v;
	}

	function getDescription()
	{
		return "近战命中 +" + this.m.Bonus + "，剩余攻击次数 " + this.m.HitsLeft + "。";
	}

	function onAnySkillUsed(_skill, _targetEntity, _properties)
	{
		if (_skill != null && _skill.isAttack() && !_skill.isRanged() && this.m.HitsLeft > 0)
		{
			_properties.MeleeSkill += this.m.Bonus;
		}
	}

	function onTargetHit(_skill, _targetEntity, _bodyPart, _damageInflictedHitpoints, _damageInflictedArmor)
	{
		if (_skill != null && _skill.isAttack() && !_skill.isRanged())
		{
			this.m.HitsLeft -= 1;

			if (this.m.HitsLeft <= 0)
			{
				this.removeSelf();
			}
		}
	}

	function onTurnEnd()
	{
		if (--this.m.TurnsLeft <= 0)
		{
			this.removeSelf();
		}
	}
});

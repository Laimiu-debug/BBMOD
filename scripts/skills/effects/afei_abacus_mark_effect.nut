this.afei_abacus_mark_effect <- this.inherit("scripts/skills/skill", {
	m = {
		TurnsLeft = 2
	},
	function create()
	{
		this.m.ID = "effects.afei_abacus_mark";
		this.m.Name = "记账";
		this.m.Description = "下一次受到的友军单体武器攻击命中 +10。";
		this.m.Icon = "skills/status_effect_62.png";
		this.m.Type = this.Const.SkillType.StatusEffect;
		this.m.IsActive = false;
		this.m.IsStacking = false;
		this.m.IsRemovedAfterBattle = true;
	}

	function onTurnEnd()
	{
		if (--this.m.TurnsLeft <= 0)
		{
			this.removeSelf();
		}
	}

	function onBeforeDamageReceived(_attacker, _skill, _hitInfo, _properties)
	{
		if (_attacker != null && _skill != null && _skill.isAttack() && !_skill.isRanged() || _skill != null && _skill.isAttack())
		{
			_properties.DamageTotalMult *= 1.0;
		}
	}

	function onMissed(_attacker, _skill)
	{
		this.removeSelf();
	}

	function onDamageReceived(_attacker, _damageHitpoints, _damageArmor)
	{
		this.removeSelf();
	}
});

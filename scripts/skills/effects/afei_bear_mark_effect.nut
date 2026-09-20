this.afei_bear_mark_effect <- this.inherit("scripts/skills/skill", {
	m = {
		TurnsLeft = 2,
		Pending = true
	},
	function create()
	{
		this.m.ID = "effects.afei_bear_mark";
		this.m.Name = "小熊干扰";
		this.m.Description = "下一次武器攻击命中 -10。";
		this.m.Icon = "skills/status_effect_02.png";
		this.m.Type = this.Const.SkillType.StatusEffect;
		this.m.IsRemovedAfterBattle = true;
	}
	function onAnySkillUsed(_skill, _targetEntity, _properties)
	{
		if (this.m.Pending && _skill != null && _skill.isAttack())
		{
			_properties.MeleeSkill -= 10;
			_properties.RangedSkill -= 10;
		}
	}
	function onAnySkillExecuted(_skill, _targetTile, _targetEntity, _forFree)
	{
		if (this.m.Pending && _skill != null && _skill.isAttack())
		{
			this.m.Pending = false;
			this.removeSelf();
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

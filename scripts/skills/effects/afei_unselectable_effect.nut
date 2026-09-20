this.afei_unselectable_effect <- this.inherit("scripts/skills/skill", {
	m = {},
	function create()
	{
		this.m.ID = "effects.afei_unselectable";
		this.m.Name = "无法选中（近似）";
		this.m.Icon = "skills/status_effect_34.png";
		this.m.Type = this.Const.SkillType.StatusEffect;
		this.m.IsRemovedAfterBattle = true;
	}
	function onUpdate(_properties)
	{
		_properties.MeleeDefense += 15;
		_properties.RangedDefense += 15;
	}
	function onTurnStart() { this.removeSelf(); }
	function onAnySkillExecuted(_skill, _targetTile, _targetEntity, _forFree)
	{
		if (_skill != null && _skill.isAttack()) { this.removeSelf(); }
	}
});

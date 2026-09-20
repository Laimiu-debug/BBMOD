this.afei_unselectable_effect <- this.inherit("scripts/skills/skill", {
	m = {},
	function create()
	{
		this.m.ID = "effects.afei_unselectable";
		this.m.Name = "无法选中";
		this.m.Description = "至下次自身行动开始：大幅降低被 AI 单体点名的吸引力；若场上另有合法友军目标，敌人优先选其他人。";
		this.m.Icon = "skills/status_effect_34.png";
		this.m.Type = this.Const.SkillType.StatusEffect;
		this.m.IsRemovedAfterBattle = true;
	}
	function onUpdate(_properties)
	{
		_properties.TargetAttractionMult *= 0.05;
		_properties.MeleeDefense += 8;
		_properties.RangedDefense += 8;
	}
	function onTurnStart() { this.removeSelf(); }
	function onAnySkillExecuted(_skill, _targetTile, _targetEntity, _forFree)
	{
		if (_skill != null && _skill.isAttack()) { this.removeSelf(); }
	}
});

this.afei_dog_bark_effect <- this.inherit("scripts/skills/skill", {
	m = {},
	function create()
	{
		this.m.ID = "effects.afei_dog_bark";
		this.m.Name = "被狗叫干扰";
		this.m.Icon = "skills/status_effect_02.png";
		this.m.Type = this.Const.SkillType.StatusEffect;
		this.m.IsStacking = false;
		this.m.IsRemovedAfterBattle = true;
	}
	function onUpdate(_properties) { _properties.MeleeSkill -= 8; }
	function onTurnEnd() { this.removeSelf(); }
});

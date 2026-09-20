this.afei_guard_gate_effect <- this.inherit("scripts/skills/skill", {
	m = {},
	function create()
	{
		this.m.ID = "effects.afei_guard_gate";
		this.m.Name = "守门";
		this.m.Icon = "skills/status_effect_34.png";
		this.m.Type = this.Const.SkillType.StatusEffect;
		this.m.IsRemovedAfterBattle = true;
	}
	function onUpdate(_properties)
	{
		_properties.MeleeDefense += 8;
		_properties.IsRooted = true;
	}
	function onTurnStart() { this.removeSelf(); }
});

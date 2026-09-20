this.afei_steady_hand_effect <- this.inherit("scripts/skills/skill", {
	m = { TurnsLeft = 2 },
	function create()
	{
		this.m.ID = "effects.afei_steady_hand";
		this.m.Name = "稳一手";
		this.m.Icon = "skills/status_effect_34.png";
		this.m.Type = this.Const.SkillType.StatusEffect;
		this.m.IsRemovedAfterBattle = true;
	}
	function onUpdate(_properties) { _properties.MeleeDefense += 5; }
	function onTurnEnd() { if (--this.m.TurnsLeft <= 0) this.removeSelf(); }
});

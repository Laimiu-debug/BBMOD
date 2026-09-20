this.afei_prince_order_effect <- this.inherit("scripts/skills/skill", {
	m = { TurnsLeft = 2 },
	function create()
	{
		this.m.ID = "effects.afei_prince_order";
		this.m.Name = "太子发令";
		this.m.Icon = "skills/status_effect_73.png";
		this.m.Type = this.Const.SkillType.StatusEffect;
		this.m.IsRemovedAfterBattle = true;
	}
	function onUpdate(_properties)
	{
		_properties.Bravery += 10;
		_properties.MeleeDefense += 5;
	}
	function onTurnEnd() { if (--this.m.TurnsLeft <= 0) this.removeSelf(); }
});

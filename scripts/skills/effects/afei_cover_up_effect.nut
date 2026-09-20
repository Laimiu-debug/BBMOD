this.afei_cover_up_effect <- this.inherit("scripts/skills/skill", {
	m = {},
	function create()
	{
		this.m.ID = "effects.afei_cover_up";
		this.m.Name = "被顶上去守护";
		this.m.Icon = "skills/status_effect_34.png";
		this.m.Type = this.Const.SkillType.StatusEffect;
		this.m.IsRemovedAfterBattle = true;
	}
	function onUpdate(_properties)
	{
		_properties.MeleeDefense += 10;
		_properties.DamageReceivedTotalMult *= 0.85;
	}
	function onTurnStart() { this.removeSelf(); }
});

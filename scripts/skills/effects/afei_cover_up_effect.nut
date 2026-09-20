this.afei_cover_up_effect <- this.inherit("scripts/skills/skill", {
	m = { ProtectorID = 0, Consumed = false },
	function create()
	{
		this.m.ID = "effects.afei_cover_up";
		this.m.Name = "被顶上去守护";
		this.m.Description = "单体近战点名时优先改打守护者；若仍打到你，则改由守护者承伤并减免生命伤害。";
		this.m.Icon = "skills/status_effect_34.png";
		this.m.Type = this.Const.SkillType.StatusEffect;
		this.m.IsRemovedAfterBattle = true;
	}
	function setProtector(_id) { this.m.ProtectorID = _id; }
	function onUpdate(_properties)
	{
		_properties.MeleeDefense += 4;
		_properties.TargetAttractionMult *= 0.35;
	}
	function onTurnStart() { this.removeSelf(); }
});

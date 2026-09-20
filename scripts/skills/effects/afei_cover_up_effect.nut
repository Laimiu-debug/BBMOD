this.afei_cover_up_effect <- this.inherit("scripts/skills/skill", {
	m = { ProtectorID = 0, Consumed = false },
	function create()
	{
		this.m.ID = "effects.afei_cover_up";
		this.m.Name = "被顶上去守护";
		this.m.Description = "首次遭受合格单体近战攻击时，若守护者仍邻接且可被同一攻击选中，则改由守护者承受（生命伤害再减 15%/25%）。";
		this.m.Icon = "skills/status_effect_34.png";
		this.m.Type = this.Const.SkillType.StatusEffect;
		this.m.IsRemovedAfterBattle = true;
	}
	function setProtector(_id) { this.m.ProtectorID = _id; }
	function onUpdate(_properties)
	{
		_properties.MeleeDefense += 4;
	}
	function onTurnStart() { this.removeSelf(); }
});

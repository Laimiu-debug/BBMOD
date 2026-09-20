this.afei_covering_effect <- this.inherit("scripts/skills/skill", {
	m = { ProtectedID = 0 },
	function create()
	{
		this.m.ID = "effects.afei_covering";
		this.m.Name = "顶上去";
		this.m.Description = "正在守护一名相邻伙伴：更容易被敌人点名；合格单体近战会优先改打你。";
		this.m.Icon = "skills/status_effect_11.png";
		this.m.Type = this.Const.SkillType.StatusEffect;
		this.m.IsRemovedAfterBattle = true;
	}
	function setProtected(_id) { this.m.ProtectedID = _id; }
	function onUpdate(_properties)
	{
		_properties.TargetAttractionMult *= 2.5;
		_properties.MeleeDefense += 2;
	}
	function onTurnStart() { this.removeSelf(); }
});

this.afei_bottle_breakthrough_penalty <- this.inherit("scripts/skills/skill", {
	m = {},
	function create()
	{
		this.m.ID = "effects.afei_bottle_breakthrough_penalty";
		this.m.Name = "突破空当";
		this.m.Description = "瓶队突破后近防 -5，至下次自身行动开始。";
		this.m.Icon = "skills/status_effect_02.png";
		this.m.Type = this.Const.SkillType.StatusEffect;
		this.m.IsActive = false;
		this.m.IsStacking = false;
		this.m.IsRemovedAfterBattle = true;
	}

	function onUpdate(_properties)
	{
		_properties.MeleeDefense -= 5;
	}

	function onTurnStart()
	{
		this.removeSelf();
	}
});

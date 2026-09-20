this.afei_steady_hand_effect <- this.inherit("scripts/skills/skill", {
	m = {
		TurnsLeft = 2,
		PushImmuneLeft = 1
	},
	function create()
	{
		this.m.ID = "effects.afei_steady_hand";
		this.m.Name = "稳一手";
		this.m.Description = "近防与决心提升；另有一次强制推拉位移免疫。";
		this.m.Icon = "skills/status_effect_34.png";
		this.m.Type = this.Const.SkillType.StatusEffect;
		this.m.IsRemovedAfterBattle = true;
	}
	function onUpdate(_properties)
	{
		_properties.MeleeDefense += 6;
		_properties.Bravery += 6;
	}
	function onTurnEnd()
	{
		if (--this.m.TurnsLeft <= 0)
		{
			this.removeSelf();
		}
	}
});

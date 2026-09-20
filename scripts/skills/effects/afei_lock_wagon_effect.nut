this.afei_lock_wagon_effect <- this.inherit("scripts/skills/skill", {
	m = {
		TurnsLeft = 1
	},
	function create()
	{
		this.m.ID = "effects.afei_lock_wagon";
		this.m.Name = "绳扣";
		this.m.Description = "移动受阻（近似锁车绳扣）；仍可原地攻击。";
		this.m.Icon = "skills/status_effect_53.png";
		this.m.Type = this.Const.SkillType.StatusEffect;
		this.m.IsRemovedAfterBattle = true;
	}
	function onUpdate(_properties)
	{
		_properties.IsRooted = true;
		_properties.InitiativeForTurnOrderMult *= 0.5;
	}
	function onTurnEnd()
	{
		if (--this.m.TurnsLeft <= 0)
		{
			this.removeSelf();
		}
	}
});

this.afei_wawa_effect <- this.inherit("scripts/skills/skill", {
	m = {
		TurnsLeft = 2,
		Bonus = 6
	},
	function create()
	{
		this.m.ID = "effects.afei_wawa";
		this.m.Name = "哇哇叫";
		this.m.Description = "被团长的号令鼓舞，决心检定获得加成。";
		this.m.Icon = "skills/status_effect_73.png";
		this.m.Type = this.Const.SkillType.StatusEffect;
		this.m.IsActive = false;
		this.m.IsStacking = false;
		this.m.IsRemovedAfterBattle = true;
	}

	function getDescription()
	{
		return "决心检定 +" + this.m.Bonus + "，剩余 " + this.m.TurnsLeft + " 轮。";
	}

	function setBonus(_v)
	{
		this.m.Bonus = _v;
	}

	function onUpdate(_properties)
	{
		_properties.Bravery += this.m.Bonus;
	}

	function onTurnEnd()
	{
		if (--this.m.TurnsLeft <= 0)
		{
			this.removeSelf();
		}
	}
});

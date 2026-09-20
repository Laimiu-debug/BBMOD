this.afei_origin_temp_cap_effect <- this.inherit("scripts/skills/skill", {
	m = {},
	function create()
	{
		this.m.ID = "effects.afei_origin_temp_cap";
		this.m.Name = "起源临时上限";
		this.m.Description = "仅钳制本起源战斗临时命中/防御/决心/先攻；不改动装备与基础属性。命中±15、近防/远防各+15、决心临≤30、先攻临≤20；同型号令取最高。";
		this.m.Icon = "skills/status_effect_34.png";
		this.m.Type = this.Const.SkillType.StatusEffect;
		this.m.Order = this.Const.SkillOrder.Last;
		this.m.IsActive = false;
		this.m.IsHidden = true;
		this.m.IsStacking = false;
		this.m.IsRemovedAfterBattle = true;
	}
	function onUpdate(_properties)
	{
		::AfeiExpedition.clampOriginTempsOnto(_properties, this.getContainer().getActor());
	}
});

this.afei_origin_temp_reset_effect <- this.inherit("scripts/skills/skill", {
	m = {},
	function create()
	{
		this.m.ID = "effects.afei_origin_temp_reset";
		this.m.Name = "";
		this.m.Description = "";
		this.m.Icon = "skills/status_effect_34.png";
		this.m.Type = this.Const.SkillType.StatusEffect;
		this.m.Order = this.Const.SkillOrder.First;
		this.m.IsActive = false;
		this.m.IsHidden = true;
		this.m.IsStacking = false;
		this.m.IsRemovedAfterBattle = true;
	}
	function onUpdate(_properties)
	{
		::AfeiExpedition.clearOriginTempBuckets(this.getContainer().getActor());
	}
});

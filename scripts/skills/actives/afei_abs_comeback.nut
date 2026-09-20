this.afei_abs_comeback <- this.inherit("scripts/skills/skill", {
	m = {},
	function create()
	{
		this.m.ID = "actives.afei_abs_comeback";
		this.m.Name = "抽象整活";
		this.m.Description = "返场被动：生命低于50%时近攻+5。";
		this.m.Icon = "ui/orientation/shortsword_orientation.png";
		this.m.Type = this.Const.SkillType.Special;
		this.m.IsActive = false;
		this.m.IsStacking = false;
	}
	function onUpdate(_properties)
	{
		
		if (this.getContainer().getActor().getHitpointsPct() < 0.5) _properties.MeleeSkill += 5;
	}
});

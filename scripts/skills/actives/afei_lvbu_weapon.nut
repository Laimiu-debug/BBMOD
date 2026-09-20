this.afei_lvbu_weapon <- this.inherit("scripts/skills/skill", {
	m = {},
	function create()
	{
		this.m.ID = "actives.afei_lvbu_weapon";
		this.m.Name = "奶团吕布";
		this.m.Description = "近攻+5。";
		this.m.Icon = "ui/orientation/shortsword_orientation.png";
		this.m.Type = this.Const.SkillType.Special;
		this.m.IsActive = false;
		this.m.IsStacking = false;
	}
	function onUpdate(_properties)
	{
		_properties.MeleeSkill += 5;
	}
});

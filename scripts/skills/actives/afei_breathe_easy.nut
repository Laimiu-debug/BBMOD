this.afei_breathe_easy <- this.inherit("scripts/skills/skill", {
	m = {},
	function create()
	{
		this.m.ID = "actives.afei_breathe_easy";
		this.m.Name = "松口气";
		this.m.Description = "守望被动占位：疲劳上限+5。";
		this.m.Icon = "ui/orientation/shortsword_orientation.png";
		this.m.Type = this.Const.SkillType.Special;
		this.m.IsActive = false;
		this.m.IsStacking = false;
	}
	function onUpdate(_properties)
	{
		_properties.Stamina += 5;
	}
});

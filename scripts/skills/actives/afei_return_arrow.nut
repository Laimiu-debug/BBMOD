this.afei_return_arrow <- this.inherit("scripts/skills/skill", {
	m = {},
	function create()
	{
		this.m.ID = "actives.afei_return_arrow";
		this.m.Name = "回头箭";
		this.m.Description = "本轮移动后远程命中 +5（近似：远攻 +5）。";
		this.m.Icon = "ui/orientation/shortsword_orientation.png";
		this.m.Type = this.Const.SkillType.Special;
		this.m.IsActive = false;
		this.m.IsStacking = false;
	}
	function onUpdate(_properties)
	{
		_properties.RangedSkill += 5;
	}
});

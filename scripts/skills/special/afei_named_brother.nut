this.afei_named_brother <- this.inherit("scripts/skills/skill", {
	m = {},
	function create()
	{
		this.m.ID = "special.afei_named_brother";
		this.m.Name = "黑旗名册";
		this.m.Description = "此人是大飞午远征团的命名伙伴。死、离、解雇均无替身；专属成长与事件不可由普通同名佣兵冒领。";
		this.m.Icon = "ui/orientation/shortsword_orientation.png";
		this.m.Type = this.Const.SkillType.Special;
		this.m.IsActive = false;
		this.m.IsStacking = false;
		this.m.IsHidden = false;
	}

	function getTooltip()
	{
		return [
			{
				id = 1,
				type = "title",
				text = this.getName()
			},
			{
				id = 2,
				type = "description",
				text = this.getDescription()
			}
		];
	}
});

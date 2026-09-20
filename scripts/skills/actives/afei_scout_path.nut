this.afei_scout_path <- this.inherit("scripts/skills/skill", {
	m = {},
	function create()
	{
		this.m.ID = "actives.afei_scout_path";
		this.m.Name = "探路";
		this.m.Description = "熟悉路线：战斗中先攻 +6；每轮第一次普通移动后疲劳恢复 2（计入起源每轮恢复上限）。世界地图行军疲劳减免受引擎限制，本版以战斗效益近似。";
		this.m.Icon = "ui/orientation/shortsword_orientation.png";
		this.m.Type = this.Const.SkillType.Special;
		this.m.IsActive = false;
		this.m.IsStacking = false;
	}
	function onUpdate(_properties)
	{
		_properties.Initiative += 6;
	}
	function onTurnStart()
	{
		this.getContainer().getActor().getFlags().set("afei_scout_move_heal", false);
	}
});

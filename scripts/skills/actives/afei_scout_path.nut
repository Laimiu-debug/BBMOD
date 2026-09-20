this.afei_scout_path <- this.inherit("scripts/skills/skill", {
	m = {},
	function create()
	{
		this.m.ID = "actives.afei_scout_path";
		this.m.Name = "探路";
		this.m.Description = "熟悉路线：战斗中先攻 +6；每轮第一次普通移动后疲劳恢复 2。世界地图上若小虎在常备队，战团移动略快（约 +5%）。";
		this.m.Icon = "ui/orientation/shortsword_orientation.png";
		this.m.Type = this.Const.SkillType.Special;
		this.m.IsActive = false;
		this.m.IsStacking = false;
	}
	function onUpdate(_properties)
	{
		_properties.Initiative += 6;
		::AfeiExpedition.noteOriginInitiative(this.getContainer().getActor(), 6, false);
	}
	function onTurnStart()
	{
		this.getContainer().getActor().getFlags().set("afei_scout_move_heal", false);
	}
});

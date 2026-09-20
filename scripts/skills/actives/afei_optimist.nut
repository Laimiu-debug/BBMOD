this.afei_optimist <- this.inherit("scripts/skills/skill", {
	m = { Used = 0, MaxUses = 1 },
	function create()
	{
		this.m.ID = "actives.afei_optimist";
		this.m.Name = "乐天派";
		this.m.Description = "每场第一次普通士气检定失败时，取消本次下降（保持检定前士气）。G07 后每战两次，每轮最多一次。";
		this.m.Icon = "ui/orientation/shortsword_orientation.png";
		this.m.Type = this.Const.SkillType.Special;
		this.m.IsActive = false;
	}
	function onCombatStarted()
	{
		this.m.Used = 0;
		this.m.MaxUses = this.World.Flags.get(::AfeiExpedition.Flags.GrowthDone + "C07") ? 2 : 1;
	}
	function onTurnStart() { this.getContainer().getActor().getFlags().set("afei_optimist_round", false); }
});

this.afei_know_rules <- this.inherit("scripts/skills/skill", {
	m = {
		Stacks = 0,
		GainedThisRound = false
	},
	function create()
	{
		this.m.ID = "actives.afei_know_rules";
		this.m.Name = "看懂";
		this.m.Description = "观察敌人重复武器招式获得看懂层数（最多 2，成长后 3；每轮最多获得 1）。可供小熊出击/敲杯为号消耗。";
		this.m.Icon = "ui/orientation/shortsword_orientation.png";
		this.m.Type = this.Const.SkillType.Special;
		this.m.IsActive = false;
		this.m.IsStacking = false;
	}
	function getMaxStacks()
	{
		local actor = this.getContainer().getActor();
		if (actor.getFlags().get("afei_understand_3") || this.World.Flags.get(::AfeiExpedition.Flags.GrowthDone + "C18"))
		{
			return 3;
		}
		return 2;
	}
	function getTooltip()
	{
		return [
			{ id = 1, type = "title", text = this.getName() },
			{ id = 2, type = "description", text = this.getDescription() },
			{ id = 10, type = "text", icon = "ui/icons/special.png", text = "当前看懂：" + this.m.Stacks + " / " + this.getMaxStacks() }
		];
	}
	function onUpdate(_properties)
	{
		_properties.Bravery += 2 + this.m.Stacks;
	}
	function tryGainStack()
	{
		if (this.m.GainedThisRound)
		{
			return false;
		}
		if (this.m.Stacks >= this.getMaxStacks())
		{
			return false;
		}
		this.m.Stacks += 1;
		this.m.GainedThisRound = true;
		return true;
	}
	function consumeStacks(_n)
	{
		local take = _n;
		if (take > this.m.Stacks)
		{
			take = this.m.Stacks;
		}
		this.m.Stacks -= take;
		return take;
	}
	function onTurnStart()
	{
		this.m.GainedThisRound = false;
	}
	function onCombatStarted()
	{
		this.m.Stacks = 0;
		this.m.GainedThisRound = false;
	}
	function onCombatFinished()
	{
		this.m.Stacks = 0;
		this.m.GainedThisRound = false;
	}
});

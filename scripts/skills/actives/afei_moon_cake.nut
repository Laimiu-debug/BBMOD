this.afei_moon_cake <- this.inherit("scripts/skills/skill", {
	m = {
		Prepared = false
	},
	function create()
	{
		this.m.ID = "actives.afei_moon_cake";
		this.m.Name = "月饼准备";
		this.m.Description = "营地可准备月饼（成长计数）。战斗中：先护住自己——每轮首次承受生命伤害时减伤 10%（成长后 15%）。";
		this.m.Icon = "ui/orientation/shortsword_orientation.png";
		this.m.Type = this.Const.SkillType.Special;
		this.m.IsActive = false;
		this.m.IsStacking = false;
	}
	function getDR()
	{
		local actor = this.getContainer().getActor();
		if (actor.getFlags().get("afei_guard_self_15") || this.World.Flags.get(::AfeiExpedition.Flags.GrowthDone + "C22"))
		{
			return 0.15;
		}
		return 0.10;
	}
	function onUpdate(_properties)
	{
		_properties.Hitpoints += 2;
	}
	function onBeforeDamageReceived(_attacker, _skill, _hitInfo, _properties)
	{
		local actor = this.getContainer().getActor();
		if (actor.getFlags().get("afei_moon_dr_used"))
		{
			return;
		}
		actor.getFlags().set("afei_moon_dr_used", true);
		local dr = this.getDR();
		_properties.DamageReceivedTotalMult *= (1.0 - dr);
	}
	function onTurnStart()
	{
		this.getContainer().getActor().getFlags().set("afei_moon_dr_used", false);
	}
	function onCombatStarted()
	{
		this.getContainer().getActor().getFlags().set("afei_moon_dr_used", false);
	}
});

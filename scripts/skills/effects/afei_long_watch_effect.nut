this.afei_long_watch_effect <- this.inherit("scripts/skills/skill", {
	m = {
		TurnsLeft = 1,
		Healed = false
	},
	function create()
	{
		this.m.ID = "effects.afei_long_watch";
		this.m.Name = "长轮守门";
		this.m.Description = "近防与远防各 +8，先攻 -10；首次被单体命中后恢复疲劳。";
		this.m.Icon = "skills/status_effect_34.png";
		this.m.Type = this.Const.SkillType.StatusEffect;
		this.m.IsRemovedAfterBattle = true;
	}
	function onUpdate(_properties)
	{
		_properties.MeleeDefense += 8;
		_properties.RangedDefense += 8;
		_properties.Initiative -= 10;
	}
	function onDamageReceived(_attacker, _damageHitpoints, _damageArmor)
	{
		if (this.m.Healed || _attacker == null)
		{
			return;
		}
		local actor = this.getContainer().getActor();
		if (_attacker.isAlliedWith(actor))
		{
			return;
		}
		local amount = 4;
		if (actor.getFlags().get("afei_long_watch_7") || this.World.Flags.get(::AfeiExpedition.Flags.GrowthDone + "C20"))
		{
			amount = 7;
		}
		local heal = ::AfeiExpedition.consumeFatigueRecoverBudget(amount, actor);
		if (heal > 0)
		{
			actor.setFatigue(this.Math.max(0, actor.getFatigue() - heal));
			this.m.Healed = true;
		}
	}
	function onTurnStart()
	{
		this.m.Healed = false;
		if (--this.m.TurnsLeft < 0)
		{
			this.removeSelf();
		}
	}
});

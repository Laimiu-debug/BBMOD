this.afei_pokemon_effect <- this.inherit("scripts/skills/skill", {
	m = {
		TurnsLeft = 2,
		WatcherID = null,
		ThreatID = null,
		MissHealUsed = false
	},
	function create()
	{
		this.m.ID = "effects.afei_pokemon";
		this.m.Name = "保可梦";
		this.m.Description = "远防提升；被敌单体武器攻击后记录威胁。";
		this.m.Icon = "skills/status_effect_34.png";
		this.m.Type = this.Const.SkillType.StatusEffect;
		this.m.IsRemovedAfterBattle = true;
	}
	function setWatcher(_id)
	{
		this.m.WatcherID = _id;
	}
	function onUpdate(_properties)
	{
		_properties.RangedDefense += 8;
		local actor = this.getContainer().getActor();
		if (actor.getFlags().get("afei_pokemon_md4") || this.World.Flags.get(::AfeiExpedition.Flags.GrowthDone + "C17"))
		{
			_properties.MeleeDefense += 4;
		}
	}
	function onDamageReceived(_attacker, _damageHitpoints, _damageArmor)
	{
		if (_attacker == null || !_attacker.isAlive())
		{
			return;
		}
		local actor = this.getContainer().getActor();
		if (_attacker.isAlliedWith(actor))
		{
			return;
		}
		this.m.ThreatID = _attacker.getID();
	}
	function onMissed(_attacker, _skill)
	{
		if (this.m.MissHealUsed || _attacker == null || _skill == null || !_skill.isAttack())
		{
			return;
		}
		local actor = this.getContainer().getActor();
		if (_attacker.isAlliedWith(actor))
		{
			return;
		}
		this.m.ThreatID = _attacker.getID();
		local watcher = null;
		foreach (a in this.Tactical.Entities.getInstancesOfFaction(actor.getFaction()))
		{
			if (a != null && a.getID() == this.m.WatcherID && a.isAlive())
			{
				watcher = a;
				break;
			}
		}
		if (watcher == null)
		{
			return;
		}
		local heal = ::AfeiExpedition.consumeFatigueRecoverBudget(4, watcher);
		if (heal > 0)
		{
			watcher.setFatigue(this.Math.max(0, watcher.getFatigue() - heal));
			this.m.MissHealUsed = true;
		}
	}
	function onTurnStart()
	{
		this.m.MissHealUsed = false;
	}
	function onTurnEnd()
	{
		if (--this.m.TurnsLeft <= 0)
		{
			this.removeSelf();
		}
	}
});

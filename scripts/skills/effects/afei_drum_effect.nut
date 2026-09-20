this.afei_drum_effect <- this.inherit("scripts/skills/skill", {
	m = { Pending = true },
	function create()
	{
		this.m.ID = "effects.afei_drum";
		this.m.Name = "定拍";
		this.m.Icon = "skills/status_effect_73.png";
		this.m.Type = this.Const.SkillType.StatusEffect;
		this.m.IsRemovedAfterBattle = true;
	}
	function onTurnStart()
	{
		if (this.m.Pending)
		{
			local actor = this.getContainer().getActor();
			local recover = ::AfeiExpedition.consumeFatigueRecoverBudget(8, actor);
			actor.setFatigue(this.Math.max(0, actor.getFatigue() - recover));
			this.m.Pending = false;
		}
	}
	function onUpdate(_properties)
	{
		if (!this.m.Pending) { _properties.Bravery += 5; }
	}
	function onTurnEnd()
	{
		if (!this.m.Pending) { this.removeSelf(); }
	}
});

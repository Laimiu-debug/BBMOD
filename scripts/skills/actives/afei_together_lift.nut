this.afei_together_lift <- this.inherit("scripts/skills/skill", {
	m = {},
	function create()
	{
		this.m.ID = "actives.afei_together_lift";
		this.m.Name = "一起抬";
		this.m.Description = "两格内至少有两名其他可行动友军时：近战护甲伤害 +10%，近战武器技能疲劳成本 -2（最低 0）。";
		this.m.Icon = "ui/orientation/shortsword_orientation.png";
		this.m.Type = this.Const.SkillType.Special;
		this.m.IsActive = false;
	}
	function hasFormation()
	{
		local actor = this.getContainer().getActor();
		if (!actor.isPlacedOnMap()) return false;
		local c = 0;
		foreach (a in this.Tactical.Entities.getInstancesOfFaction(actor.getFaction()))
		{
			if (a.getID() == actor.getID() || !a.isAlive() || a.getCurrentProperties().IsStunned) continue;
			if (a.getTile().getDistanceTo(actor.getTile()) <= 2) c++;
		}
		return c >= 2;
	}
	function onUpdate(_properties)
	{
		if (this.hasFormation())
		{
			_properties.DamageArmorMult *= 1.1;
		}
	}
	function onAfterUpdate(_properties)
	{
		// fatigue on skills handled in preload hook when this skill present
	}
});

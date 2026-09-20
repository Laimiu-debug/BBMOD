this.afei_goose_bully <- this.inherit("scripts/skills/skill", {
	m = {},
	function create()
	{
		this.m.ID = "actives.afei_goose_bully";
		this.m.Name = "鹅势欺人";
		this.m.Description = "两格内至少两名其他友军时，近防 +6、决心 +3。";
		this.m.Icon = "ui/orientation/shortsword_orientation.png";
		this.m.Type = this.Const.SkillType.Special;
		this.m.IsActive = false;
		this.m.IsStacking = false;
	}
	function onUpdate(_properties)
	{
		local actor = this.getContainer().getActor();
		if (!actor.isPlacedOnMap())
		{
			return;
		}
		local my = actor.getTile();
		local n = 0;
		foreach (a in this.Tactical.Entities.getInstancesOfFaction(actor.getFaction()))
		{
			if (a == null || !a.isAlive() || a.getID() == actor.getID())
			{
				continue;
			}
			if (a.getTile().getDistanceTo(my) <= 2)
			{
				n += 1;
			}
		}
		if (n >= 2)
		{
			_properties.MeleeDefense += 6;
			_properties.Bravery += 3;
			actor.getFlags().set("afei_goose_form", true);
		}
		else
		{
			actor.getFlags().set("afei_goose_form", false);
		}
	}
});

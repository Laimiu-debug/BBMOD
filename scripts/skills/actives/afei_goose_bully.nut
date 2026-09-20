this.afei_goose_bully <- this.inherit("scripts/skills/skill", {
	m = {},
	function create()
	{
		this.m.ID = "actives.afei_goose_bully";
		this.m.Name = "鹅势欺人";
		this.m.Description = "两格内≥2友军时近防+3。";
		this.m.Icon = "ui/orientation/shortsword_orientation.png";
		this.m.Type = this.Const.SkillType.Special;
		this.m.IsActive = false;
		this.m.IsStacking = false;
	}
	function onUpdate(_properties)
	{
		
		local actor=this.getContainer().getActor(); local c=0;
		foreach(a in this.Tactical.Entities.getInstancesOfFaction(actor.getFaction())){
			if(a.getID()!=actor.getID() && a.isAlive() && a.getTile().getDistanceTo(actor.getTile())<=2) c++;
		}
		if(c>=2) _properties.MeleeDefense+=3;
	}
});

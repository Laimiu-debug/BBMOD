this.afei_five_elder <- this.inherit("scripts/skills/skill", {
	m = {},
	function create()
	{
		this.m.ID = "actives.afei_five_elder";
		this.m.Name = "五老压阵";
		this.m.Description = "阵形被动：邻接≥2友军近防+4。";
		this.m.Icon = "ui/orientation/shortsword_orientation.png";
		this.m.Type = this.Const.SkillType.Special;
		this.m.IsActive = false;
		this.m.IsStacking = false;
	}
	function onUpdate(_properties)
	{
		
		local actor=this.getContainer().getActor(); local c=0; local t=actor.getTile();
		for(local i=0;i<6;i++){ if(t.hasNextTile(i)){ local n=t.getNextTile(i); if(n.IsOccupiedByActor && n.getEntity().isAlliedWith(actor)) c++; }}
		if(c>=2) _properties.MeleeDefense+=4;
	}
});

this.afei_leave_not_gone <- this.inherit("scripts/skills/skill", {
	m = {},
	function create()
	{
		this.m.ID = "actives.afei_leave_not_gone";
		this.m.Name = "离席未散";
		this.m.Description = "邻接友军时近防+3。";
		this.m.Icon = "ui/orientation/shortsword_orientation.png";
		this.m.Type = this.Const.SkillType.Special;
		this.m.IsActive = false;
		this.m.IsStacking = false;
	}
	function onUpdate(_properties)
	{
		
		local actor=this.getContainer().getActor(); local t=actor.getTile();
		for(local i=0;i<6;i++){ if(t.hasNextTile(i)){ local n=t.getNextTile(i); if(n.IsOccupiedByActor && n.getEntity().isAlliedWith(actor)){ _properties.MeleeDefense+=3; return; }}}
	}
});

this.afei_good_card <- this.inherit("scripts/skills/skill", {
	m = {},
	function create()
	{
		this.m.ID = "actives.afei_good_card";
		this.m.Name = "一张好牌";
		this.m.Description = "邻接友军时近攻 +3。";
		this.m.Icon = "ui/orientation/shortsword_orientation.png";
		this.m.Type = this.Const.SkillType.Special;
		this.m.IsActive = false;
		this.m.IsStacking = false;
	}
	function onUpdate(_properties)
	{
		
		local actor=this.getContainer().getActor(); local t=actor.getTile();
		for(local i=0;i<6;i++){ if(t.hasNextTile(i)){ local n=t.getNextTile(i); if(n.IsOccupiedByActor && n.getEntity().isAlliedWith(actor)){ _properties.MeleeSkill+=3; return; }}}
	}
});

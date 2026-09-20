this.afei_small_heart <- this.inherit("scripts/skills/skill", {
	m = {},
	function create()
	{
		this.m.ID = "actives.afei_small_heart";
		this.m.Name = "小心脏";
		this.m.Description = "两格内无其他可行动友军时决心 -8；持盾且邻接可行动友军时近防 +4。互斥。";
		this.m.Icon = "ui/orientation/shortsword_orientation.png";
		this.m.Type = this.Const.SkillType.Special;
		this.m.IsActive = false;
	}
	function onUpdate(_properties)
	{
		local actor = this.getContainer().getActor();
		local myTile = actor.getTile();
		local allyNear = false;
		local allyAdj = false;
		local actors = this.Tactical.Entities.getInstancesOfFaction(actor.getFaction());
		foreach (a in actors)
		{
			if (a.getID() == actor.getID() || !a.isAlive()) { continue; }
			local d = a.getTile().getDistanceTo(myTile);
			if (d <= 2) { allyNear = true; }
			if (d == 1) { allyAdj = true; }
		}
		local off = actor.getItems().getItemAtSlot(this.Const.ItemSlot.Offhand);
		local hasShield = off != null && off.isItemType(this.Const.Items.ItemType.Shield);
		if (!allyNear) { _properties.Bravery -= 8; }
		else if (hasShield && allyAdj) { _properties.MeleeDefense += 4; }
	}
});

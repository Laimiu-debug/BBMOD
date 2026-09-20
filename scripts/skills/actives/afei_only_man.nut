this.afei_only_man <- this.inherit("scripts/skills/skill", {
	m = {},
	function create()
	{
		this.m.ID = "actives.afei_only_man";
		this.m.Name = "唯一的男人";
		this.m.Description = "邻接一名可行动且未持盾伙伴时，近防 +6。";
		this.m.Icon = "ui/orientation/shortsword_orientation.png";
		this.m.Type = this.Const.SkillType.Special;
		this.m.IsActive = false;
	}
	function onUpdate(_properties)
	{
		local actor = this.getContainer().getActor();
		local myTile = actor.getTile();
		for (local i = 0; i < 6; i++)
		{
			if (!myTile.hasNextTile(i)) { continue; }
			local t = myTile.getNextTile(i);
			if (!t.IsOccupiedByActor) { continue; }
			local a = t.getEntity();
			if (!a.isAlive() || !a.isAlliedWith(actor)) { continue; }
			local off = a.getItems().getItemAtSlot(this.Const.ItemSlot.Offhand);
			local hasShield = off != null && off.isItemType(this.Const.Items.ItemType.Shield);
			if (!hasShield)
			{
				_properties.MeleeDefense += 6;
				return;
			}
		}
	}
});

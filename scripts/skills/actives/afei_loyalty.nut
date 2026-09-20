this.afei_loyalty <- this.inherit("scripts/skills/skill", {
	m = {},
	function create()
	{
		this.m.ID = "actives.afei_loyalty";
		this.m.Name = "忠诚";
		this.m.Description = "距护团中心（优先可行动阿飞）两格内决心 +10。中心本轮首次被命中时，若在范围内则近防 +4 至轮末。";
		this.m.Icon = "ui/orientation/shortsword_orientation.png";
		this.m.Type = this.Const.SkillType.Special;
		this.m.IsActive = false;
	}
	function findCenter()
	{
		local actors = this.Tactical.Entities.getInstancesOfFaction(this.getContainer().getActor().getFaction());
		foreach (a in actors)
		{
			if (a.getFlags().get(::AfeiExpedition.Flags.CaptainAfei) && a.isAlive() && !a.getCurrentProperties().IsStunned)
			{
				return a;
			}
		}
		foreach (a in actors)
		{
			if (a.getFlags().get(::AfeiExpedition.Flags.ProxyCaptain) && a.isAlive())
			{
				return a;
			}
		}
		return null;
	}
	function onUpdate(_properties)
	{
		local center = this.findCenter();
		if (center == null) { return; }
		if (this.getContainer().getActor().getTile().getDistanceTo(center.getTile()) <= 2)
		{
			_properties.Bravery += 10;
		}
	}
});

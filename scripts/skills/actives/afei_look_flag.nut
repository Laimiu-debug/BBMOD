this.afei_look_flag <- this.inherit("scripts/skills/skill", {
	m = {},
	function create()
	{
		this.m.ID = "actives.afei_look_flag";
		this.m.Name = "回看旗子";
		this.m.Description = "距阿飞或代理≤3格时决心+6。";
		this.m.Icon = "ui/orientation/shortsword_orientation.png";
		this.m.Type = this.Const.SkillType.Special;
		this.m.IsActive = false;
		this.m.IsStacking = false;
	}
	function onUpdate(_properties)
	{
		
		local actor=this.getContainer().getActor();
		foreach(a in this.Tactical.Entities.getInstancesOfFaction(actor.getFaction())){
			if((a.getFlags().get(::AfeiExpedition.Flags.CaptainAfei)||a.getFlags().get(::AfeiExpedition.Flags.ProxyCaptain)) && a.getTile().getDistanceTo(actor.getTile())<=3){ _properties.Bravery+=6; return; }
		}
	}
});

this.afei_blue_guard <- this.inherit("scripts/entity/tactical/humans/militia_guest", {
	function create()
	{
		this.militia_guest.create();
		this.m.Name = "匿名蓝旗";
		this.m.Description = "蓝旗联合护送的临时同伴。战后离队，非远征团具名成员；不会顶替嘉豪或成长线。";
	}

	function onInit()
	{
		this.militia_guest.onInit();
		this.getFlags().set("afei_blue_temp", true);
		this.getFlags().set("afei_anonymous_blue", true);

		try
		{
			local agent = this.getAIAgent();
			if (agent != null && ("getProperties" in agent))
			{
				local props = agent.getProperties();
				if ("TargetPriorityFleeingMult" in props)
				{
					props.TargetPriorityFleeingMult = 0.5;
				}
			}
		}
		catch (errorAI)
		{
		}

		try
		{
			::AfeiExpedition.ensureOriginTempSkills(this);
		}
		catch (errorCap)
		{
		}
	}
});

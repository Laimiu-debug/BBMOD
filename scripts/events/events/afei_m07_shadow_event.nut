this.afei_m07_shadow_event <- this.inherit("scripts/events/event", {
	m = {},
	function create()
	{
		this.m.ID = "event.afei_m07_shadow";
		this.m.Title = "北境白影";
		this.m.Cooldown = 14.0 * this.World.getTime().SecondsPerDay;
		this.m.Screens.push({
			ID = "A",
			Text = "%terrainImage%{可选猎人传闻。接受后生成「北境白影」狩猎契约：地图上出现巢穴，进入后以野兽编制开战。可侦察离开；击败后 +800、磨合 +6、纪念章。不锁终章。}",
			Image = "",
			List = [],
			Characters = [],
			Options = [
				{
					Text = "接下猎人传闻（生成狩猎契约）",
					function getResult(_event)
					{
						this.World.Flags.set("afei_m07_pending", 1);

						if (!::AfeiExpedition.tryOfferAfeiContract(this, "scripts/contracts/contracts/afei_frost_hunt_contract", true))
						{
							return "Fail";
						}

						return "Ok";
					}
				},
				{
					Text = "侦察后离开",
					function getResult(_event)
					{
						return 0;
					}
				}
			],
			function start(_event)
			{
			}
		});
		this.m.Screens.push({
			ID = "Ok",
			Text = "%terrainImage%{白影巢穴已标在地图上。满足出战条件后前往开战。}",
			Image = "",
			List = [],
			Characters = [],
			Options = [
				{
					Text = "准备出猎。",
					function getResult(_event)
					{
						return 0;
					}
				}
			],
			function start(_event)
			{
			}
		});
		this.m.Screens.push({
			ID = "Fail",
			Text = "%terrainImage%{一时无法挂上狩猎契约。可稍后再听传闻。}",
			Image = "",
			List = [],
			Characters = [],
			Options = [
				{
					Text = "知道了。",
					function getResult(_event)
					{
						this.World.Flags.set("afei_m07_pending", 0);
						return 0;
					}
				}
			],
			function start(_event)
			{
			}
		});
	}
	function onUpdateScore()
	{
		if (!::AfeiExpedition.isAfeiOrigin())
		{
			return;
		}

		if (this.World.Flags.get(::AfeiExpedition.Flags.M07Done) || this.World.Flags.get("afei_m07_pending"))
		{
			return;
		}

		if (this.World.getTime().Days < 75)
		{
			return;
		}

		if (::AfeiExpedition.countDeployable() < 8)
		{
			return;
		}

		if (::AfeiExpedition.getRosterAvgLevelDeployable() < 7)
		{
			return;
		}

		this.m.Score = 10;
	}
	function onPrepare()
	{
	}
	function onPrepareVariables(_vars)
	{
	}
	function onClear()
	{
	}
});

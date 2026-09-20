this.afei_m07_shadow_event <- this.inherit("scripts/events/event", {
	m = {},
	function create()
	{
		this.m.ID = "event.afei_m07_shadow";
		this.m.Title = "北境白影";
		this.m.Cooldown = 14.0 * this.World.getTime().SecondsPerDay;
		this.m.Screens.push({
			ID = "A",
			Text = "%terrainImage%{可选猎人传闻：冰霜巨兽。接受后进入狩猎状态——在可出战人数≥8且平均等级≥7时，下一场战斗胜利视为击败白影（+800、磨合 +6、纪念章）。可侦察后离开；不锁终章。}",
			Image = "",
			List = [],
			Characters = [],
			Options = [
				{
					Text = "接下猎人传闻（下场达标胜利结算）",
					function getResult(_event)
					{
						this.World.Flags.set("afei_m07_pending", 1);
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
			Text = "%terrainImage%{白影已在北方现身。满足出战条件后，下一场胜利记入 M07。}",
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

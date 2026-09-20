this.afei_m04_blue_event <- this.inherit("scripts/events/event", {
	m = {},
	function create()
	{
		this.m.ID = "event.afei_m04_blue";
		this.m.Title = "蓝旗同行";
		this.m.Cooldown = 7.0 * this.World.getTime().SecondsPerDay;
		this.m.Screens.push({
			ID = "A",
			Text = "%terrainImage%{联合护送邀请。接受后进入待完成状态：下一次成功结算的有报酬契约视为蓝旗同行完成（报酬 +200、磨合 +4，开放 R08–R10）。失败可七日后重试。}",
			Image = "",
			List = [],
			Characters = [],
			Options = [
				{
					Text = "接受同行护送（完成下一份有报酬契约）",
					function getResult(_event)
					{
						this.World.Flags.set("afei_m04_pending", 1);
						return "Ok";
					}
				},
				{
					Text = "暂缓。",
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
			Text = "%terrainImage%{蓝旗已与你们约好合流。下一份有报酬契约成功结算时，记入 M04。}",
			Image = "",
			List = [],
			Characters = [],
			Options = [
				{
					Text = "上路。",
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

		if (this.World.Flags.get(::AfeiExpedition.Flags.M04Done) || this.World.Flags.get("afei_m04_pending"))
		{
			return;
		}

		if (this.World.getTime().Days < 25)
		{
			return;
		}

		if (::AfeiExpedition.getPaidContracts() < 8)
		{
			return;
		}

		this.m.Score = 35;
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

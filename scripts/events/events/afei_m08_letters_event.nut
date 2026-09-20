this.afei_m08_letters_event <- this.inherit("scripts/events/event", {
	m = {},
	function create()
	{
		this.m.ID = "event.afei_m08_letters";
		this.m.Title = "再集合一次";
		this.m.Cooldown = 99999.0 * this.World.getTime().SecondsPerDay;
		this.m.Screens.push({
			ID = "A",
			Text = "%terrainImage%{旧营地求助：补给与护送两份实约。接受后需连续成功结算两份有报酬契约；全部完成后磨合 +6，记录终章，并尝试阿飞终极觉醒。失败可七日后重试未完成部分。}",
			Image = "",
			List = [],
			Characters = [],
			Options = [
				{
					Text = "接下两份任务（契约结算推进）",
					function getResult(_event)
					{
						this.World.Flags.set("afei_m08_pending", 1);
						this.World.Flags.set("afei_m08_left", 2);
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
			Text = "%terrainImage%{两份委托已挂上名册。每成功结算一份有报酬契约，进度减一；归零时终章信件落下。}",
			Image = "",
			List = [],
			Characters = [],
			Options = [
				{
					Text = "给下一次远行写信。",
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

		if (this.World.Flags.get(::AfeiExpedition.Flags.M08Done) || this.World.Flags.get("afei_m08_pending"))
		{
			return;
		}

		if (this.World.getTime().Days < 90)
		{
			return;
		}

		if (::AfeiExpedition.getPaidContracts() < 24)
		{
			return;
		}

		if (::AfeiExpedition.countNamedEverRecruited() < 8)
		{
			return;
		}

		if (this.World.Flags.getAsInt("afei_cohesion_peak") < 60 && this.World.Flags.getAsInt("afei_cohesion") < 60)
		{
			return;
		}

		this.m.Score = 40;
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

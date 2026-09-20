this.afei_rope_train_event <- this.inherit("scripts/events/event", {
	m = {},
	function create()
	{
		this.m.ID = "event.afei_rope_train";
		this.m.Title = "绳阵训练";
		this.m.Cooldown = 1.0 * this.World.getTime().SecondsPerDay;
		this.m.Screens.push({
			ID = "A",
			Text = "%terrainImage%{月牙在营地拉起绳阵。需要 3 份食物与约两小时；距上次绳阵须满三日。}",
			Image = "",
			List = [],
			Characters = [],
			Options = [
				{
					Text = "开始训练（3 食物）",
					function getResult(_event)
					{
						if (!::AfeiExpedition.tryRopeTrain())
						{
							return "Fail";
						}

						return "Ok";
					}
				},
				{
					Text = "下次再说。",
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
			Text = "%terrainImage%{绳阵练完一轮。计数已记入成长条件。}",
			Image = "",
			List = [],
			Characters = [],
			Options = [
				{
					Text = "好。",
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
			Text = "%terrainImage%{食物不足，或距上次绳阵未满三日。}",
			Image = "",
			List = [],
			Characters = [],
			Options = [
				{
					Text = "知道了。",
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

		if (!::AfeiExpedition.hasNamed("C07"))
		{
			return;
		}

		if (this.World.Flags.get(::AfeiExpedition.Flags.GrowthDone + "C07"))
		{
			return;
		}

		this.m.Score = 12;
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

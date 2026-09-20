this.afei_m08_letters_event <- this.inherit("scripts/events/event", {
	m = {},
	function create()
	{
		this.m.ID = "event.afei_m08_letters";
		this.m.Title = "再集合一次";
		this.m.Cooldown = 99999.0 * this.World.getTime().SecondsPerDay;
		this.m.Screens.push({
			ID = "A",
			Text = "%terrainImage%{旧营地求助：先「送补给」，再「护送滞留者」——两份可开战契约，中间可休整。全部完成后磨合 +6，记录终章，并尝试阿飞终极觉醒。}",
			Image = "",
			List = [],
			Characters = [],
			Options = [
				{
					Text = "接下两份任务（先生成送补给契约）",
					function getResult(_event)
					{
						this.World.Flags.set("afei_m08_pending", 1);
						this.World.Flags.set("afei_m08_supply_done", 0);
						this.World.Flags.set("afei_m08_escort_done", 0);

						if (!::AfeiExpedition.tryOfferAfeiContract(this, "scripts/contracts/contracts/afei_m08_supply_contract", true))
						{
							return "Fail";
						}

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
			Text = "%terrainImage%{送补给契约已挂上。完成后会自动接上护送滞留者。}",
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
		this.m.Screens.push({
			ID = "Fail",
			Text = "%terrainImage%{一时无法挂上契约。条件仍在，可稍后再试。}",
			Image = "",
			List = [],
			Characters = [],
			Options = [
				{
					Text = "知道了。",
					function getResult(_event)
					{
						this.World.Flags.set("afei_m08_pending", 0);
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

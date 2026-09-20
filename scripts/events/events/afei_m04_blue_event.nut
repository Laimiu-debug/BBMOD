this.afei_m04_blue_event <- this.inherit("scripts/events/event", {
	m = {},
	function create()
	{
		this.m.ID = "event.afei_m04_blue";
		this.m.Title = "蓝旗同行";
		this.m.Cooldown = 7.0 * this.World.getTime().SecondsPerDay;
		this.m.Screens.push({
			ID = "A",
			Text = "%terrainImage%{蓝旗送来联合护送邀请。匿名护卫会与你们同行——他们不是可招的具名伙伴，也不会被写成可误杀的永久角色。\n\n接受后生成「蓝旗联合护送」契约：地图上出现伏击点，进入后开战。成功则磨合 +4，并开放川神、小虎、大鹅的邀请；失败可七日后再试。}",
			Image = "",
			List = [],
			Characters = [],
			Options = [
				{
					Text = "接受并生成护送契约",
					function getResult(_event)
					{
						this.World.Flags.set("afei_m04_pending", 1);

						if (!::AfeiExpedition.tryOfferAfeiContract(this, "scripts/contracts/contracts/afei_blue_escort_contract", true))
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
			Text = "%terrainImage%{蓝旗联合护送已挂上名册。前往地图上的伏击点开战。}",
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
		this.m.Screens.push({
			ID = "Fail",
			Text = "%terrainImage%{一时无法挂上契约（雇主或城镇未就绪）。七日后可再试。}",
			Image = "",
			List = [],
			Characters = [],
			Options = [
				{
					Text = "知道了。",
					function getResult(_event)
					{
						this.World.Flags.set("afei_m04_pending", 0);
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

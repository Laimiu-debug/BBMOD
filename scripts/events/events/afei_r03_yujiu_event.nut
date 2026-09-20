this.afei_r03_yujiu_event <- this.inherit("scripts/events/event", {
	m = {},
	function create()
	{
		this.m.ID = "event.afei_r03_yujiu";
		this.m.Title = "渡口喊停";
		this.m.Cooldown = 7.0 * this.World.getTime().SecondsPerDay;
		this.m.Screens.push({
			ID = "A",
			Text = "%terrainImage%{渡口雾里，余初九把船桨横在车前。她说可以花两小时重画路线，再谈签约——[color=#8f2525]180[/color] 克朗。}",
			Image = "ui/events/afei_portrait_c06.png",
			List = [],
			Characters = [],
			Options = [
				{
					Text = "开始演练。",
					function getResult(_event)
					{
						return "Drill";
					}
				},
				{
					Text = "先不谈。线索留着。",
					function getResult(_event)
					{
						this.World.Flags.set(::AfeiExpedition.Flags.R03Offered, 1);
						return 0;
					}
				}
			],
			function start(_event) {}
		});
		this.m.Screens.push({
			ID = "Drill",
			Text = "%terrainImage%{两边都能完成同一次入团步骤，结果不靠投点。}",
			Image = "",
			List = [],
			Characters = [],
			Options = [
				{
					Text = "承认路图画错，请她重画。",
					function getResult(_event)
					{
						return "DrillA";
					}
				},
				{
					Text = "先请她把渡口讲明白。",
					function getResult(_event)
					{
						return "DrillB";
					}
				},
				{
					Text = "今天先停。人不消失。",
					function getResult(_event)
					{
						this.World.Flags.set(::AfeiExpedition.Flags.R03Offered, 1);
						return 0;
					}
				}
			],
			function start(_event) {}
		});
		this.m.Screens.push({
			ID = "DrillA",
			Text = "%terrainImage%{新路线抄进日志。她问：下回我喊停，你还听不听？阿飞在旁边写了一个听。\n\n演练结束，告示上的数字是 [color=#8f2525]180[/color] 克朗。}",
			Image = "",
			List = [],
			Characters = [],
			Options = [
				{
					Text = "支付 180 克朗签约。",
					function getResult(_event)
					{
						if (this.World.Assets.getMoney() < 180)
						{
							return "Poor";
						}
						return "Hire";
					}
				},
				{
					Text = "先不签。告示还在。",
					function getResult(_event)
					{
						this.World.Flags.set(::AfeiExpedition.Flags.R03Offered, 1);
						return 0;
					}
				}
			],
			function start(_event)
			{
				this.List.push({ id = 10, icon = "ui/icons/special.png", text = "完成演练（选项甲）" });
			}
		});
		this.m.Screens.push({
			ID = "DrillB",
			Text = "%terrainImage%{她检查过最后一辆车，才把自己的包放上来谈签约。\n\n演练结束，告示上的数字是 [color=#8f2525]180[/color] 克朗。}",
			Image = "",
			List = [],
			Characters = [],
			Options = [
				{
					Text = "支付 180 克朗签约。",
					function getResult(_event)
					{
						if (this.World.Assets.getMoney() < 180)
						{
							return "Poor";
						}
						return "Hire";
					}
				},
				{
					Text = "先不签。告示还在。",
					function getResult(_event)
					{
						this.World.Flags.set(::AfeiExpedition.Flags.R03Offered, 1);
						return 0;
					}
				}
			],
			function start(_event)
			{
				this.List.push({ id = 10, icon = "ui/icons/special.png", text = "完成演练（选项乙）" });
			}
		});
		this.m.Screens.push({
			ID = "Hire",
			Text = "%terrainImage%{黑旗名册多了一行：余九。有人落下，她会喊停。}",
			Image = "",
			List = [],
			Characters = [],
			Options = [
				{
					Text = "欢迎入队。",
					function getResult(_event)
					{
						if (::AfeiExpedition.hasNamed("C06"))
						{
							return 0;
						}
						if (!::AfeiExpedition.tryChargeHire("C06", 180))
						{
							return "Poor";
						}

						local bro = ::AfeiExpedition.hireNamed(this, {
							Background = "afei_yujiu_background",
							Name = "余初九",
							Title = "余九",
							NamedId = "C06",
							Attrs = [70, 118, 58, 110, 60, 35, 14, 8],
							Wage = 20,
							Place = 5,
							Skills = ["afei_dog_bark", "afei_loyalty", "afei_guard_swap"]
						});
						local talents = bro.getTalents();
						talents.resize(this.Const.Attributes.COUNT, 0);
						for (local i = 0; i < this.Const.Attributes.COUNT; i++) { talents[i] = 0; }
						talents[this.Const.Attributes.Fatigue] = 3;
						talents[this.Const.Attributes.Bravery] = 3;
						talents[this.Const.Attributes.MeleeDefense] = 3;
						bro.getSkills().update();
						this.World.Flags.set(::AfeiExpedition.Flags.R03Done, 1);
						this.World.Flags.set(::AfeiExpedition.Flags.R03Offered, 1);
						return 0;
					}
				}
			],
			function start(_event)
			{
				this.List.push({ id = 10, icon = "ui/icons/asset_money.png", text = "支付 [color=#8f2525]180[/color] 克朗签约费" });
			}
		});
		this.m.Screens.push({
			ID = "Poor",
			Text = "%terrainImage%{袋里的克朗不够。线索留着，人不消失。}",
			Image = "",
			List = [],
			Characters = [],
			Options = [{
				Text = "先攒够钱。",
				function getResult(_event)
				{
					this.World.Flags.set(::AfeiExpedition.Flags.R03Offered, 1);
					return 0;
				}
			}],
			function start(_event) {}
		});
	}

	function onUpdateScore()
	{
		if (!::AfeiExpedition.isAfeiOrigin()) { return; }
		if (this.World.Flags.get(::AfeiExpedition.Flags.R03Done)) { return; }
		if (::AfeiExpedition.hasNamed("C06")) { return; }
		if (this.World.getTime().Days < 6) { return; }
		if (::AfeiExpedition.getPaidContracts() < 3) { return; }
		if (this.World.getPlayerRoster().getSize() >= this.World.Assets.getBrothersMax()) { return; }
		this.m.Score = this.World.Flags.get(::AfeiExpedition.Flags.R03Offered) ? 20 : 40;
	}

	function onPrepare() {}
	function onPrepareVariables(_vars) {}
	function onClear() {}
});

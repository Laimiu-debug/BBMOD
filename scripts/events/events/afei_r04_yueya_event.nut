this.afei_r04_yueya_event <- this.inherit("scripts/events/event", {
	m = {},
	function create()
	{
		this.m.ID = "event.afei_r04_yueya";
		this.m.Title = "超市投掷";
		this.m.Cooldown = 7.0 * this.World.getTime().SecondsPerDay;
		this.m.Screens.push({
			ID = "A",
			Text = "%terrainImage%{招牌很大的小货摊边，小月牙说可以花 3 食物与两小时做投掷练习，再付 [color=#8f2525]180[/color] 克朗签约。}",
			Image = "ui/events/afei_portrait_c07.png",
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
						this.World.Flags.set(::AfeiExpedition.Flags.R04Offered, 1);
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
					Text = "陪她换靶练习。",
					function getResult(_event)
					{

						if (!::AfeiExpedition.trySpendFoodApprox(3))
						{
							return "NoFood";
						}
						return "DrillA";
					}
				},
				{
					Text = "让她演示绳阵。",
					function getResult(_event)
					{
						local day = this.World.getTime().Days;
						local last = this.World.Flags.getAsInt("afei_rope_train_day");

						if (last > 0 && day - last < 3)
						{
							return "NoFood";
						}

						if (!::AfeiExpedition.trySpendFoodApprox(3))
						{
							return "NoFood";
						}

						::AfeiExpedition.recordRopeTrain();
						return "DrillB";
					}
				},
				{
					Text = "今天先停。人不消失。",
					function getResult(_event)
					{
						this.World.Flags.set(::AfeiExpedition.Flags.R04Offered, 1);
						return 0;
					}
				}
			],
			function start(_event) {}
		});
		this.m.Screens.push({
			ID = "DrillA",
			Text = "%terrainImage%{第一枪扎在地上，她改投另一面正好打中。三根捡回来：午饭后还能练。消耗 3 食物。\n\n演练结束，告示上的数字是 [color=#8f2525]180[/color] 克朗。}",
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
						this.World.Flags.set(::AfeiExpedition.Flags.R04Offered, 1);
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
			Text = "%terrainImage%{歪棚子用短绳固定好。练习结束，摊位托给旧相识，牌缩成一片挂在包上。消耗 3 食物。\n\n演练结束，告示上的数字是 [color=#8f2525]180[/color] 克朗。}",
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
						this.World.Flags.set(::AfeiExpedition.Flags.R04Offered, 1);
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
			Text = "%terrainImage%{黑旗名册多了一行：月牙。先别扔，她觉得还能这么用。}",
			Image = "",
			List = [],
			Characters = [],
			Options = [
				{
					Text = "欢迎入队。",
					function getResult(_event)
					{
						if (::AfeiExpedition.hasNamed("C07"))
						{
							return 0;
						}
						if (!::AfeiExpedition.tryChargeHire("C07", 180))
						{
							return "Poor";
						}

						local bro = ::AfeiExpedition.hireNamed(this, {
							Background = "afei_yueya_background",
							Name = "小月牙",
							Title = "月牙",
							NamedId = "C07",
							Attrs = [50, 92, 34, 120, 42, 51, 1, 6],
							Wage = 10,
							Place = 15,
							Skills = ["afei_supermarket", "afei_biantai", "afei_optimist"]
						});
						local talents = bro.getTalents();
						talents.resize(this.Const.Attributes.COUNT, 0);
						for (local i = 0; i < this.Const.Attributes.COUNT; i++) { talents[i] = 0; }
						talents[this.Const.Attributes.Hitpoints] = 1;
						talents[this.Const.Attributes.Initiative] = 3;
						talents[this.Const.Attributes.RangedSkill] = 2;
						bro.getSkills().update();
						this.World.Flags.set(::AfeiExpedition.Flags.R04Done, 1);
						this.World.Flags.set(::AfeiExpedition.Flags.R04Offered, 1);
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
					this.World.Flags.set(::AfeiExpedition.Flags.R04Offered, 1);
					return 0;
				}
			}],
			function start(_event) {}
		});

		this.m.Screens.push({
			ID = "NoFood",
			Text = "%terrainImage%{营地食物不够练习（需要约 3 份补给）。线索留着，人不消失。}",
			Image = "",
			List = [],
			Characters = [],
			Options = [{
				Text = "先去补给。",
				function getResult(_event)
				{
					this.World.Flags.set(::AfeiExpedition.Flags.R04Offered, 1);
					return 0;
				}
			}],
			function start(_event) {}
		});
	}

	function onUpdateScore()
	{
		if (!::AfeiExpedition.isAfeiOrigin()) { return; }
		if (this.World.Flags.get(::AfeiExpedition.Flags.R04Done)) { return; }
		if (::AfeiExpedition.hasNamed("C07")) { return; }
		if (this.World.getTime().Days < 8) { return; }
		if (::AfeiExpedition.getPaidContracts() < 4) { return; }
		if (this.World.getPlayerRoster().getSize() >= this.World.Assets.getBrothersMax()) { return; }
		this.m.Score = this.World.Flags.get(::AfeiExpedition.Flags.R04Offered) ? 20 : 40;
	}

	function onPrepare() {}
	function onPrepareVariables(_vars) {}
	function onClear() {}
});

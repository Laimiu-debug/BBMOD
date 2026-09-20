this.afei_r05_xiaoyu_event <- this.inherit("scripts/events/event", {
	m = {},
	function create()
	{
		this.m.ID = "event.afei_r05_xiaoyu";
		this.m.Title = "栈桥接应";
		this.m.Cooldown = 7.0 * this.World.getTime().SecondsPerDay;
		this.m.Screens.push({
			ID = "A",
			Text = "%terrainImage%{短栈桥外侧，小鱼贝壳已把自己的盾立过去。她要先确认你们做过有报酬的短途搬运（已计入契约计数），再花时间检查掩护，然后付 [color=#8f2525]240[/color] 克朗。}",
			Image = "ui/events/afei_portrait_c08.png",
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
						this.World.Flags.set(::AfeiExpedition.Flags.R05Offered, 1);
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
					Text = "轮流过狭窄栈桥，检查掩护。",
					function getResult(_event)
					{
						return "DrillA";
					}
				},
				{
					Text = "让她示范顶上去的站位。",
					function getResult(_event)
					{
						return "DrillB";
					}
				},
				{
					Text = "今天先停。人不消失。",
					function getResult(_event)
					{
						this.World.Flags.set(::AfeiExpedition.Flags.R05Offered, 1);
						return 0;
					}
				}
			],
			function start(_event) {}
		});
		this.m.Screens.push({
			ID = "DrillA",
			Text = "%terrainImage%{谁需要哪一侧掩护，她都记下来。她不是雇来永远替人吃刀的。\n\n演练结束，告示上的数字是 [color=#8f2525]240[/color] 克朗。}",
			Image = "",
			List = [],
			Characters = [],
			Options = [
				{
					Text = "支付 240 克朗签约。",
					function getResult(_event)
					{
						if (this.World.Assets.getMoney() < 240)
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
						this.World.Flags.set(::AfeiExpedition.Flags.R05Offered, 1);
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
			Text = "%terrainImage%{盾带扣好。谈签约时，她只要求排守卫班次的人也去外侧站一次。\n\n演练结束，告示上的数字是 [color=#8f2525]240[/color] 克朗。}",
			Image = "",
			List = [],
			Characters = [],
			Options = [
				{
					Text = "支付 240 克朗签约。",
					function getResult(_event)
					{
						if (this.World.Assets.getMoney() < 240)
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
						this.World.Flags.set(::AfeiExpedition.Flags.R05Offered, 1);
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
			Text = "%terrainImage%{黑旗名册多了一行：小鱼。换过来，这一下她接。}",
			Image = "",
			List = [],
			Characters = [],
			Options = [
				{
					Text = "欢迎入队。",
					function getResult(_event)
					{
						if (::AfeiExpedition.hasNamed("C08"))
						{
							return 0;
						}
						if (!::AfeiExpedition.tryChargeHire("C08", 240))
						{
							return "Poor";
						}

						local bro = ::AfeiExpedition.hireNamed(this, {
							Background = "afei_xiaoyu_background",
							Name = "小鱼贝壳",
							Title = "小鱼",
							NamedId = "C08",
							Attrs = [62, 108, 47, 96, 54, 30, 7, 1],
							Wage = 12,
							Place = 2,
							Skills = ["afei_only_man", "afei_nicotine", "afei_cover_up"]
						});
						local talents = bro.getTalents();
						talents.resize(this.Const.Attributes.COUNT, 0);
						for (local i = 0; i < this.Const.Attributes.COUNT; i++) { talents[i] = 0; }
						talents[this.Const.Attributes.Hitpoints] = 1;
						talents[this.Const.Attributes.Fatigue] = 2;
						talents[this.Const.Attributes.MeleeDefense] = 3;
						bro.getSkills().update();
						this.World.Flags.set(::AfeiExpedition.Flags.R05Done, 1);
						this.World.Flags.set(::AfeiExpedition.Flags.R05Offered, 1);
						return 0;
					}
				}
			],
			function start(_event)
			{
				this.List.push({ id = 10, icon = "ui/icons/asset_money.png", text = "支付 [color=#8f2525]240[/color] 克朗签约费" });
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
					this.World.Flags.set(::AfeiExpedition.Flags.R05Offered, 1);
					return 0;
				}
			}],
			function start(_event) {}
		});
	}

	function onUpdateScore()
	{
		if (!::AfeiExpedition.isAfeiOrigin()) { return; }
		if (this.World.Flags.get(::AfeiExpedition.Flags.R05Done)) { return; }
		if (::AfeiExpedition.hasNamed("C08")) { return; }
		if (this.World.getTime().Days < 10) { return; }
		if (::AfeiExpedition.getPaidContracts() < 5) { return; }
		if (this.World.getPlayerRoster().getSize() >= this.World.Assets.getBrothersMax()) { return; }
		this.m.Score = this.World.Flags.get(::AfeiExpedition.Flags.R05Offered) ? 20 : 40;
	}

	function onPrepare() {}
	function onPrepareVariables(_vars) {}
	function onClear() {}
});

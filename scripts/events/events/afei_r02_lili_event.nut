this.afei_r02_lili_event <- this.inherit("scripts/events/event", {
	m = {},
	function create()
	{
		this.m.ID = "event.afei_r02_lili";
		this.m.Title = "超巨试射";
		this.m.Cooldown = 7.0 * this.World.getTime().SecondsPerDay;
		this.m.Screens.push({
			ID = "A",
			Text = "%terrainImage%{夜市散场后，李李还在收那把叫超巨的高背椅。她说可以花两小时安全试射，再谈签约——告示 [color=#8f2525]240[/color] 克朗。不判随机成败。}",
			Image = "ui/events/afei_portrait_c05.png",
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
						this.World.Flags.set(::AfeiExpedition.Flags.R02Offered, 1);
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
					Text = "等她收完最后一件，再一起试射。",
					function getResult(_event)
					{
						return "DrillA";
					}
				},
				{
					Text = "先安排试射，东西她自己收。",
					function getResult(_event)
					{
						return "DrillB";
					}
				},
				{
					Text = "今天先停。人不消失。",
					function getResult(_event)
					{
						this.World.Flags.set(::AfeiExpedition.Flags.R02Offered, 1);
						return 0;
					}
				}
			],
			function start(_event) {}
		});
		this.m.Screens.push({
			ID = "DrillA",
			Text = "%terrainImage%{椅子收好了。前两箭偏了，第三箭擦中靶边。她问下一轮什么时候开始。\n\n演练结束，告示上的数字是 [color=#8f2525]240[/color] 克朗。}",
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
						this.World.Flags.set(::AfeiExpedition.Flags.R02Offered, 1);
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
			Text = "%terrainImage%{靶边多了一只裹好弦的旧猎弓。试射结束，她愿意谈告示上的数字。\n\n演练结束，告示上的数字是 [color=#8f2525]240[/color] 克朗。}",
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
						this.World.Flags.set(::AfeiExpedition.Flags.R02Offered, 1);
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
			Text = "%terrainImage%{黑旗名册多了一行：超巨。灯先别撤。}",
			Image = "",
			List = [],
			Characters = [],
			Options = [
				{
					Text = "欢迎入队。",
					function getResult(_event)
					{
						if (::AfeiExpedition.hasNamed("C05"))
						{
							return 0;
						}
						if (!::AfeiExpedition.tryChargeHire("C05", 240))
						{
							return "Poor";
						}

						local bro = ::AfeiExpedition.hireNamed(this, {
							Background = "afei_lili_background",
							Name = "李李超欧",
							Title = "超巨",
							NamedId = "C05",
							Attrs = [58, 102, 38, 122, 45, 58, 8, 12],
							Wage = 20,
							Place = 14,
							Skills = ["afei_unselectable", "afei_chaoju", "afei_ouqi"]
						});
						local talents = bro.getTalents();
						talents.resize(this.Const.Attributes.COUNT, 0);
						for (local i = 0; i < this.Const.Attributes.COUNT; i++) { talents[i] = 0; }
						talents[this.Const.Attributes.Bravery] = 3;
						talents[this.Const.Attributes.Initiative] = 3;
						talents[this.Const.Attributes.RangedSkill] = 3;
						bro.getSkills().update();
						this.World.Flags.set(::AfeiExpedition.Flags.R02Done, 1);
						this.World.Flags.set(::AfeiExpedition.Flags.R02Offered, 1);
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
					this.World.Flags.set(::AfeiExpedition.Flags.R02Offered, 1);
					return 0;
				}
			}],
			function start(_event) {}
		});
	}

	function onUpdateScore()
	{
		if (!::AfeiExpedition.isAfeiOrigin()) { return; }
		if (this.World.Flags.get(::AfeiExpedition.Flags.R02Done)) { return; }
		if (::AfeiExpedition.hasNamed("C05")) { return; }
		if (this.World.getTime().Days < 4) { return; }
		if (::AfeiExpedition.getPaidContracts() < 2) { return; }
		if (this.World.getPlayerRoster().getSize() >= this.World.Assets.getBrothersMax()) { return; }
		this.m.Score = this.World.Flags.get(::AfeiExpedition.Flags.R02Offered) ? 20 : 40;
	}

	function onPrepare() {}
	function onPrepareVariables(_vars) {}
	function onClear() {}
});

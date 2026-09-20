this.afei_r06_shuaizi_event <- this.inherit("scripts/events/event", {
	m = {},
	function create()
	{
		this.m.ID = "event.afei_r06_shuaizi";
		this.m.Title = "守门鼓点";
		this.m.Cooldown = 7.0 * this.World.getTime().SecondsPerDay;
		this.m.Screens.push({
			ID = "A",
			Text = "%terrainImage%{门柱边，白小帅子手已经在盾沿上敲拍子。他说可以做两小时守门演练，再谈 [color=#8f2525]240[/color] 克朗——不能只靠一句胆子大一点。}",
			Image = "",
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
						this.World.Flags.set(::AfeiExpedition.Flags.R06Offered, 1);
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
					Text = "安排守门两侧的搭档。",
					function getResult(_event)
					{
						return "DrillA";
					}
				},
				{
					Text = "让大谋把两面盾搭在门边试站。",
					function getResult(_event)
					{
						return "DrillB";
					}
				},
				{
					Text = "今天先停。人不消失。",
					function getResult(_event)
					{
						this.World.Flags.set(::AfeiExpedition.Flags.R06Offered, 1);
						return 0;
					}
				}
			],
			function start(_event) {}
		});
		this.m.Screens.push({
			ID = "DrillA",
			Text = "%terrainImage%{四拍走一车，八拍再开另一边。他确认站位以后才肯谈签约钱。\n\n演练结束，告示上的数字是 [color=#8f2525]240[/color] 克朗。}",
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
						this.World.Flags.set(::AfeiExpedition.Flags.R06Offered, 1);
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
			Text = "%terrainImage%{他说这和战场不一样，手却没停。演练结束。\n\n演练结束，告示上的数字是 [color=#8f2525]240[/color] 克朗。}",
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
						this.World.Flags.set(::AfeiExpedition.Flags.R06Offered, 1);
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
			Text = "%terrainImage%{黑旗名册多了一行：帅子。四下以后再走。}",
			Image = "",
			List = [],
			Characters = [],
			Options = [
				{
					Text = "欢迎入队。",
					function getResult(_event)
					{
						if (::AfeiExpedition.hasNamed("C09"))
						{
							return 0;
						}
						if (!::AfeiExpedition.tryChargeHire("C09", 240))
						{
							return "Poor";
						}

						local bro = ::AfeiExpedition.hireNamed(this, {
							Background = "afei_shuaizi_background",
							Name = "白小帅子",
							Title = "帅子",
							NamedId = "C09",
							Attrs = [65, 100, 26, 90, 49, 28, 8, 2],
							Wage = 12,
							Place = 1,
							Skills = ["afei_small_heart", "afei_drum", "afei_guard_gate"]
						});
						local talents = bro.getTalents();
						talents.resize(this.Const.Attributes.COUNT, 0);
						for (local i = 0; i < this.Const.Attributes.COUNT; i++) { talents[i] = 0; }
						talents[this.Const.Attributes.Hitpoints] = 2;
						talents[this.Const.Attributes.Bravery] = 1;
						talents[this.Const.Attributes.MeleeDefense] = 3;
						bro.getSkills().update();
						this.World.Flags.set(::AfeiExpedition.Flags.R06Done, 1);
						this.World.Flags.set(::AfeiExpedition.Flags.R06Offered, 1);
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
					this.World.Flags.set(::AfeiExpedition.Flags.R06Offered, 1);
					return 0;
				}
			}],
			function start(_event) {}
		});
	}

	function onUpdateScore()
	{
		if (!::AfeiExpedition.isAfeiOrigin()) { return; }
		if (this.World.Flags.get(::AfeiExpedition.Flags.R06Done)) { return; }
		if (::AfeiExpedition.hasNamed("C09")) { return; }
		if (this.World.getTime().Days < 12) { return; }
		if (::AfeiExpedition.getPaidContracts() < 6) { return; }
		if (this.World.getPlayerRoster().getSize() >= this.World.Assets.getBrothersMax()) { return; }
		this.m.Score = this.World.Flags.get(::AfeiExpedition.Flags.R06Offered) ? 20 : 40;
	}

	function onPrepare() {}
	function onPrepareVariables(_vars) {}
	function onClear() {}
});

this.afei_r01_bottle_event <- this.inherit("scripts/events/event", {
	m = {},
	function create()
	{
		this.m.ID = "event.afei_r01_bottle";
		this.m.Title = "瓶队来信";
		this.m.Cooldown = 99999.0 * this.World.getTime().SecondsPerDay;
		this.m.Screens.push({
			ID = "A",
			Text = "%terrainImage%{烟港泥地的气味还没散尽，小酒瓶已经站在车边。他说可以花两小时演练两人配合，再谈签约——告示上的数字是 [color=#8f2525]200[/color] 克朗。\n\n大谋拍了拍矛杆：你可以接应他，也可以让他跟匿名伙伴对练。结果不靠投点。}",
			Image = "",
			List = [],
			Characters = [],
			Options = [
				{
					Text = "支付 200 克朗，签下小酒瓶。",
					function getResult(_event)
					{
						if (this.World.Assets.getMoney() < 200)
						{
							return "Poor";
						}

						return "Hire";
					}

				},
				{
					Text = "先不签。线索留着。",
					function getResult(_event)
					{
						this.World.Flags.set(::AfeiExpedition.Flags.R01Offered, 1);
						return 0;
					}

				}
			],
			function start(_event)
			{
			}

		});
		this.m.Screens.push({
			ID = "Hire",
			Text = "%terrainImage%{两小时后，小酒瓶自己问了签约费。阿飞把告示上的数字指给他看。黑旗名册多了一行：瓶队。}",
			Image = "",
			List = [],
			Characters = [],
			Options = [
				{
					Text = "欢迎入队。",
					function getResult(_event)
					{
						this.World.Assets.addMoney(-200);
						local bro = this.World.getPlayerRoster().create("scripts/entity/tactical/player");
						bro.setStartValuesEx([
							"afei_bottle_background"
						]);
						bro.setName("小酒瓶");
						bro.setTitle("瓶队");
						bro.getSkills().add(this.new("scripts/skills/special/afei_named_brother"));
						local b = bro.getBaseProperties();
						// Stage-1 placeholder stats; align to setting page when implementing full C04.
						b.Hitpoints = 55;
						b.Stamina = 100;
						b.Bravery = 40;
						b.Initiative = 100;
						b.MeleeSkill = 55;
						b.RangedSkill = 25;
						b.MeleeDefense = 5;
						b.RangedDefense = 0;
						bro.getSkills().update();
						bro.m.Level = 1;
						bro.m.DailyWage = 10;
						bro.setPlaceInFormation(4);
						this.World.Flags.set(::AfeiExpedition.Flags.R01Done, 1);
						return 0;
					}

				}
			],
			function start(_event)
			{
				this.List.push({
					id = 10,
					icon = "ui/icons/asset_money.png",
					text = "支付 [color=#8f2525]200[/color] 克朗签约费"
				});
			}

		});
		this.m.Screens.push({
			ID = "Poor",
			Text = "%terrainImage%{袋里的克朗不够。小酒瓶耸耸肩：告示还在，人也不急着消失。}",
			Image = "",
			List = [],
			Characters = [],
			Options = [
				{
					Text = "先攒够钱。",
					function getResult(_event)
					{
						this.World.Flags.set(::AfeiExpedition.Flags.R01Offered, 1);
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

		if (this.World.Flags.get(::AfeiExpedition.Flags.R01Done))
		{
			return;
		}

		if (this.World.getTime().Days < 2)
		{
			return;
		}

		if (::AfeiExpedition.getPaidContracts() < 1)
		{
			return;
		}

		if (this.World.getPlayerRoster().getSize() >= this.World.Assets.getBrothersMax())
		{
			return;
		}

		this.m.Score = 50;
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

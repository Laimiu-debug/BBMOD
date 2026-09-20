this.afei_r01_bottle_event <- this.inherit("scripts/events/event", {
	m = {
		HasDamou = false
	},
	function create()
	{
		this.m.ID = "event.afei_r01_bottle";
		this.m.Title = "瓶队来信";
		this.m.Cooldown = 7.0 * this.World.getTime().SecondsPerDay;
		this.m.Screens.push({
			ID = "A",
			Text = "%terrainImage%{烟港泥地的气味还没散尽，小酒瓶已经站在车边。他说可以花两小时演练两人配合，再谈签约——告示上的数字是 [color=#8f2525]200[/color] 克朗。\n\n大谋拍了拍矛杆：你可以让我接应他，也可以让他跟匿名试训伙伴对练。结果不靠投点。}",
			Image = "",
			List = [],
			Characters = [],
			Options = [
				{
					Text = "开始两小时演练。",
					function getResult(_event)
					{
						return "Drill";
					}

				},
				{
					Text = "先不谈。线索留着。",
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
			ID = "Drill",
			Text = "%terrainImage%{场地空了出来。小酒瓶已经在活动肩甲。阿飞问：谁来当第一个接应？}",
			Image = "",
			List = [],
			Characters = [],
			Options = [
				{
					Text = "让大谋顶靶架接应。",
					function getResult(_event)
					{
						if (_event.m.HasDamou)
						{
							return "DrillDamou";
						}

						return "DrillAnon";
					}

				},
				{
					Text = "用匿名试训伙伴完成配合。",
					function getResult(_event)
					{
						return "DrillAnon";
					}

				},
				{
					Text = "今天先停。人不消失。",
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
			ID = "DrillDamou",
			Text = "%terrainImage%{大谋先顶住靶架，瓶队从侧面挤出一条路。结束时三个人还站在同一片场地里——没有人被撞到需要付钱修告示。\n\n两小时到了。小酒瓶自己问了签约费。}",
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
					Text = "先不签。告示还在。",
					function getResult(_event)
					{
						this.World.Flags.set(::AfeiExpedition.Flags.R01Offered, 1);
						return 0;
					}

				}
			],
			function start(_event)
			{
				this.List.push({
					id = 10,
					icon = "ui/icons/special.png",
					text = "完成两小时配合演练（大谋接应）"
				});
			}

		});
		this.m.Screens.push({
			ID = "DrillAnon",
			Text = "%terrainImage%{匿名伙伴顶住木架，阿飞故意把「球」传慢了一拍。瓶队已经跑出去，又折回来接住。这一回没有人只顾证明自己能站着。\n\n两小时到了。小酒瓶自己问了签约费。}",
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
					Text = "先不签。告示还在。",
					function getResult(_event)
					{
						this.World.Flags.set(::AfeiExpedition.Flags.R01Offered, 1);
						return 0;
					}

				}
			],
			function start(_event)
			{
				this.List.push({
					id = 10,
					icon = "ui/icons/special.png",
					text = "完成两小时配合演练（匿名接应）"
				});
			}

		});
		this.m.Screens.push({
			ID = "Hire",
			Text = "%terrainImage%{阿飞把告示上的数字指给他看。黑旗名册多了一行：瓶队。}",
			Image = "",
			List = [],
			Characters = [],
			Options = [
				{
					Text = "欢迎入队。",
					function getResult(_event)
					{
						if (!::AfeiExpedition.tryChargeHire("C04", 200))
						{
							return "Poor";
						}

						local bro = this.World.getPlayerRoster().create("scripts/entity/tactical/player");
						bro.setStartValuesEx([
							"afei_bottle_background"
						]);
						bro.setName("小酒瓶");
						bro.setTitle("瓶队");
						bro.getFlags().set(::AfeiExpedition.Flags.NamedId, "C04");
						bro.getSkills().add(this.new("scripts/skills/special/afei_named_brother"));
						bro.getSkills().add(this.new("scripts/skills/actives/afei_cohesion_rule"));
						local b = bro.getBaseProperties();
						// C04 五人大哥 · 9 星晚游向
						b.Hitpoints = 75;
						b.Stamina = 118;
						b.Bravery = 48;
						b.Initiative = 120;
						b.MeleeSkill = 72;
						b.RangedSkill = 32;
						b.MeleeDefense = 10;
						b.RangedDefense = 4;
						local talents = bro.getTalents();
						talents.resize(this.Const.Attributes.COUNT, 0);

						for (local i = 0; i < this.Const.Attributes.COUNT; i++)
						{
							talents[i] = 0;
						}

						talents[this.Const.Attributes.Fatigue] = 3;
						talents[this.Const.Attributes.Initiative] = 3;
						talents[this.Const.Attributes.MeleeSkill] = 3;
						bro.getSkills().update();
						bro.m.Level = 1;
						bro.m.XP = this.Const.LevelXP[0];
						bro.m.LevelUps = 0;
						bro.m.DailyWage = 24;
						bro.setPlaceInFormation(4);
						bro.getSkills().add(this.new("scripts/skills/actives/afei_bottle_breakthrough"));
						bro.getSkills().add(this.new("scripts/skills/actives/afei_teammate_ball"));
						bro.getSkills().add(this.new("scripts/skills/actives/afei_finals_moment"));
						::AfeiExpedition.markEverRecruited("C04");
						this.World.Flags.set(::AfeiExpedition.Flags.R01Done, 1);
						this.World.Flags.set(::AfeiExpedition.Flags.R01Offered, 1);
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

		// 已拒绝/缺钱后仍可再遇（冷却 7 日）；满员不暗中消失
		this.m.Score = this.World.Flags.get(::AfeiExpedition.Flags.R01Offered) ? 25 : 50;
	}

	function onPrepare()
	{
		this.m.HasDamou = false;
		local roster = this.World.getPlayerRoster().getAll();

		foreach (bro in roster)
		{
			if (bro.getFlags().get(::AfeiExpedition.Flags.NamedId) == "C03" || bro.getNameOnly() == "王大谋")
			{
				this.m.HasDamou = true;
				break;
			}
		}
	}

	function onPrepareVariables(_vars)
	{
	}

	function onClear()
	{
		this.m.HasDamou = false;
	}

});

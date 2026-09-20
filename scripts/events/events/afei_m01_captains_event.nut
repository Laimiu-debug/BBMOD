this.afei_m01_captains_event <- this.inherit("scripts/events/event", {
	m = {
		Afei = null,
		Mocha = null,
		Damou = null
	},
	function create()
	{
		this.m.ID = "event.afei_m01_captains";
		this.m.Title = "三个队长先上路";
		this.m.Cooldown = 99999.0 * this.World.getTime().SecondsPerDay;
		this.m.Screens.push({
			ID = "A",
			Text = "%terrainImage%{烟港酒馆里，阿飞把团约按在桌上签字。抹茶用旧尺量完旗布，又量了量口粮能撑几天。王大谋检查车轮与箱扣，说：先把第一段路走出去。\n\n雇主托付的那本账还在抹茶手里——送到邻镇即可，报酬 [color=#8f2525]180[/color] 克朗，路上不必硬闯。拒绝也无妨，之后用普通有报酬契约同样能打开招募节奏。}",
			Image = "",
			List = [],
			Characters = [],
			Options = [
				{
					Text = "接安全送账，先把账送到。",
					function getResult(_event)
					{
						return "B";
					}

				},
				{
					Text = "先不接。我们用普通契约开路。",
					function getResult(_event)
					{
						return "C";
					}

				}
			],
			function start(_event)
			{
				this.Characters.push(_event.m.Afei.getImagePath());
				this.Characters.push(_event.m.Mocha.getImagePath());
			}

		});
		this.m.Screens.push({
			ID = "B",
			Text = "%terrainImage%{抹茶把账本夹进行囊。阿飞把路线又念了一遍，大谋扛起箱子。安全送账计作一份有报酬契约，且只此一次。}",
			Image = "",
			List = [],
			Characters = [],
			Options = [
				{
					Text = "出发。",
					function getResult(_event)
					{
						this.World.Assets.addMoney(180);
						::AfeiExpedition.addPaidContract(1);
						this.World.Flags.set(::AfeiExpedition.Flags.SafeDeliveryDone, 1);
						this.World.Flags.set(::AfeiExpedition.Flags.M01Done, 1);
						return 0;
					}

				}
			],
			function start(_event)
			{
				this.List.push({
					id = 10,
					icon = "ui/icons/asset_money.png",
					text = "获得 [color=#8f2525]180[/color] 克朗（安全送账）"
				});
			}

		});
		this.m.Screens.push({
			ID = "C",
			Text = "%terrainImage%{阿飞把告示叠好。抹茶点头：普通契约结算成功，一样算进招募门槛。黑旗名册仍只有三行。}",
			Image = "",
			List = [],
			Characters = [],
			Options = [
				{
					Text = "出城。",
					function getResult(_event)
					{
						this.World.Flags.set(::AfeiExpedition.Flags.M01Done, 1);
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

		if (this.World.Flags.get(::AfeiExpedition.Flags.M01Done))
		{
			return;
		}

		if (this.World.getTime().Days > 2)
		{
			return;
		}

		local brothers = this.World.getPlayerRoster().getAll();
		local afei;
		local mocha;
		local damou;

		foreach (bro in brothers)
		{
			if (bro.getFlags().get(::AfeiExpedition.Flags.CaptainAfei))
			{
				afei = bro;
			}
			else if (bro.getBackground().getID() == "background.afei_mocha")
			{
				mocha = bro;
			}
			else if (bro.getBackground().getID() == "background.afei_damou")
			{
				damou = bro;
			}
		}

		if (afei == null || mocha == null || damou == null)
		{
			return;
		}

		this.m.Afei = this.WeakTableRef(afei);
		this.m.Mocha = this.WeakTableRef(mocha);
		this.m.Damou = this.WeakTableRef(damou);
		this.m.Score = 5000;
	}

	function onPrepare()
	{
	}

	function onPrepareVariables(_vars)
	{
	}

	function onClear()
	{
		this.m.Afei = null;
		this.m.Mocha = null;
		this.m.Damou = null;
	}

});

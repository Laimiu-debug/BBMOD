this.afei_expedition_intro_event <- this.inherit("scripts/events/event", {
	m = {},
	function create()
	{
		this.m.ID = "event.afei_expedition_scenario_intro";
		this.m.IsSpecial = true;
		this.m.Screens.push({
			ID = "A",
			Text = "[img]gfx/ui/events/afei_portrait_c01.png[/img]{烟港酒馆里，阿飞把团约按在桌上签字。抹茶用旧尺量完旗布与口粮，王大谋检查车轮与箱扣。\n\n雇主托付的账本还在抹茶手里——送到邻近友好城镇即可，报酬 [color=#8f2525]180[/color] 克朗，不生成强制战斗。拒绝也无妨，之后用普通有报酬契约同样能打开招募节奏。黑旗名册此刻只有三行。}",
			Image = "ui/events/afei_portrait_c01.png",
			Banner = "",
			List = [],
			Characters = [],
			Options = [
				{
					Text = "接安全送账，先把账送到邻镇。",
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
				this.Banner = "ui/banners/" + this.World.Assets.getBanner() + "s.png";
			}

		});
		this.m.Screens.push({
			ID = "B",
			Text = "[img]gfx/ui/events/event_65.png[/img]{抹茶把账本夹进行囊。阿飞把路线又念了一遍，大谋扛起箱子。\n\n[color=#bcad8c]安全送账已接取：[/color] 进入一座与开局不同的友好城镇即可交付。计作一份有报酬契约，且只此一次。路上仍可自由接普通任务。\n\n[color=#8f2525]说明：[/color] 阶段 1 以「进镇结算」近似真实送货契约；完整契约类接入留待后续。}",
			Image = "",
			List = [],
			Characters = [],
			Options = [
				{
					Text = "出发。",
					function getResult(_event)
					{
						this.World.Flags.set(::AfeiExpedition.Flags.SafeDeliveryActive, 1);
						this.World.Flags.set(::AfeiExpedition.Flags.SafeDeliveryDone, 0);
						this.World.Flags.set(::AfeiExpedition.Flags.M01Done, 1);
						return 0;
					}

				}
			],
			function start(_event)
			{
				this.List.push({
					id = 10,
					icon = "ui/icons/special.png",
					text = "已接取安全送账（邻镇交付 · 180 克朗）"
				});
			}

		});
		this.m.Screens.push({
			ID = "C",
			Text = "[img]gfx/ui/events/event_65.png[/img]{阿飞把告示叠好。抹茶点头：普通契约结算成功，一样算进招募门槛。}",
			Image = "",
			List = [],
			Characters = [],
			Options = [
				{
					Text = "出城。",
					function getResult(_event)
					{
						this.World.Flags.set(::AfeiExpedition.Flags.SafeDeliveryActive, 0);
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
		return;
	}

	function onPrepare()
	{
		this.m.Title = "三个队长先上路";
	}

	function onPrepareVariables(_vars)
	{
	}

	function onClear()
	{
	}

});

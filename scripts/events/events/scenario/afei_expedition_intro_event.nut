this.afei_expedition_intro_event <- this.inherit("scripts/events/event", {
	m = {},
	function create()
	{
		this.m.ID = "event.afei_expedition_scenario_intro";
		this.m.IsSpecial = true;
		this.m.Screens.push({
			ID = "A",
			Text = "[img]gfx/ui/events/event_65.png[/img]{烟港酒馆里，阿飞把团约按在桌上签字。抹茶用旧尺量完旗布与口粮，王大谋检查车轮与箱扣。\n\n雇主托付的账本还在抹茶手里——可接一份低危「安全送账」契约（报酬 [color=#8f2525]180[/color] 克朗）。拒绝也无妨，之后用普通有报酬契约同样能打开招募节奏。黑旗名册此刻只有三行。}",
			Image = "",
			Banner = "",
			List = [],
			Characters = [],
			Options = [
				{
					Text = "接安全送账契约。",
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
			Text = "[img]gfx/ui/events/event_65.png[/img]{抹茶把账本夹进行囊。系统会挂上一份「安全送账」低危契约：地图上出现途中遭遇点，也可仍用邻镇交付结算。计作一份有报酬契约，且只此一次。}",
			Image = "",
			List = [],
			Characters = [],
			Options = [
				{
					Text = "挂上契约并出发。",
					function getResult(_event)
					{
						this.World.Flags.set(::AfeiExpedition.Flags.SafeDeliveryActive, 1);
						this.World.Flags.set(::AfeiExpedition.Flags.SafeDeliveryDone, 0);
						if (!::AfeiExpedition.tryOfferSafeDelivery(this))
						{
							return "BFail";
						}
						return 0;
					}
				}
			],
			function start(_event)
			{
				this.List.push({
					id = 10,
					icon = "ui/icons/special.png",
					text = "安全送账契约（180 克朗 · 低危）"
				});
			}
		});
		this.m.Screens.push({
			ID = "BFail",
			Text = "[img]gfx/ui/events/event_65.png[/img]{一时无法挂上契约模板。仍可按旧方式：进入一座与开局不同的友好城镇交付。}",
			Image = "",
			List = [],
			Characters = [],
			Options = [
				{
					Text = "知道了。",
					function getResult(_event)
					{
						this.World.Flags.set(::AfeiExpedition.Flags.SafeDeliveryActive, 1);
						this.World.Flags.set(::AfeiExpedition.Flags.M01Done, 1);
						return 0;
					}
				}
			],
			function start(_event) {}
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
			function start(_event) {}
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
	function onPrepareVariables(_vars) {}
	function onClear() {}
});

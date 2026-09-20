this.afei_bottle_leave_bicycle_event <- this.inherit("scripts/events/event", {
	m = {},
	function create()
	{
		this.m.ID = "event.afei_bottle_leave_bicycle";
		this.m.IsSpecial = true;
		this.m.Title = "遗弃自行车？";
		this.m.Screens.push({
			ID = "A",
			Text = "[img]gfx/ui/events/event_65.png[/img]{小酒瓶的铺位空了。车把还靠在车厢边，铃铛轻轻晃了一下。\n\n你可以遗弃这辆自行车——阿飞会把那段路上的节奏记进骨子里，此后经验获取 [color=#1e781e]×1.2[/color]。全战役仅这一次；遗弃后自行车消失。\n\n也可以留下车。车还在，但不会再给你第二次倍率。}",
			Image = "",
			List = [],
			Characters = [],
			Options = [
				{
					Text = "遗弃自行车。阿飞经验获取 ×1.2。",
					function getResult(_event)
					{
						::AfeiExpedition.abandonBicycleForXp();
						return "Abandoned";
					}
				},
				{
					Text = "留下自行车。不要倍率。",
					function getResult(_event)
					{
						::AfeiExpedition.keepBicycleNoXp();
						return "Kept";
					}
				}
			],
			function start(_event)
			{
			}
		});
		this.m.Screens.push({
			ID = "Abandoned",
			Text = "[img]gfx/ui/events/event_65.png[/img]{车被推下坡道，铃声远去。阿飞把那点空缺换成了更长的路——经验获取永久 [color=#1e781e]×1.2[/color]。}",
			Image = "",
			List = [],
			Characters = [],
			Options = [
				{
					Text = "走吧。",
					function getResult(_event)
					{
						return 0;
					}
				}
			],
			function start(_event)
			{
				this.List.push({
					id = 10,
					icon = "ui/icons/xp_received.png",
					text = "阿飞经验获取 [color=#1e781e]×1.2[/color]（永久，仅一次）"
				});
				this.List.push({
					id = 11,
					icon = "ui/icons/special.png",
					text = "自行车已消失"
				});
			}
		});
		this.m.Screens.push({
			ID = "Kept",
			Text = "[img]gfx/ui/events/event_65.png[/img]{车仍在行囊里。没有遗弃，也就没有那份经验倍率。}",
			Image = "",
			List = [],
			Characters = [],
			Options = [
				{
					Text = "知道了。",
					function getResult(_event)
					{
						return 0;
					}
				}
			],
			function start(_event)
			{
				this.List.push({
					id = 10,
					icon = "ui/icons/special.png",
					text = "自行车保留；未获得经验倍率"
				});
			}
		});
	}

	function onUpdateScore()
	{
		return;
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

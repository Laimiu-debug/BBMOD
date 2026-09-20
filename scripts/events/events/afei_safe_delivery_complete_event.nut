this.afei_safe_delivery_complete_event <- this.inherit("scripts/events/event", {
	m = {},
	function create()
	{
		this.m.ID = "event.afei_safe_delivery_complete";
		this.m.IsSpecial = true;
		this.m.Title = "账册送达";
		this.m.Screens.push({
			ID = "A",
			Text = "[img]gfx/ui/events/event_41.png[/img]{邻镇驿站的伙计核对了封印。抹茶松了一口气，大谋把空箱子踢到一边，阿飞把第一笔「真正送到的」报酬记进名册。\n\n安全送账完成：获得 [color=#8f2525]180[/color] 克朗，并计入一份有报酬契约。}",
			Image = "",
			List = [],
			Characters = [],
			Options = [
				{
					Text = "第一班守夜，算是走完了。",
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
					icon = "ui/icons/asset_money.png",
					text = "获得 [color=#8f2525]180[/color] 克朗（安全送账）"
				});
				this.List.push({
					id = 11,
					icon = "ui/icons/special.png",
					text = "有报酬契约计数 +1"
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

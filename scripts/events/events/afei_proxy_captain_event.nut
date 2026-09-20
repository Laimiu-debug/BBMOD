this.afei_proxy_captain_event <- this.inherit("scripts/events/event", {
	m = {},
	function create()
	{
		this.m.ID = "event.afei_proxy_captain";
		this.m.Title = "指定代理队长";
		this.m.Cooldown = 5.0 * this.World.getTime().SecondsPerDay;
		this.m.Screens.push({
			ID = "A",
			Text = "%terrainImage%{阿飞可进替补，战前需指定代理队长。代理不转移团长身份与嘉豪。开战时若未指定，会按怼怼→大谋→其他命名自动点名。}",
			Image = "",
			List = [],
			Characters = [],
			Options = [
				{
					Text = "指定王大谋为代理。",
					function getResult(_event)
					{
						::AfeiExpedition.clearProxyFlags();
						::AfeiExpedition.setProxyByNamedId("C03");
						return 0;
					}
				},
				{
					Text = "指定王怼怼为代理（若已入队）。",
					function getResult(_event)
					{
						::AfeiExpedition.clearProxyFlags();
						if (!::AfeiExpedition.setProxyByNamedId("C10"))
						{
							::AfeiExpedition.setProxyByNamedId("C03");
						}
						return 0;
					}
				},
				{
					Text = "指定白小帅子为代理（若已入队）。",
					function getResult(_event)
					{
						::AfeiExpedition.clearProxyFlags();
						if (!::AfeiExpedition.setProxyByNamedId("C09"))
						{
							::AfeiExpedition.ensureProxyCaptain();
						}
						return 0;
					}
				},
				{
					Text = "交给自动指定。",
					function getResult(_event)
					{
						::AfeiExpedition.clearProxyFlags();
						::AfeiExpedition.ensureProxyCaptain();
						return 0;
					}
				}
			],
			function start(_event) {}
		});
	}
	function onUpdateScore()
	{
		if (!::AfeiExpedition.isAfeiOrigin()) { return; }
		if (this.World.getTime().Days < 3) { return; }
		if (this.World.getPlayerRoster().getSize() < 3) { return; }
		this.m.Score = 5;
	}
	function onPrepare() {}
	function onPrepareVariables(_vars) {}
	function onClear() {}
});

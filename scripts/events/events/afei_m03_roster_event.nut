this.afei_m03_roster_event <- this.inherit("scripts/events/event", {
	m = {},
	function create()
	{
		this.m.ID = "event.afei_m03_roster";
		this.m.Title = "黑旗上的十个位置";
		this.m.Cooldown = 99999.0 * this.World.getTime().SecondsPerDay;
		this.m.Screens.push({
			ID = "A",
			Text = "%terrainImage%{营地整编：演示战前代理、替补、号令共用与个人成长记录。尚未加入的黑队只在日志留空位。}",
			Image = "", List = [], Characters = [],
			Options = [{ Text = "记下了。", function getResult(_event) {
				this.World.Flags.set(::AfeiExpedition.Flags.M03Done, 1);
				::AfeiExpedition.ensureProxyCaptain();
				return 0;
			}}],
			function start(_event) {}
		});
	}
	function onUpdateScore()
	{
		if (!::AfeiExpedition.isAfeiOrigin()) return;
		if (this.World.Flags.get(::AfeiExpedition.Flags.M03Done)) return;
		if (this.World.getTime().Days < 20) return;
		if (::AfeiExpedition.countNamedInRoster() < 8) return;
		this.m.Score = 35;
	}
	function onPrepare() {}
	function onPrepareVariables(_vars) {}
	function onClear() {}
});

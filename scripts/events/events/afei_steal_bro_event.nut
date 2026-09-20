this.afei_steal_bro_event <- this.inherit("scripts/events/event", {
	m = {},
	function create()
	{
		this.m.ID = "event.afei_steal_bro";
		this.m.Title = "偷大哥·引荐";
		this.m.Cooldown = 1.0 * this.World.getTime().SecondsPerDay;
		this.m.Screens.push({
			ID = "A",
			Text = "%terrainImage%{大谋说认识一个大哥。为一名已满足招募条件、尚未签约的候选人保留八折报价（最多省 200）。}",
			Image = "", List = [], Characters = [],
			Options = [
				{ Text = "为当前可招候选人保留八折", function getResult(_event) {
					if (!::AfeiExpedition.tryStartStealDiscount()) return "Fail";
					return "Ok";
				}},
				{ Text = "先不谈", function getResult(_event) { return 0; }}
			],
			function start(_event) {}
		});
		this.m.Screens.push({ ID="Ok", Text="%terrainImage%{报价已保留。签约时自动减免。}", Image="", List=[], Characters=[],
			Options=[{Text="好。", function getResult(_event){ return 0; }}], function start(_event){} });
		this.m.Screens.push({ ID="Fail", Text="%terrainImage%{冷却中或没有可引荐的已开门候选人。}", Image="", List=[], Characters=[],
			Options=[{Text="知道了。", function getResult(_event){ return 0; }}], function start(_event){} });
	}
	function onUpdateScore()
	{
		if (!::AfeiExpedition.isAfeiOrigin()) return;
		if (!::AfeiExpedition.hasNamed("C03")) return;
		if (this.World.getTime().Days < this.World.Flags.getAsInt("afei_steal_ready_day")) return;
		this.m.Score = 8;
	}
	function onPrepare() {}
	function onPrepareVariables(_vars) {}
	function onClear() {}
});

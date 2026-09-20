this.afei_m08_letters_event <- this.inherit("scripts/events/event", {
	m = {},
	function create()
	{
		this.m.ID = "event.afei_m08_letters";
		this.m.Title = "再集合一次";
		this.m.Cooldown = 99999.0 * this.World.getTime().SecondsPerDay;
		this.m.Screens.push({
			ID = "A",
			Text = "%terrainImage%{旧营地求助。阶段实现：连续完成两份事件契约（补给+护送），磨合 +6，记录终章。}",
			Image = "", List = [], Characters = [],
			Options = [
				{ Text = "完成两份任务（事件结算）", function getResult(_event) {
					::AfeiExpedition.addPaidContract(2);
					local c=this.World.Flags.getAsInt("afei_cohesion");
					this.World.Flags.set("afei_cohesion", this.Math.min(100,c+6));
					this.World.Flags.set(::AfeiExpedition.Flags.M08Done,1);
					::AfeiExpedition.tryAwakenAfei();
					return "End";
				}},
				{ Text = "暂缓。", function getResult(_event) { return 0; }}
			],
			function start(_event) {}
		});
		this.m.Screens.push({ ID="End", Text="%terrainImage%{书信结局落下。未招完的人仍可继续；死者仅纪念。若阿飞已 11 级且嘉豪 16 并完成本事件，解锁终极觉醒。}", Image="", List=[], Characters=[],
			Options=[{Text="给下一次远行写信。", function getResult(_event){ return 0; }}], function start(_event){} });
	}
	function onUpdateScore()
	{
		if (!::AfeiExpedition.isAfeiOrigin()) return;
		if (this.World.Flags.get(::AfeiExpedition.Flags.M08Done)) return;
		if (this.World.getTime().Days < 90) return;
		if (::AfeiExpedition.getPaidContracts() < 24) return;
		if (::AfeiExpedition.countNamedEverRecruited() < 8) return;
		if (this.World.Flags.getAsInt("afei_cohesion_peak") < 60 && this.World.Flags.getAsInt("afei_cohesion") < 60) return;
		this.m.Score = 40;
	}
	function onPrepare() {}
	function onPrepareVariables(_vars) {}
	function onClear() {}
});

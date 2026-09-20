this.afei_m05_bear_event <- this.inherit("scripts/events/event", {
	m = {},
	function create()
	{
		this.m.ID = "event.afei_m05_bear";
		this.m.Title = "小熊出击";
		this.m.Cooldown = 99999.0 * this.World.getTime().SecondsPerDay;
		this.m.Screens.push({
			ID = "A",
			Text = "%terrainImage%{童猪带着木熊来访。原创答案：先敲杯再举熊。猜对错都留下 R15 线索。}",
			Image = "", List = [], Characters = [],
			Options = [
				{ Text = "先敲杯再举熊（猜对）", function getResult(_event) {
					local c=this.World.Flags.getAsInt("afei_cohesion");
					this.World.Flags.set("afei_cohesion", this.Math.min(100,c+4));
					this.World.Flags.set(::AfeiExpedition.Flags.M05Done,1);
					return "Ok";
				}},
				{ Text = "先举熊（猜错，仍学会）", function getResult(_event) {
					local c=this.World.Flags.getAsInt("afei_cohesion");
					this.World.Flags.set("afei_cohesion", this.Math.min(100,c+2));
					this.World.Flags.set(::AfeiExpedition.Flags.M05Done,1);
					return "Ok";
				}}
			],
			function start(_event) {}
		});
		this.m.Screens.push({ ID="Ok", Text="%terrainImage%{童猪只是来访，未入册。第45日后可正式付费邀请（R15）。}", Image="", List=[], Characters=[],
			Options=[{Text="记下线索。", function getResult(_event){ return 0; }}], function start(_event){} });
	}
	function onUpdateScore()
	{
		if (!::AfeiExpedition.isAfeiOrigin()) return;
		if (this.World.Flags.get(::AfeiExpedition.Flags.M05Done)) return;
		if (this.World.getTime().Days < 40) return;
		if (::AfeiExpedition.getPaidContracts() < 10) return;
		this.m.Score = 30;
	}
	function onPrepare() {}
	function onPrepareVariables(_vars) {}
	function onClear() {}
});

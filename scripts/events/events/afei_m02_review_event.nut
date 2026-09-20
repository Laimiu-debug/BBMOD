this.afei_m02_review_event <- this.inherit("scripts/events/event", {
	m = {},
	function create()
	{
		this.m.ID = "event.afei_m02_review";
		this.m.Title = "第一次把话说完";
		this.m.Cooldown = 99999.0 * this.World.getTime().SecondsPerDay;
		this.m.Screens.push({
			ID = "A",
			Text = "%terrainImage%{一次合作失误后，阿飞还想继续哇哇叫。抹茶按住他的肩膀：先听每个人把话说完。\n\n这是黑旗第一次正式复盘——大约三小时，可以一起把错处摊开，也可以先休息，让火气落下去。}",
			Image = "", List = [], Characters = [],
			Options = [
				{ Text = "一起复盘（6 食物、约 3 小时、磨合 +6）", function getResult(_event) {
					if (!::AfeiExpedition.trySpendFoodApprox(6)) return "NoFood";
					local c = this.World.Flags.getAsInt("afei_cohesion");
					this.World.Flags.set("afei_cohesion", this.Math.min(100, c + 6));
					this.World.Flags.set(::AfeiExpedition.Flags.ReviewCount, this.World.Flags.getAsInt(::AfeiExpedition.Flags.ReviewCount) + 1);
					this.World.Flags.set(::AfeiExpedition.Flags.M02Done, 1);
					return "Done";
				}},
				{ Text = "先休息（磨合 +3）", function getResult(_event) {
					local c = this.World.Flags.getAsInt("afei_cohesion");
					this.World.Flags.set("afei_cohesion", this.Math.min(100, c + 3));
					this.World.Flags.set(::AfeiExpedition.Flags.M02Done, 1);
					return "Done";
				}}
			],
			function start(_event) {}
		});
		this.m.Screens.push({ ID="Done", Text="%terrainImage%{话说完了。此后普通营地复盘可满足成长条件，也会被川神等伙伴的入团步骤认作「复盘过」。}", Image="", List=[], Characters=[],
			Options=[{Text="好。", function getResult(_event){ return 0; }}], function start(_event){} });
		this.m.Screens.push({ ID="NoFood", Text="%terrainImage%{食物不够复盘。}", Image="", List=[], Characters=[],
			Options=[{Text="稍后。", function getResult(_event){ return 0; }}], function start(_event){} });
	}
	function onUpdateScore()
	{
		if (!::AfeiExpedition.isAfeiOrigin()) return;
		if (this.World.Flags.get(::AfeiExpedition.Flags.M02Done)) return;
		if (::AfeiExpedition.getPaidContracts() < 4) return;
		if (this.World.getPlayerRoster().getSize() < 5) return;
		this.m.Score = 40;
	}
	function onPrepare() {}
	function onPrepareVariables(_vars) {}
	function onClear() {}
});

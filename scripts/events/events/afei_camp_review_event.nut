this.afei_camp_review_event <- this.inherit("scripts/events/event", {
	m = {},
	function create()
	{
		this.m.ID = "event.afei_camp_review";
		this.m.Title = "普通营地复盘";
		this.m.Cooldown = 3.0 * this.World.getTime().SecondsPerDay;
		this.m.Screens.push({
			ID = "A",
			Text = "%terrainImage%{普通复盘：80 克朗、6 食物，磨合 +5。可满足成长条件中的复盘计数。}",
			Image = "", List = [], Characters = [],
			Options = [
				{ Text = "复盘", function getResult(_event) {
					if (this.World.Assets.getMoney() < 80) return "Poor";
					if (!::AfeiExpedition.trySpendFoodApprox(6)) return "Poor";
					this.World.Assets.addMoney(-80);
					local c=this.World.Flags.getAsInt("afei_cohesion");
					this.World.Flags.set("afei_cohesion", this.Math.min(100,c+5));
					this.World.Flags.set(::AfeiExpedition.Flags.ReviewCount, this.World.Flags.getAsInt(::AfeiExpedition.Flags.ReviewCount)+1);
					local peak = this.World.Flags.getAsInt("afei_cohesion_peak");
					local cur = this.World.Flags.getAsInt("afei_cohesion");
					if (cur > peak) this.World.Flags.set("afei_cohesion_peak", cur);
					return 0;
				}},
				{ Text = "离开", function getResult(_event) { return 0; }}
			],
			function start(_event) {}
		});
		this.m.Screens.push({ ID="Poor", Text="%terrainImage%{钱或食物不够。}", Image="", List=[], Characters=[],
			Options=[{Text="好。", function getResult(_event){ return 0; }}], function start(_event){} });
	}
	function onUpdateScore()
	{
		if (!::AfeiExpedition.isAfeiOrigin()) return;
		if (!this.World.Flags.get(::AfeiExpedition.Flags.M02Done)) return;
		this.m.Score = 10;
	}
	function onPrepare() {}
	function onPrepareVariables(_vars) {}
	function onClear() {}
});

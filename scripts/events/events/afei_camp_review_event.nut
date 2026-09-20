this.afei_camp_review_event <- this.inherit("scripts/events/event", {
	m = {},
	function create()
	{
		this.m.ID = "event.afei_camp_review";
		this.m.Title = "普通营地复盘";
		this.m.Cooldown = 3.0 * this.World.getTime().SecondsPerDay;
		this.m.Screens.push({
			ID = "A",
			Text = "%terrainImage%{普通营地复盘：花费 [color=#8f2525]80[/color] 克朗与 6 食物，大约三小时把话说完。磨合 +5，并计入成长条件中的复盘次数。\n\n川神等伙伴的入团步骤也可能要求你们先完成一次这样的复盘。}",
			Image = "", List = [], Characters = [],
			Options = [
				{ Text = "复盘（80 克朗、6 食物、约 3 小时）", function getResult(_event) {
					if (this.World.Assets.getMoney() < 80) return "Poor";
					if (!::AfeiExpedition.trySpendFoodApprox(6)) return "Poor";
					this.World.Assets.addMoney(-80);
					local c=this.World.Flags.getAsInt("afei_cohesion");
					this.World.Flags.set("afei_cohesion", this.Math.min(100,c+5));
					this.World.Flags.set(::AfeiExpedition.Flags.ReviewCount, this.World.Flags.getAsInt(::AfeiExpedition.Flags.ReviewCount)+1);
					local peak = this.World.Flags.getAsInt("afei_cohesion_peak");
					local cur = this.World.Flags.getAsInt("afei_cohesion");
					if (cur > peak) this.World.Flags.set("afei_cohesion_peak", cur);
					return "Done";
				}},
				{ Text = "离开", function getResult(_event) { return 0; }}
			],
			function start(_event) {}
		});
		this.m.Screens.push({
			ID = "Done",
			Text = "%terrainImage%{话说完了。复盘次数 +1。}",
			Image = "", List = [], Characters = [],
			Options = [{ Text = "好。", function getResult(_event) { return 0; }}],
			function start(_event) {
				this.List.push({ id = 10, icon = "ui/icons/special.png", text = "普通营地复盘完成（约 3 小时）" });
			}
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

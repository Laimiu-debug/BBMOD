this.afei_m09_camp_event <- this.inherit("scripts/events/event", {
	m = {},
	function create()
	{
		this.m.ID = "event.afei_m09_camp";
		this.m.Title = "给后来的人留一张床";
		this.m.Cooldown = 99999.0 * this.World.getTime().SecondsPerDay;
		this.m.Screens.push({
			ID = "A",
			Text = "%terrainImage%{旧驿站租约。承租：300 克朗、12 食物、6 工具。启用总名册 39、常备 ≤20、驻营 ≤19。}",
			Image = "", List = [], Characters = [],
			Options = [
				{ Text = "承租营地", function getResult(_event) {
					if (this.World.Assets.getMoney() < 300) return "Poor";
					if (!::AfeiExpedition.trySpendFoodApprox(12)) return "Poor";
					if (this.World.Assets.getArmorParts() < 6) return "Poor";
					this.World.Assets.addMoney(-300);
					this.World.Assets.addArmorParts(-6);
					local c=this.World.Flags.getAsInt("afei_cohesion");
					this.World.Flags.set("afei_cohesion", this.Math.min(100,c+4));
					this.World.Flags.set(::AfeiExpedition.Flags.M09Done,1);
					this.World.Flags.set(::AfeiExpedition.Flags.CampEnabled,1);
					this.World.Assets.m.BrothersMax = 39;
					return "Ok";
				}},
				{ Text = "先看别处", function getResult(_event) { return 0; }}
			],
			function start(_event) {}
		});
		this.m.Screens.push({ ID="Ok", Text="%terrainImage%{营地启用。可用驻营事件把命名伙伴标为驻营（日薪 35% 近似 + 有驻营时租金 30）。}", Image="", List=[], Characters=[],
			Options=[{Text="好。", function getResult(_event){ return 0; }}], function start(_event){} });
		this.m.Screens.push({ ID="Poor", Text="%terrainImage%{资源不足。}", Image="", List=[], Characters=[],
			Options=[{Text="稍后。", function getResult(_event){ return 0; }}], function start(_event){} });
	}
	function onUpdateScore()
	{
		if (!::AfeiExpedition.isAfeiOrigin()) return;
		if (this.World.Flags.get(::AfeiExpedition.Flags.M09Done)) return;
		if (this.World.getTime().Days < 45) return;
		if (::AfeiExpedition.getPaidContracts() < 14) return;
		this.m.Score = 30;
	}
	function onPrepare() {}
	function onPrepareVariables(_vars) {}
	function onClear() {}
});

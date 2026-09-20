this.afei_m07_shadow_event <- this.inherit("scripts/events/event", {
	m = {},
	function create()
	{
		this.m.ID = "event.afei_m07_shadow";
		this.m.Title = "北境白影";
		this.m.Cooldown = 14.0 * this.World.getTime().SecondsPerDay;
		this.m.Screens.push({
			ID = "A",
			Text = "%terrainImage%{可选猎人传闻：冰霜巨兽。本环境无法生成真实巨兽战——选择「击败」给事件奖励；可离开。不锁终章。}",
			Image = "", List = [], Characters = [],
			Options = [
				{ Text = "视为击败（事件奖励）", function getResult(_event) {
					this.World.Assets.addMoney(800);
					local c=this.World.Flags.getAsInt("afei_cohesion");
					this.World.Flags.set("afei_cohesion", this.Math.min(100,c+6));
					this.World.Flags.set(::AfeiExpedition.Flags.M07Done,1);
					return "Ok";
				}},
				{ Text = "侦察后离开", function getResult(_event) { return 0; }}
			],
			function start(_event) {}
		});
		this.m.Screens.push({ ID="Ok", Text="%terrainImage%{白影挑战记入名册。}", Image="", List=[], Characters=[],
			Options=[{Text="好。", function getResult(_event){ return 0; }}], function start(_event){
				this.List.push({id=10,icon="ui/icons/asset_money.png",text="800 克朗"});
			}});
	}
	function onUpdateScore()
	{
		if (!::AfeiExpedition.isAfeiOrigin()) return;
		if (this.World.Flags.get(::AfeiExpedition.Flags.M07Done)) return;
		if (this.World.getTime().Days < 75) return;
		if (this.World.getPlayerRoster().getSize() < 8) return;
		this.m.Score = 10;
	}
	function onPrepare() {}
	function onPrepareVariables(_vars) {}
	function onClear() {}
});

this.afei_m06_key_event <- this.inherit("scripts/events/event", {
	m = {},
	function create()
	{
		this.m.ID = "event.afei_m06_key";
		this.m.Title = "我不上这个当";
		this.m.Cooldown = 99999.0 * this.World.getTime().SecondsPerDay;
		this.m.Screens.push({
			ID = "A",
			Text = "%terrainImage%{小杰把货车锁上后，发现钥匙去向不明。这不是要锁死你们的物品栏——只是追问钥匙该怎么分工。\n\n可以一起花大约两小时翻找，也可以花六十克朗请锁匠。七日后若仍未处理，也会保底收场（本版以事件一次结算近似）。}",
			Image = "", List = [], Characters = [],
			Options = [
				{ Text = "一起检查（约 2 小时，磨合 +2）", function getResult(_event) {
					local c=this.World.Flags.getAsInt("afei_cohesion");
					this.World.Flags.set("afei_cohesion", this.Math.min(100,c+2));
					this.World.Flags.set(::AfeiExpedition.Flags.M06Done,1);
					return "Done";
				}},
				{ Text = "请锁匠（60 克朗）", function getResult(_event) {
					if (this.World.Assets.getMoney() < 60) return "Poor";
					this.World.Assets.addMoney(-60);
					this.World.Flags.set(::AfeiExpedition.Flags.M06Done,1);
					return "Done";
				}}
			],
			function start(_event) {}
		});
		this.m.Screens.push({
			ID = "Done",
			Text = "%terrainImage%{备用钥匙挂到车门边。笑话还在，物品栏没有被锁死。}",
			Image = "", List = [], Characters = [],
			Options = [{ Text = "好。", function getResult(_event) { return 0; }}],
			function start(_event) {}
		});
		this.m.Screens.push({
			ID = "Poor",
			Text = "%terrainImage%{钱不够请锁匠。可以改为一合同检查。}",
			Image = "", List = [], Characters = [],
			Options = [{ Text = "返回。", function getResult(_event) { return "A"; }}],
			function start(_event) {}
		});
	}
	function onUpdateScore()
	{
		if (!::AfeiExpedition.isAfeiOrigin()) return;
		if (this.World.Flags.get(::AfeiExpedition.Flags.M06Done)) return;
		if (!::AfeiExpedition.hasNamed("C14")) return;
		if (this.World.getTime().Days < 38) return;
		this.m.Score = 25;
	}
	function onPrepare() {}
	function onPrepareVariables(_vars) {}
	function onClear() {}
});

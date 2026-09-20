this.afei_m06_key_event <- this.inherit("scripts/events/event", {
	m = {},
	function create()
	{
		this.m.ID = "event.afei_m06_key";
		this.m.Title = "我不上这个当";
		this.m.Cooldown = 99999.0 * this.World.getTime().SecondsPerDay;
		this.m.Screens.push({
			ID = "A",
			Text = "%terrainImage%{小杰把货车锁上后发现钥匙去向不明。}",
			Image = "", List = [], Characters = [],
			Options = [
				{ Text = "一起检查（磨合 +2）", function getResult(_event) {
					local c=this.World.Flags.getAsInt("afei_cohesion");
					this.World.Flags.set("afei_cohesion", this.Math.min(100,c+2));
					this.World.Flags.set(::AfeiExpedition.Flags.M06Done,1);
					return 0;
				}},
				{ Text = "请锁匠（60 克朗）", function getResult(_event) {
					if (this.World.Assets.getMoney()>=60) this.World.Assets.addMoney(-60);
					this.World.Flags.set(::AfeiExpedition.Flags.M06Done,1);
					return 0;
				}}
			],
			function start(_event) {}
		});
	}
	function onUpdateScore()
	{
		if (!::AfeiExpedition.isAfeiOrigin()) return;
		if (this.World.Flags.get(::AfeiExpedition.Flags.M06Done)) return;
		if (!::AfeiExpedition.hasNamed("C14")) return;
		// 入队满三日近似：日数足够且已招 R11
		if (this.World.getTime().Days < 38) return;
		this.m.Score = 25;
	}
	function onPrepare() {}
	function onPrepareVariables(_vars) {}
	function onClear() {}
});

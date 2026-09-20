this.afei_camp_assign_event <- this.inherit("scripts/events/event", {
	m = {},
	function create()
	{
		this.m.ID = "event.afei_camp_assign";
		this.m.Title = "驻营调换";
		this.m.Cooldown = 1.0 * this.World.getTime().SecondsPerDay;
		this.m.Screens.push({
			ID = "A",
			Text = "%terrainImage%{花约 4 小时调换常备/驻营。阶段实现：切换名册中非阿飞成员的驻营标记（最多 19 人驻营）。驻营不计战斗经验与多数被动。}",
			Image = "", List = [], Characters = [],
			Options = [
				{ Text = "自动：超出常备 20 的命名伙伴改驻营", function getResult(_event) {
					::AfeiExpedition.autoAssignCamp();
					return 0;
				}},
				{ Text = "清驻营，全部常备", function getResult(_event) {
					::AfeiExpedition.clearCampFlags();
					return 0;
				}},
				{ Text = "离开", function getResult(_event) { return 0; }}
			],
			function start(_event) {}
		});
	}
	function onUpdateScore()
	{
		if (!::AfeiExpedition.isAfeiOrigin()) return;
		if (!this.World.Flags.get(::AfeiExpedition.Flags.CampEnabled)) return;
		this.m.Score = 8;
	}
	function onPrepare() {}
	function onPrepareVariables(_vars) {}
	function onClear() {}
});

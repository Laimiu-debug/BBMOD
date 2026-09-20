this.afei_camp_assign_event <- this.inherit("scripts/events/event", {
	m = {},
	function create()
	{
		this.m.ID = "event.afei_camp_assign";
		this.m.Title = "驻营调换";
		this.m.Cooldown = 1.0 * this.World.getTime().SecondsPerDay;
		this.m.Screens.push({
			ID = "A",
			Text = "%terrainImage%{须在城镇旁花费约 4 小时调换常备/驻营（优先承租营地所属城镇）。最多 19 人驻营；驻营不计战斗经验与多数被动。}",
			Image = "", List = [], Characters = [],
			Options = [
				{ Text = "调换（约 4 小时）：超出常备 20 的命名伙伴改驻营", function getResult(_event) {
					if (!::AfeiExpedition.isNearCampTown()) return "WrongTown";
					::AfeiExpedition.autoAssignCamp();
					this.World.Flags.set("afei_camp_swap_day", this.World.getTime().Days);
					return "Done";
				}},
				{ Text = "清驻营，全部常备（约 4 小时）", function getResult(_event) {
					if (!::AfeiExpedition.isNearCampTown()) return "WrongTown";
					::AfeiExpedition.clearCampFlags();
					this.World.Flags.set("afei_camp_swap_day", this.World.getTime().Days);
					return "Done";
				}},
				{ Text = "离开", function getResult(_event) { return 0; }}
			],
			function start(_event) {}
		});
		this.m.Screens.push({
			ID = "Done",
			Text = "%terrainImage%{调换完成，大约耗去 4 小时。}",
			Image = "", List = [], Characters = [],
			Options = [{ Text = "好。", function getResult(_event) { return 0; }}],
			function start(_event) {
				this.List.push({ id = 10, icon = "ui/icons/special.png", text = "驻营调换（约 4 小时）" });
			}
		});
		this.m.Screens.push({
			ID = "WrongTown",
			Text = "%terrainImage%{请到承租营地所属城镇（或任意邻近友好城镇）再调换。}",
			Image = "", List = [], Characters = [],
			Options = [{ Text = "知道了。", function getResult(_event) { return 0; }}],
			function start(_event) {}
		});
	}
	function onUpdateScore()
	{
		if (!::AfeiExpedition.isAfeiOrigin()) return;
		if (!this.World.Flags.get(::AfeiExpedition.Flags.CampEnabled)) return;
		if (!::AfeiExpedition.isNearCampTown()) return;
		this.m.Score = 12;
	}
	function onPrepare() {}
	function onPrepareVariables(_vars) {}
	function onClear() {}
});

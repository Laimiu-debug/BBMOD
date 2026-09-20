this.afei_growth_check_event <- this.inherit("scripts/events/event", {
	m = { Completed = [] },
	function create()
	{
		this.m.ID = "event.afei_growth_check";
		this.m.Title = "个人成长结算";
		this.m.Cooldown = 3.0 * this.World.getTime().SecondsPerDay;
		this.m.Screens.push({
			ID = "A",
			Text = "%terrainImage%{检查名册中达到成长门槛的命名伙伴。除阿飞外统一约 5 级；阿飞 G01 为 7 级。完成时磨合 +3，并写入嘉豪（阿飞在世时）。}",
			Image = "", List = [], Characters = [],
			Options = [
				{ Text = "结算所有达标成长", function getResult(_event) {
					_event.m.Completed = ::AfeiExpedition.trySettleAllGrowths();
					return "B";
				}},
				{ Text = "稍后再说", function getResult(_event) { return 0; }}
			],
			function start(_event) {}
		});
		this.m.Screens.push({
			ID = "B",
			Text = "%terrainImage%{本批结算完成。详见列表。}",
			Image = "", List = [], Characters = [],
			Options = [{ Text = "好。", function getResult(_event) { return 0; }}],
			function start(_event) {
				if (_event.m.Completed.len() == 0) {
					this.List.push({ id=10, icon="ui/icons/special.png", text="无人新达标（或已结算）" });
				} else {
					foreach (id in _event.m.Completed) {
						this.List.push({ id=10, icon="ui/icons/special.png", text="完成 " + id });
					}
				}
			}
		});
	}
	function onUpdateScore()
	{
		if (!::AfeiExpedition.isAfeiOrigin()) return;
		if (this.World.getTime().Days < 5) return;
		this.m.Score = 12;
	}
	function onPrepare() { this.m.Completed = []; }
	function onPrepareVariables(_vars) {}
	function onClear() { this.m.Completed = []; }
});

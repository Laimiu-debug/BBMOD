this.afei_m04_blue_event <- this.inherit("scripts/events/event", {
	m = {},
	function create()
	{
		this.m.ID = "event.afei_m04_blue";
		this.m.Title = "蓝旗同行";
		this.m.Cooldown = 7.0 * this.World.getTime().SecondsPerDay;
		this.m.Screens.push({
			ID = "A",
			Text = "%terrainImage%{联合护送邀请。阶段实现：以事件结算代替完整契约战斗——成功则开放川神/小虎/大鹅邀请，磨合 +4，计 1 份有报酬契约。}",
			Image = "", List = [], Characters = [],
			Options = [
				{ Text = "接受并完成护送（事件结算）", function getResult(_event) {
					::AfeiExpedition.addPaidContract(1);
					local c = this.World.Flags.getAsInt("afei_cohesion");
					this.World.Flags.set("afei_cohesion", this.Math.min(100, c + 4));
					this.World.Flags.set(::AfeiExpedition.Flags.M04Done, 1);
					this.World.Assets.addMoney(200);
					return "Ok";
				}},
				{ Text = "暂缓。", function getResult(_event) { return 0; }}
			],
			function start(_event) {}
		});
		this.m.Screens.push({ ID="Ok", Text="%terrainImage%{护送完成。蓝旗三人个人邀请已开放（R08–R10）。}", Image="", List=[], Characters=[],
			Options=[{Text="好。", function getResult(_event){ return 0; }}], function start(_event){
				this.List.push({id=10,icon="ui/icons/asset_money.png",text="获得报酬（事件近似）"});
			}});
	}
	function onUpdateScore()
	{
		if (!::AfeiExpedition.isAfeiOrigin()) return;
		if (this.World.Flags.get(::AfeiExpedition.Flags.M04Done)) return;
		if (this.World.getTime().Days < 25) return;
		if (::AfeiExpedition.getPaidContracts() < 8) return;
		this.m.Score = 35;
	}
	function onPrepare() {}
	function onPrepareVariables(_vars) {}
	function onClear() {}
});

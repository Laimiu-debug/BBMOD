this.afei_r27_event <- this.inherit("scripts/events/event", {
	m = {},
	function create()
	{
		this.m.ID = "event.afei_r27_event";
		this.m.Title = "招募 · 罗一可";
		this.m.Cooldown = 7.0 * this.World.getTime().SecondsPerDay;
		this.m.Screens.push({
			ID = "A",
			Text = "%terrainImage%{球场占道委托后。签约 [color=#8f2525]350[/color] 克朗。\n\n暂缓不消失；满员或缺钱时可晚些再见。}",
			Image = "", List = [], Characters = [],
			Options = [
				{ Text = "开始相遇/演练。", function getResult(_event) { return "B"; } },
				{ Text = "线索留着。", function getResult(_event) { this.World.Flags.set(::AfeiExpedition.Flags.R27Offered, 1); return 0; } }
			],
			function start(_event) {}
		});
		this.m.Screens.push({
			ID = "B",
			Text = "%terrainImage%{演练/委托结束。签约费 [color=#8f2525]350[/color] 克朗。身份 C30，入队 1 级 0 经验。}",
			Image = "", List = [], Characters = [],
			Options = [
				{ Text = "支付 350 克朗签约。", function getResult(_event) {
						if (this.World.Assets.getMoney() < 350) return "Poor";
						
						return "Hire";
				} },
				{ Text = "先不签。", function getResult(_event) { this.World.Flags.set(::AfeiExpedition.Flags.R27Offered, 1); return 0; } }
			],
			function start(_event) {}
		});
		this.m.Screens.push({
			ID = "Hire",
			Text = "%terrainImage%{黑旗名册多了一行：罗一可。}",
			Image = "", List = [], Characters = [],
			Options = [{ Text = "欢迎入队。", function getResult(_event) {
						if (::AfeiExpedition.hasNamed("C30")) return 0;
						this.World.Assets.addMoney(-350);
						local bro = ::AfeiExpedition.hireNamed(this, {
							Background = "afei_c30_background",
							Name = "罗一可",
							Title = "罗一可",
							NamedId = "C30",
							Attrs = [56, 91, 39, 113, 57, 41, 6, 3],
							Wage = 16,
							Place = 8,
							Skills = ["afei_two_steps", "afei_door_block", "afei_long_run_breath"]
						});
						local talents = bro.getTalents();
						talents.resize(this.Const.Attributes.COUNT, 0);
						for (local i = 0; i < this.Const.Attributes.COUNT; i++) { talents[i] = 0; }
						talents[this.Const.Attributes.Fatigue] = 1;
						talents[this.Const.Attributes.MeleeSkill] = 3;
						talents[this.Const.Attributes.MeleeDefense] = 2;
						bro.getSkills().update();
						this.World.Flags.set(::AfeiExpedition.Flags.R27Done, 1);
						this.World.Flags.set(::AfeiExpedition.Flags.R27Offered, 1);
						return 0;
			} }],
			function start(_event) {
				this.List.push({ id=10, icon="ui/icons/asset_money.png", text="支付 [color=#8f2525]350[/color] 克朗" });
			}
		});
		this.m.Screens.push({
			ID = "Poor",
			Text = "%terrainImage%{资源不够。线索留着。}",
			Image = "", List = [], Characters = [],
			Options = [{ Text = "知道了。", function getResult(_event) { this.World.Flags.set(::AfeiExpedition.Flags.R27Offered, 1); return 0; } }],
			function start(_event) {}
		});
	}
	function onUpdateScore()
	{
		if (!::AfeiExpedition.isAfeiOrigin()) return;
		if (this.World.Flags.get(::AfeiExpedition.Flags.R27Done)) return;
		if (::AfeiExpedition.hasNamed("C30")) return;
				if (this.World.getTime().Days < 50) { return; }
		if (::AfeiExpedition.getPaidContracts() < 17) { return; }
		if (this.World.getPlayerRoster().getSize() >= this.World.Assets.getBrothersMax()) return;
		this.m.Score = this.World.Flags.get(::AfeiExpedition.Flags.R27Offered) ? 15 : 30;
	}
	function onPrepare() {}
	function onPrepareVariables(_vars) {}
	function onClear() {}
});

this.afei_r08_event <- this.inherit("scripts/events/event", {
	m = {},
	function create()
	{
		this.m.ID = "event.afei_r08_event";
		this.m.Title = "招募 · 川神";
		this.m.Cooldown = 7.0 * this.World.getTime().SecondsPerDay;
		this.m.Screens.push({
			ID = "A",
			Text = "%terrainImage%{蓝旗同行之后，川神带着裂口的队形图来找黑旗。完成一次普通营地复盘后，可付 [color=#8f2525]800[/color] 克朗签约。\n\n暂缓不消失；满员或缺钱时可晚些再见。}",
			Image = "", List = [], Characters = [],
			Options = [
				{ Text = "开始相遇/演练。", function getResult(_event) { return "B"; } },
				{ Text = "线索留着。", function getResult(_event) { this.World.Flags.set(::AfeiExpedition.Flags.R08Offered, 1); return 0; } }
			],
			function start(_event) {}
		});
		this.m.Screens.push({
			ID = "B",
			Text = "%terrainImage%{演练/委托结束。签约费 [color=#8f2525]800[/color] 克朗。身份 C11，入队 1 级 0 经验。}",
			Image = "", List = [], Characters = [],
			Options = [
				{ Text = "支付 800 克朗签约。", function getResult(_event) {
						if (this.World.Assets.getMoney() < 800) return "Poor";
						
						return "Hire";
				} },
				{ Text = "先不签。", function getResult(_event) { this.World.Flags.set(::AfeiExpedition.Flags.R08Offered, 1); return 0; } }
			],
			function start(_event) {}
		});
		this.m.Screens.push({
			ID = "Hire",
			Text = "%terrainImage%{黑旗名册多了一行：川神。}",
			Image = "", List = [], Characters = [],
			Options = [{ Text = "欢迎入队。", function getResult(_event) {
						if (::AfeiExpedition.hasNamed("C11")) return 0;
						this.World.Assets.addMoney(-800);
						local bro = ::AfeiExpedition.hireNamed(this, {
							Background = "afei_c11_background",
							Name = "川神",
							Title = "川神",
							NamedId = "C11",
							Attrs = [57, 98, 55, 96, 55, 34, 4, 3],
							Wage = 18,
							Place = 6,
							Skills = ["afei_blue_form", "afei_steady_hand", "afei_good_card"]
						});
						local talents = bro.getTalents();
						talents.resize(this.Const.Attributes.COUNT, 0);
						for (local i = 0; i < this.Const.Attributes.COUNT; i++) { talents[i] = 0; }
						talents[this.Const.Attributes.Fatigue] = 1;
						talents[this.Const.Attributes.Bravery] = 2;
						talents[this.Const.Attributes.MeleeSkill] = 2;
						bro.getSkills().update();
						this.World.Flags.set(::AfeiExpedition.Flags.R08Done, 1);
						this.World.Flags.set(::AfeiExpedition.Flags.R08Offered, 1);
						return 0;
			} }],
			function start(_event) {
				this.List.push({ id=10, icon="ui/icons/asset_money.png", text="支付 [color=#8f2525]800[/color] 克朗" });
			}
		});
		this.m.Screens.push({
			ID = "Poor",
			Text = "%terrainImage%{资源不够。线索留着。}",
			Image = "", List = [], Characters = [],
			Options = [{ Text = "知道了。", function getResult(_event) { this.World.Flags.set(::AfeiExpedition.Flags.R08Offered, 1); return 0; } }],
			function start(_event) {}
		});
	}
	function onUpdateScore()
	{
		if (!::AfeiExpedition.isAfeiOrigin()) return;
		if (this.World.Flags.get(::AfeiExpedition.Flags.R08Done)) return;
		if (::AfeiExpedition.hasNamed("C11")) return;
				if (this.World.getTime().Days < 25) { return; }
		if (::AfeiExpedition.getPaidContracts() < 8) { return; }
		if (!this.World.Flags.get(::AfeiExpedition.Flags.M04Done)) { return; }
		if (this.World.getPlayerRoster().getSize() >= this.World.Assets.getBrothersMax()) return;
		this.m.Score = this.World.Flags.get(::AfeiExpedition.Flags.R08Offered) ? 15 : 30;
	}
	function onPrepare() {}
	function onPrepareVariables(_vars) {}
	function onClear() {}
});

this.afei_r14_event <- this.inherit("scripts/events/event", {
	m = {},
	function create()
	{
		this.m.ID = "event.afei_r14_event";
		this.m.Title = "招募 · 可可";
		this.m.Cooldown = 7.0 * this.World.getTime().SecondsPerDay;
		this.m.Screens.push({
			ID = "A",
			Text = "%terrainImage%{磨合够了就聚餐：消耗约 6 食物。再付 [color=#8f2525]600[/color] 克朗。\n\n暂缓不消失；满员或缺钱时可晚些再见。}",
			Image = "", List = [], Characters = [],
			Options = [
				{ Text = "开始相遇/演练。", function getResult(_event) { return "B"; } },
				{ Text = "线索留着。", function getResult(_event) { this.World.Flags.set(::AfeiExpedition.Flags.R14Offered, 1); return 0; } }
			],
			function start(_event) {}
		});
		this.m.Screens.push({
			ID = "B",
			Text = "%terrainImage%{演练/委托结束。签约费 [color=#8f2525]600[/color] 克朗。身份 C17，入队 1 级 0 经验。}",
			Image = "", List = [], Characters = [],
			Options = [
				{ Text = "支付 600 克朗签约。", function getResult(_event) {
						if (this.World.Assets.getMoney() < 600) return "Poor";
						
						if (!::AfeiExpedition.trySpendFoodApprox(6)) { return "Poor"; }

						return "Hire";
				} },
				{ Text = "先不签。", function getResult(_event) { this.World.Flags.set(::AfeiExpedition.Flags.R14Offered, 1); return 0; } }
			],
			function start(_event) {}
		});
		this.m.Screens.push({
			ID = "Hire",
			Text = "%terrainImage%{黑旗名册多了一行：可可。}",
			Image = "", List = [], Characters = [],
			Options = [{ Text = "欢迎入队。", function getResult(_event) {
						if (::AfeiExpedition.hasNamed("C17")) return 0;
						this.World.Assets.addMoney(-600);
						local bro = ::AfeiExpedition.hireNamed(this, {
							Background = "afei_c17_background",
							Name = "可可",
							Title = "可可",
							NamedId = "C17",
							Attrs = [50, 93, 48, 105, 43, 55, 2, 6],
							Wage = 15,
							Place = 13,
							Skills = ["afei_own_people", "afei_pokemon", "afei_breathe_easy"]
						});
						local talents = bro.getTalents();
						talents.resize(this.Const.Attributes.COUNT, 0);
						for (local i = 0; i < this.Const.Attributes.COUNT; i++) { talents[i] = 0; }
						talents[this.Const.Attributes.Bravery] = 2;
						talents[this.Const.Attributes.Initiative] = 1;
						talents[this.Const.Attributes.RangedSkill] = 2;
						bro.getSkills().update();
						this.World.Flags.set(::AfeiExpedition.Flags.R14Done, 1);
						this.World.Flags.set(::AfeiExpedition.Flags.R14Offered, 1);
						return 0;
			} }],
			function start(_event) {
				this.List.push({ id=10, icon="ui/icons/asset_money.png", text="支付 [color=#8f2525]600[/color] 克朗" });
			}
		});
		this.m.Screens.push({
			ID = "Poor",
			Text = "%terrainImage%{资源不够。线索留着。}",
			Image = "", List = [], Characters = [],
			Options = [{ Text = "知道了。", function getResult(_event) { this.World.Flags.set(::AfeiExpedition.Flags.R14Offered, 1); return 0; } }],
			function start(_event) {}
		});
	}
	function onUpdateScore()
	{
		if (!::AfeiExpedition.isAfeiOrigin()) return;
		if (this.World.Flags.get(::AfeiExpedition.Flags.R14Done)) return;
		if (::AfeiExpedition.hasNamed("C17")) return;
				if (this.World.getTime().Days < 42) { return; }
		if (::AfeiExpedition.getPaidContracts() < 12) { return; }
		if (this.World.Flags.getAsInt("afei_cohesion") < 45) { return; }
		if (this.World.getPlayerRoster().getSize() >= this.World.Assets.getBrothersMax()) return;
		this.m.Score = this.World.Flags.get(::AfeiExpedition.Flags.R14Offered) ? 15 : 30;
	}
	function onPrepare() {}
	function onPrepareVariables(_vars) {}
	function onClear() {}
});

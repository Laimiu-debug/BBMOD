this.afei_r28_event <- this.inherit("scripts/events/event", {
	m = {},
	function create()
	{
		this.m.ID = "event.afei_r28_event";
		this.m.Title = "招募 · bula";
		this.m.Cooldown = 7.0 * this.World.getTime().SecondsPerDay;
		this.m.Screens.push({
			ID = "A",
			Text = "%terrainImage%{商旅公用钱袋核账后。签约 [color=#8f2525]360[/color] 克朗。\n\n暂缓不消失；满员或缺钱时可晚些再见。}",
			Image = "ui/events/afei_portrait_c31.png", List = [], Characters = [],
			Options = [
				{ Text = "开始相遇/演练。", function getResult(_event) { return "B"; } },
				{ Text = "线索留着。", function getResult(_event) { this.World.Flags.set(::AfeiExpedition.Flags.R28Offered, 1); return 0; } }
			],
			function start(_event) {}
		});
		this.m.Screens.push({
			ID = "B",
			Text = "%terrainImage%{演练/委托结束。签约费 [color=#8f2525]360[/color] 克朗。身份 C31，入队 1 级 0 经验。}",
			Image = "", List = [], Characters = [],
			Options = [
				{ Text = "支付 360 克朗签约。", function getResult(_event) {
						if (this.World.Assets.getMoney() < 360) return "Poor";
						
						return "Hire";
				} },
				{ Text = "先不签。", function getResult(_event) { this.World.Flags.set(::AfeiExpedition.Flags.R28Offered, 1); return 0; } }
			],
			function start(_event) {}
		});
		this.m.Screens.push({
			ID = "Hire",
			Text = "%terrainImage%{黑旗名册多了一行：bula。}",
			Image = "", List = [], Characters = [],
			Options = [{ Text = "欢迎入队。", function getResult(_event) {
						if (::AfeiExpedition.hasNamed("C31")) return 0;
						if (!::AfeiExpedition.tryChargeHire("C31", 360))
						{
							return "Poor";
						}

						local bro = ::AfeiExpedition.hireNamed(this, {
							Background = "afei_c31_background",
							Name = "bula",
							Title = "bula",
							NamedId = "C31",
							Attrs = [55, 96, 45, 107, 47, 51, 4, 5],
							Wage = 16,
							Place = 13,
							Skills = ["afei_purse_clear", "afei_no_last_throw", "afei_budget_share"]
						});
						local talents = bro.getTalents();
						talents.resize(this.Const.Attributes.COUNT, 0);
						for (local i = 0; i < this.Const.Attributes.COUNT; i++) { talents[i] = 0; }
						talents[this.Const.Attributes.Fatigue] = 2;
						talents[this.Const.Attributes.Bravery] = 1;
						talents[this.Const.Attributes.RangedSkill] = 3;
						bro.getSkills().update();
						this.World.Flags.set(::AfeiExpedition.Flags.R28Done, 1);
						this.World.Flags.set(::AfeiExpedition.Flags.R28Offered, 1);
						return 0;
			} }],
			function start(_event) {
				this.List.push({ id=10, icon="ui/icons/asset_money.png", text="支付 [color=#8f2525]360[/color] 克朗" });
			}
		});
		this.m.Screens.push({
			ID = "Poor",
			Text = "%terrainImage%{资源不够。线索留着。}",
			Image = "", List = [], Characters = [],
			Options = [{ Text = "知道了。", function getResult(_event) { this.World.Flags.set(::AfeiExpedition.Flags.R28Offered, 1); return 0; } }],
			function start(_event) {}
		});
	}
	function onUpdateScore()
	{
		if (!::AfeiExpedition.isAfeiOrigin()) return;
		if (this.World.Flags.get(::AfeiExpedition.Flags.R28Done)) return;
		if (::AfeiExpedition.hasNamed("C31")) return;
				if (this.World.getTime().Days < 58) { return; }
		if (::AfeiExpedition.getPaidContracts() < 20) { return; }
		if (this.World.getPlayerRoster().getSize() >= this.World.Assets.getBrothersMax()) return;
		this.m.Score = this.World.Flags.get(::AfeiExpedition.Flags.R28Offered) ? 15 : 30;
	}
	function onPrepare() {}
	function onPrepareVariables(_vars) {}
	function onClear() {}
});

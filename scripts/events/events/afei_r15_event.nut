this.afei_r15_event <- this.inherit("scripts/events/event", {
	m = {},
	function create()
	{
		this.m.ID = "event.afei_r15_event";
		this.m.Title = "招募 · 童猪";
		this.m.Cooldown = 7.0 * this.World.getTime().SecondsPerDay;
		this.m.Screens.push({
			ID = "A",
			Text = "%terrainImage%{M05 之后正式邀请童猪。答错不封锁。签约 [color=#8f2525]750[/color] 克朗。\n\n暂缓不消失；满员或缺钱时可晚些再见。}",
			Image = "", List = [], Characters = [],
			Options = [
				{ Text = "开始相遇/演练。", function getResult(_event) { return "B"; } },
				{ Text = "线索留着。", function getResult(_event) { this.World.Flags.set(::AfeiExpedition.Flags.R15Offered, 1); return 0; } }
			],
			function start(_event) {}
		});
		this.m.Screens.push({
			ID = "B",
			Text = "%terrainImage%{演练/委托结束。签约费 [color=#8f2525]750[/color] 克朗。身份 C18，入队 1 级 0 经验。}",
			Image = "", List = [], Characters = [],
			Options = [
				{ Text = "支付 750 克朗签约。", function getResult(_event) {
						if (this.World.Assets.getMoney() < 750) return "Poor";
						
						return "Hire";
				} },
				{ Text = "先不签。", function getResult(_event) { this.World.Flags.set(::AfeiExpedition.Flags.R15Offered, 1); return 0; } }
			],
			function start(_event) {}
		});
		this.m.Screens.push({
			ID = "Hire",
			Text = "%terrainImage%{黑旗名册多了一行：童猪。}",
			Image = "", List = [], Characters = [],
			Options = [{ Text = "欢迎入队。", function getResult(_event) {
						if (::AfeiExpedition.hasNamed("C18")) return 0;
						if (!::AfeiExpedition.tryChargeHire("C18", 750))
						{
							return "Poor";
						}

						local bro = ::AfeiExpedition.hireNamed(this, {
							Background = "afei_c18_background",
							Name = "童猪",
							Title = "童猪",
							NamedId = "C18",
							Attrs = [56, 98, 56, 99, 49, 35, 4, 3],
							Wage = 17,
							Place = 9,
							Skills = ["afei_bear_strike", "afei_know_rules", "afei_cup_signal"]
						});
						local talents = bro.getTalents();
						talents.resize(this.Const.Attributes.COUNT, 0);
						for (local i = 0; i < this.Const.Attributes.COUNT; i++) { talents[i] = 0; }
						talents[this.Const.Attributes.Fatigue] = 2;
						talents[this.Const.Attributes.Bravery] = 3;
						talents[this.Const.Attributes.MeleeSkill] = 1;
						bro.getSkills().update();
						this.World.Flags.set(::AfeiExpedition.Flags.R15Done, 1);
						this.World.Flags.set(::AfeiExpedition.Flags.R15Offered, 1);
						return 0;
			} }],
			function start(_event) {
				this.List.push({ id=10, icon="ui/icons/asset_money.png", text="支付 [color=#8f2525]750[/color] 克朗" });
			}
		});
		this.m.Screens.push({
			ID = "Poor",
			Text = "%terrainImage%{资源不够。线索留着。}",
			Image = "", List = [], Characters = [],
			Options = [{ Text = "知道了。", function getResult(_event) { this.World.Flags.set(::AfeiExpedition.Flags.R15Offered, 1); return 0; } }],
			function start(_event) {}
		});
	}
	function onUpdateScore()
	{
		if (!::AfeiExpedition.isAfeiOrigin()) return;
		if (this.World.Flags.get(::AfeiExpedition.Flags.R15Done)) return;
		if (::AfeiExpedition.hasNamed("C18")) return;
				if (this.World.getTime().Days < 45) { return; }
		if (::AfeiExpedition.getPaidContracts() < 12) { return; }
		if (!this.World.Flags.get(::AfeiExpedition.Flags.M05Done)) { return; }
		if (this.World.getPlayerRoster().getSize() >= this.World.Assets.getBrothersMax()) return;
		this.m.Score = this.World.Flags.get(::AfeiExpedition.Flags.R15Offered) ? 15 : 30;
	}
	function onPrepare() {}
	function onPrepareVariables(_vars) {}
	function onClear() {}
});

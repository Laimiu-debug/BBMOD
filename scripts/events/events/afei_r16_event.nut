this.afei_r16_event <- this.inherit("scripts/events/event", {
	m = {},
	function create()
	{
		this.m.ID = "event.afei_r16_event";
		this.m.Title = "招募 · 奶盖";
		this.m.Cooldown = 7.0 * this.World.getTime().SecondsPerDay;
		this.m.Screens.push({
			ID = "A",
			Text = "%terrainImage%{两段安全试训后，奶盖谈签约 [color=#8f2525]650[/color] 克朗。\n\n暂缓不消失；满员或缺钱时可晚些再见。}",
			Image = "", List = [], Characters = [],
			Options = [
				{ Text = "开始相遇/演练。", function getResult(_event) { return "B"; } },
				{ Text = "线索留着。", function getResult(_event) { this.World.Flags.set(::AfeiExpedition.Flags.R16Offered, 1); return 0; } }
			],
			function start(_event) {}
		});
		this.m.Screens.push({
			ID = "B",
			Text = "%terrainImage%{演练/委托结束。签约费 [color=#8f2525]650[/color] 克朗。身份 C19，入队 1 级 0 经验。}",
			Image = "", List = [], Characters = [],
			Options = [
				{ Text = "支付 650 克朗签约。", function getResult(_event) {
						if (this.World.Assets.getMoney() < 650) return "Poor";
						
						return "Hire";
				} },
				{ Text = "先不签。", function getResult(_event) { this.World.Flags.set(::AfeiExpedition.Flags.R16Offered, 1); return 0; } }
			],
			function start(_event) {}
		});
		this.m.Screens.push({
			ID = "Hire",
			Text = "%terrainImage%{黑旗名册多了一行：奶盖。}",
			Image = "", List = [], Characters = [],
			Options = [{ Text = "欢迎入队。", function getResult(_event) {
						if (::AfeiExpedition.hasNamed("C19")) return 0;
						if (!::AfeiExpedition.tryChargeHire("C19", 650))
						{
							return "Poor";
						}

						local bro = ::AfeiExpedition.hireNamed(this, {
							Background = "afei_c19_background",
							Name = "奶盖",
							Title = "奶盖",
							NamedId = "C19",
							Attrs = [54, 98, 32, 108, 44, 50, 4, 4],
							Wage = 15,
							Place = 10,
							Skills = ["afei_mouth_strong", "afei_shrink_cover", "afei_abs_comeback"]
						});
						local talents = bro.getTalents();
						talents.resize(this.Const.Attributes.COUNT, 0);
						for (local i = 0; i < this.Const.Attributes.COUNT; i++) { talents[i] = 0; }
						talents[this.Const.Attributes.Fatigue] = 1;
						talents[this.Const.Attributes.RangedSkill] = 2;
						talents[this.Const.Attributes.MeleeDefense] = 3;
						bro.getSkills().update();
						this.World.Flags.set(::AfeiExpedition.Flags.R16Done, 1);
						this.World.Flags.set(::AfeiExpedition.Flags.R16Offered, 1);
						return 0;
			} }],
			function start(_event) {
				this.List.push({ id=10, icon="ui/icons/asset_money.png", text="支付 [color=#8f2525]650[/color] 克朗" });
			}
		});
		this.m.Screens.push({
			ID = "Poor",
			Text = "%terrainImage%{资源不够。线索留着。}",
			Image = "", List = [], Characters = [],
			Options = [{ Text = "知道了。", function getResult(_event) { this.World.Flags.set(::AfeiExpedition.Flags.R16Offered, 1); return 0; } }],
			function start(_event) {}
		});
	}
	function onUpdateScore()
	{
		if (!::AfeiExpedition.isAfeiOrigin()) return;
		if (this.World.Flags.get(::AfeiExpedition.Flags.R16Done)) return;
		if (::AfeiExpedition.hasNamed("C19")) return;
				if (this.World.getTime().Days < 48) { return; }
		if (::AfeiExpedition.getPaidContracts() < 14) { return; }
		if (this.World.Flags.getAsInt("afei_cohesion") < 45) { return; }
		if (this.World.getPlayerRoster().getSize() >= this.World.Assets.getBrothersMax()) return;
		this.m.Score = this.World.Flags.get(::AfeiExpedition.Flags.R16Offered) ? 15 : 30;
	}
	function onPrepare() {}
	function onPrepareVariables(_vars) {}
	function onClear() {}
});

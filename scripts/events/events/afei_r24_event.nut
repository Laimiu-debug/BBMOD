this.afei_r24_event <- this.inherit("scripts/events/event", {
	m = {},
	function create()
	{
		this.m.ID = "event.afei_r24_event";
		this.m.Title = "招募 · 瑶瑶牙";
		this.m.Cooldown = 7.0 * this.World.getTime().SecondsPerDay;
		this.m.Screens.push({
			ID = "A",
			Text = "%terrainImage%{修车铺长柄斧线索。签约 [color=#8f2525]500[/color] 克朗。\n\n暂缓不消失；满员或缺钱时可晚些再见。}",
			Image = "", List = [], Characters = [],
			Options = [
				{ Text = "开始相遇/演练。", function getResult(_event) { return "B"; } },
				{ Text = "线索留着。", function getResult(_event) { this.World.Flags.set(::AfeiExpedition.Flags.R24Offered, 1); return 0; } }
			],
			function start(_event) {}
		});
		this.m.Screens.push({
			ID = "B",
			Text = "%terrainImage%{演练/委托结束。签约费 [color=#8f2525]500[/color] 克朗。身份 C27，入队 1 级 0 经验。}",
			Image = "", List = [], Characters = [],
			Options = [
				{ Text = "支付 500 克朗签约。", function getResult(_event) {
						if (this.World.Assets.getMoney() < 500) return "Poor";
						
						return "Hire";
				} },
				{ Text = "先不签。", function getResult(_event) { this.World.Flags.set(::AfeiExpedition.Flags.R24Offered, 1); return 0; } }
			],
			function start(_event) {}
		});
		this.m.Screens.push({
			ID = "Hire",
			Text = "%terrainImage%{黑旗名册多了一行：瑶瑶牙。}",
			Image = "", List = [], Characters = [],
			Options = [{ Text = "欢迎入队。", function getResult(_event) {
						if (::AfeiExpedition.hasNamed("C27")) return 0;
						if (!::AfeiExpedition.tryChargeHire("C27", 500))
						{
							return "Poor";
						}

						local bro = ::AfeiExpedition.hireNamed(this, {
							Background = "afei_c27_background",
							Name = "瑶瑶牙",
							Title = "瑶瑶牙",
							NamedId = "C27",
							Attrs = [68, 112, 41, 90, 60, 30, 3, 0],
							Wage = 23,
							Place = 3,
							Skills = ["afei_lvbu_weapon", "afei_breach_strike", "afei_look_flag"]
						});
						local talents = bro.getTalents();
						talents.resize(this.Const.Attributes.COUNT, 0);
						for (local i = 0; i < this.Const.Attributes.COUNT; i++) { talents[i] = 0; }
						talents[this.Const.Attributes.Hitpoints] = 2;
						talents[this.Const.Attributes.Fatigue] = 2;
						talents[this.Const.Attributes.MeleeSkill] = 3;
						bro.getSkills().update();
						this.World.Flags.set(::AfeiExpedition.Flags.R24Done, 1);
						this.World.Flags.set(::AfeiExpedition.Flags.R24Offered, 1);
						return 0;
			} }],
			function start(_event) {
				this.List.push({ id=10, icon="ui/icons/asset_money.png", text="支付 [color=#8f2525]500[/color] 克朗" });
			}
		});
		this.m.Screens.push({
			ID = "Poor",
			Text = "%terrainImage%{资源不够。线索留着。}",
			Image = "", List = [], Characters = [],
			Options = [{ Text = "知道了。", function getResult(_event) { this.World.Flags.set(::AfeiExpedition.Flags.R24Offered, 1); return 0; } }],
			function start(_event) {}
		});
	}
	function onUpdateScore()
	{
		if (!::AfeiExpedition.isAfeiOrigin()) return;
		if (this.World.Flags.get(::AfeiExpedition.Flags.R24Done)) return;
		if (::AfeiExpedition.hasNamed("C27")) return;
				if (this.World.getTime().Days < 40) { return; }
		if (::AfeiExpedition.getPaidContracts() < 13) { return; }
		if (this.World.getPlayerRoster().getSize() >= this.World.Assets.getBrothersMax()) return;
		this.m.Score = this.World.Flags.get(::AfeiExpedition.Flags.R24Offered) ? 15 : 30;
	}
	function onPrepare() {}
	function onPrepareVariables(_vars) {}
	function onClear() {}
});

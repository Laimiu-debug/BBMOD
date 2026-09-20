this.afei_r26_event <- this.inherit("scripts/events/event", {
	m = {},
	function create()
	{
		this.m.ID = "event.afei_r26_event";
		this.m.Title = "招募 · 一凹瑶";
		this.m.Cooldown = 7.0 * this.World.getTime().SecondsPerDay;
		this.m.Screens.push({
			ID = "A",
			Text = "%terrainImage{联合营地开放反应试训。一凹瑶把铃交给你们看一眼，说来过后可付 [color=#8f2525]420[/color] 克朗。\n\n暂缓不消失；满员或缺钱时可晚些再见。}",
			Image = "", List = [], Characters = [],
			Options = [
				{ Text = "开始相遇。", function getResult(_event) { return "Drill"; } },
				{ Text = "线索留着。", function getResult(_event) { this.World.Flags.set(::AfeiExpedition.Flags.R26Offered, 1); return 0; } }
			],
			function start(_event) {}
		});
		this.m.Screens.push({
			ID = "Drill",
			Text = "%terrainImage{接棒增益只给还没结束行动的人。她说铃可以交出去。}",
			Image = "", List = [], Characters = [],
			Options = [
				{ Text = "谈签约。", function getResult(_event) { return "B"; } },
				{ Text = "今天先停。", function getResult(_event) { this.World.Flags.set(::AfeiExpedition.Flags.R26Offered, 1); return 0; } }
			],
			function start(_event) {}
		});
		this.m.Screens.push({
			ID = "B",
			Text = "%terrainImage{签约费 [color=#8f2525]420[/color] 克朗。身份 C29，入队 1 级 0 经验。}",
			Image = "", List = [], Characters = [],
			Options = [
				{ Text = "支付 420 克朗签约。", function getResult(_event) {
					if (this.World.Assets.getMoney() < 420) return "Poor";
					return "Hire";
				} },
				{ Text = "先不签。", function getResult(_event) { this.World.Flags.set(::AfeiExpedition.Flags.R26Offered, 1); return 0; } }
			],
			function start(_event) {}
		});
		this.m.Screens.push({
			ID = "Hire",
			Text = "%terrainImage{黑旗名册多了一行：一凹瑶。}",
			Image = "", List = [], Characters = [],
			Options = [{ Text = "欢迎入队。", function getResult(_event) {
						if (::AfeiExpedition.hasNamed("C29")) return 0;
						if (!::AfeiExpedition.tryChargeHire("C29", 420))
						{
							return "Poor";
						}

						local bro = ::AfeiExpedition.hireNamed(this, {
							Background = "afei_c29_background",
							Name = "一凹瑶",
							Title = "一凹瑶",
							NamedId = "C29",
							Attrs = [55, 98, 43, 119, 55, 47, 5, 4],
							Wage = 18,
							Place = 11,
							Skills = ["afei_half_react", "afei_catch_baton", "afei_duck_turn"]
						});
						local talents = bro.getTalents();
						talents.resize(this.Const.Attributes.COUNT, 0);
												for (local i = 0; i < this.Const.Attributes.COUNT; i++) { talents[i] = 0; }
												talents[this.Const.Attributes.Bravery] = 1;
												talents[this.Const.Attributes.Initiative] = 3;
												talents[this.Const.Attributes.MeleeSkill] = 2;
						bro.getSkills().update();
						this.World.Flags.set(::AfeiExpedition.Flags.R26Done, 1);
						this.World.Flags.set(::AfeiExpedition.Flags.R26Offered, 1);
						return 0;
			} }],
			function start(_event) {
				this.List.push({ id=10, icon="ui/icons/asset_money.png", text="支付 [color=#8f2525]420[/color] 克朗" });
			}
		});
		this.m.Screens.push({
			ID = "Poor",
			Text = "%terrainImage{资源不够。线索留着，人不消失。}",
			Image = "", List = [], Characters = [],
			Options = [{ Text = "知道了。", function getResult(_event) { this.World.Flags.set(::AfeiExpedition.Flags.R26Offered, 1); return 0; } }],
			function start(_event) {}
		});
	}
	function onUpdateScore()
	{
		if (!::AfeiExpedition.isAfeiOrigin()) return;
		if (this.World.Flags.get(::AfeiExpedition.Flags.R26Done)) return;
		if (::AfeiExpedition.hasNamed("C29")) return;
		if (this.World.getTime().Days < 48) { return; }
		if (::AfeiExpedition.getPaidContracts() < 16) { return; }
		if (this.World.getPlayerRoster().getSize() >= this.World.Assets.getBrothersMax()) return;
		this.m.Score = this.World.Flags.get(::AfeiExpedition.Flags.R26Offered) ? 15 : 30;
	}
	function onPrepare() {}
	function onPrepareVariables(_vars) {}
	function onClear() {}
});

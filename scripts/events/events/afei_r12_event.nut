this.afei_r12_event <- this.inherit("scripts/events/event", {
	m = {},
	function create()
	{
		this.m.ID = "event.afei_r12_event";
		this.m.Title = "招募 · 苏袜";
		this.m.Cooldown = 7.0 * this.World.getTime().SecondsPerDay;
		this.m.Screens.push({
			ID = "A",
			Text = "%terrainImage{苏袜要带你们做一段大约四小时的踏勘，确认两个岔路口怎么记、怎么交给别人用。不耗额外物资，也不搞速度排行榜。\n\n谈妥再付 [color=#8f2525]600[/color] 克朗。}",
			Image = "", List = [], Characters = [],
			Options = [
				{ Text = "开始相遇/演练。", function getResult(_event) { return "Drill"; } },
				{ Text = "线索留着。", function getResult(_event) { this.World.Flags.set(::AfeiExpedition.Flags.R12Offered, 1); return 0; } }
			],
			function start(_event) {}
		});
		this.m.Screens.push({
			ID = "Drill",
			Text = "%terrainImage{怎么进行？两条路都能完成同一次入团步骤。}",
			Image = "", List = [], Characters = [],
			Options = [
				{ Text = "边走边记岔路。", function getResult(_event) { return "DrillA"; } },
				{ Text = "到站后复述路线。", function getResult(_event) { return "DrillB"; } },
				{ Text = "今天先停。", function getResult(_event) { this.World.Flags.set(::AfeiExpedition.Flags.R12Offered, 1); return 0; } }
			],
			function start(_event) {}
		});
		this.m.Screens.push({
			ID = "DrillA",
			Text = "%terrainImage{你们边走边记。苏袜在两处岔路各钉一枚记号，让后到的人也能读懂。}",
			Image = "", List = [], Characters = [],
			Options = [{ Text = "谈签约。", function getResult(_event) { return "B"; } }],
			function start(_event) {}
		});
		this.m.Screens.push({
			ID = "DrillB",
			Text = "%terrainImage{你们到站后复述。苏袜听完，只改了两处容易说反的地名，把路线交回给你们。}",
			Image = "", List = [], Characters = [],
			Options = [{ Text = "谈签约。", function getResult(_event) { return "B"; } }],
			function start(_event) {}
		});
		this.m.Screens.push({
			ID = "B",
			Text = "%terrainImage{踏勘结束。签约费 [color=#8f2525]600[/color] 克朗。身份 C15，入队一级零经验。}",
			Image = "", List = [], Characters = [],
			Options = [
				{ Text = "支付 600 克朗签约。", function getResult(_event) {
					if (this.World.Assets.getMoney() < 600) return "Poor";
					return "Hire";
				} },
				{ Text = "先不签。", function getResult(_event) { this.World.Flags.set(::AfeiExpedition.Flags.R12Offered, 1); return 0; } }
			],
			function start(_event) {}
		});
		this.m.Screens.push({
			ID = "Hire",
			Text = "%terrainImage{苏袜入册。先到的本事还在，队友终于有机会跟得上。}",
			Image = "", List = [], Characters = [],
			Options = [{ Text = "欢迎入队。", function getResult(_event) {
						if (::AfeiExpedition.hasNamed("C15")) return 0;
						if (!::AfeiExpedition.tryChargeHire("C15", 600))
						{
							return "Poor";
						}

						local bro = ::AfeiExpedition.hireNamed(this, {
							Background = "afei_c15_background",
							Name = "苏袜",
							Title = "苏袜",
							NamedId = "C15",
							Attrs = [52, 106, 39, 125, 49, 50, 4, 6],
							Wage = 15,
							Place = 15,
							Skills = ["afei_foot_point", "afei_half_step", "afei_hard_brake"]
						});
						local talents = bro.getTalents();
						talents.resize(this.Const.Attributes.COUNT, 0);
												for (local i = 0; i < this.Const.Attributes.COUNT; i++) { talents[i] = 0; }
												talents[this.Const.Attributes.Fatigue] = 2;
												talents[this.Const.Attributes.Initiative] = 3;
												talents[this.Const.Attributes.RangedSkill] = 1;
						bro.getSkills().update();
						this.World.Flags.set(::AfeiExpedition.Flags.R12Done, 1);
						this.World.Flags.set(::AfeiExpedition.Flags.R12Offered, 1);
						return 0;
			} }],
			function start(_event) {
				this.List.push({ id=10, icon="ui/icons/asset_money.png", text="支付 [color=#8f2525]600[/color] 克朗" });
			}
		});
		this.m.Screens.push({
			ID = "Poor",
			Text = "%terrainImage{资源不够。线索留着，人不消失。}",
			Image = "", List = [], Characters = [],
			Options = [{ Text = "知道了。", function getResult(_event) { this.World.Flags.set(::AfeiExpedition.Flags.R12Offered, 1); return 0; } }],
			function start(_event) {}
		});
	}
	function onUpdateScore()
	{
		if (!::AfeiExpedition.isAfeiOrigin()) return;
		if (this.World.Flags.get(::AfeiExpedition.Flags.R12Done)) return;
		if (::AfeiExpedition.hasNamed("C15")) return;
		if (this.World.getTime().Days < 38) { return; }
		if (::AfeiExpedition.getPaidContracts() < 10) { return; }
		if (this.World.getPlayerRoster().getSize() >= this.World.Assets.getBrothersMax()) return;
		this.m.Score = this.World.Flags.get(::AfeiExpedition.Flags.R12Offered) ? 15 : 30;
	}
	function onPrepare() {}
	function onPrepareVariables(_vars) {}
	function onClear() {}
});

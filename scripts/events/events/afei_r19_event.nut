this.afei_r19_event <- this.inherit("scripts/events/event", {
	m = {},
	function create()
	{
		this.m.ID = "event.afei_r19_event";
		this.m.Title = "招募 · 陈知含";
		this.m.Cooldown = 7.0 * this.World.getTime().SecondsPerDay;
		this.m.Screens.push({
			ID = "A",
			Text = "%terrainImage{城镇粮铺出现碎饼委托。陈知含把月饼皮捏紧，说相遇后可付 [color=#8f2525]260[/color] 克朗；钱不够也能晚些见。\n\n暂缓不消失；满员或缺钱时可晚些再见。}",
			Image = "", List = [], Characters = [],
			Options = [
				{ Text = "开始相遇。", function getResult(_event) { return "Drill"; } },
				{ Text = "线索留着。", function getResult(_event) { this.World.Flags.set(::AfeiExpedition.Flags.R19Offered, 1); return 0; } }
			],
			function start(_event) {}
		});
		this.m.Screens.push({
			ID = "Drill",
			Text = "%terrainImage{她把自己的那份留下，先问你们谁还没吃上热的。}",
			Image = "", List = [], Characters = [],
			Options = [
				{ Text = "谈签约。", function getResult(_event) { return "B"; } },
				{ Text = "今天先停。", function getResult(_event) { this.World.Flags.set(::AfeiExpedition.Flags.R19Offered, 1); return 0; } }
			],
			function start(_event) {}
		});
		this.m.Screens.push({
			ID = "B",
			Text = "%terrainImage{签约费 [color=#8f2525]260[/color] 克朗。身份 C22，入队 1 级 0 经验。}",
			Image = "", List = [], Characters = [],
			Options = [
				{ Text = "支付 260 克朗签约。", function getResult(_event) {
					if (this.World.Assets.getMoney() < 260) return "Poor";
					return "Hire";
				} },
				{ Text = "先不签。", function getResult(_event) { this.World.Flags.set(::AfeiExpedition.Flags.R19Offered, 1); return 0; } }
			],
			function start(_event) {}
		});
		this.m.Screens.push({
			ID = "Hire",
			Text = "%terrainImage{黑旗名册多了一行：陈知含。}",
			Image = "", List = [], Characters = [],
			Options = [{ Text = "欢迎入队。", function getResult(_event) {
						if (::AfeiExpedition.hasNamed("C22")) return 0;
						if (!::AfeiExpedition.tryChargeHire("C22", 260))
						{
							return "Poor";
						}

						local bro = ::AfeiExpedition.hireNamed(this, {
							Background = "afei_c22_background",
							Name = "陈知含",
							Title = "知含",
							NamedId = "C22",
							Attrs = [61, 103, 31, 93, 48, 28, 6, 2],
							Wage = 12,
							Place = 3,
							Skills = ["afei_remember_shield", "afei_guard_self", "afei_moon_cake"]
						});
						local talents = bro.getTalents();
						talents.resize(this.Const.Attributes.COUNT, 0);
												for (local i = 0; i < this.Const.Attributes.COUNT; i++) { talents[i] = 0; }
												talents[this.Const.Attributes.Hitpoints] = 2;
												talents[this.Const.Attributes.Fatigue] = 1;
												talents[this.Const.Attributes.MeleeDefense] = 3;
						bro.getSkills().update();
						this.World.Flags.set(::AfeiExpedition.Flags.R19Done, 1);
						this.World.Flags.set(::AfeiExpedition.Flags.R19Offered, 1);
						return 0;
			} }],
			function start(_event) {
				this.List.push({ id=10, icon="ui/icons/asset_money.png", text="支付 [color=#8f2525]260[/color] 克朗" });
			}
		});
		this.m.Screens.push({
			ID = "Poor",
			Text = "%terrainImage{资源不够。线索留着，人不消失。}",
			Image = "", List = [], Characters = [],
			Options = [{ Text = "知道了。", function getResult(_event) { this.World.Flags.set(::AfeiExpedition.Flags.R19Offered, 1); return 0; } }],
			function start(_event) {}
		});
	}
	function onUpdateScore()
	{
		if (!::AfeiExpedition.isAfeiOrigin()) return;
		if (this.World.Flags.get(::AfeiExpedition.Flags.R19Done)) return;
		if (::AfeiExpedition.hasNamed("C22")) return;
		if (this.World.getTime().Days < 32) { return; }
		if (::AfeiExpedition.getPaidContracts() < 10) { return; }
		if (this.World.getPlayerRoster().getSize() >= this.World.Assets.getBrothersMax()) return;
		this.m.Score = this.World.Flags.get(::AfeiExpedition.Flags.R19Offered) ? 15 : 30;
	}
	function onPrepare() {}
	function onPrepareVariables(_vars) {}
	function onClear() {}
});

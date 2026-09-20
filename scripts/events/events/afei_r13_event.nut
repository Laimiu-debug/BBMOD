this.afei_r13_event <- this.inherit("scripts/events/event", {
	m = {},
	function create()
	{
		this.m.ID = "event.afei_r13_event";
		this.m.Title = "招募 · 涂涂";
		this.m.Cooldown = 7.0 * this.World.getTime().SecondsPerDay;
		this.m.Screens.push({
			ID = "A",
			Text = "%terrainImage{一次正常护送结算之后，涂涂被正式邀请加入黑旗。她可以暂时告别，候选资格仍保留在日志里；加入以后，普通休整不会强制她离队。\n\n签约费 [color=#8f2525]550[/color] 克朗。}",
			Image = "", List = [], Characters = [],
			Options = [
				{ Text = "开始相遇/演练。", function getResult(_event) { return "Drill"; } },
				{ Text = "线索留着。", function getResult(_event) { this.World.Flags.set(::AfeiExpedition.Flags.R13Offered, 1); return 0; } }
			],
			function start(_event) {}
		});
		this.m.Screens.push({
			ID = "Drill",
			Text = "%terrainImage{护送的尘土还没落净。涂涂没有含糊地说「随便」，只问下一站名字是否已经写进路线。}",
			Image = "", List = [], Characters = [],
			Options = [
				{ Text = "继续谈签约。", function getResult(_event) { return "B"; } },
				{ Text = "今天先停。", function getResult(_event) { this.World.Flags.set(::AfeiExpedition.Flags.R13Offered, 1); return 0; } }
			],
			function start(_event) {}
		});
		this.m.Screens.push({
			ID = "B",
			Text = "%terrainImage{可以签约了。身份 C16，入队一级零经验。暂时告别也不会抹掉邀请。}",
			Image = "", List = [], Characters = [],
			Options = [
				{ Text = "支付 550 克朗签约。", function getResult(_event) {
					if (this.World.Assets.getMoney() < 550) return "Poor";
					return "Hire";
				} },
				{ Text = "先不签。", function getResult(_event) { this.World.Flags.set(::AfeiExpedition.Flags.R13Offered, 1); return 0; } }
			],
			function start(_event) {}
		});
		this.m.Screens.push({
			ID = "Hire",
			Text = "%terrainImage{涂涂在新路线旁添上自己的名字。回头路从这里开始记。}",
			Image = "", List = [], Characters = [],
			Options = [{ Text = "欢迎入队。", function getResult(_event) {
						if (::AfeiExpedition.hasNamed("C16")) return 0;
						if (!::AfeiExpedition.tryChargeHire("C16", 550))
						{
							return "Poor";
						}

						local bro = ::AfeiExpedition.hireNamed(this, {
							Background = "afei_c16_background",
							Name = "涂涂",
							Title = "涂涂",
							NamedId = "C16",
							Attrs = [58, 99, 46, 103, 53, 32, 5, 2],
							Wage = 14,
							Place = 8,
							Skills = ["afei_return_road", "afei_leave_not_gone", "afei_one_more_night"]
						});
						local talents = bro.getTalents();
						talents.resize(this.Const.Attributes.COUNT, 0);
												for (local i = 0; i < this.Const.Attributes.COUNT; i++) { talents[i] = 0; }
												talents[this.Const.Attributes.Fatigue] = 1;
												talents[this.Const.Attributes.MeleeSkill] = 2;
												talents[this.Const.Attributes.MeleeDefense] = 2;
						bro.getSkills().update();
						this.World.Flags.set(::AfeiExpedition.Flags.R13Done, 1);
						this.World.Flags.set(::AfeiExpedition.Flags.R13Offered, 1);
						return 0;
			} }],
			function start(_event) {
				this.List.push({ id=10, icon="ui/icons/asset_money.png", text="支付 [color=#8f2525]550[/color] 克朗" });
			}
		});
		this.m.Screens.push({
			ID = "Poor",
			Text = "%terrainImage{资源不够。线索留着，人不消失。}",
			Image = "", List = [], Characters = [],
			Options = [{ Text = "知道了。", function getResult(_event) { this.World.Flags.set(::AfeiExpedition.Flags.R13Offered, 1); return 0; } }],
			function start(_event) {}
		});
	}
	function onUpdateScore()
	{
		if (!::AfeiExpedition.isAfeiOrigin()) return;
		if (this.World.Flags.get(::AfeiExpedition.Flags.R13Done)) return;
		if (::AfeiExpedition.hasNamed("C16")) return;
		if (this.World.getTime().Days < 40) { return; }
		if (::AfeiExpedition.getPaidContracts() < 12) { return; }
		if (this.World.getPlayerRoster().getSize() >= this.World.Assets.getBrothersMax()) return;
		this.m.Score = this.World.Flags.get(::AfeiExpedition.Flags.R13Offered) ? 15 : 30;
	}
	function onPrepare() {}
	function onPrepareVariables(_vars) {}
	function onClear() {}
});

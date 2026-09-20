this.afei_r10_event <- this.inherit("scripts/events/event", {
	m = {},
	function create()
	{
		this.m.ID = "event.afei_r10_event";
		this.m.Title = "招募 · 大鹅";
		this.m.Cooldown = 7.0 * this.World.getTime().SecondsPerDay;
		this.m.Screens.push({
			ID = "A",
			Text = "%terrainImage{有人弄丢了补给箱。大鹅愿意一起找：可以先侦察，也可以按正常强度打一场遭遇。签约前不会生成一个会被你们误杀的永久角色。\n\n失败的话，七日后还能再试；线索不消失。}",
			Image = "", List = [], Characters = [],
			Options = [
				{ Text = "开始相遇/演练。", function getResult(_event) { return "Drill"; } },
				{ Text = "线索留着。", function getResult(_event) { this.World.Flags.set(::AfeiExpedition.Flags.R10Offered, 1); return 0; } }
			],
			function start(_event) {}
		});
		this.m.Screens.push({
			ID = "Drill",
			Text = "%terrainImage{怎么进行？两条路都能完成同一次入团步骤。}",
			Image = "", List = [], Characters = [],
			Options = [
				{ Text = "先侦察箱线。", function getResult(_event) { return "DrillA"; } },
				{ Text = "按正常遭遇清开拦路。", function getResult(_event) { return "DrillB"; } },
				{ Text = "今天先停。", function getResult(_event) { this.World.Flags.set(::AfeiExpedition.Flags.R10Offered, 1); return 0; } }
			],
			function start(_event) {}
		});
		this.m.Screens.push({
			ID = "DrillA",
			Text = "%terrainImage{你们选择先侦察箱线。脚印、绳痕和半截封条对上了——箱子还在安全处。大鹅把箱单拍在车板上，等你们正式交付。}",
			Image = "", List = [], Characters = [],
			Options = [{ Text = "谈签约。", function getResult(_event) { return "B"; } }],
			function start(_event) {}
		});
		this.m.Screens.push({
			ID = "DrillB",
			Text = "%terrainImage{你们选择按正常遭遇清开拦路的人。结束后箱子被抬回，大鹅核对封条，没有把人提前绑进黑旗名册。}",
			Image = "", List = [], Characters = [],
			Options = [{ Text = "谈签约。", function getResult(_event) { return "B"; } }],
			function start(_event) {}
		});
		this.m.Screens.push({
			ID = "B",
			Text = "%terrainImage{任务成功。签约费 [color=#8f2525]650[/color] 克朗。身份 C13，入队一级零经验。她在安全交付时才会正式接过箱单。}",
			Image = "", List = [], Characters = [],
			Options = [
				{ Text = "支付 650 克朗签约。", function getResult(_event) {
					if (this.World.Assets.getMoney() < 650) return "Poor";
					return "Hire";
				} },
				{ Text = "先不签。", function getResult(_event) { this.World.Flags.set(::AfeiExpedition.Flags.R10Offered, 1); return 0; } }
			],
			function start(_event) {}
		});
		this.m.Screens.push({
			ID = "Hire",
			Text = "%terrainImage{大鹅接过黑旗箱单。脾气还在，箱子里是大家的。}",
			Image = "", List = [], Characters = [],
			Options = [{ Text = "欢迎入队。", function getResult(_event) {
						if (::AfeiExpedition.hasNamed("C13")) return 0;
						if (!::AfeiExpedition.tryChargeHire("C13", 650))
						{
							return "Poor";
						}

						local bro = ::AfeiExpedition.hireNamed(this, {
							Background = "afei_c13_background",
							Name = "大鹅",
							Title = "大鹅",
							NamedId = "C13",
							Attrs = [85, 125, 52, 100, 65, 30, 14, 4],
							Wage = 28,
							Place = 4,
							Skills = ["afei_goose_bully", "afei_gaga_charge", "afei_guard_nest"]
						});
						local talents = bro.getTalents();
						talents.resize(this.Const.Attributes.COUNT, 0);
												for (local i = 0; i < this.Const.Attributes.COUNT; i++) { talents[i] = 0; }
												talents[this.Const.Attributes.Hitpoints] = 3;
												talents[this.Const.Attributes.Fatigue] = 3;
												talents[this.Const.Attributes.MeleeDefense] = 3;
						bro.getSkills().update();
						this.World.Flags.set(::AfeiExpedition.Flags.R10Done, 1);
						this.World.Flags.set(::AfeiExpedition.Flags.R10Offered, 1);
						return 0;
			} }],
			function start(_event) {
				this.List.push({ id=10, icon="ui/icons/asset_money.png", text="支付 [color=#8f2525]650[/color] 克朗" });
			}
		});
		this.m.Screens.push({
			ID = "Poor",
			Text = "%terrainImage{资源不够。线索留着，人不消失。}",
			Image = "", List = [], Characters = [],
			Options = [{ Text = "知道了。", function getResult(_event) { this.World.Flags.set(::AfeiExpedition.Flags.R10Offered, 1); return 0; } }],
			function start(_event) {}
		});
	}
	function onUpdateScore()
	{
		if (!::AfeiExpedition.isAfeiOrigin()) return;
		if (this.World.Flags.get(::AfeiExpedition.Flags.R10Done)) return;
		if (::AfeiExpedition.hasNamed("C13")) return;
		if (this.World.getTime().Days < 30) { return; }
		if (!this.World.Flags.get(::AfeiExpedition.Flags.M04Done)) { return; }
		if (this.World.getPlayerRoster().getSize() >= this.World.Assets.getBrothersMax()) return;
		this.m.Score = this.World.Flags.get(::AfeiExpedition.Flags.R10Offered) ? 15 : 30;
	}
	function onPrepare() {}
	function onPrepareVariables(_vars) {}
	function onClear() {}
});

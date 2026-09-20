this.afei_r09_event <- this.inherit("scripts/events/event", {
	m = {},
	function create()
	{
		this.m.ID = "event.afei_r09_event";
		this.m.Title = "招募 · 小虎";
		this.m.Cooldown = 7.0 * this.World.getTime().SecondsPerDay;
		this.m.Screens.push({
			ID = "A",
			Text = "%terrainImage{蓝旗那边托小虎捎一封信到邻近友好城镇，没有强制期限。他把已经空下来的信袋系在腰侧，问黑旗下一程往哪边走。\n\n送达后可以谈签约；暂缓保留邀请。}",
			Image = "", List = [], Characters = [],
			Options = [
				{ Text = "开始相遇/演练。", function getResult(_event) { return "Drill"; } },
				{ Text = "线索留着。", function getResult(_event) { this.World.Flags.set(::AfeiExpedition.Flags.R09Offered, 1); return 0; } }
			],
			function start(_event) {}
		});
		this.m.Screens.push({
			ID = "Drill",
			Text = "%terrainImage{信送到了。收信人读完，给他添了一碗水。小虎把空信袋重新系好，没有追问里面写了什么。\n\n他问：黑旗还缺不缺能把人送到的人？}",
			Image = "", List = [], Characters = [],
			Options = [
				{ Text = "继续谈签约。", function getResult(_event) { return "B"; } },
				{ Text = "今天先停。", function getResult(_event) { this.World.Flags.set(::AfeiExpedition.Flags.R09Offered, 1); return 0; } }
			],
			function start(_event) {}
		});
		this.m.Screens.push({
			ID = "B",
			Text = "%terrainImage{送达之后，签约费 [color=#8f2525]650[/color] 克朗。身份 C12，入队一级零经验。}",
			Image = "", List = [], Characters = [],
			Options = [
				{ Text = "支付 650 克朗签约。", function getResult(_event) {
					if (this.World.Assets.getMoney() < 650) return "Poor";
					return "Hire";
				} },
				{ Text = "先不签。", function getResult(_event) { this.World.Flags.set(::AfeiExpedition.Flags.R09Offered, 1); return 0; } }
			],
			function start(_event) {}
		});
		this.m.Screens.push({
			ID = "Hire",
			Text = "%terrainImage{小虎入册。信袋还在，下一封也许是黑旗自己的路线。}",
			Image = "", List = [], Characters = [],
			Options = [{ Text = "欢迎入队。", function getResult(_event) {
						if (::AfeiExpedition.hasNamed("C12")) return 0;
						if (!::AfeiExpedition.tryChargeHire("C12", 650))
						{
							return "Poor";
						}

						local bro = ::AfeiExpedition.hireNamed(this, {
							Background = "afei_c12_background",
							Name = "小虎",
							Title = "小虎",
							NamedId = "C12",
							Attrs = [54, 97, 43, 114, 47, 57, 2, 5],
							Wage = 16,
							Place = 14,
							Skills = ["afei_scout_path", "afei_return_arrow", "afei_catch_rear"]
						});
						local talents = bro.getTalents();
						talents.resize(this.Const.Attributes.COUNT, 0);
												for (local i = 0; i < this.Const.Attributes.COUNT; i++) { talents[i] = 0; }
												talents[this.Const.Attributes.Fatigue] = 1;
												talents[this.Const.Attributes.Initiative] = 2;
												talents[this.Const.Attributes.RangedSkill] = 3;
						bro.getSkills().update();
						this.World.Flags.set(::AfeiExpedition.Flags.R09Done, 1);
						this.World.Flags.set(::AfeiExpedition.Flags.R09Offered, 1);
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
			Options = [{ Text = "知道了。", function getResult(_event) { this.World.Flags.set(::AfeiExpedition.Flags.R09Offered, 1); return 0; } }],
			function start(_event) {}
		});
	}
	function onUpdateScore()
	{
		if (!::AfeiExpedition.isAfeiOrigin()) return;
		if (this.World.Flags.get(::AfeiExpedition.Flags.R09Done)) return;
		if (::AfeiExpedition.hasNamed("C12")) return;
		if (this.World.getTime().Days < 27) { return; }
		if (!this.World.Flags.get(::AfeiExpedition.Flags.M04Done)) { return; }
		if (this.World.getPlayerRoster().getSize() >= this.World.Assets.getBrothersMax()) return;
		this.m.Score = this.World.Flags.get(::AfeiExpedition.Flags.R09Offered) ? 15 : 30;
	}
	function onPrepare() {}
	function onPrepareVariables(_vars) {}
	function onClear() {}
});

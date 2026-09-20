this.afei_r08_event <- this.inherit("scripts/events/event", {
	m = {},
	function create()
	{
		this.m.ID = "event.afei_r08_event";
		this.m.Title = "招募 · 川神";
		this.m.Cooldown = 7.0 * this.World.getTime().SecondsPerDay;
		this.m.Screens.push({
			ID = "A",
			Text = "%terrainImage{蓝旗同行之后，川神带着裂口的队形图来到黑旗营地。他愿意谈入团，但先要你们按黑旗规矩做一次普通营地复盘：八十克朗、六份食物、大约三小时把话说完。\n\n他不是来替谁站队的——他要的是一套能在现场改位置的分工。暂缓不会让线索消失。}",
			Image = "", List = [], Characters = [],
			Options = [
				{ Text = "开始相遇/演练。", function getResult(_event) { return "Drill"; } },
				{ Text = "线索留着。", function getResult(_event) { this.World.Flags.set(::AfeiExpedition.Flags.R08Offered, 1); return 0; } }
			],
			function start(_event) {}
		});
		this.m.Screens.push({
			ID = "Drill",
			Text = "%terrainImage{黑旗的普通复盘：八十克朗、六份食物、大约三小时。川神站在一旁听，不插话，只在结束时把图边按平。}",
			Image = "", List = [], Characters = [],
			Options = [
				{ Text = "按黑旗规矩复盘。", function getResult(_event) {
					if (this.World.Assets.getMoney() < 80) return "Poor";
					if (!::AfeiExpedition.trySpendFoodApprox(6)) return "Poor";
					this.World.Assets.addMoney(-80);
					local c = this.World.Flags.getAsInt("afei_cohesion");
					this.World.Flags.set("afei_cohesion", this.Math.min(100, c + 5));
					this.World.Flags.set(::AfeiExpedition.Flags.ReviewCount, this.World.Flags.getAsInt(::AfeiExpedition.Flags.ReviewCount) + 1);
					local peak = this.World.Flags.getAsInt("afei_cohesion_peak");
					local cur = this.World.Flags.getAsInt("afei_cohesion");
					if (cur > peak) this.World.Flags.set("afei_cohesion_peak", cur);
					return "B";
				} },
				{ Text = "已复盘过，直接谈签约。", function getResult(_event) {
					if (this.World.Flags.getAsInt(::AfeiExpedition.Flags.ReviewCount) < 1) return "NeedReview";
					return "B";
				} },
				{ Text = "今天先停。", function getResult(_event) { this.World.Flags.set(::AfeiExpedition.Flags.R08Offered, 1); return 0; } }
			],
			function start(_event) {}
		});
		this.m.Screens.push({
			ID = "NeedReview",
			Text = "%terrainImage{他还没听见你们按黑旗规矩把话说完。先复盘，或去做一次普通营地复盘后再来。}",
			Image = "", List = [], Characters = [],
			Options = [{ Text = "知道了。", function getResult(_event) { return "Drill"; } }],
			function start(_event) {}
		});
		this.m.Screens.push({
			ID = "B",
			Text = "%terrainImage{复盘刚结束，纸边还温着。川神把旧图摊开，让你们直接在补丁处改站位，而不是另画一张整洁却用不上的图。\n\n签约费 [color=#8f2525]800[/color] 克朗。身份 C11，入队仍是一级、零经验。}",
			Image = "", List = [], Characters = [],
			Options = [
				{ Text = "支付 800 克朗签约。", function getResult(_event) {
					if (this.World.Assets.getMoney() < 800) return "Poor";
					return "Hire";
				} },
				{ Text = "先不签。", function getResult(_event) { this.World.Flags.set(::AfeiExpedition.Flags.R08Offered, 1); return 0; } }
			],
			function start(_event) {}
		});
		this.m.Screens.push({
			ID = "Hire",
			Text = "%terrainImage{川神的名字写进黑旗名册。他收起裂口的图，说下一场再改也不迟。}",
			Image = "", List = [], Characters = [],
			Options = [{ Text = "欢迎入队。", function getResult(_event) {
						if (::AfeiExpedition.hasNamed("C11")) return 0;
						if (!::AfeiExpedition.tryChargeHire("C11", 800))
						{
							return "Poor";
						}

						local bro = ::AfeiExpedition.hireNamed(this, {
							Background = "afei_c11_background",
							Name = "川神",
							Title = "川神",
							NamedId = "C11",
							Attrs = [57, 98, 55, 96, 55, 34, 4, 3],
							Wage = 18,
							Place = 6,
							Skills = ["afei_blue_form", "afei_steady_hand", "afei_good_card"]
						});
						local talents = bro.getTalents();
						talents.resize(this.Const.Attributes.COUNT, 0);
												for (local i = 0; i < this.Const.Attributes.COUNT; i++) { talents[i] = 0; }
												talents[this.Const.Attributes.Fatigue] = 1;
												talents[this.Const.Attributes.Bravery] = 2;
												talents[this.Const.Attributes.MeleeSkill] = 2;
						bro.getSkills().update();
						this.World.Flags.set(::AfeiExpedition.Flags.R08Done, 1);
						this.World.Flags.set(::AfeiExpedition.Flags.R08Offered, 1);
						return 0;
			} }],
			function start(_event) {
				this.List.push({ id=10, icon="ui/icons/asset_money.png", text="支付 [color=#8f2525]800[/color] 克朗" });
			}
		});
		this.m.Screens.push({
			ID = "Poor",
			Text = "%terrainImage{资源不够。线索留着，人不消失。}",
			Image = "", List = [], Characters = [],
			Options = [{ Text = "知道了。", function getResult(_event) { this.World.Flags.set(::AfeiExpedition.Flags.R08Offered, 1); return 0; } }],
			function start(_event) {}
		});
	}
	function onUpdateScore()
	{
		if (!::AfeiExpedition.isAfeiOrigin()) return;
		if (this.World.Flags.get(::AfeiExpedition.Flags.R08Done)) return;
		if (::AfeiExpedition.hasNamed("C11")) return;
		if (this.World.getTime().Days < 25) { return; }
		if (::AfeiExpedition.getPaidContracts() < 8) { return; }
		if (!this.World.Flags.get(::AfeiExpedition.Flags.M04Done)) { return; }
		if (this.World.getPlayerRoster().getSize() >= this.World.Assets.getBrothersMax()) return;
		this.m.Score = this.World.Flags.get(::AfeiExpedition.Flags.R08Offered) ? 15 : 30;
	}
	function onPrepare() {}
	function onPrepareVariables(_vars) {}
	function onClear() {}
});

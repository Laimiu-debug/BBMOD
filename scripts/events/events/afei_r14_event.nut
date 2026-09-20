this.afei_r14_event <- this.inherit("scripts/events/event", {
	m = {},
	function create()
	{
		this.m.ID = "event.afei_r14_event";
		this.m.Title = "招募 · 可可";
		this.m.Cooldown = 7.0 * this.World.getTime().SecondsPerDay;
		this.m.Screens.push({
			ID = "A",
			Text = "%terrainImage{磨合够热络时，可可提议先聚餐：大约六份食物、两小时把话说开，再付 [color=#8f2525]600[/color] 克朗签约。\n\n她会把一小截同色布交给最先认识的伙伴；战场上保谁，仍看需要。}",
			Image = "", List = [], Characters = [],
			Options = [
				{ Text = "开始相遇/演练。", function getResult(_event) { return "Drill"; } },
				{ Text = "线索留着。", function getResult(_event) { this.World.Flags.set(::AfeiExpedition.Flags.R14Offered, 1); return 0; } }
			],
			function start(_event) {}
		});
		this.m.Screens.push({
			ID = "Drill",
			Text = "%terrainImage{聚餐散了。可可把布条塞进对方手里，自己只留短头。没有人被强迫发誓，只是约好别装作看不见自己人。}",
			Image = "", List = [], Characters = [],
			Options = [
				{ Text = "办聚餐（约 6 食物）。", function getResult(_event) {
					if (!::AfeiExpedition.trySpendFoodApprox(6)) return "Poor";
					return "B";
				} },
				{ Text = "今天先停。", function getResult(_event) { this.World.Flags.set(::AfeiExpedition.Flags.R14Offered, 1); return 0; } }
			],
			function start(_event) {
				this.List.push({ id = 10, icon = "ui/icons/asset_food.png", text = "准备聚餐（约 6 食物）" });
			}
		});
		this.m.Screens.push({
			ID = "B",
			Text = "%terrainImage{聚餐完成。签约费 [color=#8f2525]600[/color] 克朗。身份 C17，入队一级零经验。}",
			Image = "", List = [], Characters = [],
			Options = [
				{ Text = "支付 600 克朗签约。", function getResult(_event) {
					if (this.World.Assets.getMoney() < 600) return "Poor";
					return "Hire";
				} },
				{ Text = "先不签。", function getResult(_event) { this.World.Flags.set(::AfeiExpedition.Flags.R14Offered, 1); return 0; } }
			],
			function start(_event) {}
		});
		this.m.Screens.push({
			ID = "Hire",
			Text = "%terrainImage{可可入册。布条在，守望也在。}",
			Image = "", List = [], Characters = [],
			Options = [{ Text = "欢迎入队。", function getResult(_event) {
						if (::AfeiExpedition.hasNamed("C17")) return 0;
						if (!::AfeiExpedition.tryChargeHire("C17", 600))
						{
							return "Poor";
						}

						local bro = ::AfeiExpedition.hireNamed(this, {
							Background = "afei_c17_background",
							Name = "可可",
							Title = "可可",
							NamedId = "C17",
							Attrs = [50, 93, 48, 105, 43, 55, 2, 6],
							Wage = 15,
							Place = 13,
							Skills = ["afei_own_people", "afei_pokemon", "afei_breathe_easy"]
						});
						local talents = bro.getTalents();
						talents.resize(this.Const.Attributes.COUNT, 0);
												for (local i = 0; i < this.Const.Attributes.COUNT; i++) { talents[i] = 0; }
												talents[this.Const.Attributes.Bravery] = 2;
												talents[this.Const.Attributes.Initiative] = 1;
												talents[this.Const.Attributes.RangedSkill] = 2;
						bro.getSkills().update();
						this.World.Flags.set(::AfeiExpedition.Flags.R14Done, 1);
						this.World.Flags.set(::AfeiExpedition.Flags.R14Offered, 1);
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
			Options = [{ Text = "知道了。", function getResult(_event) { this.World.Flags.set(::AfeiExpedition.Flags.R14Offered, 1); return 0; } }],
			function start(_event) {}
		});
	}
	function onUpdateScore()
	{
		if (!::AfeiExpedition.isAfeiOrigin()) return;
		if (this.World.Flags.get(::AfeiExpedition.Flags.R14Done)) return;
		if (::AfeiExpedition.hasNamed("C17")) return;
		if (this.World.getTime().Days < 42) { return; }
		if (::AfeiExpedition.getPaidContracts() < 12) { return; }
		if (this.World.Flags.getAsInt("afei_cohesion") < 45) { return; }
		if (this.World.getPlayerRoster().getSize() >= this.World.Assets.getBrothersMax()) return;
		this.m.Score = this.World.Flags.get(::AfeiExpedition.Flags.R14Offered) ? 15 : 30;
	}
	function onPrepare() {}
	function onPrepareVariables(_vars) {}
	function onClear() {}
});

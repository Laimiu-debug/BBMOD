this.afei_r11_event <- this.inherit("scripts/events/event", {
	m = {},
	function create()
	{
		this.m.ID = "event.afei_r11_event";
		this.m.Title = "招募 · 小杰";
		this.m.Cooldown = 7.0 * this.World.getTime().SecondsPerDay;
		this.m.Screens.push({
			ID = "A",
			Text = "%terrainImage{小杰围着车辆转了两圈，说要花大约两小时检查锁、销和备用钥匙的位置，再谈五百克朗签约。\n\n入团后还会有钥匙怎么分工的笑话（M06），不会靠锁死你们的物品栏来演。}",
			Image = "", List = [], Characters = [],
			Options = [
				{ Text = "开始相遇/演练。", function getResult(_event) { return "Drill"; } },
				{ Text = "线索留着。", function getResult(_event) { this.World.Flags.set(::AfeiExpedition.Flags.R11Offered, 1); return 0; } }
			],
			function start(_event) {}
		});
		this.m.Screens.push({
			ID = "Drill",
			Text = "%terrainImage{两小时检查结束。小杰把一把备用钥匙搁在手心又收回去，说正式签约以后再交。车还能走，锁也还听使唤。}",
			Image = "", List = [], Characters = [],
			Options = [
				{ Text = "继续谈签约。", function getResult(_event) { return "B"; } },
				{ Text = "今天先停。", function getResult(_event) { this.World.Flags.set(::AfeiExpedition.Flags.R11Offered, 1); return 0; } }
			],
			function start(_event) {}
		});
		this.m.Screens.push({
			ID = "B",
			Text = "%terrainImage{检查完毕。签约费 [color=#8f2525]500[/color] 克朗。身份 C14，入队一级零经验。}",
			Image = "", List = [], Characters = [],
			Options = [
				{ Text = "支付 500 克朗签约。", function getResult(_event) {
					if (this.World.Assets.getMoney() < 500) return "Poor";
					return "Hire";
				} },
				{ Text = "先不签。", function getResult(_event) { this.World.Flags.set(::AfeiExpedition.Flags.R11Offered, 1); return 0; } }
			],
			function start(_event) {}
		});
		this.m.Screens.push({
			ID = "Hire",
			Text = "%terrainImage{小杰入册。锁车的习惯留下，钥匙的笑话以后再算。}",
			Image = "", List = [], Characters = [],
			Options = [{ Text = "欢迎入队。", function getResult(_event) {
						if (::AfeiExpedition.hasNamed("C14")) return 0;
						if (!::AfeiExpedition.tryChargeHire("C14", 500))
						{
							return "Poor";
						}

						local bro = ::AfeiExpedition.hireNamed(this, {
							Background = "afei_c14_background",
							Name = "小杰",
							Title = "小杰",
							NamedId = "C14",
							Attrs = [56, 103, 36, 107, 50, 33, 5, 3],
							Wage = 14,
							Place = 7,
							Skills = ["afei_lock_wagon", "afei_not_fooled", "afei_spare_key"]
						});
						local talents = bro.getTalents();
						talents.resize(this.Const.Attributes.COUNT, 0);
												for (local i = 0; i < this.Const.Attributes.COUNT; i++) { talents[i] = 0; }
												talents[this.Const.Attributes.Fatigue] = 2;
												talents[this.Const.Attributes.Bravery] = 1;
												talents[this.Const.Attributes.MeleeDefense] = 2;
						bro.getSkills().update();
						this.World.Flags.set(::AfeiExpedition.Flags.R11Done, 1);
						this.World.Flags.set(::AfeiExpedition.Flags.R11Offered, 1);
						return 0;
			} }],
			function start(_event) {
				this.List.push({ id=10, icon="ui/icons/asset_money.png", text="支付 [color=#8f2525]500[/color] 克朗" });
			}
		});
		this.m.Screens.push({
			ID = "Poor",
			Text = "%terrainImage{资源不够。线索留着，人不消失。}",
			Image = "", List = [], Characters = [],
			Options = [{ Text = "知道了。", function getResult(_event) { this.World.Flags.set(::AfeiExpedition.Flags.R11Offered, 1); return 0; } }],
			function start(_event) {}
		});
	}
	function onUpdateScore()
	{
		if (!::AfeiExpedition.isAfeiOrigin()) return;
		if (this.World.Flags.get(::AfeiExpedition.Flags.R11Done)) return;
		if (::AfeiExpedition.hasNamed("C14")) return;
		if (this.World.getTime().Days < 35) { return; }
		if (::AfeiExpedition.getPaidContracts() < 10) { return; }
		if (this.World.getPlayerRoster().getSize() >= this.World.Assets.getBrothersMax()) return;
		this.m.Score = this.World.Flags.get(::AfeiExpedition.Flags.R11Offered) ? 15 : 30;
	}
	function onPrepare() {}
	function onPrepareVariables(_vars) {}
	function onClear() {}
});

// Legacy Modding Script Hooks（与 Fate / 沙匪起源同代际；非 Modern/MSU）
// 参考：Fate.zip 用 ::mods_hookNewObject；沙匪用 mods_registerMod + mods_queue。
// scenario 靠新增 scripts/scenarios/world/*_scenario.nut 自出现在列表（Fate/沙匪均未 hook scenario_manager）。
::AfeiExpedition <- {
	ID = "mod_afei_expedition",
	Name = "大飞午远征团",
	Version = 1.1,
	OrderBudgetMax = 2,
	OrderBudget = 2,
	LastOrderRound = -1,
	Flags = {
		PaidContracts = "afei_paid_contracts",
		M01Done = "afei_m01_done",
		SafeDeliveryDone = "afei_safe_delivery_done",
		R01Done = "afei_r01_done",
		R01Offered = "afei_r01_offered",
		CaptainAfei = "afei_captain_afei"
	},

	function resetOrders()
	{
		this.OrderBudget = this.OrderBudgetMax;
		this.LastOrderRound = -1;
	},

	function getRound()
	{
		if (!("Tactical" in getroottable()) || this.Tactical.State == null)
		{
			return -1;
		}

		try
		{
			return this.Time.getRound();
		}
		catch (error)
		{
			return -1;
		}
	},

	function canUseOrder()
	{
		if (this.OrderBudget <= 0)
		{
			return false;
		}

		local round = this.getRound();

		if (round >= 0 && round == this.LastOrderRound)
		{
			return false;
		}

		return true;
	},

	function consumeOrder()
	{
		if (!this.canUseOrder())
		{
			return false;
		}

		this.OrderBudget -= 1;
		this.LastOrderRound = this.getRound();
		return true;
	},

	function isAfeiOrigin()
	{
		if (!("World" in getroottable()) || this.World.Assets == null)
		{
			return false;
		}

		local origin = this.World.Assets.getOrigin();
		return origin != null && origin.getID() == "scenario.afei_expedition";
	},

	function getPaidContracts()
	{
		if (!this.isAfeiOrigin())
		{
			return 0;
		}

		return this.World.Flags.getAsInt(this.Flags.PaidContracts);
	},

	function addPaidContract(_n = 1)
	{
		if (!this.isAfeiOrigin())
		{
			return;
		}

		this.World.Flags.set(this.Flags.PaidContracts, this.getPaidContracts() + _n);
	}
};

::mods_registerMod(::AfeiExpedition.ID, ::AfeiExpedition.Version, ::AfeiExpedition.Name);

::mods_queue(::AfeiExpedition.ID, null, function()
{
	// 有报酬契约成功结算计数（R01 门控）
	::mods_hookExactClass("contracts/contract", function(o)
	{
		local onClear = o.onClear;
		o.onClear = function(_success)
		{
			if (_success && ::AfeiExpedition.isAfeiOrigin())
			{
				local payment = 0;

				try
				{
					if ("getPayment" in this)
					{
						local p = this.getPayment();

						if (p != null && "Base" in p.m)
						{
							payment = p.m.Base;
						}
					}
				}
				catch (error)
				{
				}

				if (payment > 0)
				{
					::AfeiExpedition.addPaidContract(1);
				}
			}

			return onClear(_success);
		};
	});

	// 阿飞不可解雇（UI 路径名因版本而异，尽力挂钩）
	::mods_hookExactClass("entity/tactical/player", function(o)
	{
		o.afei_isUndismissable <- function()
		{
			return this.getFlags().get(::AfeiExpedition.Flags.CaptainAfei) == true;
		};
	});

	::mods_hookExactClass("ui/screens/world/modules/world_character_screen/world_character_screen", function(o)
	{
		if ("dismissBrother" in o)
		{
			local dismissBrother = o.dismissBrother;
			o.dismissBrother = function(_brother)
			{
				if (_brother != null && _brother.getFlags().get(::AfeiExpedition.Flags.CaptainAfei) == true)
				{
					return;
				}

				return dismissBrother(_brother);
			};
		}
	});

	// 团队号令：每场重置；每轮闸门在 ::AfeiExpedition
	::mods_hookExactClass("states/tactical_state", function(o)
	{
		local onInit = o.onInit;
		o.onInit = function()
		{
			onInit();

			if (::AfeiExpedition.isAfeiOrigin())
			{
				::AfeiExpedition.resetOrders();
			}
		};
	});

	::mods_hookExactClass("tactical/turn_sequence_bar", function(o)
	{
		if ("initNextRound" in o)
		{
			local initNextRound = o.initNextRound;
			o.initNextRound = function()
			{
				local result = initNextRound();
				::AfeiExpedition.LastOrderRound = -1;
				return result;
			};
		}
	});

	// R01 为普通可评分事件，需注入 event_manager（沙匪开场用 IsSpecial + fire，不走评分）
	::mods_hookExactClass("events/event_manager", function(o)
	{
		local create = o.create;
		o.create = function()
		{
			create();
			this.m.Events.push(this.new("scripts/events/events/afei_r01_bottle_event"));
		};
	});
});

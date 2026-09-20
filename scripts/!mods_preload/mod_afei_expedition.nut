// Legacy Modding Script Hooks entry (mod_hooks 21.x).
// Package id: mod_afei_expedition · Game target: Battle Brothers 1.5.2.3
::AfeiExpedition <- {
	ID = "mod_afei_expedition",
	Name = "大飞午远征团",
	Version = 1.0,
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

::mods_queue(::AfeiExpedition.ID, "mod_hooks(>=20)", function()
{
	// Register origin without replacing any vanilla *_scenario path.
	::mods_hookExactClass("scenarios/scenario_manager", function(o)
	{
		local create = o.create;
		o.create = function()
		{
			create();
			this.addScenario(this.new("scripts/scenarios/world/afei_expedition_scenario"));
		};
	});

	// Count successful paid contracts (best-effort; full contract taxonomy pending ZIP校准).
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

				if (payment > 0 || (this.getType() != "contract.tutorial"))
				{
					// Prefer payment>0; still count most non-tutorial successes as paid for stage-1 gate.
					if (payment > 0)
					{
						::AfeiExpedition.addPaidContract(1);
					}
				}
			}

			return onClear(_success);
		};
	});

	// Prevent dismissing 阿飞 (named captain flag).
	::mods_hookExactClass("entity/tactical/player", function(o)
	{
		local isReallyKilled = o.isReallyKilled;
		// UI dismiss path checks IsPlayerCharacter in several builds; also block via getTryoutCost? 
		// Provide an explicit helper used by our hooks below.
		o.afei_isUndismissable <- function()
		{
			return this.getFlags().get(::AfeiExpedition.Flags.CaptainAfei) == true;
		};
	});

	::mods_hookExactClass("ui/screens/world/modules/world_character_screen/world_character_screen", function(o)
	{
		// Soft guard: if dismissBrother exists, wrap it. Not all builds expose the same name.
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

	// Shared 号令 budget: reset each combat; per-round gate lives in ::AfeiExpedition.
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

		local onBattleEnded = ("onBattleEnded" in o) ? o.onBattleEnded : null;

		if (onBattleEnded != null)
		{
			o.onBattleEnded = function()
			{
				::AfeiExpedition.resetOrders();
				return onBattleEnded();
			};
		}
	});

	// Round boundary: allow one 号令 per round again (budget is combat-scoped).
	::mods_hookExactClass("tactical/turn_sequence_bar", function(o)
	{
		local initNextRound = ("initNextRound" in o) ? o.initNextRound : null;

		if (initNextRound != null)
		{
			o.initNextRound = function()
			{
				local result = initNextRound();
				::AfeiExpedition.LastOrderRound = -1;
				return result;
			};
		}
	});

	// Event manager: inject M01 / R01 skeletons.
	::mods_hookExactClass("events/event_manager", function(o)
	{
		local create = o.create;
		o.create = function()
		{
			create();
			this.m.Events.push(this.new("scripts/events/events/afei_m01_captains_event"));
			this.m.Events.push(this.new("scripts/events/events/afei_r01_bottle_event"));
		};
	});
});

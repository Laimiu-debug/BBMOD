// Legacy Modding Script Hooks（与 Fate / 沙匪起源同代际；非 Modern/MSU）
// 参考：Fate.zip 用 ::mods_hookNewObject；沙匪用 mods_registerMod + mods_queue。
// scenario 靠新增 scripts/scenarios/world/*_scenario.nut 自出现在列表（Fate/沙匪均未 hook scenario_manager）。
::AfeiExpedition <- {
	ID = "mod_afei_expedition",
	Name = "大飞午远征团",
	Version = 1.2,
	OrderBudgetMax = 2,
	OrderBudget = 2,
	LastOrderRound = -1,
	Flags = {
		PaidContracts = "afei_paid_contracts",
		M01Done = "afei_m01_done",
		SafeDeliveryDone = "afei_safe_delivery_done",
		SafeDeliveryActive = "afei_safe_delivery_active",
		SafeDeliveryHome = "afei_safe_delivery_home",
		R01Done = "afei_r01_done",
		R01Offered = "afei_r01_offered",
		CaptainAfei = "afei_captain_afei",
		NamedId = "afei_named_id"
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
	},

	function tryCompleteSafeDelivery(_settlement)
	{
		if (!this.isAfeiOrigin())
		{
			return false;
		}

		if (this.World.Flags.get(this.Flags.SafeDeliveryDone))
		{
			return false;
		}

		if (!this.World.Flags.get(this.Flags.SafeDeliveryActive))
		{
			return false;
		}

		if (_settlement == null || _settlement.isMilitary())
		{
			return false;
		}

		local homeId = this.World.Flags.get(this.Flags.SafeDeliveryHome);

		if (homeId != null && homeId != "" && _settlement.getID() == homeId)
		{
			return false;
		}

		this.World.Assets.addMoney(180);
		this.addPaidContract(1);
		this.World.Flags.set(this.Flags.SafeDeliveryDone, 1);
		this.World.Flags.set(this.Flags.SafeDeliveryActive, 0);
		this.World.Flags.set(this.Flags.M01Done, 1);

		try
		{
			this.World.Events.fire("event.afei_safe_delivery_complete");
		}
		catch (error)
		{
		}

		return true;
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

	// 阿飞不可解雇：角色标记 + UI 拦截（多路径尽力挂钩）
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

		if ("onDismissBrother" in o)
		{
			local onDismissBrother = o.onDismissBrother;
			o.onDismissBrother = function(_data)
			{
				local bro = null;

				try
				{
					if (typeof _data == "integer" || typeof _data == "float")
					{
						bro = this.World.getPlayerRoster().getBrotherByID(_data);
					}
					else if (_data != null && "getID" in _data)
					{
						bro = _data;
					}
				}
				catch (error)
				{
				}

				if (bro != null && bro.getFlags().get(::AfeiExpedition.Flags.CaptainAfei) == true)
				{
					return;
				}

				return onDismissBrother(_data);
			};
		}
	});

	// 团队号令：每场重置预算；每轮最多 1 次（consumeOrder 记 LastOrderRound）
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

	// 地精算盘：友军对该目标的下一次单体武器攻击命中 +10（命中/未中均消耗）
	::mods_hookExactClass("skills/skill", function(o)
	{
		local onAnySkillUsed = o.onAnySkillUsed;
		o.onAnySkillUsed = function(_skill, _targetEntity, _properties)
		{
			onAnySkillUsed(_skill, _targetEntity, _properties);

			// 仅在「正在使用的那条攻击技」自身回调里加一次，避免名册内每个 skill 叠层
			if (_skill != this || !::AfeiExpedition.isAfeiOrigin() || _targetEntity == null || !this.isAttack())
			{
				return;
			}

			if (!_targetEntity.getSkills().hasSkill("effects.afei_abacus_mark"))
			{
				return;
			}

			local user = this.getContainer().getActor();

			if (user == null || !user.isAlive() || user.isAlliedWith(_targetEntity))
			{
				return;
			}

			if (this.isRanged())
			{
				_properties.RangedSkill += 10;
			}
			else
			{
				_properties.MeleeSkill += 10;
			}
		};

		local onAnySkillExecuted = o.onAnySkillExecuted;
		o.onAnySkillExecuted = function(_skill, _targetTile, _targetEntity, _forFree)
		{
			local result = onAnySkillExecuted(_skill, _targetTile, _targetEntity, _forFree);

			if (_skill == this && ::AfeiExpedition.isAfeiOrigin() && this.isAttack() && _targetEntity != null)
			{
				local mark = _targetEntity.getSkills().getSkillByID("effects.afei_abacus_mark");

				if (mark != null)
				{
					mark.removeSelf();
				}
			}

			return result;
		};
	});

	// M01 安全送账：进入非家乡友好城镇时结算（非完整契约类，见 STAGE1）
	::mods_hookExactClass("entity/world/settlement", function(o)
	{
		if ("onEnter" in o)
		{
			local onEnter = o.onEnter;
			o.onEnter = function()
			{
				local result = onEnter();
				::AfeiExpedition.tryCompleteSafeDelivery(this);
				return result;
			};
		}

		if ("enter" in o)
		{
			local enter = o.enter;
			o.enter = function()
			{
				local result = enter();
				::AfeiExpedition.tryCompleteSafeDelivery(this);
				return result;
			};
		}
	});

	::mods_hookExactClass("states/world/world_state", function(o)
	{
		if ("showTownScreen" in o)
		{
			local showTownScreen = o.showTownScreen;
			o.showTownScreen = function()
			{
				local result = showTownScreen();

				try
				{
					local player = this.World.State.getPlayer();

					if (player != null)
					{
						local tile = player.getTile();

						if (tile != null && tile.IsOccupiedByTown)
						{
							::AfeiExpedition.tryCompleteSafeDelivery(tile.getEntity());
						}
					}
				}
				catch (error)
				{
				}

				return result;
			};
		}
	});

	// 队友给的球：记录本轮命中该敌人的友军 ID
	::mods_hookExactClass("entity/tactical/actor", function(o)
	{
		local onDamageReceived = o.onDamageReceived;
		o.onDamageReceived = function(_attacker, _skill, _hitInfo)
		{
			local result = onDamageReceived(_attacker, _skill, _hitInfo);

			if (::AfeiExpedition.isAfeiOrigin() && _attacker != null && _skill != null && _skill.isAttack())
			{
				if (!_attacker.isAlliedWith(this))
				{
					this.getFlags().set("afei_hit_by_ally_id", _attacker.getID());
				}
			}

			return result;
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

				try
				{
					local all = this.Tactical.Entities.getAllInstancesAsArray();

					foreach (a in all)
					{
						if (a != null && a.getFlags().has("afei_hit_by_ally_id"))
						{
							a.getFlags().set("afei_hit_by_ally_id", 0);
						}
					}
				}
				catch (error)
				{
				}

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
			this.m.Events.push(this.new("scripts/events/events/afei_safe_delivery_complete_event"));
		};
	});
});

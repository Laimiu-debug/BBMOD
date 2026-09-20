// Legacy Modding Script Hooks（与 Fate / 沙匪起源同代际；非 Modern/MSU）
// scenario 靠新增 scripts/scenarios/world/*_scenario.nut 自出现在列表。
::AfeiExpedition <- {
	ID = "mod_afei_expedition",
	Name = "大飞午远征团",
	Version = 1.3,
	OrderBudgetMax = 2,
	OrderBudget = 2,
	LastOrderRound = -1,
	FatigueRecoverUsed = 0,
	FatigueRecoverCap = 20,
	Flags = {
		PaidContracts = "afei_paid_contracts",
		M01Done = "afei_m01_done",
		SafeDeliveryDone = "afei_safe_delivery_done",
		SafeDeliveryActive = "afei_safe_delivery_active",
		SafeDeliveryHome = "afei_safe_delivery_home",
		R01Done = "afei_r01_done",
		R01Offered = "afei_r01_offered",
		R02Done = "afei_r02_done",
		R02Offered = "afei_r02_offered",
		R03Done = "afei_r03_done",
		R03Offered = "afei_r03_offered",
		R04Done = "afei_r04_done",
		R04Offered = "afei_r04_offered",
		R05Done = "afei_r05_done",
		R05Offered = "afei_r05_offered",
		R06Done = "afei_r06_done",
		R06Offered = "afei_r06_offered",
		R07Done = "afei_r07_done",
		R07Offered = "afei_r07_offered",
		CaptainAfei = "afei_captain_afei",
		NamedId = "afei_named_id",
		ProxyCaptain = "afei_proxy_captain",
		JiahaoCount = "afei_jiahao_count",
		JiahaoSeen = "afei_jiahao_seen_"
	},

	function resetOrders()
	{
		this.OrderBudget = this.OrderBudgetMax;
		this.LastOrderRound = -1;
		this.FatigueRecoverUsed = 0;
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

	function consumeFatigueRecoverBudget(_n)
	{
		local left = this.FatigueRecoverCap - this.FatigueRecoverUsed;

		if (left <= 0)
		{
			return 0;
		}

		local take = _n;

		if (take > left)
		{
			take = left;
		}

		this.FatigueRecoverUsed += take;
		return take;
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

	function getJiahaoCount()
	{
		if (!this.isAfeiOrigin())
		{
			return 0;
		}

		return this.World.Flags.getAsInt(this.Flags.JiahaoCount);
	},

	function recordJiahao(_namedId)
	{
		if (!this.isAfeiOrigin() || _namedId == null || _namedId == "" || _namedId == "C01")
		{
			return false;
		}

		local key = this.Flags.JiahaoSeen + _namedId;

		if (this.World.Flags.get(key))
		{
			return false;
		}

		local n = this.getJiahaoCount();

		if (n >= 16)
		{
			return false;
		}

		this.World.Flags.set(key, 1);
		this.World.Flags.set(this.Flags.JiahaoCount, n + 1);
		return true;
	},

	function hasNamed(_namedId)
	{
		if (!("World" in getroottable()) || this.World.getPlayerRoster == null)
		{
			return false;
		}

		local roster = this.World.getPlayerRoster().getAll();

		foreach (bro in roster)
		{
			if (bro.getFlags().get(this.Flags.NamedId) == _namedId)
			{
				return true;
			}
		}

		return false;
	},

	function trySpendFoodApprox(_n)
	{
		local gt = getroottable();
		local stash = gt.World.Assets.getStash();
		local removed = 0;
		local items = stash.getItems();

		for (local i = items.len() - 1; i >= 0 && removed < _n; i--)
		{
			local it = items[i];

			if (it != null && it.isItemType(gt.Const.Items.ItemType.Food))
			{
				stash.remove(it);
				removed += 1;
			}
		}

		return removed >= _n;
	},

	function hireNamed(_ctx, _def)
	{
		local gt = getroottable();
		local bro = gt.World.getPlayerRoster().create("scripts/entity/tactical/player");
		bro.setStartValuesEx([
			_def.Background
		]);
		bro.setName(_def.Name);
		bro.setTitle(_def.Title);
		bro.getFlags().set(this.Flags.NamedId, _def.NamedId);
		bro.getSkills().add(_ctx.new("scripts/skills/special/afei_named_brother"));
		bro.getSkills().add(_ctx.new("scripts/skills/actives/afei_cohesion_rule"));
		local b = bro.getBaseProperties();
		local a = _def.Attrs;
		b.Hitpoints = a[0];
		b.Stamina = a[1];
		b.Bravery = a[2];
		b.Initiative = a[3];
		b.MeleeSkill = a[4];
		b.RangedSkill = a[5];
		b.MeleeDefense = a[6];
		b.RangedDefense = a[7];
		bro.m.Level = 1;
		bro.m.XP = gt.Const.LevelXP[0];
		bro.m.LevelUps = 0;
		bro.m.DailyWage = _def.Wage;
		bro.setPlaceInFormation(_def.Place);

		if ("Skills" in _def)
		{
			foreach (sid in _def.Skills)
			{
				bro.getSkills().add(_ctx.new("scripts/skills/actives/" + sid));
			}
		}

		bro.getSkills().update();
		return bro;
	},

	function clearProxyFlags()
	{
		local roster = this.World.getPlayerRoster().getAll();

		foreach (bro in roster)
		{
			bro.getFlags().set(this.Flags.ProxyCaptain, false);
		}
	},

	function setProxyByNamedId(_namedId)
	{
		local roster = this.World.getPlayerRoster().getAll();

		foreach (bro in roster)
		{
			if (bro.getFlags().get(this.Flags.NamedId) == _namedId)
			{
				bro.getFlags().set(this.Flags.ProxyCaptain, true);
				return true;
			}
		}

		return false;
	},

	function ensureProxyCaptain()
	{
		if (!this.isAfeiOrigin())
		{
			return;
		}

		local roster = this.World.getPlayerRoster().getAll();
		local hasProxy = false;

		foreach (bro in roster)
		{
			if (bro.getFlags().get(this.Flags.ProxyCaptain))
			{
				hasProxy = true;
				break;
			}
		}

		if (hasProxy)
		{
			return;
		}

		// 默认：怼怼(C10) > 大谋(C03) > 任意非阿飞命名
		local order = [
			"C10",
			"C03",
			"C02",
			"C08",
			"C09",
			"C06",
			"C04",
			"C05",
			"C07"
		];

		foreach (cid in order)
		{
			foreach (bro in roster)
			{
				if (bro.getFlags().get(this.Flags.NamedId) == cid)
				{
					bro.getFlags().set(this.Flags.ProxyCaptain, true);
					return;
				}
			}
		}
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
				::AfeiExpedition.ensureProxyCaptain();
			}
		};

		if ("onCombatFinished" in o)
		{
			local onCombatFinished = o.onCombatFinished;
			o.onCombatFinished = function()
			{
				local result = onCombatFinished();

				if (::AfeiExpedition.isAfeiOrigin())
				{
					try
					{
						local c = this.World.Flags.getAsInt("afei_cohesion");

						if (c < 100)
						{
							this.World.Flags.set("afei_cohesion", this.Math.min(100, c + 1));
						}
					}
					catch (error)
					{
					}
				}

				return result;
			};
		}
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
			this.m.Events.push(this.new("scripts/events/events/afei_r02_lili_event"));
			this.m.Events.push(this.new("scripts/events/events/afei_r03_yujiu_event"));
			this.m.Events.push(this.new("scripts/events/events/afei_r04_yueya_event"));
			this.m.Events.push(this.new("scripts/events/events/afei_r05_xiaoyu_event"));
			this.m.Events.push(this.new("scripts/events/events/afei_r06_shuaizi_event"));
			this.m.Events.push(this.new("scripts/events/events/afei_r07_duidui_event"));
			this.m.Events.push(this.new("scripts/events/events/afei_safe_delivery_complete_event"));
			this.m.Events.push(this.new("scripts/events/events/afei_proxy_captain_event"));
		};
	});
});

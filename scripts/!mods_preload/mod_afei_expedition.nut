// Legacy Modding Script Hooks（与 Fate / 沙匪起源同代际；非 Modern/MSU）
// scenario 靠新增 scripts/scenarios/world/*_scenario.nut 自出现在列表。
::AfeiExpedition <- {
	ID = "mod_afei_expedition",
	Name = "大飞午远征团",
	Version = 2.0,
	OrderBudgetMax = 2,
	OrderBudget = 2,
	LastOrderRound = -1,
	FatigueRecoverUsed = 0,
	FatigueRecoverCap = 20,
	Flags = {
		PaidContracts = "afei_paid_contracts",
		M01Done = "afei_m01_done",
		M02Done = "afei_m02_done",
		M03Done = "afei_m03_done",
		M04Done = "afei_m04_done",
		M05Done = "afei_m05_done",
		M06Done = "afei_m06_done",
		M07Done = "afei_m07_done",
		M08Done = "afei_m08_done",
		M09Done = "afei_m09_done",
		CampEnabled = "afei_camp_enabled",
		ReviewCount = "afei_review_count",
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
		R08Done = "afei_r08_done",
		R08Offered = "afei_r08_offered",
		R09Done = "afei_r09_done",
		R09Offered = "afei_r09_offered",
		R10Done = "afei_r10_done",
		R10Offered = "afei_r10_offered",
		R11Done = "afei_r11_done",
		R11Offered = "afei_r11_offered",
		R12Done = "afei_r12_done",
		R12Offered = "afei_r12_offered",
		R13Done = "afei_r13_done",
		R13Offered = "afei_r13_offered",
		R14Done = "afei_r14_done",
		R14Offered = "afei_r14_offered",
		R15Done = "afei_r15_done",
		R15Offered = "afei_r15_offered",
		R16Done = "afei_r16_done",
		R16Offered = "afei_r16_offered",
		R17Done = "afei_r17_done",
		R17Offered = "afei_r17_offered",
		R18Done = "afei_r18_done",
		R18Offered = "afei_r18_offered",
		R19Done = "afei_r19_done",
		R19Offered = "afei_r19_offered",
		R20Done = "afei_r20_done",
		R20Offered = "afei_r20_offered",
		R21Done = "afei_r21_done",
		R21Offered = "afei_r21_offered",
		R22Done = "afei_r22_done",
		R22Offered = "afei_r22_offered",
		R23Done = "afei_r23_done",
		R23Offered = "afei_r23_offered",
		R24Done = "afei_r24_done",
		R24Offered = "afei_r24_offered",
		R25Done = "afei_r25_done",
		R25Offered = "afei_r25_offered",
		R26Done = "afei_r26_done",
		R26Offered = "afei_r26_offered",
		R27Done = "afei_r27_done",
		R27Offered = "afei_r27_offered",
		R28Done = "afei_r28_done",
		R28Offered = "afei_r28_offered",
		CaptainAfei = "afei_captain_afei",
		NamedId = "afei_named_id",
		ProxyCaptain = "afei_proxy_captain",
		JiahaoCount = "afei_jiahao_count",
		JiahaoSeen = "afei_jiahao_seen_",
		AfeiAwakened = "afei_awakened",
		AfeiDead = "afei_captain_dead",
		Camped = "afei_camped",
		GrowthDone = "afei_growth_done_",
		WinCount = "afei_win_count",
		EverRecruited = "afei_ever_"
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
		this.markEverRecruited(_def.NamedId);
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


	function countNamedInRoster()
	{
		local n = 0;
		local roster = this.World.getPlayerRoster().getAll();

		foreach (bro in roster)
		{
			local id = bro.getFlags().get(this.Flags.NamedId);

			if (id != null && id != "")
			{
				n += 1;
			}
		}

		return n;
	},

	function countNamedEverRecruited()
	{
		local n = 0;

		for (local i = 1; i <= 31; i++)
		{
			local cid = i < 10 ? "C0" + i : "C" + i;

			if (this.World.Flags.get(this.Flags.EverRecruited + cid) || this.hasNamed(cid))
			{
				n += 1;
			}
		}

		return n;
	},

	function markEverRecruited(_namedId)
	{
		this.World.Flags.set(this.Flags.EverRecruited + _namedId, 1);
	},

	function bumpCohesion(_n)
	{
		local c = this.World.Flags.getAsInt("afei_cohesion") + _n;
		c = c < 0 ? 0 : (c > 100 ? 100 : c);
		this.World.Flags.set("afei_cohesion", c);
		local peak = this.World.Flags.getAsInt("afei_cohesion_peak");

		if (c > peak)
		{
			this.World.Flags.set("afei_cohesion_peak", c);
		}
	},

	function clearCampFlags()
	{
		local roster = this.World.getPlayerRoster().getAll();

		foreach (bro in roster)
		{
			bro.getFlags().set(this.Flags.Camped, false);
		}
	},

	function autoAssignCamp()
	{
		if (!this.World.Flags.get(this.Flags.CampEnabled))
		{
			return;
		}

		this.clearCampFlags();
		local roster = this.World.getPlayerRoster().getAll();
		local active = 0;

		foreach (bro in roster)
		{
			if (bro.getFlags().get(this.Flags.CaptainAfei))
			{
				active += 1;
				continue;
			}

			if (active < 20)
			{
				active += 1;
			}
			else
			{
				bro.getFlags().set(this.Flags.Camped, true);
			}
		}
	},

	function tryAwakenAfei()
	{
		if (this.World.Flags.get(this.Flags.AfeiDead))
		{
			return false;
		}

		if (this.World.Flags.get(this.Flags.AfeiAwakened))
		{
			return true;
		}

		if (!this.World.Flags.get(this.Flags.M08Done))
		{
			return false;
		}

		if (this.getJiahaoCount() < 16)
		{
			return false;
		}

		local roster = this.World.getPlayerRoster().getAll();

		foreach (bro in roster)
		{
			if (bro.getFlags().get(this.Flags.CaptainAfei) && bro.getLevel() >= 11)
			{
				this.World.Flags.set(this.Flags.AfeiAwakened, 1);
				this.OrderBudgetMax = 3;

				if (!bro.getSkills().hasSkill("actives.afei_full_circle"))
				{
					// added next combat via ensure
				}

				bro.getFlags().set("afei_need_full_circle", true);
				return true;
			}
		}

		return false;
	},

	function trySettleAllGrowths()
	{
		local done = [];
		local roster = this.World.getPlayerRoster().getAll();

		foreach (bro in roster)
		{
			local cid = bro.getFlags().get(this.Flags.NamedId);

			if (cid == null || cid == "")
			{
				continue;
			}

			local gkey = this.Flags.GrowthDone + cid;

			if (this.World.Flags.get(gkey))
			{
				continue;
			}

			local needLevel = cid == "C01" ? 7 : 5;

			if (bro.getLevel() < needLevel)
			{
				continue;
			}

			local wins = bro.getFlags().getAsInt(this.Flags.WinCount);

			if (cid == "C01" && (wins < 8 || this.getJiahaoCount() < 6))
			{
				continue;
			}

			if (cid != "C01" && wins < 3)
			{
				continue;
			}

			this.World.Flags.set(gkey, 1);
			this.bumpCohesion(3);

			if (cid != "C01")
			{
				this.recordJiahao(cid);
			}

			if (cid == "C01")
			{
				local b = bro.getBaseProperties();
				b.Hitpoints += 8;
				bro.getSkills().update();
			}

			done.push(cid == "C01" ? "G01" : ("G" + cid.slice(1)));
		}

		this.tryAwakenAfei();
		return done;
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
				::AfeiExpedition.tryAwakenAfei();
				// 带教标记
				try
				{
					local levels = [];
					local actors = this.Tactical.Entities.getInstancesOfFaction(this.Const.Faction.Player);
					foreach (a in actors)
					{
						if (a != null && a.isAlive()) levels.push(a.getLevel());
					}
					levels.sort();
					local med = levels.len() > 0 ? levels[levels.len()/2] : 1;
					foreach (a in actors)
					{
						if (a == null) continue;
						a.getFlags().set("afei_mentorship", false);
						local nid = a.getFlags().get(::AfeiExpedition.Flags.NamedId);
						if (nid != null && nid != "" && a.getLevel() < 7 && a.getLevel() <= med - 3)
						{
							a.getFlags().set("afei_mentorship", true);
						}
						if (a.getFlags().get("afei_need_full_circle") && !a.getSkills().hasSkill("actives.afei_full_circle"))
						{
							a.getSkills().add(this.new("scripts/skills/actives/afei_full_circle"));
							a.getFlags().set("afei_need_full_circle", false);
						}
					}
					if (::AfeiExpedition.World.Flags.get(::AfeiExpedition.Flags.AfeiAwakened))
					{
						::AfeiExpedition.OrderBudgetMax = 3;
						::AfeiExpedition.OrderBudget = 3;
					}
				}
				catch (error) {}
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
						::AfeiExpedition.bumpCohesion(1);
						local roster = this.World.getPlayerRoster().getAll();

						foreach (bro in roster)
						{
							if (bro.getFlags().get(::AfeiExpedition.Flags.NamedId) && !bro.getFlags().get(::AfeiExpedition.Flags.Camped))
							{
								bro.getFlags().set(::AfeiExpedition.Flags.WinCount, bro.getFlags().getAsInt(::AfeiExpedition.Flags.WinCount) + 1);
							}

							if (bro.getFlags().get("afei_need_full_circle") && !bro.getSkills().hasSkill("actives.afei_full_circle"))
							{
								bro.getSkills().add(this.new("scripts/skills/actives/afei_full_circle"));
								bro.getFlags().set("afei_need_full_circle", false);
							}
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
			this.m.Events.push(this.new("scripts/events/events/afei_r08_event"));
			this.m.Events.push(this.new("scripts/events/events/afei_r09_event"));
			this.m.Events.push(this.new("scripts/events/events/afei_r10_event"));
			this.m.Events.push(this.new("scripts/events/events/afei_r11_event"));
			this.m.Events.push(this.new("scripts/events/events/afei_r12_event"));
			this.m.Events.push(this.new("scripts/events/events/afei_r13_event"));
			this.m.Events.push(this.new("scripts/events/events/afei_r14_event"));
			this.m.Events.push(this.new("scripts/events/events/afei_r15_event"));
			this.m.Events.push(this.new("scripts/events/events/afei_r16_event"));
			this.m.Events.push(this.new("scripts/events/events/afei_r17_event"));
			this.m.Events.push(this.new("scripts/events/events/afei_r18_event"));
			this.m.Events.push(this.new("scripts/events/events/afei_r19_event"));
			this.m.Events.push(this.new("scripts/events/events/afei_r20_event"));
			this.m.Events.push(this.new("scripts/events/events/afei_r21_event"));
			this.m.Events.push(this.new("scripts/events/events/afei_r22_event"));
			this.m.Events.push(this.new("scripts/events/events/afei_r23_event"));
			this.m.Events.push(this.new("scripts/events/events/afei_r24_event"));
			this.m.Events.push(this.new("scripts/events/events/afei_r25_event"));
			this.m.Events.push(this.new("scripts/events/events/afei_r26_event"));
			this.m.Events.push(this.new("scripts/events/events/afei_r27_event"));
			this.m.Events.push(this.new("scripts/events/events/afei_r28_event"));
			this.m.Events.push(this.new("scripts/events/events/afei_safe_delivery_complete_event"));
			this.m.Events.push(this.new("scripts/events/events/afei_proxy_captain_event"));
			this.m.Events.push(this.new("scripts/events/events/afei_m02_review_event"));
			this.m.Events.push(this.new("scripts/events/events/afei_m03_roster_event"));
			this.m.Events.push(this.new("scripts/events/events/afei_m04_blue_event"));
			this.m.Events.push(this.new("scripts/events/events/afei_m05_bear_event"));
			this.m.Events.push(this.new("scripts/events/events/afei_m06_key_event"));
			this.m.Events.push(this.new("scripts/events/events/afei_m07_shadow_event"));
			this.m.Events.push(this.new("scripts/events/events/afei_m08_letters_event"));
			this.m.Events.push(this.new("scripts/events/events/afei_m09_camp_event"));
			this.m.Events.push(this.new("scripts/events/events/afei_camp_assign_event"));
			this.m.Events.push(this.new("scripts/events/events/afei_growth_check_event"));
			this.m.Events.push(this.new("scripts/events/events/afei_camp_review_event"));
		};
	});

	// 驻营日薪 35%（向上取整最低 2）+ 有驻营时日租 30
	::mods_hookExactClass("entity/tactical/player", function(o)
	{
		local getDailyCost = "getDailyCost" in o ? o.getDailyCost : null;
		if (getDailyCost != null)
		{
			o.getDailyCost = function()
			{
				local cost = getDailyCost();
				if (::AfeiExpedition.isAfeiOrigin() && this.getFlags().get(::AfeiExpedition.Flags.Camped))
				{
					cost = this.Math.max(2, this.Math.ceil(cost * 0.35));
				}
				return cost;
			};
		}
	});

});

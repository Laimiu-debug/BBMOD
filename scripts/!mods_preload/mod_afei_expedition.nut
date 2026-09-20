// Legacy Modding Script Hooks（与 Fate / 沙匪起源同代际；非 Modern/MSU）
// scenario 靠新增 scripts/scenarios/world/*_scenario.nut 自出现在列表。
::AfeiExpedition <- {
	ID = "mod_afei_expedition",
	Name = "大飞午远征团",
	Version = 2.7,
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
		EverRecruited = "afei_ever_",
		BicycleXp = "afei_bicycle_xp",
		BicyclePromptDone = "afei_bicycle_prompt_done",
		BicycleItemId = "accessory.afei_bicycle",
		EcigItemId = "accessory.afei_ecig"
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

	function isBicycleItem(_it)
	{
		return _it != null && _it.getID() == this.Flags.BicycleItemId;
	},

	function hasBicycleItem()
	{
		local gt = getroottable();
		local stashItems = gt.World.Assets.getStash().getItems();

		foreach (it in stashItems)
		{
			if (this.isBicycleItem(it))
			{
				return true;
			}
		}

		local roster = gt.World.getPlayerRoster().getAll();

		foreach (bro in roster)
		{
			try
			{
				local all = bro.getItems().getAllItems();

				foreach (it in all)
				{
					if (this.isBicycleItem(it))
					{
						return true;
					}
				}
			}
			catch (error)
			{
				local acc = bro.getItems().getItemAtSlot(gt.Const.ItemSlot.Accessory);

				if (this.isBicycleItem(acc))
				{
					return true;
				}
			}
		}

		return false;
	},

	function removeAllBicycles()
	{
		local gt = getroottable();
		local stash = gt.World.Assets.getStash();
		local stashItems = stash.getItems();

		for (local i = stashItems.len() - 1; i >= 0; i--)
		{
			local it = stashItems[i];

			if (this.isBicycleItem(it))
			{
				stash.remove(it);
			}
		}

		local roster = gt.World.getPlayerRoster().getAll();

		foreach (bro in roster)
		{
			local inv = bro.getItems();

			try
			{
				local all = inv.getAllItems();
				local toDrop = [];

				foreach (it in all)
				{
					if (this.isBicycleItem(it))
					{
						toDrop.push(it);
					}
				}

				foreach (it in toDrop)
				{
					inv.unequip(it);
				}
			}
			catch (error)
			{
				local acc = inv.getItemAtSlot(gt.Const.ItemSlot.Accessory);

				if (this.isBicycleItem(acc))
				{
					inv.unequip(acc);
				}
			}
		}
	},

	function abandonBicycleForXp()
	{
		local gt = getroottable();

		if (gt.World.Flags.get(this.Flags.BicycleXp))
		{
			return false;
		}

		this.removeAllBicycles();
		gt.World.Flags.set(this.Flags.BicycleXp, 1);
		gt.World.Flags.set(this.Flags.BicyclePromptDone, 1);

		local roster = gt.World.getPlayerRoster().getAll();

		foreach (bro in roster)
		{
			if (bro.getFlags().get(this.Flags.CaptainAfei) == true)
			{
				bro.getFlags().set(this.Flags.BicycleXp, true);
			}
		}

		return true;
	},

	function keepBicycleNoXp()
	{
		local gt = getroottable();
		gt.World.Flags.set(this.Flags.BicyclePromptDone, 1);
		return true;
	},

	function tryOfferBicycleAbandonAfterBottleLeave()
	{
		local gt = getroottable();

		if (!this.isAfeiOrigin())
		{
			return;
		}

		if (gt.World.Flags.get(this.Flags.BicyclePromptDone) || gt.World.Flags.get(this.Flags.BicycleXp))
		{
			return;
		}

		if (!this.hasBicycleItem())
		{
			gt.World.Flags.set(this.Flags.BicyclePromptDone, 1);
			return;
		}

		try
		{
			gt.World.Events.fire("event.afei_bottle_leave_bicycle");
		}
		catch (error)
		{
		}
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

		if (this.hasNamed("C02"))
		{
			this.noteUniqueFlag("afei_sign_witness_", _def.NamedId);
		}

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

		// C01–C31 编号保留；C24 糕糕已按用户要求移除，不计入
		for (local i = 1; i <= 31; i++)
		{
			if (i == 24)
			{
				continue;
			}

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


	function getFlagInt(_key)
	{
		return this.World.Flags.getAsInt(_key);
	},

	function addFlagInt(_key, _n)
	{
		this.World.Flags.set(_key, this.getFlagInt(_key) + _n);
	},

	function noteUniqueFlag(_prefix, _id)
	{
		if (_id == null || _id == "")
		{
			return false;
		}

		local key = _prefix + _id;

		if (this.World.Flags.get(key))
		{
			return false;
		}

		this.World.Flags.set(key, 1);
		this.addFlagInt(_prefix + "count", 1);
		return true;
	},

	function bumpBroFlag(_bro, _key, _n = 1)
	{
		if (_bro == null)
		{
			return;
		}

		_bro.getFlags().set(_key, _bro.getFlags().getAsInt(_key) + _n);
	},

	function getRosterAvgLevelDeployable()
	{
		local roster = this.World.getPlayerRoster().getAll();
		local sum = 0;
		local n = 0;

		foreach (bro in roster)
		{
			if (bro.getFlags().get(this.Flags.Camped))
			{
				continue;
			}

			sum += bro.getLevel();
			n += 1;
		}

		if (n <= 0)
		{
			return 0;
		}

		return sum * 1.0 / n;
	},

	function countDeployable()
	{
		local n = 0;
		local roster = this.World.getPlayerRoster().getAll();

		foreach (bro in roster)
		{
			if (!bro.getFlags().get(this.Flags.Camped))
			{
				n += 1;
			}
		}

		return n;
	},

	function tryStartStealDiscount()
	{
		if (!this.isAfeiOrigin() || !this.hasNamed("C03"))
		{
			return false;
		}

		if (this.World.getTime().Days < this.getFlagInt("afei_steal_ready_day"))
		{
			return false;
		}

		// 选一名已开门、未签约的候选人（R01–R28）
		local picks = [];

		for (local i = 1; i <= 28; i++)
		{
			local ri = i < 10 ? "0" + i : "" + i;
			local offered = this.World.Flags.get("afei_r" + ri + "_offered");
			local done = this.World.Flags.get("afei_r" + ri + "_done");

			if (offered && !done)
			{
				picks.push(ri);
			}
		}

		// 若无 Offered，仍允许对尚未招募的 C04–C31 预留（按序号找第一个未在队）
		local targetCid = null;

		if (picks.len() > 0)
		{
			local map = {
				"01": "C04", "02": "C05", "03": "C06", "04": "C07", "05": "C08", "06": "C09", "07": "C10",
				"08": "C11", "09": "C12", "10": "C13", "11": "C14", "12": "C15", "13": "C16", "14": "C17",
				"15": "C18", "16": "C19", "17": "C20", "18": "C21", "19": "C22", "20": "C23",
				"22": "C25", "23": "C26", "24": "C27", "25": "C28", "26": "C29", "27": "C30", "28": "C31"
			};
			targetCid = map[picks[0]];
		}
		else
		{
			for (local c = 4; c <= 31; c++)
			{
				local cid = c < 10 ? "C0" + c : "C" + c;

				if (!this.hasNamed(cid) && !this.World.Flags.get(this.Flags.EverRecruited + cid))
				{
					targetCid = cid;
					break;
				}
			}
		}

		if (targetCid == null || this.hasNamed(targetCid))
		{
			return false;
		}

		this.World.Flags.set("afei_steal_target", targetCid);
		return true;
	},

	function getHireCostFor(_namedId, _baseCost)
	{
		local cost = _baseCost;
		local target = this.World.Flags.get("afei_steal_target");

		if (target == _namedId)
		{
			local M = getroottable().Math;
			local save = M.min(200, M.floor(_baseCost * 0.2));
			cost = _baseCost - save;
		}

		return cost;
	},

	function tryChargeHire(_namedId, _baseCost)
	{
		local cost = this.getHireCostFor(_namedId, _baseCost);

		if (this.World.Assets.getMoney() < cost)
		{
			return false;
		}

		this.World.Assets.addMoney(-cost);

		if (this.World.Flags.get("afei_steal_target") == _namedId)
		{
			this.World.Flags.set("afei_steal_target", "");
			this.World.Flags.set("afei_steal_ready_day", this.World.getTime().Days + 7);
			this.noteUniqueFlag("afei_steal_hire_", _namedId);
			this.addFlagInt("afei_steal_hire_total", 1);
		}

		return true;
	},

	function onScrapToolsSpent(_n)
	{
		if (!this.isAfeiOrigin() || !this.hasNamed("C02") || _n <= 0)
		{
			return;
		}

		local prog = this.getFlagInt("afei_scrap_progress") + _n;

		while (prog >= 7 && this.getFlagInt("afei_scrap_charges") < 3)
		{
			prog -= 7;
			this.addFlagInt("afei_scrap_charges", 1);
		}

		this.World.Flags.set("afei_scrap_progress", prog);
	},

	function tryConsumeScrapCharge(_neededTools)
	{
		if (_neededTools < 2)
		{
			return 0;
		}

		if (this.getFlagInt("afei_scrap_charges") <= 0)
		{
			return 0;
		}

		this.World.Flags.set("afei_scrap_charges", this.getFlagInt("afei_scrap_charges") - 1);
		return 1;
	},


	function isEscortContractType(_type)
	{
		if (_type == null || _type == "")
		{
			return false;
		}

		if (_type == "contract.escort_caravan" || _type == "contract.escort_envoy" || _type == "contract.afei_blue_escort" || _type == "contract.afei_m08_escort")
		{
			return true;
		}

		return false;
	},

	function tryRopeTrain()
	{
		if (!this.isAfeiOrigin() || !this.hasNamed("C07"))
		{
			return false;
		}

		local day = this.World.getTime().Days;
		local last = this.getFlagInt("afei_rope_train_day");

		if (last > 0 && day - last < 3)
		{
			return false;
		}

		if (!this.trySpendFoodApprox(3))
		{
			return false;
		}

		this.World.Flags.set("afei_rope_train_day", day);
		this.addFlagInt("afei_rope_train", 1);
		return true;
	},

	function recordRopeTrain()
	{
		if (!this.isAfeiOrigin())
		{
			return false;
		}

		local day = this.World.getTime().Days;
		local last = this.getFlagInt("afei_rope_train_day");

		if (last > 0 && day - last < 3)
		{
			return false;
		}

		this.World.Flags.set("afei_rope_train_day", day);
		this.addFlagInt("afei_rope_train", 1);
		return true;
	},

	function findContractHome()
	{
		local home = null;

		try
		{
			local list = this.World.EntityManager.getSettlements();
			local pt = this.World.State.getPlayer().getTile();
			local best = 99999;

			foreach (s in list)
			{
				if (s == null)
				{
					continue;
				}

				try
				{
					if (s.isMilitary())
					{
						continue;
					}
				}
				catch (error)
				{
				}

				local d = s.getTile().getDistanceTo(pt);

				if (d < best)
				{
					best = d;
					home = s;
				}
			}
		}
		catch (error2)
		{
		}

		return home;
	},

	function bindContractEmployer(_contract, _home)
	{
		try
		{
			if (_home != null && ("setHome" in _contract))
			{
				_contract.setHome(_home);
			}
		}
		catch (error)
		{
		}

		local fac = null;

		try
		{
			if (_home != null)
			{
				fac = _home.getOwner();
			}
		}
		catch (error2)
		{
		}

		if (fac == null)
		{
			try
			{
				fac = this.World.FactionManager.getFactionOfType(this.Const.FactionType.Settlement);
			}
			catch (error3)
			{
				try
				{
					fac = this.World.FactionManager.getFactionOfType(this.Const.FactionType.NobleHouse);
				}
				catch (error4)
				{
				}
			}
		}

		if (fac == null)
		{
			return false;
		}

		try
		{
			_contract.setFaction(fac.getID());
		}
		catch (error5)
		{
		}

		try
		{
			local ch = fac.getRandomCharacter();

			if (ch != null)
			{
				_contract.setEmployerID(ch.getID());
			}
		}
		catch (error6)
		{
		}

		return true;
	},


	function spawnBlueEscorts(_ctx)
	{
		local gt = getroottable();

		if (!gt.World.Flags.get("afei_spawn_blue_escorts"))
		{
			return 0;
		}

		gt.World.Flags.set("afei_spawn_blue_escorts", 0);
		local spawned = 0;

		try
		{
			local players = gt.Tactical.Entities.getInstancesOfFaction(gt.Const.Faction.Player);

			if (players == null || players.len() == 0)
			{
				return 0;
			}

			local anchor = players[0];

			for (local n = 0; n < 2; n++)
			{
				local tile = null;

				foreach (p in players)
				{
					if (p == null || !p.isPlacedOnMap())
					{
						continue;
					}

					local myTile = p.getTile();

					for (local dir = 0; dir < 6; dir++)
					{
						if (!myTile.hasNextTile(dir))
						{
							continue;
						}

						local t = myTile.getNextTile(dir);

						if (t != null && t.IsEmpty)
						{
							tile = t;
							break;
						}
					}

					if (tile != null)
					{
						break;
					}
				}

				if (tile == null)
				{
					break;
				}

				local path = "scripts/entity/tactical/humans/afei_blue_guard";
				local e = null;

				try
				{
					e = gt.Tactical.spawnEntity(path, tile.Coords.X, tile.Coords.Y);
				}
				catch (errorSpawn)
				{
					try
					{
						e = gt.Tactical.spawnEntity("scripts/entity/tactical/humans/militia_guest", tile.Coords.X, tile.Coords.Y);
					}
					catch (error2)
					{
					}
				}

				if (e == null)
				{
					continue;
				}

				try
				{
					e.setFaction(gt.Const.Faction.Player);
				}
				catch (errorFac)
				{
				}

				try
				{
					e.setName("匿名蓝旗");
					e.getFlags().set("afei_blue_temp", true);
					e.getFlags().set("afei_anonymous_blue", true);
				}
				catch (errorFlag)
				{
				}

				spawned += 1;
			}
		}
		catch (errorAll)
		{
		}

		return spawned;
	},

	function spawnFrostRosterFallback(_ctx)
	{
		local gt = getroottable();

		if (!gt.World.Flags.get("afei_spawn_frost_roster"))
		{
			return 0;
		}

		gt.World.Flags.set("afei_spawn_frost_roster", 0);
		local spawned = 0;

		try
		{
			local enemies = gt.Tactical.Entities.getHostileActors(gt.Const.Faction.Player);
			local alreadyFrost = 0;
			local alreadyUnhold = 0;

			if (enemies != null)
			{
				foreach (e in enemies)
				{
					if (e == null)
					{
						continue;
					}

					if (e.getFlags().get("afei_frost_unhold"))
					{
						alreadyFrost += 1;
					}

					local n = e.getName();

					if (n != null && (n.find("Unhold") != null || n.find("巨兽") != null || n.find("unhold") != null))
					{
						alreadyUnhold += 1;
					}
				}
			}

			// 若地点 spawnlist 已给出足够巨兽，则不再硬塞
			if (alreadyFrost >= 1 || alreadyUnhold >= 3)
			{
				return 0;
			}

			local beastFaction = gt.Const.Faction.Beasts;
			local tiles = [];

			try
			{
				local all = gt.Tactical.Entities.getInstancesOfFaction(beastFaction);

				if (all != null && all.len() > 0)
				{
					foreach (a in all)
					{
						if (a != null && a.isPlacedOnMap())
						{
							tiles.push(a.getTile());
						}
					}
				}
			}
			catch (errorTiles)
			{
			}

			local near = tiles.len() > 0 ? tiles[0] : null;
			local paths = [
				"scripts/entity/tactical/enemies/afei_frost_unhold",
				"scripts/entity/tactical/enemies/unhold_frost",
				"scripts/entity/tactical/enemies/unhold"
			];

			if (alreadyFrost < 1)
			{
				foreach (path in paths)
				{
					local tile = null;

					if (near != null)
					{
						for (local dir = 0; dir < 6; dir++)
						{
							if (!near.hasNextTile(dir))
							{
								continue;
							}

							local t = near.getNextTile(dir);

							if (t != null && t.IsEmpty)
							{
								tile = t;
								break;
							}
						}
					}

					if (tile == null)
					{
						continue;
					}

					local frost = null;

					try
					{
						frost = gt.Tactical.spawnEntity(path, tile.Coords.X, tile.Coords.Y);
					}
					catch (errorS)
					{
						frost = null;
					}

					if (frost == null)
					{
						continue;
					}

					try
					{
						frost.setFaction(beastFaction);
					}
					catch (errorF)
					{
					}

					frost.getFlags().set("afei_frost_unhold", true);

					try
					{
						frost.setName("冰霜巨兽");
					}
					catch (errorN)
					{
					}

					spawned += 1;
					break;
				}
			}

			local needEscorts = 2;

			if (alreadyUnhold > alreadyFrost)
			{
				needEscorts = 2 - (alreadyUnhold - alreadyFrost);
			}

			if (needEscorts < 0)
			{
				needEscorts = 0;
			}

			if (needEscorts > 2)
			{
				needEscorts = 2;
			}

			for (local i = 0; i < needEscorts; i++)
			{
				local tile = null;

				if (near != null)
				{
					for (local dir = 0; dir < 6; dir++)
					{
						if (!near.hasNextTile(dir))
						{
							continue;
						}

						local t = near.getNextTile(dir);

						if (t != null && t.IsEmpty)
						{
							tile = t;
							break;
						}
					}
				}

				if (tile == null)
				{
					break;
				}

				local u = null;

				try
				{
					u = gt.Tactical.spawnEntity("scripts/entity/tactical/enemies/unhold", tile.Coords.X, tile.Coords.Y);
				}
				catch (errorU)
				{
					break;
				}

				if (u == null)
				{
					break;
				}

				try
				{
					u.setFaction(beastFaction);
					u.setName("巨兽护卫");
				}
				catch (errorU2)
				{
				}

				spawned += 1;
			}
		}
		catch (errorAll)
		{
		}

		return spawned;
	},

	function resolveCoverProtector(_target)
	{
		if (_target == null)
		{
			return null;
		}

		local cover = _target.getSkills().getSkillByID("effects.afei_cover_up");

		if (cover == null || cover.m.Consumed || cover.m.ProtectorID == 0)
		{
			return null;
		}

		local protector = null;

		try
		{
			foreach (a in getroottable().Tactical.Entities.getAllInstancesAsArray())
			{
				if (a != null && a.getID() == cover.m.ProtectorID && a.isAlive())
				{
					protector = a;
					break;
				}
			}
		}
		catch (error)
		{
		}

		if (protector == null || protector.getID() == _target.getID())
		{
			return null;
		}

		try
		{
			if (protector.getTile().getDistanceTo(_target.getTile()) > 1)
			{
				return null;
			}
		}
		catch (error2)
		{
			return null;
		}

		return protector;
	},

	function tryOfferAfeiContract(_ctx, _scriptPath, _activate)
	{
		if (!this.isAfeiOrigin())
		{
			return false;
		}

		local c = null;

		try
		{
			c = _ctx.new(_scriptPath);
		}
		catch (error)
		{
			return false;
		}

		local home = this.findContractHome();
		this.bindContractEmployer(c, home);

		try
		{
			if (("start" in c))
			{
				c.start();
			}
		}
		catch (error2)
		{
		}

		try
		{
			this.World.Contracts.addContract(c);
		}
		catch (error3)
		{
			return false;
		}

		if (_activate)
		{
			try
			{
				this.World.Contracts.setActiveContract(c);
				c.setState("Running");
			}
			catch (error4)
			{
			}
		}

		return true;
	},

	function completeM04FromContract(_type)
	{
		if (_type != "contract.afei_blue_escort")
		{
			return false;
		}

		if (this.World.Flags.get(this.Flags.M04Done))
		{
			return false;
		}

		this.World.Flags.set("afei_m04_pending", 0);
		this.World.Flags.set(this.Flags.M04Done, 1);
		this.bumpCohesion(4);
		return true;
	},

	function completeM08StepFromContract(_type, _ctx)
	{
		if (!this.World.Flags.get("afei_m08_pending") || this.World.Flags.get(this.Flags.M08Done))
		{
			return false;
		}

		if (_type == "contract.afei_m08_supply")
		{
			if (this.World.Flags.get("afei_m08_supply_done"))
			{
				return false;
			}

			this.World.Flags.set("afei_m08_supply_done", 1);

			if (_ctx != null)
			{
				this.tryOfferAfeiContract(_ctx, "scripts/contracts/contracts/afei_m08_escort_contract", true);
			}
		}
		else if (_type == "contract.afei_m08_escort")
		{
			if (this.World.Flags.get("afei_m08_escort_done"))
			{
				return false;
			}

			this.World.Flags.set("afei_m08_escort_done", 1);
		}
		else
		{
			return false;
		}

		if (this.World.Flags.get("afei_m08_supply_done") && this.World.Flags.get("afei_m08_escort_done"))
		{
			this.World.Flags.set("afei_m08_pending", 0);
			this.World.Flags.set(this.Flags.M08Done, 1);
			this.bumpCohesion(6);
			this.tryAwakenAfei();
			return true;
		}

		return false;
	},

	function tryCompleteM07FromCombat()
	{
		if (this.World.Flags.get(this.Flags.M07Done))
		{
			return false;
		}

		local combat = this.World.Flags.get("afei_active_contract_combat");

		if (combat != "contract.afei_frost_hunt" && !this.World.Flags.get("afei_m07_combat"))
		{
			return false;
		}

		if (!this.World.Flags.get("afei_m07_pending") && combat != "contract.afei_frost_hunt")
		{
			return false;
		}

		if (this.countDeployable() < 8 || this.getRosterAvgLevelDeployable() < 7)
		{
			return false;
		}

		this.World.Flags.set("afei_m07_pending", 0);
		this.World.Flags.set("afei_m07_combat", 0);
		this.World.Flags.set("afei_active_contract_combat", "");
		this.World.Flags.set(this.Flags.M07Done, 1);
		this.World.Assets.addMoney(800);
		this.bumpCohesion(6);
		this.World.Flags.set("afei_m07_medal", 1);
		return true;
	},

	function growthCond(_cid, _bro)
	{
		local wins = _bro.getFlags().getAsInt(this.Flags.WinCount);
		local level = _bro.getLevel();
		local contracts = this.getPaidContracts();
		local reviews = this.getFlagInt(this.Flags.ReviewCount);
		local jiahao = this.getJiahaoCount();
		local bf = _bro.getFlags();

		if (_cid == "C01")
		{
			return level >= 7 && wins >= 8 && jiahao >= 6;
		}

		if (level < 5)
		{
			return false;
		}

		// 糕糕（C24）已移除
		if (_cid == "C24")
		{
			return false;
		}

		if (_cid == "C02")
		{
			return this.getFlagInt("afei_sign_witness_count") >= 3 && contracts >= 4 && reviews >= 2;
		}

		if (_cid == "C03")
		{
			return wins >= 5 && (this.getFlagInt("afei_steal_hire_count") >= 3 || jiahao >= 6);
		}

		if (_cid == "C04")
		{
			return bf.getAsInt("afei_ball_win") >= 5 && this.getFlagInt("afei_ball_partner_count") >= 3;
		}

		if (_cid == "C05")
		{
			return wins >= 6 && bf.getAsInt("afei_spotlight2_win") >= 3;
		}

		if (_cid == "C06")
		{
			return this.getFlagInt("afei_swap_partner_count") >= 3 && wins >= 3;
		}

		if (_cid == "C07")
		{
			return this.getFlagInt("afei_rope_train") >= 2 && bf.getAsInt("afei_biantai_win") >= 3;
		}

		if (_cid == "C08")
		{
			return bf.getAsInt("afei_cover_intercept") >= 5 || wins >= 10;
		}

		if (_cid == "C09")
		{
			return wins >= 5 && bf.getAsInt("afei_drum_heal_win") >= 2;
		}

		if (_cid == "C10")
		{
			return bf.getAsInt("afei_order_win") >= 4 && bf.getAsInt("afei_proxy_win") >= 1;
		}

		if (_cid == "C11")
		{
			return bf.getAsInt("afei_proxy_win") >= 3 && reviews >= 2;
		}

		if (_cid == "C12")
		{
			return this.getFlagInt("afei_escort_contracts") >= 3 || contracts >= 6;
		}

		if (_cid == "C13")
		{
			return wins >= 5 && bf.getAsInt("afei_goose_win") >= 3;
		}

		if (_cid == "C14")
		{
			return this.World.Flags.get(this.Flags.M06Done) && (bf.getAsInt("afei_net_free") >= 3 || wins >= 8);
		}

		if (_cid == "C15")
		{
			return (this.getFlagInt("afei_escort_contracts") >= 2 || contracts >= 4) && bf.getAsInt("afei_halfstep_win") >= 5;
		}

		if (_cid == "C16")
		{
			return (this.getFlagInt("afei_escort_contracts") >= 3 || contracts >= 6) && bf.getAsInt("afei_return_road") >= 2;
		}

		if (_cid == "C17")
		{
			return wins >= 6 && this.getFlagInt("afei_pokemon_partner_count") >= 3;
		}

		if (_cid == "C18")
		{
			return bf.getAsInt("afei_understand2_win") >= 3;
		}

		if (_cid == "C19")
		{
			return bf.getAsInt("afei_mouth_win") >= 3;
		}

		if (_cid == "C20")
		{
			return wins >= 6;
		}

		if (_cid == "C21")
		{
			return bf.getAsInt("afei_king_dance_total") >= 8 && bf.getAsInt("afei_curtain_use") >= 3;
		}

		if (_cid == "C22")
		{
			return this.getFlagInt("afei_moon_cake") >= 4 && wins >= 6;
		}

		if (_cid == "C23")
		{
			return bf.getAsInt("afei_sprint_win") >= 6;
		}


		if (_cid == "C25")
		{
			return bf.getAsInt("afei_qin_win") >= 6;
		}

		if (_cid == "C26")
		{
			return wins >= 6 && bf.getAsInt("afei_curtain_leave_win") >= 3;
		}

		if (_cid == "C27")
		{
			return wins >= 6 && bf.getAsInt("afei_look_flag") >= 6;
		}

		if (_cid == "C28")
		{
			return bf.getAsInt("afei_bell_win") >= 6;
		}

		if (_cid == "C29")
		{
			return bf.getAsInt("afei_baton_hit") >= 8 && wins >= 6;
		}

		if (_cid == "C30")
		{
			return bf.getAsInt("afei_door_block") >= 8 && wins >= 6;
		}

		if (_cid == "C31")
		{
			return contracts >= 8;
		}

		return wins >= 5;
	},

	function applyGrowthReward(_cid, _bro)
	{
		local b = _bro.getBaseProperties();

		if (_cid == "C01")
		{
			b.Hitpoints += 8;
			_bro.getFlags().set("afei_wawa_range4", true);
		}
		else if (_cid == "C02")
		{
			this.World.Flags.set("afei_abacus_dual", 1);
		}
		else if (_cid == "C03")
		{
			this.World.Flags.set("afei_borrow_g03", 1);
		}
		else if (_cid == "C04")
		{
			_bro.getFlags().set("afei_bottle_no_md_pen", true);
		}
		else if (_cid == "C06")
		{
			_bro.getFlags().set("afei_loyalty_range3", true);
		}
		else if (_cid == "C08")
		{
			_bro.getFlags().set("afei_cover_dr25", true);
		}
		else if (_cid == "C09")
		{
			_bro.getFlags().set("afei_small_heart_ok", true);
		}
		else if (_cid == "C10")
		{
			_bro.getFlags().set("afei_fear_no_hit_pen", true);
		}
		else if (_cid == "C11")
		{
			_bro.getFlags().set("afei_steady_five", true);
		}
		else if (_cid == "C12")
		{
			_bro.getFlags().set("afei_late_aim_1", true);
		}
		else if (_cid == "C13")
		{
			_bro.getFlags().set("afei_gaga_no_hit_pen", true);
		}
		else if (_cid == "C14")
		{
			_bro.getFlags().set("afei_lock_first_free", true);
		}
		else if (_cid == "C15")
		{
			_bro.getFlags().set("afei_move_fatigue_2", true);
		}
		else if (_cid == "C16")
		{
			_bro.getFlags().set("afei_return_twice", true);
		}
		else if (_cid == "C17")
		{
			_bro.getFlags().set("afei_pokemon_md4", true);
		}
		else if (_cid == "C18")
		{
			_bro.getFlags().set("afei_understand_3", true);
		}
		else if (_cid == "C19")
		{
			b.Bravery += 8;
			_bro.getFlags().set("afei_shrink_fat14", true);
		}
		else if (_cid == "C20")
		{
			_bro.getFlags().set("afei_long_watch_7", true);
		}
		else if (_cid == "C21")
		{
			_bro.getFlags().set("afei_king_dance_3", true);
		}
		else if (_cid == "C22")
		{
			_bro.getFlags().set("afei_guard_self_15", true);
		}
		else if (_cid == "C23")
		{
			_bro.getFlags().set("afei_sprint_fat10", true);
		}
		else if (_cid == "C25")
		{
			_bro.getFlags().set("afei_snake_90", true);
		}
		else if (_cid == "C26")
		{
			_bro.getFlags().set("afei_hold_md5", true);
		}
		else if (_cid == "C27")
		{
			_bro.getFlags().set("afei_breach_no_pen", true);
		}
		else if (_cid == "C28")
		{
			_bro.getFlags().set("afei_detour_fat9", true);
		}
		else if (_cid == "C29")
		{
			_bro.getFlags().set("afei_baton_range3", true);
		}
		else if (_cid == "C30")
		{
			_bro.getFlags().set("afei_door_fat12", true);
		}
		else if (_cid == "C31")
		{
			_bro.getFlags().set("afei_budget_two", true);
		}

		_bro.getSkills().update();
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

			if (!this.growthCond(cid, bro))
			{
				continue;
			}

			this.World.Flags.set(gkey, 1);
			this.bumpCohesion(3);

			if (cid != "C01")
			{
				this.recordJiahao(cid);
			}

			this.applyGrowthReward(cid, bro);
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

				local ctype = "";

				try
				{
					if ("getType" in this)
					{
						ctype = this.getType();
					}
				}
				catch (errorType)
				{
				}

				local isAfeiPaid = ctype.find("contract.afei_") == 0;

				if (payment > 0 || isAfeiPaid)
				{
					::AfeiExpedition.addPaidContract(1);

					if (::AfeiExpedition.isEscortContractType(ctype))
					{
						::AfeiExpedition.addFlagInt("afei_escort_contracts", 1);
					}

					::AfeiExpedition.completeM04FromContract(ctype);
					::AfeiExpedition.completeM08StepFromContract(ctype, this);

					if (ctype == "contract.afei_frost_hunt")
					{
						::AfeiExpedition.tryCompleteM07FromCombat();
						this.World.Flags.set("afei_spawn_blue_escorts", 0);
						this.World.Flags.set("afei_spawn_frost_roster", 0);
						this.World.Flags.set("afei_active_contract_combat", "");
					}
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

				local bottleLeaving = _brother != null && _brother.getFlags().get(::AfeiExpedition.Flags.NamedId) == "C04";
				local result = dismissBrother(_brother);

				if (bottleLeaving)
				{
					::AfeiExpedition.tryOfferBicycleAbandonAfterBottleLeave();
				}

				return result;
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

				local bottleLeaving = bro != null && bro.getFlags().get(::AfeiExpedition.Flags.NamedId) == "C04";
				local result = onDismissBrother(_data);

				if (bottleLeaving)
				{
					::AfeiExpedition.tryOfferBicycleAbandonAfterBottleLeave();
				}

				return result;
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
				::AfeiExpedition.spawnBlueEscorts(this);
				::AfeiExpedition.spawnFrostRosterFallback(this);
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
						::AfeiExpedition.tryCompleteM07FromCombat();
						this.World.Flags.set("afei_spawn_blue_escorts", 0);
						this.World.Flags.set("afei_spawn_frost_roster", 0);
						this.World.Flags.set("afei_active_contract_combat", "");
						local roster = this.World.getPlayerRoster().getAll();

						foreach (bro in roster)
						{
							if (bro.getFlags().get(::AfeiExpedition.Flags.NamedId) && !bro.getFlags().get(::AfeiExpedition.Flags.Camped))
							{
								bro.getFlags().set(::AfeiExpedition.Flags.WinCount, bro.getFlags().getAsInt(::AfeiExpedition.Flags.WinCount) + 1);

								local f = bro.getFlags();

								if (f.get("afei_combat_ball"))
								{
									f.set("afei_ball_win", f.getAsInt("afei_ball_win") + 1);
								}

								if (f.getAsInt("afei_combat_spotlight") >= 2)
								{
									f.set("afei_spotlight2_win", f.getAsInt("afei_spotlight2_win") + 1);
								}

								if (f.get("afei_combat_biantai"))
								{
									f.set("afei_biantai_win", f.getAsInt("afei_biantai_win") + 1);
								}

								if (f.get("afei_combat_drum_heal"))
								{
									f.set("afei_drum_heal_win", f.getAsInt("afei_drum_heal_win") + 1);
								}

								if (f.get("afei_combat_order"))
								{
									f.set("afei_order_win", f.getAsInt("afei_order_win") + 1);
								}

								if (f.get(::AfeiExpedition.Flags.ProxyCaptain))
								{
									f.set("afei_proxy_win", f.getAsInt("afei_proxy_win") + 1);
								}

								if (f.get("afei_combat_goose"))
								{
									f.set("afei_goose_win", f.getAsInt("afei_goose_win") + 1);
								}

								if (f.get("afei_combat_halfstep"))
								{
									f.set("afei_halfstep_win", f.getAsInt("afei_halfstep_win") + 1);
								}

								if (f.get("afei_combat_understand2"))
								{
									f.set("afei_understand2_win", f.getAsInt("afei_understand2_win") + 1);
								}

								if (f.get("afei_combat_mouth"))
								{
									f.set("afei_mouth_win", f.getAsInt("afei_mouth_win") + 1);
								}

								if (f.get("afei_combat_sprint"))
								{
									f.set("afei_sprint_win", f.getAsInt("afei_sprint_win") + 1);
								}

								if (f.get("afei_combat_late_hit"))
								{
									f.set("afei_late_hit_win", f.getAsInt("afei_late_hit_win") + 1);
								}

								if (f.get("afei_combat_qin"))
								{
									f.set("afei_qin_win", f.getAsInt("afei_qin_win") + 1);
								}

								if (f.get("afei_combat_curtain_leave"))
								{
									f.set("afei_curtain_leave_win", f.getAsInt("afei_curtain_leave_win") + 1);
								}

								if (f.get("afei_combat_bell"))
								{
									f.set("afei_bell_win", f.getAsInt("afei_bell_win") + 1);
								}

								// clear combat temp flags
								f.set("afei_combat_ball", false);
								f.set("afei_combat_spotlight", 0);
								f.set("afei_combat_biantai", false);
								f.set("afei_combat_drum_heal", false);
								f.set("afei_combat_order", false);
								f.set("afei_combat_goose", false);
								f.set("afei_combat_halfstep", false);
								f.set("afei_combat_understand2", false);
								f.set("afei_combat_mouth", false);
								f.set("afei_combat_sprint", false);
								f.set("afei_combat_late_hit", false);
								f.set("afei_combat_qin", false);
								f.set("afei_combat_curtain_leave", false);
								f.set("afei_combat_bell", false);
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

			if (_skill == this && ::AfeiExpedition.isAfeiOrigin())
			{
				local user = this.getContainer().getActor();
				local sid = this.getID();

				if (user != null && user.isAlive())
				{
					local f = user.getFlags();

					if (sid == "actives.afei_teammate_ball" || sid.find("teammate_ball") != null)
					{
						f.set("afei_combat_ball", true);
					}

					if (sid == "actives.afei_biantai")
					{
						f.set("afei_combat_biantai", true);
					}

					if (sid == "actives.afei_guard_swap" && _targetEntity != null)
					{
						local tid = _targetEntity.getFlags().get(::AfeiExpedition.Flags.NamedId);
						if (tid == null || tid == "") { tid = "" + _targetEntity.getID(); }
						::AfeiExpedition.noteUniqueFlag("afei_swap_partner_", tid);
					}

					if (sid == "actives.afei_chaoju")
					{
						f.set("afei_combat_spotlight", f.getAsInt("afei_combat_spotlight") + 1);
					}

					if (sid == "actives.afei_drum")
					{
						f.set("afei_combat_drum_heal", true);
					}

					if (sid == "actives.afei_dui_sentence" || sid == "actives.afei_wawa_call" || sid == "actives.afei_full_circle")
					{
						f.set("afei_combat_order", true);
					}

					if (sid == "actives.afei_goose_bully")
					{
						f.set("afei_combat_goose", true);
					}

					if (sid == "actives.afei_half_step")
					{
						f.set("afei_combat_halfstep", true);
					}

					if (sid == "actives.afei_return_road")
					{
						f.set("afei_return_road", f.getAsInt("afei_return_road") + 1);
					}

					if (sid == "actives.afei_pokemon" && _targetEntity != null)
					{
						local tid = _targetEntity.getFlags().get(::AfeiExpedition.Flags.NamedId);
						if (tid == null || tid == "") { tid = "" + _targetEntity.getID(); }
						::AfeiExpedition.noteUniqueFlag("afei_pokemon_partner_", tid);
					}

					if (sid == "actives.afei_mouth_strong")
					{
						f.set("afei_combat_mouth", true);
					}

					if (sid == "actives.afei_short_sprint")
					{
						f.set("afei_combat_sprint", true);
					}

					if (sid == "actives.afei_qin_god" || sid == "actives.afei_curve_force")
					{
						f.set("afei_combat_qin", true);
					}

					if (sid == "actives.afei_bell_lead")
					{
						f.set("afei_combat_bell", true);
					}

					if (sid == "actives.afei_look_flag")
					{
						f.set("afei_look_flag", f.getAsInt("afei_look_flag") + 1);
					}

					if (sid == "actives.afei_door_block")
					{
						f.set("afei_door_block", f.getAsInt("afei_door_block") + 1);
					}

					if (sid == "actives.afei_catch_baton")
					{
						f.set("afei_baton_hit", f.getAsInt("afei_baton_hit") + 1);
					}

					if (sid == "actives.afei_king_dance")
					{
						f.set("afei_king_dance_total", f.getAsInt("afei_king_dance_total") + 1);
					}

					if (sid == "actives.afei_curtain_yield")
					{
						f.set("afei_curtain_use", f.getAsInt("afei_curtain_use") + 1);
					}

					if (sid == "actives.afei_spare_key" || sid == "actives.afei_lock_wagon")
					{
						f.set("afei_net_free", f.getAsInt("afei_net_free") + 1);
					}
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


	// 顶上去：攻击管线改目标（优先于受击承伤）
	::mods_hookExactClass("skills/skill", function(o)
	{
		if (!("attackEntity" in o))
		{
			return;
		}

		local attackEntity = o.attackEntity;
		o.attackEntity = function(_user, _targetEntity)
		{
			if (::AfeiExpedition.isAfeiOrigin() && _targetEntity != null && this.isAttack() && !this.isRanged())
			{
				local protector = ::AfeiExpedition.resolveCoverProtector(_targetEntity);

				if (protector != null)
				{
					local canHit = true;

					try
					{
						local dist = _user.getTile().getDistanceTo(protector.getTile());
						local maxr = this.getMaxRange();
						local minr = this.getMinRange();

						if (dist < minr || dist > maxr)
						{
							canHit = false;
						}
					}
					catch (errorRange)
					{
					}

					if (canHit)
					{
						local cover = _targetEntity.getSkills().getSkillByID("effects.afei_cover_up");

						if (cover != null)
						{
							cover.m.Consumed = true;
							protector.getFlags().set("afei_cover_intercept", protector.getFlags().getAsInt("afei_cover_intercept") + 1);
							cover.removeSelf();

							local covering = protector.getSkills().getSkillByID("effects.afei_covering");

							if (covering != null)
							{
								covering.removeSelf();
							}
						}

						_targetEntity = protector;
						protector.getFlags().set("afei_cover_dr_pending", true);
					}
				}
			}

			return attackEntity(_user, _targetEntity);
		};
	});

	// 顶上去承伤减免（改目标后打在守护者上）
	::mods_hookExactClass("entity/tactical/actor", function(o)
	{
		local onBeforeDamageReceived = "onBeforeDamageReceived" in o ? o.onBeforeDamageReceived : null;

		if (onBeforeDamageReceived != null)
		{
			o.onBeforeDamageReceived = function(_attacker, _skill, _hitInfo)
			{
				if (::AfeiExpedition.isAfeiOrigin() && this.getFlags().get("afei_cover_dr_pending"))
				{
					this.getFlags().set("afei_cover_dr_pending", false);
					local dr = 0.85;

					if (this.getFlags().get("afei_cover_dr25") || this.World.Flags.get(::AfeiExpedition.Flags.GrowthDone + "C08"))
					{
						dr = 0.75;
					}

					try
					{
						if ("DamageInflictedHitpoints" in _hitInfo)
						{
							_hitInfo.DamageInflictedHitpoints = this.Math.floor(_hitInfo.DamageInflictedHitpoints * dr);
						}
					}
					catch (error)
					{
					}
				}

				return onBeforeDamageReceived(_attacker, _skill, _hitInfo);
			};
		}
	});

	// 队友给的球 + 顶上去改目标（单体近战，尝试即消耗）
	::mods_hookExactClass("entity/tactical/actor", function(o)
	{
		local onDamageReceived = o.onDamageReceived;
		o.onDamageReceived = function(_attacker, _skill, _hitInfo)
		{
			if (::AfeiExpedition.isAfeiOrigin() && this.getFlags().get("afei_cover_dr_pending"))
			{
				this.getFlags().set("afei_cover_dr_pending", false);
				local dr = 0.85;

				if (this.getFlags().get("afei_cover_dr25") || this.World.Flags.get(::AfeiExpedition.Flags.GrowthDone + "C08"))
				{
					dr = 0.75;
				}

				try
				{
					if ("DamageInflictedHitpoints" in _hitInfo)
					{
						_hitInfo.DamageInflictedHitpoints = this.Math.floor(_hitInfo.DamageInflictedHitpoints * dr);
					}
				}
				catch (errorDr)
				{
				}
			}

			if (::AfeiExpedition.isAfeiOrigin() && _attacker != null && _skill != null && _skill.isAttack() && !_skill.isRanged())
			{
				local cover = this.getSkills().getSkillByID("effects.afei_cover_up");

				if (cover != null && !cover.m.Consumed && cover.m.ProtectorID != 0)
				{
					local protector = null;

					try
					{
						foreach (a in this.Tactical.Entities.getAllInstancesAsArray())
						{
							if (a != null && a.getID() == cover.m.ProtectorID && a.isAlive())
							{
								protector = a;
								break;
							}
						}
					}
					catch (error)
					{
					}

					if (protector != null && protector.getID() != this.getID())
					{
						local adj = false;

						try
						{
							adj = protector.getTile().getDistanceTo(this.getTile()) <= 1;
						}
						catch (error2)
						{
						}

						if (adj)
						{
							cover.m.Consumed = true;
							local dr = 0.85;

							if (protector.getFlags().get("afei_cover_dr25") || this.World.Flags.get(::AfeiExpedition.Flags.GrowthDone + "C08"))
							{
								dr = 0.75;
							}

							// G08 后拦截生命减伤 25%

							try
							{
								if ("DamageInflictedHitpoints" in _hitInfo)
								{
									_hitInfo.DamageInflictedHitpoints = this.Math.floor(_hitInfo.DamageInflictedHitpoints * dr);
								}
							}
							catch (error3)
							{
							}

							protector.getFlags().set("afei_cover_intercept", protector.getFlags().getAsInt("afei_cover_intercept") + 1);
							cover.removeSelf();
							return protector.onDamageReceived(_attacker, _skill, _hitInfo);
						}
					}
				}
			}

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

		if ("checkMorale" in o)
		{
			local checkMorale = o.checkMorale;
			o.checkMorale = function(_change, _difficulty, _type = null, _showIconBeforeMoraleChange = true, _noNewLine = false)
			{
				local before = this.getMoraleState();
				local result = checkMorale(_change, _difficulty, _type, _showIconBeforeMoraleChange, _noNewLine);

				if (!::AfeiExpedition.isAfeiOrigin() || _change >= 0 || result)
				{
					return result;
				}

				local opt = this.getSkills().getSkillByID("actives.afei_optimist");

				if (opt != null && "m" in opt && opt.m.Used < opt.m.MaxUses && !this.getFlags().get("afei_optimist_round"))
				{
					opt.m.Used += 1;
					this.getFlags().set("afei_optimist_round", true);

					try
					{
						this.setMoraleState(before);
					}
					catch (error)
					{
					}

					return true;
				}

				local ouqi = this.getSkills().getSkillByID("actives.afei_ouqi");

				if (ouqi != null && "m" in ouqi && !ouqi.m.Used)
				{
					ouqi.m.Used = true;

					try
					{
						this.setMoraleState(before);
					}
					catch (error2)
					{
					}

					return checkMorale(_change, _difficulty, _type, _showIconBeforeMoraleChange, _noNewLine);
				}

				return result;
			};
		}

		if ("addXP" in o)
		{
			local addXP = o.addXP;
			o.addXP = function(_xp, _show = true)
			{
				if (::AfeiExpedition.isAfeiOrigin() && _xp > 0)
				{
					if (this.getFlags().get("afei_mentorship"))
					{
						_xp = this.Math.floor(_xp * 1.5);
					}

					if (this.getFlags().get(::AfeiExpedition.Flags.CaptainAfei) == true && this.World.Flags.get(::AfeiExpedition.Flags.BicycleXp))
					{
						_xp = this.Math.floor(_xp * 1.2);
					}
				}

				return addXP(_xp, _show);
			};
		}
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
			this.m.Events.push(this.new("scripts/events/events/afei_steal_bro_event"));
			this.m.Events.push(this.new("scripts/events/events/afei_rope_train_event"));
			this.m.Events.push(this.new("scripts/events/events/afei_bottle_leave_bicycle_event"));
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

	// 无法选中：场上另有合法友军时，禁止敌人单体点名
	::mods_hookExactClass("skills/skill", function(o)
	{
		local onVerifyTarget = o.onVerifyTarget;
		o.onVerifyTarget = function(_originTile, _targetTile)
		{
			local ok = onVerifyTarget(_originTile, _targetTile);

			if (!ok || !::AfeiExpedition.isAfeiOrigin() || _targetTile == null || !this.isAttack())
			{
				return ok;
			}

			local target = _targetTile.getEntity();
			local user = this.getContainer().getActor();

			if (target == null || user == null || user.isAlliedWith(target))
			{
				return ok;
			}

			if (!target.getSkills().hasSkill("effects.afei_unselectable"))
			{
				return ok;
			}

			try
			{
				local allies = this.Tactical.Entities.getInstancesOfFaction(target.getFaction());
				local range = this.getMaxRange();

				foreach (a in allies)
				{
					if (a == null || a.getID() == target.getID() || !a.isAlive())
					{
						continue;
					}

					if (a.getSkills().hasSkill("effects.afei_unselectable"))
					{
						continue;
					}

					if (user.getTile().getDistanceTo(a.getTile()) <= range)
					{
						return false;
					}
				}
			}
			catch (error)
			{
			}

			return ok;
		};

		local onAfterUpdate = "onAfterUpdate" in o ? o.onAfterUpdate : null;
		o.onAfterUpdate <- function(_properties)
		{
			if (onAfterUpdate != null)
			{
				onAfterUpdate(_properties);
			}

			if (!::AfeiExpedition.isAfeiOrigin() || this.getContainer() == null)
			{
				return;
			}

			local actor = this.getContainer().getActor();

			if (actor == null || !this.isAttack() || this.isRanged())
			{
				return;
			}

			local lift = actor.getSkills().getSkillByID("actives.afei_together_lift");

			if (lift != null && ("hasFormation" in lift) && lift.hasFormation())
			{
				if (!("afei_base_fatigue" in this.m))
				{
					this.m.afei_base_fatigue <- this.m.FatigueCost;
				}
				else
				{
					this.m.afei_base_fatigue = this.Math.max(this.m.afei_base_fatigue, this.m.FatigueCost);
				}

				this.m.FatigueCost = this.Math.max(0, this.m.afei_base_fatigue - 2);
			}
		};
	});

	// 超市里：食物买入价 getBuyPrice（当日未用且报价开启）
	local afei_shop_buy_hook = function(o)
	{
		if (!("getBuyPrice" in o))
		{
			return;
		}

		local getBuyPrice = o.getBuyPrice;
		o.getBuyPrice = function()
		{
			local v = getBuyPrice();

			if (!::AfeiExpedition.isAfeiOrigin() || !::AfeiExpedition.hasNamed("C07"))
			{
				return v;
			}

			local isFood = false;

			try
			{
				isFood = this.isItemType(this.Const.Items.ItemType.Food);
			}
			catch (error)
			{
			}

			if (!isFood)
			{
				return v;
			}

			local day = this.World.getTime().Days;

			if (this.World.Flags.getAsInt("afei_market_day") == day || !this.World.Flags.get("afei_market_quote"))
			{
				return v;
			}

			local save = this.Math.min(30, this.Math.floor(v * 0.15));
			this.World.Flags.set("afei_market_pending", 1);
			return this.Math.max(1, this.Math.ceil(v - save));
		};
	};

	::mods_hookExactClass("items/item", afei_shop_buy_hook);

	if ("mods_hookDescendants" in getroottable())
	{
		::mods_hookDescendants("items/item", afei_shop_buy_hook);
	}

	// 成交后消耗超市次数：仅在食物报价被读取后的扣款
	::mods_hookExactClass("states/world/asset_manager", function(o)
	{
		local addMoney = o.addMoney;
		o.addMoney = function(_money)
		{
			if (::AfeiExpedition.isAfeiOrigin() && _money < 0 && this.World.Flags.get("afei_market_pending"))
			{
				local day = this.World.getTime().Days;
				this.World.Flags.set("afei_market_day", day);
				this.World.Flags.set("afei_market_quote", 0);
				this.World.Flags.set("afei_market_pending", 0);
			}

			return addMoney(_money);
		};

		if ("addArmorParts" in o)
		{
			local addArmorParts = o.addArmorParts;
			o.addArmorParts = function(_v)
			{
				if (::AfeiExpedition.isAfeiOrigin() && _v < 0)
				{
					local need = -_v;
					local rebate = ::AfeiExpedition.tryConsumeScrapCharge(need);

					if (rebate > 0)
					{
						_v = _v + rebate;
					}

					if (_v < 0)
					{
						::AfeiExpedition.onScrapToolsSpent(-_v);
					}
				}

				return addArmorParts(_v);
			};
		}
	});

	// 进城镇开启超市报价
	::mods_hookExactClass("states/world/world_state", function(o)
	{
		if ("showTownScreen" in o)
		{
			// 已在上方 hook 过 showTownScreen，再包一层
			local showTownScreen = o.showTownScreen;
			o.showTownScreen = function()
			{
				if (::AfeiExpedition.isAfeiOrigin() && ::AfeiExpedition.hasNamed("C07"))
				{
					local day = this.World.getTime().Days;

					if (this.World.Flags.getAsInt("afei_market_day") != day)
					{
						this.World.Flags.set("afei_market_quote", 1);
					}
				}

				return showTownScreen();
			};
		}
	});


	::mods_hookExactClass("states/world/asset_manager", function(o)
	{
		if ("getDailyMoneyCost" in o)
		{
			local getDailyMoneyCost = o.getDailyMoneyCost;
			o.getDailyMoneyCost = function()
			{
				local cost = getDailyMoneyCost();

				if (::AfeiExpedition.isAfeiOrigin() && this.World.Flags.get(::AfeiExpedition.Flags.CampEnabled))
				{
					local roster = this.World.getPlayerRoster().getAll();

					foreach (bro in roster)
					{
						if (bro.getFlags().get(::AfeiExpedition.Flags.Camped))
						{
							cost += 30;
							break;
						}
					}
				}

				return cost;
			};
		}
	});

});

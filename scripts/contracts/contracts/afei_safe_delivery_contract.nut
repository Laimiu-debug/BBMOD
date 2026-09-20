this.afei_safe_delivery_contract <- this.inherit("scripts/contracts/contract", {
	m = {
		Destination = null,
		Title = "安全送账"
	},
	function create()
	{
		this.m.DifficultyMult = 0.75;
		this.m.Flags = this.new("scripts/tools/tag_collection");
		this.m.TempFlags = this.new("scripts/tools/tag_collection");
		this.createStates();
		this.createScreens();
		this.m.Type = "contract.afei_safe_delivery";
		this.m.Name = "安全送账";
		this.m.TimeOut = this.Time.getVirtualTimeF() + this.World.getTime().SecondsPerDay * 10.0;
	}

	function getBanner()
	{
		return "ui/banners/factions/banner_03s";
	}

	function start()
	{
		this.m.IsNegotiated = true;
		try
		{
			this.m.Payment.Pool = 180;
			if ("Base" in this.m.Payment) this.m.Payment.Base = 180;
		}
		catch (errorPay) {}
		this.contract.start();
	}

	function createStates()
	{
		this.m.States.push({
			ID = "Offer",
			function start()
			{
				this.Contract.m.BulletpointsObjectives = [
					"将账册送到邻近友好城镇（低危；可拒）"
				];
				this.Contract.setScreen("Task");
			}
			function end()
			{
				this.World.Contracts.setActiveContract(this.Contract);
				this.World.Flags.set(::AfeiExpedition.Flags.SafeDeliveryActive, 1);
			}
		});
		this.m.States.push({
			ID = "Running",
			function start()
			{
				if (this.Contract.m.Destination != null && !this.Contract.m.Destination.isNull())
				{
					this.Contract.m.Destination.getSprite("selection").Visible = true;
					this.Contract.m.Destination.setOnEnterCallback(this.onDestinationAttacked.bindenv(this));
					return;
				}
				local tile = null;
				try
				{
					tile = this.Contract.getTileToSpawnLocation(this.World.State.getPlayer().getTile(), 2, 8, []);
				}
				catch (error)
				{
					tile = this.World.State.getPlayer().getTile();
				}
				local camp = null;
				if (tile != null)
				{
					camp = this.World.spawnLocation("scripts/entity/world/locations/afei_blue_ambush_location", tile.Coords);
				}
				if (camp != null)
				{
					try { camp.setName("送账途中低危遭遇"); } catch (errorName) {}
					camp.onSpawned();
					camp.setDiscovered(true);
					camp.setAttackable(true);
					camp.getSprite("selection").Visible = true;
					camp.setOnEnterCallback(this.onDestinationAttacked.bindenv(this));
					this.World.uncoverFogOfWar(camp.getTile().Pos, 400.0);
					this.Contract.m.Destination = this.WeakTableRef(camp);
					camp.getFlags().set("afei_safe_delivery_site", 1);
				}
			}
			function update()
			{
			}
			function onDestinationAttacked(_dest, _already)
			{
				this.World.Flags.set("afei_active_contract_combat", "contract.afei_safe_delivery");
				this.World.Contracts.showCombatDialog();
			}
		});
		this.m.States.push({
			ID = "Return",
			function start()
			{
				this.Contract.setScreen("Success");
			}
		});
	}

	function createScreens()
	{
		this.m.Screens.push({
			ID = "Task",
			Title = "安全送账",
			Text = "{烟港账房托你们把一份账册送到邻近友好方向。报酬 [color=#8f2525]180[/color] 克朗，风险偏低。也可以拒绝，改走其它起步路。}",
			Image = "",
			List = [],
			Options = [
				{
					Text = "接下这份低危送账。",
					function getResult()
					{
						this.Contract.setState("Running");
						return 0;
					}
				},
				{
					Text = "拒绝。",
					function getResult()
					{
						this.World.Flags.set(::AfeiExpedition.Flags.SafeDeliveryActive, 0);
						this.World.Flags.set(::AfeiExpedition.Flags.M01Done, 1);
						this.Contract.setState("Offer");
						this.World.Contracts.removeContract(this.Contract);
						return 0;
					}
				}
			],
			function start() {}
		});
		this.m.Screens.push({
			ID = "Success",
			Title = "送达",
			Text = "{账册交割完毕。第一次招募线索可以指向瓶队。}",
			Image = "",
			List = [],
			Options = [
				{
					Text = "好。",
					function getResult()
					{
						::AfeiExpedition.completeSafeDeliveryFromContract();
						this.World.Contracts.finishActiveContract();
						return 0;
					}
				}
			],
			function start() {}
		});
	}

	function onClear()
	{
		if (this.m.IsActive)
		{
			if (this.m.Destination != null && !this.m.Destination.isNull())
			{
				this.m.Destination.setOnEnterCallback(null);
				this.m.Destination.getSprite("selection").Visible = false;
			}
		}
	}
});

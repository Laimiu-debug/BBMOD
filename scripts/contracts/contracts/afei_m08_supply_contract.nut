this.afei_m08_supply_contract <- this.inherit("scripts/contracts/contract", {
	m = {
		Destination = null,
		Title = "再集合·送补给"
	},
	function create()
	{
		this.m.DifficultyMult = 1.0;
		this.m.Flags = this.new("scripts/tools/tag_collection");
		this.m.TempFlags = this.new("scripts/tools/tag_collection");
		this.createStates();
		this.createScreens();
		this.m.Type = "contract.afei_m08_supply";
		this.m.Name = "再集合·送补给";
		this.m.TimeOut = this.Time.getVirtualTimeF() + this.World.getTime().SecondsPerDay * 14.0;
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
			this.m.Payment.Pool = 150;

			if ("Base" in this.m.Payment)
			{
				this.m.Payment.Base = 150;
			}
		}
		catch (errorPay)
		{
		}

		this.contract.start();
	}

	function createStates()
	{
		this.m.States.push({
			ID = "Offer",
			function start()
			{
				this.Contract.m.BulletpointsObjectives = [
					"将补给送到旧营地外围，击退拦路者"
				];
				this.Contract.setScreen("Task");
			}
			function end()
			{
				this.World.Contracts.setActiveContract(this.Contract);
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
					tile = this.Contract.getTileToSpawnLocation(this.World.State.getPlayer().getTile(), 3, 10, []);
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
					try { camp.setName("补给拦路点"); } catch (errorName) { camp.m.Name = "补给拦路点"; }
					camp.onSpawned();
					camp.setDiscovered(true);
					camp.setAttackable(true);
					camp.getSprite("selection").Visible = true;
					camp.setOnEnterCallback(this.onDestinationAttacked.bindenv(this));
					this.World.uncoverFogOfWar(camp.getTile().Pos, 400.0);
					this.Contract.m.Destination = this.WeakTableRef(camp);
				}
			}
			function update()
			{
				if (this.Contract.m.Destination == null || this.Contract.m.Destination.isNull())
				{
					this.Contract.setScreen("Success");
					this.World.Contracts.finishActiveContract();
				}
			}
			function onDestinationAttacked(_dest, _isPlayerAttacking = true)
			{
				this.Contract.setScreen("Fight");
				this.World.Contracts.showActiveContract();
			}
		});
	}

	function createScreens()
	{
		this.m.Screens.push({
			ID = "Task",
			Title = this.m.Title,
			Text = "%terrainImage%{旧营地需要一批补给。送到外围并打通拦路即可。}",
			Image = "",
			List = [],
			Options = [
				{
					Text = "接下送补给。",
					function getResult()
					{
						this.Contract.setState("Running");
						return 0;
					}
				},
				{
					Text = "暂缓。",
					function getResult()
					{
						this.Contract.removeThisContract();
						return 0;
					}
				}
			],
			function start()
			{
			}
		});
		this.m.Screens.push({
			ID = "Fight",
			Title = this.m.Title,
			Text = "%terrainImage%{有人拦在补给路上。}",
			Image = "",
			List = [],
			Options = [
				{
					Text = "开战！",
					function getResult()
					{
						this.World.Flags.set("afei_active_contract_combat", "contract.afei_m08_supply");
						this.World.State.getLastLocation().setFaction(this.World.FactionManager.getFactionOfType(this.Const.FactionType.Bandits).getID());
						this.World.Contracts.showCombatDialog();
						return 0;
					}
				},
				{
					Text = "先撤。",
					function getResult()
					{
						return 0;
					}
				}
			],
			function start()
			{
			}
		});
		this.m.Screens.push({
			ID = "Success",
			Title = this.m.Title,
			Text = "%terrainImage%{补给送到。}",
			Image = "",
			List = [],
			Options = [
				{
					Text = "好。",
					function getResult()
					{
						return 0;
					}
				}
			],
			function start()
			{
			}
		});
	}

	function onClear()
	{
		if (this.m.IsActive && this.m.Destination != null && !this.m.Destination.isNull())
		{
			this.m.Destination.getSprite("selection").Visible = false;
			this.m.Destination.die();
		}
	}

	function removeThisContract()
	{
		this.World.Contracts.removeContract(this);
	}

	function onSerialize(_out)
	{
		if (this.m.Destination != null && !this.m.Destination.isNull())
		{
			_out.writeU32(this.m.Destination.getID());
		}
		else
		{
			_out.writeU32(0);
		}

		this.contract.onSerialize(_out);
	}

	function onDeserialize(_in)
	{
		local destination = _in.readU32();

		if (destination != 0)
		{
			this.m.Destination = this.WeakTableRef(this.World.getEntityByID(destination));
		}

		this.contract.onDeserialize(_in);
	}
});

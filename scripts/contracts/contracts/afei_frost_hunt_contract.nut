this.afei_frost_hunt_contract <- this.inherit("scripts/contracts/contract", {
	m = {
		Destination = null,
		Title = "北境白影"
	},
	function create()
	{
		this.m.DifficultyMult = 1.15;
		this.m.Flags = this.new("scripts/tools/tag_collection");
		this.m.TempFlags = this.new("scripts/tools/tag_collection");
		this.createStates();
		this.createScreens();
		this.m.Type = "contract.afei_frost_hunt";
		this.m.Name = "北境白影";
		this.m.TimeOut = this.Time.getVirtualTimeF() + this.World.getTime().SecondsPerDay * 21.0;
	}

	function getBanner()
	{
		return "ui/banners/factions/banner_07s";
	}

	function start()
	{
		this.m.IsNegotiated = true;

		try
		{
			this.m.Payment.Pool = 800;

			if ("Base" in this.m.Payment)
			{
				this.m.Payment.Base = 800;
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
					"击败北境白影（冰霜巨兽遭遇）；可侦察后离开"
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
					local homeTile = this.World.State.getPlayer().getTile();
					tile = this.Contract.getTileToSpawnLocation(homeTile, 6, 18, []);
				}
				catch (error)
				{
					tile = this.World.State.getPlayer().getTile();
				}

				local camp = null;

				if (tile != null)
				{
					camp = this.World.spawnLocation("scripts/entity/world/locations/afei_frost_shadow_location", tile.Coords);
				}

				if (camp != null)
				{
					camp.onSpawned();
					camp.setDiscovered(true);
					camp.setAttackable(true);
					camp.getSprite("selection").Visible = true;
					camp.setOnEnterCallback(this.onDestinationAttacked.bindenv(this));
					this.World.uncoverFogOfWar(camp.getTile().Pos, 500.0);
					this.Contract.m.Destination = this.WeakTableRef(camp);
				}
			}
			function update()
			{
				if (this.Contract.m.Destination == null || this.Contract.m.Destination.isNull())
				{
					this.World.Flags.set("afei_m07_combat", 1);
					this.Contract.setScreen("Success");
					this.World.Contracts.finishActiveContract();
				}
			}
			function onDestinationAttacked(_dest, _isPlayerAttacking = true)
			{
				this.Contract.setScreen("Hunt");
				this.World.Contracts.showActiveContract();
			}
		});
	}

	function createScreens()
	{
		this.m.Screens.push({
			ID = "Task",
			Title = this.m.Title,
			Text = "%terrainImage%{猎人指着北方：一只冰霜巨兽，至多两只普通巨兽护卫。可侦察后离开；击败后另有悬赏。}",
			Image = "",
			List = [],
			Options = [
				{
					Text = "接猎人传闻。",
					function getResult()
					{
						this.Contract.setState("Running");
						return 0;
					}
				},
				{
					Text = "先不接。",
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
			ID = "Hunt",
			Title = this.m.Title,
			Text = "%terrainImage%{白影就在前方。开战将以野兽编制结算；失败或撤退后只要巢穴仍在即可重试。}",
			Image = "",
			List = [],
			Options = [
				{
					Text = "开战！",
					function getResult()
					{
						this.World.Flags.set("afei_active_contract_combat", "contract.afei_frost_hunt");
						this.World.Flags.set("afei_m07_combat", 1);
						this.World.State.getLastLocation().setFaction(this.World.FactionManager.getFactionOfType(this.Const.FactionType.Beasts).getID());
						this.World.Contracts.showCombatDialog();
						return 0;
					}
				},
				{
					Text = "侦察后离开。",
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
			Text = "%terrainImage%{白影倒下。战利品按普通规则结算，悬赏与纪念章记入名册。}",
			Image = "",
			List = [],
			Options = [
				{
					Text = "收工。",
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
		if (this.m.IsActive)
		{
			if (this.m.Destination != null && !this.m.Destination.isNull())
			{
				this.m.Destination.getSprite("selection").Visible = false;
				this.m.Destination.die();
			}
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

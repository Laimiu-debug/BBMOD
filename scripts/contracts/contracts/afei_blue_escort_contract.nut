this.afei_blue_escort_contract <- this.inherit("scripts/contracts/contract", {
	m = {
		Destination = null,
		Title = "蓝旗联合护送"
	},
	function create()
	{
		this.m.DifficultyMult = 1.0;
		this.m.Flags = this.new("scripts/tools/tag_collection");
		this.m.TempFlags = this.new("scripts/tools/tag_collection");
		this.createStates();
		this.createScreens();
		this.m.Type = "contract.afei_blue_escort";
		this.m.Name = "蓝旗联合护送";
		this.m.TimeOut = this.Time.getVirtualTimeF() + this.World.getTime().SecondsPerDay * 14.0;
	}

	function getBanner()
	{
		return "ui/banners/factions/banner_02s";
	}

	function start()
	{
		this.m.IsNegotiated = true;

		try
		{
			this.m.Payment.Pool = 200;

			if ("Base" in this.m.Payment)
			{
				this.m.Payment.Base = 200;
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
					"与蓝旗匿名护卫完成联合护送，击退途中伏击"
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
					local homeTile = this.Contract.m.Home != null ? this.Contract.m.Home.getTile() : this.World.State.getPlayer().getTile();
					tile = this.Contract.getTileToSpawnLocation(homeTile, 4, 12, []);
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
				this.Contract.setScreen("Ambush");
				this.World.Contracts.showActiveContract();
			}
		});
	}

	function createScreens()
	{
		this.m.Screens.push({
			ID = "Task",
			Title = this.m.Title,
			Text = "%terrainImage%{蓝旗提出联合护送。匿名护卫会与你们同行——途中的伏击需要你们一起打下来。}",
			Image = "",
			List = [],
			Options = [
				{
					Text = "接受护送。",
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
			ID = "Ambush",
			Title = this.m.Title,
			Text = "%terrainImage%{伏击！蓝旗护卫已经就位。可侦察后离开，目标仍在即可再战。}",
			Image = "",
			List = [],
			Options = [
				{
					Text = "开战！",
					function getResult()
					{
						this.World.Flags.set("afei_active_contract_combat", "contract.afei_blue_escort");
						this.World.State.getLastLocation().setFaction(this.World.FactionManager.getFactionOfType(this.Const.FactionType.Bandits).getID());
						this.World.Contracts.showCombatDialog();
						return 0;
					}
				},
				{
					Text = "先撤，改日再来。",
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
			Text = "%terrainImage%{护送抵达。蓝旗记下了黑旗的名字——川神、小虎、大鹅的个人邀请将开放。}",
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
				this.List.push({
					id = 10,
					icon = "ui/icons/asset_money.png",
					text = "护送报酬入账"
				});
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

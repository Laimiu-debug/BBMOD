this.afei_expedition_scenario <- this.inherit("scripts/scenarios/world/starting_scenario", {
	m = {},
	function create()
	{
		this.m.ID = "scenario.afei_expedition";
		this.m.Name = "大飞午远征团";
		this.m.Description = "[p=c][img]gfx/ui/events/event_65.png[/img][/p][p]烟港酒馆里，三名队长把一面还没写满名字的黑旗挂上车：阿飞签下团约，抹茶算清口粮，王大谋扛起最重的箱子。\n\n[color=#bcad8c]三队长开局：[/color] 阿飞、抹茶、王大谋共同起家；阿飞为固定团长，不可主动解雇。\n[color=#bcad8c]团队号令：[/color] 每场战斗全队共享 2 次号令，每轮最多施放 1 次。\n[color=#bcad8c]招募节奏：[/color] 完成首份有报酬契约后，可遇瓶队小酒瓶（R01）。[/p]";
		this.m.Difficulty = 2;
		this.m.Order = 86;
		this.m.IsFixedLook = true;
	}

	function isValid()
	{
		return true;
	}

	function onSpawnAssets()
	{
		local roster = this.World.getPlayerRoster();

		local function makeCaptain(_background, _name, _title, _place, _attrs, _talents, _wage, _namedId, _isAfei)
		{
			local bro = roster.create("scripts/entity/tactical/player");
			bro.setStartValuesEx([
				_background
			]);
			bro.setName(_name);
			bro.setTitle(_title);
			bro.setPlaceInFormation(_place);
			bro.getBackground().m.RawDescription = bro.getBackground().getDescription();
			bro.getBackground().buildDescription(true);

			local b = bro.getBaseProperties();
			b.Hitpoints = _attrs[0];
			b.Stamina = _attrs[1];
			b.Bravery = _attrs[2];
			b.Initiative = _attrs[3];
			b.MeleeSkill = _attrs[4];
			b.RangedSkill = _attrs[5];
			b.MeleeDefense = _attrs[6];
			b.RangedDefense = _attrs[7];
			bro.getSkills().update();

			local talents = bro.getTalents();
			talents.resize(this.Const.Attributes.COUNT, 0);

			for (local i = 0; i < this.Const.Attributes.COUNT; i++)
			{
				talents[i] = 0;
			}

			foreach (t in _talents)
			{
				talents[t[0]] = t[1];
			}

			bro.m.LevelUps = 0;
			bro.m.Level = 1;
			bro.m.XP = this.Const.LevelXP[0];
			bro.m.DailyWage = _wage;
			bro.m.HireTime = this.Time.getVirtualTimeF();
			bro.getFlags().set(::AfeiExpedition.Flags.NamedId, _namedId);

			if (_isAfei)
			{
				bro.getFlags().set(::AfeiExpedition.Flags.CaptainAfei, true);
				bro.getFlags().set("IsPlayerCharacter", true);
				bro.getSkills().add(this.new("scripts/skills/traits/player_character_trait"));
			}

			bro.getSkills().add(this.new("scripts/skills/special/afei_named_brother"));
			return bro;
		}

		// C01 阿飞 · 后排团长（设定八维/星级/日薪）
		local afei = makeCaptain("afei_captain_background", "阿飞", "团长", 12, [
			36,
			70,
			18,
			85,
			38,
			22,
			-5,
			-3
		], [
			[
				this.Const.Attributes.Hitpoints,
				1
			],
			[
				this.Const.Attributes.Fatigue,
				2
			],
			[
				this.Const.Attributes.Bravery,
				3
			]
		], 6, "C01", true);
		afei.getSkills().add(this.new("scripts/skills/actives/afei_wawa_call"));
		afei.getSkills().add(this.new("scripts/skills/actives/afei_toad_escape"));

		// C02 抹茶 · 远程谋士 / 副队长
		local mocha = makeCaptain("afei_mocha_background", "抹茶", "副队长", 13, [
			46,
			85,
			48,
			110,
			45,
			48,
			2,
			5
		], [
			[
				this.Const.Attributes.Bravery,
				2
			],
			[
				this.Const.Attributes.Initiative,
				1
			],
			[
				this.Const.Attributes.RangedSkill,
				2
			]
		], 12, "C02", false);
		mocha.getSkills().add(this.new("scripts/skills/actives/afei_shadow_captain"));
		mocha.getSkills().add(this.new("scripts/skills/actives/afei_abacus_mark"));

		// C03 王大谋 · 前排 / 副队长
		local damou = makeCaptain("afei_damou_background", "王大谋", "副队长", 3, [
			66,
			112,
			44,
			88,
			57,
			30,
			4,
			0
		], [
			[
				this.Const.Attributes.Hitpoints,
				1
			],
			[
				this.Const.Attributes.Fatigue,
				2
			],
			[
				this.Const.Attributes.MeleeSkill,
				2
			]
		], 16, "C03", false);
		damou.getSkills().add(this.new("scripts/skills/actives/afei_borrow_strike"));

		// 起步资源（设定表）
		this.World.Assets.m.BusinessReputation = 0;
		this.World.Assets.getStash().resize(this.World.Assets.getStash().getCapacity() + 9);
		this.World.Assets.m.Money = 1800;
		this.World.Assets.m.ArmorParts = 30;
		this.World.Assets.m.Medicine = 15;
		this.World.Assets.m.Ammo = 25;
		// 食物以补给物品近似 55：多份谷物（待实机校准 Food 字段）
		this.World.Flags.set("afei_cohesion", 25);
		this.World.Flags.set(::AfeiExpedition.Flags.PaidContracts, 0);
		this.World.Flags.set(::AfeiExpedition.Flags.SafeDeliveryActive, 0);
		this.World.Flags.set(::AfeiExpedition.Flags.SafeDeliveryDone, 0);

		for (local i = 0; i < 6; i++)
		{
			this.World.Assets.getStash().add(this.new("scripts/items/supplies/ground_grains_item"));
		}
	}

	function onSpawnPlayer()
	{
		local randomVillage;

		for (local i = 0; i != this.World.EntityManager.getSettlements().len(); i++)
		{
			randomVillage = this.World.EntityManager.getSettlements()[i];

			if (!randomVillage.isMilitary() && !randomVillage.isIsolatedFromRoads() && randomVillage.getSize() >= 2)
			{
				break;
			}
		}

		local randomVillageTile = randomVillage.getTile();
		local navSettings = this.World.getNavigator().createSettings();
		navSettings.ActionPointCosts = this.Const.World.TerrainTypeNavCost_Flat;
		local closest;
		local closestDist = 9000;

		for (local x = this.Math.max(2, randomVillageTile.SquareCoords.X - 4); x <= this.Math.min(this.Const.World.Settings.SizeX - 2, randomVillageTile.SquareCoords.X + 4); x++)
		{
			for (local y = this.Math.max(2, randomVillageTile.SquareCoords.Y - 4); y <= this.Math.min(this.Const.World.Settings.SizeY - 2, randomVillageTile.SquareCoords.Y + 4); y++)
			{
				if (!this.World.isValidTileSquare(x, y))
				{
				}
				else
				{
					local tile = this.World.getTileSquare(x, y);

					if (tile.Type == this.Const.World.TerrainType.Ocean || tile.Type == this.Const.World.TerrainType.Shore || tile.IsOccupied)
					{
					}
					else if (tile.getDistanceTo(randomVillageTile) <= 1)
					{
					}
					else
					{
						local path = this.World.getNavigator().findPath(tile, randomVillageTile, navSettings, 0);

						if (!path.isEmpty() && path.getSize() < closestDist)
						{
							closestDist = path.getSize();
							closest = tile;
						}
					}
				}
			}
		}

		if (closest != null)
		{
			randomVillageTile = closest;
		}

		this.World.State.m.Player = this.World.spawnEntity("scripts/entity/world/player_party", randomVillageTile.Coords.X, randomVillageTile.Coords.Y);
		this.World.Assets.updateLook(1);
		this.World.getCamera().setPos(this.World.State.m.Player.getPos());

		try
		{
			this.World.Flags.set(::AfeiExpedition.Flags.SafeDeliveryHome, randomVillage.getID());
		}
		catch (error)
		{
			this.World.Flags.set(::AfeiExpedition.Flags.SafeDeliveryHome, "");
		}

		this.Time.scheduleEvent(this.TimeUnit.Real, 1000, function ( _tag )
		{
			this.Music.setTrackList([
				this.Const.Music.NewCampaignTracks[0]
			], this.Const.Music.CrossFadeTime);
			this.World.Events.fire("event.afei_expedition_scenario_intro");
		}, null);
	}

	function onInit()
	{
		this.World.Assets.m.BrothersMax = 20;
	}

	function onCombatFinished()
	{
		local roster = this.World.getPlayerRoster().getAll();

		foreach (bro in roster)
		{
			if (bro.getFlags().get(::AfeiExpedition.Flags.CaptainAfei))
			{
				return true;
			}
		}

		return false;
	}
});

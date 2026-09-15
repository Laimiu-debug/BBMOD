::include("seed_generator/define_lair");
::include("seed_generator/define_score");

local gt = this.getroottable();

gt.SeedGenerator.printBroInfo <- function(roster, role_array, team_score_avg_, bros_len, bros, bros_entries)
{
	local team_info = "";
	for(local i = 0; i < RoleNum; i++)
	{
		team_info = team_info + " " + RoleName[i] + ":" + role_array[i];
	}
	this.logInfo("TeamInfo: " + team_score_avg_ + team_info);

	for(local i = 0; i < bros_len; i++)
	{
		local traits = "";
		local talents = null;
		if(roster == null)
		{
			talents = bros[i]["Talents"];
			foreach(s in bros[i]["Traits"] )
			{
				traits += (" " + s);
			}
		}
		else
		{
			talents = bros[i].getTalents();
			foreach(s in bros[i].m.Skills.m.Skills )
			{
				if (s.getType() == this.Const.SkillType.Trait)
				{
					traits += (" " + s.getID());
				}
			}
		}

		this.logInfo("CharInfo: " + i + " "
		+ RoleName[bros_entries[i][BroScoreEntry.BestRoleScoreType]] + ":" + bros_entries[i][BroScoreEntry.BestRoleScore] + " "
		+ AttrName[Attr.Hitpoints] + ":" + bros_entries[i][BroScoreEntry.InitAttr][Attr.Hitpoints] + "(" + bros_entries[i][BroScoreEntry.MaxAttr][Attr.Hitpoints]  + ")" + talents[this.Const.Attributes.Hitpoints] + "   "
		+ AttrName[Attr.Bravery] + ":" + bros_entries[i][BroScoreEntry.InitAttr][Attr.Bravery] + "(" + bros_entries[i][BroScoreEntry.MaxAttr][Attr.Bravery]  + ")" + talents[this.Const.Attributes.Bravery] + "   "
		+ AttrName[Attr.Stamina] + ":" + bros_entries[i][BroScoreEntry.InitAttr][Attr.Stamina] + "(" + bros_entries[i][BroScoreEntry.MaxAttr][Attr.Stamina]  + ")" + talents[this.Const.Attributes.Fatigue] + "   "
		+ AttrName[Attr.MeleeSkill] + ":" + bros_entries[i][BroScoreEntry.InitAttr][Attr.MeleeSkill] + "(" + bros_entries[i][BroScoreEntry.MaxAttr][Attr.MeleeSkill]  + ")" + talents[this.Const.Attributes.MeleeSkill] + "   "
		+ AttrName[Attr.RangedSkill] + ":" + bros_entries[i][BroScoreEntry.InitAttr][Attr.RangedSkill] + "(" + bros_entries[i][BroScoreEntry.MaxAttr][Attr.RangedSkill]  + ")" + talents[this.Const.Attributes.RangedSkill] + "   "
		+ AttrName[Attr.MeleeDefense] + ":" + bros_entries[i][BroScoreEntry.InitAttr][Attr.MeleeDefense] + "(" + bros_entries[i][BroScoreEntry.MaxAttr][Attr.MeleeDefense]  + ")" + talents[this.Const.Attributes.MeleeDefense] + "   "
		+ AttrName[Attr.RangedDefense] + ":" + bros_entries[i][BroScoreEntry.InitAttr][Attr.RangedDefense] + "(" + bros_entries[i][BroScoreEntry.MaxAttr][Attr.RangedDefense]  + ")" + talents[this.Const.Attributes.RangedDefense] + "   "
		+ AttrName[Attr.Initiative] + ":" + bros_entries[i][BroScoreEntry.InitAttr][Attr.Initiative] + "(" + bros_entries[i][BroScoreEntry.MaxAttr][Attr.Initiative]  + ")" + talents[this.Const.Attributes.Initiative]);

		this.logInfo("Trait: " + traits);
	}
}

gt.SeedGenerator.printLairInfo <- function()
{
	foreach( lair_info in lair_info_list )
	{
		if(CommonConfig.PrintLairNamedDetail)
			this.logInfo("LairInfo: " + lair_info[LairInfoEntry.LairName] + "(" + LairTypeName[lair_info[LairInfoEntry.LairType]] + ")" + " "
			 + lair_info[LairInfoEntry.Strength] + " " + lair_info[LairInfoEntry.NearestSettlementName] + " "
			 + lair_info[LairInfoEntry.NearestSettlementDistance] + "-" + lair_info[LairInfoEntry.NearestSettlementDirection]);
		foreach(item in lair_info[LairInfoEntry.NamedItemsList])
			printItemInfo(item);
	}

	local NamedInfo = "";
	for(local i = 0; i < NamedTypeNum; i++)
	{
		NamedInfo = NamedInfo + NamedTypeName[i] + ":" + named_type_num[i] + " ";
	}
	// local LairInfo = "" + lair_num + " ";
	// for(local i = 0; i < LairTypeNum; i++)
	// {
	// 	LairInfo = LairInfo + LairTypeName[i] + ":" + lair_type_num[i] + " ";
	// }
	// this.logInfo("LairInfoSum: " + LairInfo)

	local LairTypeNamedInfo = "";
	local DoubleNameSum = 0;
	for(local i = 0; i < LairTypeNum; i++)
	{
		DoubleNameSum += lair_type_double_named_num[i];
		LairTypeNamedInfo = LairTypeNamedInfo + LairTypeName[i] + ":" + lair_type_named_num[i] + "(" + lair_type_double_named_num[i] + ")" + " ";
	}
	this.logInfo("NamedInfo: " + NamedInfo + "Sum:" + named_total_num + "(" + DoubleNameSum + ")" + " " + LairTypeNamedInfo + " "
		+ "Strength:" + "[" + small_named_lair_num + ", " + medium_named_lair_num + ", " + large_named_lair_num + "]" + " "
		+ "Distance:" + "[" + distance_close_named_lair_num + ", " + distance_medium_named_lair_num + ", " + distance_far_named_lair_num + "]");
}

gt.SeedGenerator.printSettlementInfo <- function()
{
	local port_location_info = "[";
	for(local i = 0; i < PortLocationNum; i++)
	{
		port_location_info += port_location[i]
		if(i != PortLocationNum - 1)
			port_location_info += ", ";
	}
	port_location_info += "]";

	local settlements_type_info = "[";
	for(local i = 0; i < SettlementTypeNum; i++)
	{
		settlements_type_info += SettlementTypeName[i] + ":" + settlements_type_num[i]
		if(i != SettlementTypeNum - 1)
		settlements_type_info += " ";
	}
	settlements_type_info += "]";

	this.logInfo("SettlementInfo: " + "Settlements:" + settlements_num + "(" + settlement_port_avg_dis + "|" + settlement_avg_dis + ")"
			+ "[" + large_settlement_num + ", " + medium_settlement_num + ", " + small_settlement_num + "]" + "   "
			+ "Port:" + port_num + port_location_info + "   "
			+ "CityPort:" + city_port_num + "(" + arena_port + ") " + "   "
			+ "Products:" + products_num + "("  + products_settlements_num + "|" + products_total_value + "|" + products_city_total_value  + "|" + products_port_total_value + ")" + "   "
			+ "Connected:" + connected_info[ConnectedInfoEntry.SettlementsNum]
			+ "(" + connected_info[ConnectedInfoEntry.AvgRoadSize] + "|" + connected_info[ConnectedInfoEntry.PortNum]
			+ "|" + connected_info[ConnectedInfoEntry.CityNum] + "|" + connected_info[ConnectedInfoEntry.IsolatedCityNum] + ")" + "   "
			+ "ConnectedCity:" + "[" + connected_info[ConnectedInfoEntry.LargeSettlementsNum] + "(" + connected_info[ConnectedInfoEntry.LargeFortNum] + ")" + ", "
			+ connected_info[ConnectedInfoEntry.MediumSettlementsNum] + "(" + connected_info[ConnectedInfoEntry.MediumFortNum] + ")" + ", "
			+ connected_info[ConnectedInfoEntry.SmallSettlementsNum] + "(" + connected_info[ConnectedInfoEntry.SmallFortNum] + ")" + "]" + "   "
			+ "ConnectedProducts:" + "("  + connected_info[ConnectedInfoEntry.ProductSettlementsNum] + "|" + connected_info[ConnectedInfoEntry.ProductValue] + ")" + "   "
			+ settlements_type_info);

	this.logInfo("BuildInfo: " + "Build:" + build_num + "   "
			+ "Armorsmith:" + armorsmith_num + "   "
			+ "Weaponsmith:" + weaponsmith_num + "   "
			+ "Fletcher:" + fletcher_num + "   "
			// + "Alchemist:" + alchemist_num + "   "
			+ "Barber:" + barber_num + "   "
			+ "Kennel:" + kennel_num + "   "
			+ "Tavern:" + tavern_num + "   "
			+ "Taxidermist:" + taxidermist_num + "   "
			+ "Temple:" + temple_num + "   "
			+ "Traininghall:" + training_hall_num)

	this.logInfo("AttachedInfo: " + "Attached:" + attached_num + "   "
			// 军事建筑
			+ "Barracks:" + attached_id_num_dict["attached_location.fortified_outpost"] + "   "
			// + "GuardedCheckpoint:" + attached_id_num_dict["attached_location.guarded_checkpoint"] + "   "
			+ "MilitiaTrainingCamp:" + attached_id_num_dict["attached_location.militia_trainingcamp"] + "   "
			+ "StoneWatchTower:" + attached_id_num_dict["attached_location.stone_watchtower"] + "   "
			+ "WoodenWatchTower:" + attached_id_num_dict["attached_location.wooden_watchtower"] + "   "
			// 佣兵 贵族 小偷
			+ "BlastFurnace:" + attached_id_num_dict["attached_location.blast_furnace"] + "   "
			+ "GemMine:" + attached_id_num_dict["attached_location.gem_mine"] + "   "
			// + "GoldMine:" + attached_id_num_dict["attached_location.gold_mine"] + "   "
			+ "SaltMine:" + attached_id_num_dict["attached_location.salt_mine"] + "   "
			// 拳手
			+ "Brewery:" + attached_id_num_dict["attached_location.brewery"] + "   "
			+ "Winery:" + attached_id_num_dict["attached_location.winery"] + "   "
			// 远程
			+ "ArrowMaker:" + attached_id_num_dict["attached_location.fletchers_hut"] + "   "
			+ "HunterCabin:" + attached_id_num_dict["attached_location.hunters_cabin"] + "   "
			// 民兵 野人 异教徒 伐木工 民兵等
			+ "leatherTanner:" + attached_id_num_dict["attached_location.leather_tanner"] + "   "
			+ "LumberCamp:" + attached_id_num_dict["attached_location.lumber_camp"] + "   "
			+ "MushroomGrove:" + attached_id_num_dict["attached_location.mushroom_grove"] + "   "
			+ "IronVein:" + attached_id_num_dict["attached_location.surface_iron_vein"] + "   ")
}

gt.SeedGenerator.printItemInfo <- function(item)
{
	local random_info = "(";
	local rate1 = this.Math.round(100.0 * (NamedIndexDict[item.m.NamedInitIndex][1] * 1.0 - NamedIndexDict[item.m.NamedInitIndex][2]) / (NamedIndexDict[item.m.NamedInitIndex][3] - NamedIndexDict[item.m.NamedInitIndex][2]));
	local rate2 = this.Math.round(100.0 * (NamedIndexDict[item.m.NamedInitIndex][5] * 1.0 - NamedIndexDict[item.m.NamedInitIndex][6]) / (NamedIndexDict[item.m.NamedInitIndex][7] - NamedIndexDict[item.m.NamedInitIndex][6]));
	random_info += NamedAttrName[NamedIndexDict[item.m.NamedInitIndex][0]] + ":" + rate1 + "%|";
	random_info += NamedAttrName[NamedIndexDict[item.m.NamedInitIndex][4]] + ":" + rate2;
	random_info += "%)";
	if(item.isItemType(this.Const.Items.ItemType.Helmet)) // 头盔
	{
		if(CommonConfig.PrintLairNamedDetail)
			this.logInfo("    ItemInfo(Helmet): " + item.m.ID + random_info + "    Stamina:" + item.getStaminaModifier() + " Armor:" + item.m.ConditionMax);
		named_type_num[NamedType.Helmet]++;
	}
	else if(item.isItemType(this.Const.Items.ItemType.Armor)) // 护甲
	{
		if(CommonConfig.PrintLairNamedDetail)
			this.logInfo("    ItemInfo(Armor): " + item.m.ID + random_info + "    Stamina:" + item.getStaminaModifier() + " Armor:" + item.m.ConditionMax);
		named_type_num[NamedType.Armor]++;
	}
	else if(item.isItemType(this.Const.Items.ItemType.Shield)) // 护盾
	{
		if(CommonConfig.PrintLairNamedDetail)
			this.logInfo("    ItemInfo(Shield): " + item.m.ID + random_info + "    Stamina:" + item.getStaminaModifier() + " MeleeDefense:" + item.getMeleeDefense()
				+ " RangedDefense:" + item.getRangedDefense()  + " FatigueOnSkillUse:" + item.m.FatigueOnSkillUse + " Condition:" + item.m.ConditionMax);
		named_type_num[NamedType.Shield]++;
	}
	else if(item.isItemType(this.Const.Items.ItemType.MeleeWeapon) && item.isItemType(this.Const.Items.ItemType.TwoHanded)) // 双手近战
	{
		if(CommonConfig.PrintLairNamedDetail)
			this.logInfo("    ItemInfo(TwoHanded): " + item.m.ID + random_info + "    Stamina:" + item.getStaminaModifier() + " MinDamage:" + item.getDamageMin()
				+ " MaxDamage:" + item.getDamageMax()  + " ArmorDamage:" + item.getArmorDamageMult() + " DirectDamage:" + (item.m.DirectDamageMult + item.m.DirectDamageAdd)
				+ " ChanceToHitHead:" + item.m.ChanceToHitHead + " FatigueOnSkillUse:" + item.m.FatigueOnSkillUse + " Condition:" + item.m.ConditionMax);
		named_type_num[NamedType.TwoHanded]++;
	}
	else if(item.isItemType(this.Const.Items.ItemType.MeleeWeapon) && item.isItemType(this.Const.Items.ItemType.OneHanded)) // 单手近战
	{
		if(CommonConfig.PrintLairNamedDetail)
			this.logInfo("    ItemInfo(OneHanded): " + item.m.ID + random_info + "    Stamina:" + item.getStaminaModifier() + " MinDamage:" + item.getDamageMin()
				+ " MaxDamage:" + item.getDamageMax()  + " ArmorDamage:" + item.getArmorDamageMult() + " DirectDamage:" + (item.m.DirectDamageMult + item.m.DirectDamageAdd)
				+ " ChanceToHitHead:" + item.m.ChanceToHitHead + " FatigueOnSkillUse:" + item.m.FatigueOnSkillUse + " Condition:" + item.m.ConditionMax);
		named_type_num[NamedType.OneHanded]++;
	}
	else if(item.isItemType(this.Const.Items.ItemType.RangedWeapon)) // 远程武器
	{
		if(CommonConfig.PrintLairNamedDetail)
			this.logInfo("    ItemInfo(RangedWeapon): " + item.m.ID + random_info + "    Stamina:" + item.getStaminaModifier() + " MinDamage:" + item.getDamageMin()
				+ " MaxDamage:" + item.getDamageMax() + " ArmorDamage:" + item.getArmorDamageMult() + " DirectDamage:" + (item.m.DirectDamageMult + item.m.DirectDamageAdd)
				+ " AdditionalAccuracy:" + item.getAdditionalAccuracy() + " FatigueOnSkillUse:" + item.m.FatigueOnSkillUse
				+ " AmmoMax:" + item.m.AmmoMax + " ChanceToHitHead:" + item.m.ChanceToHitHead + " Condition:" + item.m.ConditionMax);
		named_type_num[NamedType.RangedWeapon]++;
	}
}
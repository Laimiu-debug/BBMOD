::include("seed_generator/define_lair");
::include("seed_generator/function_lair_output_check");

local gt = this.getroottable();

gt.SeedGenerator.lair_num <- 0; # 营地总数量
gt.SeedGenerator.named_total_num <- 0; # 红装总数量
gt.SeedGenerator.small_named_lair_num <- 0;
gt.SeedGenerator.medium_named_lair_num <- 0;
gt.SeedGenerator.large_named_lair_num <- 0;
gt.SeedGenerator.distance_close_named_lair_num <- 0;
gt.SeedGenerator.distance_medium_named_lair_num <- 0;
gt.SeedGenerator.distance_far_named_lair_num <- 0;
gt.SeedGenerator.named_type_num <- array(gt.SeedGenerator.NamedTypeNum, 0); # 著名物品类型数量
gt.SeedGenerator.lair_type_num <- array(gt.SeedGenerator.LairTypeNum, 0); # 各类型的营地数量
gt.SeedGenerator.lair_type_named_num <- array(gt.SeedGenerator.LairTypeNum, 0); # 各类型营地红的数量
gt.SeedGenerator.lair_type_double_named_num <- array(gt.SeedGenerator.LairTypeNum, 0); # 双红营地的数量
gt.SeedGenerator.lair_info_list <- [];

gt.SeedGenerator.generateLairInfo <- function()
{
	local output_type = -1;
	named_total_num = 0;
	lair_num = 0;
	small_named_lair_num = 0;
 	medium_named_lair_num = 0;
	large_named_lair_num = 0;
	distance_close_named_lair_num = 0;
 	distance_medium_named_lair_num = 0;
 	distance_far_named_lair_num = 0;
	named_type_num = array(NamedTypeNum, 0);
	lair_type_num = array(LairTypeNum, 0);
	lair_type_named_num = array(LairTypeNum, 0);
	lair_type_double_named_num  = array(LairTypeNum, 0);
	lair_info_list = [];
	local locations = this.World.EntityManager.getLocations();
	foreach(location in locations)
	{
		if(location.isLocationType(Const.World.LocationType.Lair) && !location.isLocationType(Const.World.LocationType.Unique))
		{
			lair_num++;
			local lair_type = -1;

			if(location.m.TypeID.find("bandit") != null)
			{
				lair_type_num[LairType.Bandit]++;
				lair_type = LairType.Bandit;
			}
			else if(location.m.TypeID.find("nomad") != null)
			{
				lair_type_num[LairType.Nomad]++;
				lair_type = LairType.Nomad;
			}
			else if(location.m.TypeID.find("barbarian") != null)
			{
				lair_type_num[LairType.Barbarian]++;
				lair_type = LairType.Barbarian;
			}
			else if(location.m.TypeID.find("goblin") != null)
			{
				lair_type_num[LairType.Goblin]++;
				lair_type = LairType.Goblin;
			}
			else if(location.m.TypeID.find("undead") != null)
			{
				lair_type_num[LairType.Undead]++;
				lair_type = LairType.Undead;
			}
			else if(location.m.TypeID.find("orc") != null)
			{
				lair_type_num[LairType.Orc]++;
				lair_type = LairType.Orc;
			}
			else
			{
				lair_type_num[LairType.Other]++;
				lair_type = LairType.Other;
			}

			if (!location.getLoot().isEmpty())
			{
				local named_items = [];
				foreach( item in location.getLoot().getItems() )
				{
					if (item.isItemType(this.Const.Items.ItemType.Named))
					{
						named_items.push(item)
						lair_type_named_num[lair_type]++;
					}
					if(named_items.len() >= 2)
						lair_type_double_named_num[lair_type]++;
				}

				if(named_items.len() != 0)
				{
					local tile = location.getTile(), nearestDistance = 1000000;
					local nearestSettlement;
					foreach(settlement in World.EntityManager.getSettlements())
					{
						local dis = tile.getDistanceTo(settlement.getTile());
						if(dis < nearestDistance)
						{
							nearestDistance = dis;
							nearestSettlement = settlement;
						}
					}

					local sPos = nearestSettlement.getTile().Pos;
					local lPos = tile.Pos;
					local direction = "upper";

					if((lPos.X - sPos.X) == 0)
					{
						if(lPos.Y > sPos.Y)
							direction = "upper";
						else
							direction = "lower";
					}
					else
					{
						local v = (lPos.Y - sPos.Y) / (lPos.X - sPos.X);
						if(lPos.X > sPos.X)
						{
							if(-0.4142 < v && v <= 0.4142)
								direction = "right";
							else if(0.4142 < v && v <= 2.4142)
								direction = "upper_right"
							else if(v > 2.4142)
								direction = "upper";
							else if(-2.4142 < v && v <= -0.4142)
								direction = "lower_right";
							else if(v <= -2.4142)
								direction = "lower";
						}
						else
						{
							if(-0.4142 < v && v <= 0.4142)
								direction = "left";
							else if(0.4142 < v && v <= 2.4142)
								direction = "lower_left"
							else if(v > 2.4142)
								direction = "lower";
							else if(-2.4142 < v && v <= -0.4142)
								direction = "upper_left";
							else if(v <= -2.4142)
								direction = "upper";
						}
					}

					local lair_info = array(LairInfoEntryNum);
					lair_info[LairInfoEntry.LairName] = location.getName();
					lair_info[LairInfoEntry.LairType] = lair_type;
					lair_info[LairInfoEntry.Strength] = location.getStrength();
					if(lair_info[LairInfoEntry.Strength] <= 150)
						small_named_lair_num++;
					else if(lair_info[LairInfoEntry.Strength] <= 250)
						medium_named_lair_num++;
					else
						large_named_lair_num++;
					lair_info[LairInfoEntry.NearestSettlementName] = nearestSettlement.getName();
					lair_info[LairInfoEntry.NearestSettlementDistance] = nearestDistance;
					lair_info[LairInfoEntry.NearestSettlementDirection] = direction;
					if(lair_info[LairInfoEntry.NearestSettlementDistance] <= 20)
						distance_close_named_lair_num++;
					else if(lair_info[LairInfoEntry.NearestSettlementDistance] <= 40)
						distance_medium_named_lair_num++;
					else
						distance_far_named_lair_num++;
					lair_info[LairInfoEntry.NamedItemsList] = named_items;

					lair_info_list.push(lair_info);
					named_total_num += named_items.len();
				}
			}
		}
	}

	if(CommonConfig.OnlyPrintMatchingLair)
	{
		output_type = lairOutoutCheck();
	}
	return output_type;
}
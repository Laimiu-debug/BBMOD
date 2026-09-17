::include("seed_generator/define_lair");
::include("seed_generator/function_map_output_check");

local gt = this.getroottable();

gt.SeedGenerator.port_num <- 0;			# 港口
gt.SeedGenerator.port_location <- array(gt.SeedGenerator.PortLocationNum, 0); # 左上 左下 中间 右上 右下 五种位置的港口
gt.SeedGenerator.city_port_num <- 0;	# 城邦港口
gt.SeedGenerator.armorsmith_num <- 0; 	# 盔甲店
// gt.SeedGenerator.alchemist_num <- 0;	# 炼金店
gt.SeedGenerator.barber_num <- 0;		# 理发店
gt.SeedGenerator.kennel_num <- 0;		# 犬舍
gt.SeedGenerator.tavern_num <- 0;		# 酒馆
gt.SeedGenerator.taxidermist_num <- 0;	# 剥制师
gt.SeedGenerator.temple_num <- 0;		# 神殿
gt.SeedGenerator.training_hall_num <- 0;# 训练厅
gt.SeedGenerator.weaponsmith_num <- 0; 	# 武器店
gt.SeedGenerator.fletcher_num <- 0;  	# 弓弩店
gt.SeedGenerator.settlements_num <- 0;	# 城市总数
gt.SeedGenerator.settlements_type_num <- array(gt.SeedGenerator.SettlementTypeNum, 0); # 城市类型总数
gt.SeedGenerator.arena_port <- 0; 		# 竞技场是否为港口
gt.SeedGenerator.products_num <- 0;		# 特产数量
gt.SeedGenerator.products_settlements_num <- 0; # 有特产的城市数量
gt.SeedGenerator.products_total_value <- 0; # 特产总价值
gt.SeedGenerator.products_city_total_value <- 0; # 城邦特产总价值
gt.SeedGenerator.products_port_total_value <- 0; # 港口特产总价值
gt.SeedGenerator.products_avg_value <- 0; # 特产平均价值，以products_settlements_num进行平均
gt.SeedGenerator.build_num <- 0; 	# 城市建筑数量
gt.SeedGenerator.settlement_avg_dis <- 0; # 城市平均距离
gt.SeedGenerator.settlement_port_avg_dis <- 0; # 城市以港口聚类后的平均距离
gt.SeedGenerator.large_settlement_num <- 0;
gt.SeedGenerator.large_fort_num <- 0;
gt.SeedGenerator.medium_settlement_num <- 0;
gt.SeedGenerator.medium_fort_num <- 0;
gt.SeedGenerator.small_settlement_num <- 0;
gt.SeedGenerator.small_fort_num <- 0;
gt.SeedGenerator.city_num <- 0;

// gt.SeedGenerator.named_type_num <- array(gt.SeedGenerator.NamedTypeNum, 0); # 著名物品类型数量
// gt.SeedGenerator.lair_num <- 0; # 营地总数量
// gt.SeedGenerator.small_named_lair_num <- 0;
// gt.SeedGenerator.medium_named_lair_num <- 0;
// gt.SeedGenerator.large_named_lair_num <- 0;
// gt.SeedGenerator.distance_close_named_lair_num <- 0;
// gt.SeedGenerator.distance_medium_named_lair_num <- 0;
// gt.SeedGenerator.distance_far_named_lair_num <- 0;
// gt.SeedGenerator.lair_type_num <- array(LairTypeNum, 0); # 各类型的营地数量
// gt.SeedGenerator.lair_type_named_num <- array(LairTypeNum, 0); # 各类型营地红的数量
// gt.SeedGenerator.lair_type_double_named_num <- array(LairTypeNum, 0); # 双红营地的数量
// gt.SeedGenerator.lair_info_list <- [];

gt.SeedGenerator.connected_info <- array(gt.SeedGenerator.ConnectedInfoEntryNum, 0); # 连通的城市信息
gt.SeedGenerator.attached_num <- 0; # 附属建筑数量
gt.SeedGenerator.attached_id_num_dict <- {}; # 对应ID的附属建筑数量
// gt.SeedGenerator.amber_collector_num <- 0; # 琥珀采集 小贩 临时工 小偷
// gt.SeedGenerator.beekeeper_num <- 0; # 养蜂人 农民
// gt.SeedGenerator.blast_furnace_num <- 0; # 高炉 扈从 逃兵 落魄贵族
// gt.SeedGenerator.brewery_num <- 0; # 啤酒厂 僧侣 拳手 赌徒
// gt.SeedGenerator.dye_maker_num <- 0; # 染料厂 学徒 商队帮工 裁缝
// gt.SeedGenerator.fishing_huts_num <- 0; # 钓鱼小屋 渔夫
// gt.SeedGenerator.fletchers_hut_num <- 0; # 弓箭小屋 弓匠 猎人 偷猎 女巫猎人
// gt.SeedGenerator.fortified_outpost_num <- 0; # 军营 退役士兵 逃兵 佣兵 骑士 宣誓者
// gt.SeedGenerator.gatherers_hut_num <- 0; # 采集小屋 临时工
// gt.SeedGenerator.gem_mine_num <- 0; # 宝石矿场 矿工 佣兵 商队帮工 小偷
// gt.SeedGenerator.goat_herd_num <- 0; # 山羊牧场 屠夫 临时工 农民 牧羊人
// gt.SeedGenerator.gold_mine_num <- 0; # 矿场 矿工 佣兵 商队帮工 小偷	   当前不存在
// gt.SeedGenerator.guarded_checkpoint_num <- 0; # 检查站 民兵 逃兵 佣兵  当前不存在
// gt.SeedGenerator.harbor_num <- 0; # 海港
// gt.SeedGenerator.herbalists_grove_num <- 0; # 草药师 僧侣 苦修 解刨
// gt.SeedGenerator.hunters_cabin_num <- 0; # 猎人小屋 屠夫 猎人 偷猎
// gt.SeedGenerator.incense_dryer_num <- 0; # 熏香烘干 临时工
// gt.SeedGenerator.leather_tanner_num <- 0; # 皮革鞣制工 民兵 学徒 退役士兵 屠夫
// gt.SeedGenerator.lumber_camp_num <- 0; # 伐木营地 伐木工 偷猎 野人
// gt.SeedGenerator.militia_trainingcamp_num <- 0; # 军事训练营 民兵 退役士兵
// gt.SeedGenerator.mushroom_grove_num <- 0; # 蘑菇园 异教徒 苦修 野人
// gt.SeedGenerator.orchard_num <- 0; # 果园 临时工 农民
// gt.SeedGenerator.ore_smelters_num <- 0; # 矿石熔炼 学徒 逃兵
// gt.SeedGenerator.peat_pit_num <- 0; # 泥炭场 临时工 小贩
// gt.SeedGenerator.pig_farm_num <- 0; # 养猪场 屠夫 临时工 农民 解刨
// gt.SeedGenerator.plantation_num <- 0; # 种植园 奴隶
// gt.SeedGenerator.salt_mine_num <- 0; # 盐矿 矿工 商队帮工
// gt.SeedGenerator.silk_farm_num <- 0; # 丝绸 临时工
// gt.SeedGenerator.stone_watchtower_num <- 0; # 石头瞭望塔 退役士兵 逃兵 宣誓
// gt.SeedGenerator.surface_copper_vein_num <- 0; # 露天铜矿 矿工 商队帮工
// gt.SeedGenerator.surface_iron_vein_num <- 0; # 露天铁矿 民兵 矿工 退役士兵
// gt.SeedGenerator.trapper_num <- 0; # 捕兽陷阱 小贩 偷猎 商队帮工
// gt.SeedGenerator.wheat_fields_num <- 0; # 麦田 农民 临时工 磨坊工
// gt.SeedGenerator.winery_num <- 0; # 葡萄酒酿造 僧侣 拳手 商队帮工
// gt.SeedGenerator.wooden_watchtower_num <- 0; # 木头瞭望塔 民兵 宣誓
// gt.SeedGenerator.wool_spinner_num <- 0; # 纺织厂 学徒 商队帮工 裁缝 牧羊人
// gt.SeedGenerator.workshop_num <- 0; # 工坊 学徒 商队帮工 小贩 临时工

enum ConnectedAnsEntry
{
	VertexNum,
	RoadSizeSum,
	ResultIndexList,
	End,
};

enum VertexEntry
{
	SrcIndex,
	DstIndex,
	RoadSize,
	RoadType,
	End,
};

local ConnectedAnsEntryNum = ConnectedAnsEntry.End;
local VertexEntryNum = VertexEntry.End;

local getDistance = function(x1, y1, x2, y2)
{
	local dis = this.Math.pow((x1 - x2) * (x1 - x2) + (y1 - y2) * (y1 - y2), 0.5);
	return dis;
}

local getPosDistance = function(pos1, pos2)
{
	local dis = this.Math.pow((pos1.X - pos2.X) * (pos1.X - pos2.X) + (pos1.Y - pos2.Y) * (pos1.Y - pos2.Y), 0.5);
	return dis;
}

local vertexSortByAscend = function(first, second)
{
	if(first[VertexEntry.RoadSize] > second[VertexEntry.RoadSize]) return 1;
	if(first[VertexEntry.RoadSize] < second[VertexEntry.RoadSize]) return -1;
	return 0;
}

local dfs;
local route_visits = 0;
local route_deadline = 0.0;
dfs = function(index, end_index, graph_list, visited_flags, visited_index, temp, ans)
{
	// Bound exponential simple-cycle enumeration; reject rather than claim a partial match.
	route_visits++;
	if(route_visits > 250000 || (route_visits % 1024 == 0 && ::Time.getExactTime() >= route_deadline))
		throw "BBMOD-route-budget";
	temp[0]++;
	local graph = graph_list[index];
	visited_flags[index] = true;
	visited_index.push(index);
	foreach( v in graph )
	{
		if(v[VertexEntry.DstIndex] == end_index )
		{
			if( temp[0] > ans[ConnectedAnsEntry.VertexNum] )
			{
				temp[1] += v[VertexEntry.RoadSize];
				ans[ConnectedAnsEntry.VertexNum] = temp[0];
				ans[ConnectedAnsEntry.RoadSizeSum] = temp[1];
				ans[ConnectedAnsEntry.ResultIndexList] = visited_index.slice(0);
				temp[1] -= v[VertexEntry.RoadSize];
			}
		}
		else
		{
			if(visited_flags[v[VertexEntry.DstIndex]] == false)
			{
				temp[1] += v[VertexEntry.RoadSize];
				dfs(v[VertexEntry.DstIndex], end_index, graph_list, visited_flags, visited_index, temp, ans);
				temp[1] -= v[VertexEntry.RoadSize];
			}
		}
	}
	temp[0]--;
	visited_flags[index] = false;
	visited_index.pop();
}

# 根据种子生成城市
gt.SeedGenerator.generateSettlement <- function(seedString, world_state)
{
	this.reportProgress("map");
	port_num = 0;
	port_location = array(PortLocationNum, 0);
	city_port_num = 0;
	armorsmith_num = 0;
	// alchemist_num = 0;	# 炼金店
	barber_num = 0;		# 理发店
	kennel_num = 0;		# 犬舍
	tavern_num = 0;		# 酒馆
	taxidermist_num = 0;	# 剥制师
	temple_num = 0;		# 神殿
	training_hall_num = 0;# 训练厅
	weaponsmith_num = 0;
	fletcher_num = 0;
	settlements_num = 0;
	settlements_type_num = array(SettlementTypeNum, 0);
	arena_port = 0;
	products_num = 0;
	products_settlements_num = 0;
	products_total_value = 0; # 特产总价值
	products_city_total_value = 0;
	products_port_total_value = 0;
	products_avg_value = 0; # 特产平均价值
	build_num = 0;
	settlement_avg_dis = 0;
	settlement_port_avg_dis = 0;
	large_settlement_num = 0;
	large_fort_num = 0;
	medium_settlement_num = 0;
	medium_fort_num = 0;
	small_settlement_num = 0;
	small_fort_num = 0;
	city_num = 0;
	connected_info = array(ConnectedInfoEntryNum, 0);

	gt.SeedGenerator.NamedIndex = 0;
	gt.SeedGenerator.NamedIndexDict = {};

	attached_num = 0;
	attached_id_num_dict = {};
	attached_id_num_dict["attached_location.fortified_outpost"] <- 0;
	// attached_id_num_dict["attached_location.guarded_checkpoint"] <- 0;
	attached_id_num_dict["attached_location.militia_trainingcamp"] <- 0;
	attached_id_num_dict["attached_location.stone_watchtower"] <- 0;
	attached_id_num_dict["attached_location.wooden_watchtower"] <- 0;

	attached_id_num_dict["attached_location.blast_furnace"] <- 0;
	attached_id_num_dict["attached_location.gem_mine"] <- 0;
	// attached_id_num_dict["attached_location.gold_mine"] <- 0;
	attached_id_num_dict["attached_location.salt_mine"] <- 0;

	attached_id_num_dict["attached_location.brewery"] <- 0;
	attached_id_num_dict["attached_location.winery"] <- 0;

	attached_id_num_dict["attached_location.fletchers_hut"] <- 0;
	attached_id_num_dict["attached_location.hunters_cabin"] <- 0;

	attached_id_num_dict["attached_location.leather_tanner"] <- 0;
	attached_id_num_dict["attached_location.lumber_camp"] <- 0;
	attached_id_num_dict["attached_location.mushroom_grove"] <- 0;
	attached_id_num_dict["attached_location.surface_iron_vein"] <- 0;

	this.Math.seedRandomString(seedString);
	local worldmap = this.MapGen.get("world.worldmap_generator");
	local minX = worldmap.getMinX();
	local minY = worldmap.getMinY();
	this.World.resizeScene(minX, minY);
	worldmap.fill({
		X = 0,
		Y = 0,
		W = minX,
		H = minY
	}, null);

	local settlements = this.World.EntityManager.getSettlements();
	settlements_num = settlements.len();

	local settlements_id_dict = {};
	local settlements_name = array(settlements_num, "");
	for( local i = 0; i != settlements_num; i++ )
	{
		local settlement = settlements[i];
		settlements_name[i] = settlement.getName();
		settlements_id_dict[settlement.getID()] <- [i, settlement];
	}

	local navSettings = this.World.getNavigator().createSettings();
	local graph_list = array(settlements_num);
	foreach( i, st in settlements )
	{
		graph_list[i] = [];
		local added_idx_list = [];

		if(st.m.ConnectedToByRoads.len() == 0)
		{
			connected_info[ConnectedInfoEntry.IsolatedCityNum]++;
		}

		foreach( id in st.m.ConnectedToByRoads )
		{
			local j = settlements_id_dict[id][0];
			local end = settlements_id_dict[id][1];
			navSettings.ActionPointCosts = this.Const.World.TerrainTypeNavCost;
			navSettings.RoadOnly = true;
			local path = this.World.getNavigator().findPath(st.getTile(), end.getTile(), navSettings, 0);

			if (!path.isEmpty())
			{
				added_idx_list.push(j);
				local vertex = array(VertexEntryNum);
				vertex[VertexEntry.SrcIndex] = i;
				vertex[VertexEntry.DstIndex] = j;
				vertex[VertexEntry.RoadSize] = path.getSize();
				vertex[VertexEntry.RoadType] = "";
				graph_list[i].push(vertex);
			}
		}

		foreach( id in st.m.ConnectedTo )
		{
			local j = settlements_id_dict[id][0];
			if(added_idx_list.find(j) != null)
				continue;
			local end = settlements_id_dict[id][1];
			navSettings.ActionPointCosts = this.Const.World.TerrainTypeNavCost;
			navSettings.RoadOnly = false;
			local path = this.World.getNavigator().findPath(st.getTile(), end.getTile(), navSettings, 0);

			if (!path.isEmpty() && path.getSize() * 1.5 <= 30)
			{
				added_idx_list.push(j);
				local vertex = array(VertexEntryNum);
				vertex[VertexEntry.SrcIndex] = i;
				vertex[VertexEntry.DstIndex] = j;
				vertex[VertexEntry.RoadSize] = path.getSize() * 1.5;
				vertex[VertexEntry.RoadType] = "'";
				graph_list[i].push(vertex);
			}
		}
		graph_list[i].sort(vertexSortByAscend);
	}

	local graph_simple_list = array(settlements_num);
	foreach( i, graph in graph_list ) // 排序后的队列
	{
		graph_simple_list[i] = [];
		foreach( j, vertex in graph ) // 逐个判断是否直接相连
		{
			if(j == 0) // 最近的肯定连接
			{
				graph_simple_list[i].push(vertex);
			}
			else
			{
				local flag = true;
				foreach( z, v in graph_list[i] ) // 看是否由之前的点连过去
				{
					foreach( i_, v_ in graph_list[v[VertexEntry.DstIndex]] )
					{
						if( v_[VertexEntry.DstIndex] == vertex[VertexEntry.DstIndex])
						{
							if((v[VertexEntry.RoadSize] + v_[VertexEntry.RoadSize] - vertex[VertexEntry.RoadSize]) <= 10 )
								flag = false;
							break;
						}
					}
					if(!flag)
					 break;
				}

				if(flag)
					graph_simple_list[i].push(vertex);
			}
		}
	}

	local road_count = 0;
	local connected_table = array(settlements_num);
	for( local i = 0; i < settlements_num; i++)
		connected_table[i] = array(settlements_num, false)
	foreach( i, graph in graph_simple_list )
	{
		local connected_id_str = "";
		foreach( v in graph )
		{
			if(connected_table[i][v[VertexEntry.DstIndex]] == false)
			{
				connected_table[i][v[VertexEntry.DstIndex]] = true;
				connected_table[v[VertexEntry.DstIndex]][i] = true;
				road_count++;
				if(v[VertexEntry.RoadType] == "")
					connected_info[ConnectedInfoEntry.TotalRoadSize] += v[VertexEntry.RoadSize];
			}
			connected_id_str += " " + v[VertexEntry.DstIndex] + "-" + settlements_name[v[VertexEntry.DstIndex]] + "(" + v[VertexEntry.RoadSize] + ")" + v[VertexEntry.RoadType];
		}
		if(DebugConfig.DebugMode)
			this.logInfo("ID " + i + "-" + settlements_name[i] + " [" + connected_id_str + "]");
	}
	// this.logInfo("RoadCount: " + road_count);

	local last_ans = array(ConnectedAnsEntryNum, 0);
	last_ans[ConnectedAnsEntry.ResultIndexList] = [];
	this.reportProgress("routes");
	route_visits = 0;
	route_deadline = ::Time.getExactTime() + 3.0;
	# 循环dfs
	try
	{
	for ( local i = 0; i < settlements_num; i++)
	{
		local visited_flags = array(settlements_num, false);
		local ans = array(ConnectedAnsEntryNum, 0);
		local temp = array(2, 0); # num roadsize

		local visited_index = [];
		dfs(i, i, graph_simple_list, visited_flags, visited_index, temp, ans);
		if(ans[ConnectedAnsEntry.VertexNum] < 3)
			ans[ConnectedAnsEntry.VertexNum]= 0;
		if( ans[ConnectedAnsEntry.VertexNum] > last_ans[ConnectedAnsEntry.VertexNum] )
		// if( ans[ConnectedAnsEntry.MinWeightNum] < last_ans[ConnectedAnsEntry.MinWeightNum] )
		{
			last_ans[ConnectedAnsEntry.VertexNum] = ans[ConnectedAnsEntry.VertexNum];
			last_ans[ConnectedAnsEntry.RoadSizeSum] = ans[ConnectedAnsEntry.RoadSizeSum];
			last_ans[ConnectedAnsEntry.ResultIndexList] = ans[ConnectedAnsEntry.ResultIndexList].slice(0);
		}
	}

	}
	catch(error)
	{
		if(error != "BBMOD-route-budget") throw error;
		this.reportProgress("map-skipped");
		return -2;
	}
	// this.logInfo("ANS: " + last_ans[ConnectedAnsEntry.VertexNum] + " " + last_ans[ConnectedAnsEntry.RoadSizeSum] + " " + last_ans[ConnectedAnsEntry.RoadSizeSum] / last_ans[ConnectedAnsEntry.VertexNum]);
	for( local i = 0; i < last_ans[ConnectedAnsEntry.ResultIndexList].len(); i++)
	{
		local idx = last_ans[ConnectedAnsEntry.ResultIndexList][i];
		local next_idx = -1;
		local road_size = -1;
		if(i != last_ans[ConnectedAnsEntry.ResultIndexList].len() - 1)
			next_idx = last_ans[ConnectedAnsEntry.ResultIndexList][i + 1]
		else
			next_idx = last_ans[ConnectedAnsEntry.ResultIndexList][0];
		foreach( v in graph_simple_list[idx])
		{
			if(v[VertexEntry.DstIndex] == next_idx)
				road_size = v[VertexEntry.RoadSize]
		}
		if(DebugConfig.DebugMode)
			this.logInfo("VisitedInfo: " + i + " " + idx + "-" + settlements_name[idx] + "->" + settlements_name[next_idx] + " "  + road_size);
	}
	connected_info[ConnectedInfoEntry.SettlementsNum] = last_ans[ConnectedAnsEntry.VertexNum];
	if(last_ans[ConnectedAnsEntry.VertexNum] != 0)
	{
		connected_info[ConnectedInfoEntry.AvgRoadSize] = last_ans[ConnectedAnsEntry.RoadSizeSum] / last_ans[ConnectedAnsEntry.VertexNum];
		connected_info[ConnectedInfoEntry.AvgRoadSize] = connected_info[ConnectedInfoEntry.AvgRoadSize].tointeger();
	}

	local minX = 1000000;
	local minY = 1000000;
	local maxX = -1;
	local maxY = -1;
	local midX = 0;
	local midY = 0;
	local meanX = 0;
	local meanY = 0;
	local mid_radius = 0;
	local mean_radius = 0;
	for( local i = 0; i < settlements_num; i++ )
	{
		local settlement = settlements[i];
		local pos = settlement.getTile().Pos;
		meanX += pos.X;
		meanY += pos.Y;
		if(pos.X < minX)
			minX = pos.X;
		if(pos.Y < minY)
			minY = pos.Y;
		if(pos.X > maxX)
			maxX = pos.X;
		if(pos.Y > maxY)
			maxY = pos.Y;
	}
	midX = (minX + maxX) / 2;
	midY = (minY + maxY) / 2;
	meanX = meanX / settlements_num;
	meanY = meanY / settlements_num;
	mid_radius = this.Math.pow((maxX - minX) * (maxX - minX) + (maxY - minY) * (maxY - minY), 0.5) / 2.0;

	// local avg_distance = 0;
	// for( local i = 0; i != settlements_num; i++ )
	// {
	// 	local settlement = settlements[i];
	// }

	// this.logInfo(minX + " " + maxX + " " + minY + " " + maxY + " " + midX + " " + midY + " " + mid_radius + " " + meanX + " " + meanY);
	local port_pos_array = [];
	local pos_array = [];

	local settlements_product_num = array(settlements_num, 0);
	local settlements_product_value = array(settlements_num, 0);
	for( local i = 0; i < settlements_num; i++ )
	{
		local settlement = settlements[i];
		local pos = settlement.getTile().Pos;
		local has_product = false;
		pos_array.append(pos);

		if(settlement.m.Rumors == this.Const.Strings.RumorsFishingSettlement)
		{
			settlements_type_num[SettlementType.Coast]++;
		}
		else if(settlement.m.Rumors == this.Const.Strings.RumorsFarmingSettlement)
		{
			settlements_type_num[SettlementType.Farm]++;
		}
		else if(settlement.m.Rumors == this.Const.Strings.RumorsForestSettlement)
		{
			settlements_type_num[SettlementType.Forest]++;
		}
		else if(settlement.m.Rumors == this.Const.Strings.RumorsMiningSettlement || (settlement.m.Size == 1 && settlement.m.Rumors.len() == 0))
		{
			settlements_type_num[SettlementType.Mountains]++;
		}
		else if(settlement.m.Rumors == this.Const.Strings.RumorsSnowSettlement)
		{
			settlements_type_num[SettlementType.Snow]++;
		}
		else if(settlement.m.Rumors == this.Const.Strings.RumorsSteppeSettlement)
		{
			settlements_type_num[SettlementType.Steppe]++;
		}
		else if(settlement.m.Rumors == this.Const.Strings.RumorsSwampSettlement)
		{
			settlements_type_num[SettlementType.Swamp]++;
		}
		else if(settlement.m.Rumors == this.Const.Strings.RumorsTundraSettlement)
		{
			settlements_type_num[SettlementType.Tundra]++;
		}
		else if(settlement.m.Rumors == this.Const.Strings.RumorsDesertSettlement)
		{
			settlements_type_num[SettlementType.Desert]++;
		}
		else
		{
			this.logInfo("Unknown name " + settlement.m.Name);
		}


		// this.logInfo(settlement.getName() + " " + settlement.getTile().Pos.X + " " + settlement.getTile().Pos.Y);
		foreach ( b in settlement.m.Buildings )
		{
			if (b == null || b.isHidden() || b.getID() == "building.marketplace" || b.getID() == "building.crowd" ||
			 	b.getID() == "building.arena" || b.getID() == "building.barber")
			{
				continue;
			}
			// this.logInfo(b.getID());
			build_num += 1;
		}

		local last_products_num = products_num;
		local last_products_total_value = products_total_value;
		foreach ( a in settlement.m.AttachedLocations )
		{
			if (a == null || !a.m.IsActive)
			{
				continue;
			}
			// this.logInfo(a.getTypeID());
			if( a.getTypeID() in attached_id_num_dict )
				attached_id_num_dict[a.getTypeID()]++;
			else
				attached_id_num_dict[a.getTypeID()] <- 1;
			attached_num += 1;

			if (a.getTypeID() == "attached_location.amber_collector")
			{
				has_product = true;
				products_num++;
				products_total_value += 260;
			}
			if (a.getTypeID() == "attached_location.dye_maker")
			{
				has_product = true;
				products_num++;
				products_total_value += 400;
			}
			if (a.getTypeID() == "attached_location.gem_mine")
			{
				has_product = true;
				products_num++;
				products_total_value += 520;
			}
			if (a.getTypeID() == "attached_location.incense_dryer")
			{
				has_product = true;
				products_num++;
				products_total_value += 380;
			}
			if (a.getTypeID() == "attached_location.lumber_camp")
			{
				has_product = true;
				products_num++;
				products_total_value += 180;
			}
			if (a.getTypeID() == "attached_location.peat_pit")
			{
				has_product = true;
				products_num++;
				products_total_value += 100;
			}
			if (a.getTypeID() == "attached_location.plantation")
			{
				has_product = true;
				products_num++;
				products_total_value += 320;
			}
			if (a.getTypeID() == "attached_location.salt_mine")
			{
				has_product = true;
				products_num++;
				products_total_value += 340;
			}
			if (a.getTypeID() == "attached_location.silk_farm")
			{
				has_product = true;
				products_num++;
				products_total_value += 460;
			}
			if (a.getTypeID() == "attached_location.surface_copper_vein")
			{
				has_product = true;
				products_num++;
				products_total_value += 220;
			}
			if (a.getTypeID() == "attached_location.trapper")
			{
				has_product = true;
				products_num++;
				products_total_value += 300;
			}
			if (a.getTypeID() == "attached_location.wool_spinner")
			{
				has_product = true;
				products_num++;
				products_total_value += 140;
			}
		}
		if(has_product)
			products_settlements_num++;
		settlements_product_num[i] = products_num - last_products_num;
		settlements_product_value[i] = products_total_value - last_products_total_value;
		if(settlement.isSouthern())
			products_city_total_value += settlements_product_value[i];

		if(last_ans[ConnectedAnsEntry.ResultIndexList].find(i) != null)
		{
			if(settlement.isSouthern())
				connected_info[ConnectedInfoEntry.CityNum]++;

			if(has_product)
			{
				connected_info[ConnectedInfoEntry.ProductSettlementsNum]++;
				connected_info[ConnectedInfoEntry.ProductNum] += settlements_product_num[i];
				connected_info[ConnectedInfoEntry.ProductValue] += settlements_product_value[i];
			}

			if(settlement.m.HousesType == 3)
			{
				if(settlement.m.IsMilitary)
					connected_info[ConnectedInfoEntry.LargeFortNum]++;
				else
					connected_info[ConnectedInfoEntry.LargeSettlementsNum]++;
			}
			else if(settlement.m.HousesType == 2)
			{
				if(settlement.m.IsMilitary)
					connected_info[ConnectedInfoEntry.MediumFortNum]++;
				else
					connected_info[ConnectedInfoEntry.MediumSettlementsNum]++;
			}
			else if(settlement.m.HousesType == 1)
			{
				if(settlement.m.IsMilitary)
					connected_info[ConnectedInfoEntry.SmallFortNum]++;
				else
					connected_info[ConnectedInfoEntry.SmallSettlementsNum]++;
			}

			if (settlement.hasBuilding("building.port"))
				connected_info[ConnectedInfoEntry.PortNum]++;
		}

		{
			if (settlement.hasBuilding("building.port"))
			{
				port_pos_array.append(pos);
				port_num++;
				if(settlement.hasBuilding("building.arena"))
					arena_port= 1;
				if(settlement.isSouthern())
					city_port_num++;
				products_port_total_value += settlements_product_value[i];
				if(getDistance(pos.X, pos.Y, midX, midY) < 0.3 * mid_radius)
					port_location[PortLocation.Middle]++;
				else if(pos.X <= midX && pos.Y >= midY)
					port_location[PortLocation.UpperLeft]++;
				else if(pos.X <= midX && pos.Y <= midY)
					port_location[PortLocation.LowerLeft]++;
				else if(pos.X >= midX && pos.Y >= midY)
					port_location[PortLocation.UpperRight]++;
				else if(pos.X >= midX && pos.Y <= midY)
					port_location[PortLocation.LowerRight]++;
			}
			if (settlement.hasBuilding("building.armorsmith") || settlement.hasBuilding("building.armorsmith_oriental"))
			{
				armorsmith_num++;
			}
			if (settlement.hasBuilding("building.weaponsmith") || settlement.hasBuilding("building.weaponsmith_oriental"))
			{
				weaponsmith_num++;
			}
			if (settlement.hasBuilding("building.fletcher"))
			{
				fletcher_num++;
			}
			// if (settlement.hasBuilding("building.alchemist"))
			// {
			// 	alchemist_num++;
			// }
			if (settlement.hasBuilding("building.barber"))
			{
				barber_num++;
			}
			if (settlement.hasBuilding("building.kennel"))
			{
				kennel_num++;
			}
			if (settlement.hasBuilding("building.tavern"))
			{
				tavern_num++;
			}
			if (settlement.hasBuilding("building.taxidermist") || settlement.hasBuilding("building.taxidermist_oriental"))
			{
				taxidermist_num++;
			}
			if (settlement.hasBuilding("building.temple"))
			{
				temple_num++;
			}
			if (settlement.hasBuilding("building.training_hall"))
			{
				training_hall_num++;
			}
		}

		if(settlement.m.HousesType == 4)
		{
			city_num++;
		}
		else if(settlement.m.HousesType == 3)
		{
			if(settlement.m.IsMilitary)
				large_fort_num++;
			else
				large_settlement_num++;
		}
		else if(settlement.m.HousesType == 2)
		{
			if(settlement.m.IsMilitary)
				medium_fort_num++;
			else
				medium_settlement_num++;
		}
		else if(settlement.m.HousesType == 1)
		{
			if(settlement.m.IsMilitary)
				small_fort_num++;
			else
				small_settlement_num++;
		}
	}
	if(products_settlements_num != 0)
		products_avg_value = products_total_value / products_settlements_num;
	if(connected_info[ConnectedInfoEntry.ProductSettlementsNum] != 0)
		connected_info[ConnectedInfoEntry.ProductAvgValue] = connected_info[ConnectedInfoEntry.ProductValue] /
			connected_info[ConnectedInfoEntry.ProductSettlementsNum];

	local dis_sum = 0;
	for( local i = 0; i < settlements_num; i++ )
	{
		local pos = pos_array[i];
		dis_sum += this.Math.pow((pos.X - meanX) * (pos.X - meanX) + (pos.Y - meanY) * (pos.Y - meanY), 0.5);
	}
	settlement_avg_dis = dis_sum  / 100 / settlements_num;
	settlement_avg_dis = settlement_avg_dis.tointeger()

	if(port_pos_array.len() > 1)
	{
		local settltment_cluster_pos = array(port_pos_array.len());
		local settltment_cluster_sum_X = array(port_pos_array.len(), 0.0);
		local settltment_cluster_sum_Y = array(port_pos_array.len(), 0.0);
		local settltment_cluster_avg_dis = array(port_pos_array.len(), 0.0);
		for( local i = 0; i != port_pos_array.len(); i++ )
		{
			settltment_cluster_pos[i] = [];
		}

		for( local i = 0; i != settlements_num; i++ )
		{
			local pos = pos_array[i];
			local min_dis = 100000;
			local min_index = -1;
			for( local j = 0; j != port_pos_array.len(); j++ )
			{
				local port_pos = port_pos_array[j];
				local dis = this.Math.pow((pos.X - port_pos.X) * (pos.X - port_pos.X) + (pos.Y - port_pos.Y) * (pos.Y - port_pos.Y), 0.5);
				if(dis < min_dis)
				{
					min_index = j;
					min_dis = dis;
				}
			}

			settltment_cluster_pos[min_index].append(pos);
			settltment_cluster_sum_X[min_index] += pos.X;
			settltment_cluster_sum_Y[min_index] += pos.Y;
		}


		for( local i = 0; i < port_pos_array.len(); i++ )
		{
			settltment_cluster_sum_X[i] = settltment_cluster_sum_X[i] / settltment_cluster_pos[i].len();
			settltment_cluster_sum_Y[i] = settltment_cluster_sum_Y[i] / settltment_cluster_pos[i].len();

			foreach( pos in settltment_cluster_pos[i] )
			{
				settltment_cluster_avg_dis[i] += this.Math.pow((pos.X - settltment_cluster_sum_X[i]) * (pos.X - settltment_cluster_sum_X[i]) +
					(pos.Y - settltment_cluster_sum_Y[i]) * (pos.Y - settltment_cluster_sum_Y[i]), 0.5);
			}
			settltment_cluster_avg_dis[i] = settltment_cluster_avg_dis[i] / settltment_cluster_pos[i].len();
			settlement_port_avg_dis += settltment_cluster_avg_dis[i];
		}
		settlement_port_avg_dis = settlement_port_avg_dis / 100 / port_pos_array.len();
		settlement_port_avg_dis = settlement_port_avg_dis.tointeger();
	}

	world_state.m.Assets.init();
	this.World.FactionManager.createFactions();

	local output_type = -1;
	if(CommonConfig.OnlyPrintMatchingSettlement)
	{
        output_type = mapOutputCheck();
	}
	return output_type;
}

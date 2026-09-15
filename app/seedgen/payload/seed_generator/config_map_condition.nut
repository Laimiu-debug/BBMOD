local gt = this.getroottable();

gt.SeedGenerator.MapOutput <- {
	SettlementNum = 0,	# 城市数量 >=
	PortNum = 1,		# 港口数量 >=
	CityPortNum = 2,	# 城邦港口数量 >=
	PortMeanDis = 3,	# 以港口进行聚类的城市平均距离 <=
	MeanDis = 4,		# 城市平均距离 <=
	ArenaPort = 5,		# 竞技场港口 >=
	ProductsNum = 6,	# 特产数量 >=
	ProductsValue = 7,	# 特产价值 >=
	PortProductsValue = 8,	# 带港口的城的特产价值 >=
	ConnectedNum = 9,	# 环线连通的城市数 >=
	ConnectedRoad = 10,	# 环线连通的城市平均道路长度 <=
	BuildNum = 11,		# 总互动建筑数量 已经剔除人群、市场、竞技场、理发店 >=
	AttachedNum = 12,	# 总附属建筑数量 >=
	UpperLeftPortNum = 13,   # 左上港数量（北港）>=
	LowerLeftPortNum = 14,   # 左下港数量（南港）>=
	MiddlePortNum = 15,   	# 中间港数量（中港）>=
	UpperRightPortNum = 16,  # 右上港数量 >=
	LowerRightPortNum = 17,  # 右下港数量（东港）>=
	PortTypeNum = 18,		# 五种类型的港口类型数量 >=
	ArmorsmithNum = 19,		# 盔甲店数量 >=
	WeaponsmithNum = 20,		# 武器店数量 >=
	FletchernNum = 21,		# 弓弩店数量 >=
	ConnectedLargeSettlementsNum = 22, 	# 环线上的大城市数量 >=
	ConnectedLargeFortNum = 23,		 	# 环线上的大堡垒数量 >=
	ConnectedPortNum = 24, 				# 环线上的港口数量 >=
	SwampNum = 25, 	# 沼泽城数量 >=
	SnowNum = 26,	# 雪地城数量 >=
	TundraNum = 27,	# 苔原城数量 >=
	NoLostLargeSettlements = 28, # 不丢大城 1 or 0
	GemMineNum = 29, # 宝石矿数量 >=
	SaltMineNum = 30, # 盐矿数量 >=
};

local MapOutput = gt.SeedGenerator.MapOutput;

## 输出条件 满足任一条件则会输出结果
gt.SeedGenerator.MapOutputConditionArray <- [
	[MapOutput.SettlementNum, 22, MapOutput.PortNum, 8],	# 输出满足城市数>=22，港口>=8的地图
	[MapOutput.SettlementNum, 22, MapOutput.PortNum, 6, MapOutput.ArenaPort, 1, MapOutput.PortTypeNum, 3],	# 输出满足城市数>=22，港口>=6，港口位置>=3，有竞技港的地图
	[MapOutput.SettlementNum, 22, MapOutput.PortNum, 5, MapOutput.CityPortNum, 2, MapOutput.PortTypeNum, 3, MapOutput.ArenaPort, 1],	# 输出满足城市数>=22，港口>=5，港口位置>=3，城邦两港口的地图
	[MapOutput.SettlementNum, 22, MapOutput.PortNum, 4, MapOutput.CityPortNum, 3, MapOutput.PortTypeNum, 3],	# 输出满足城市数>=22，港口>=4，港口位置>=3，城邦全港口的地图
	[MapOutput.SettlementNum, 22, MapOutput.PortNum, 4, MapOutput.ArenaPort, 1, MapOutput.PortTypeNum, 4],
	// # 5
	[MapOutput.SettlementNum, 22, MapOutput.WeaponsmithNum, 6, MapOutput.ConnectedNum, 20, MapOutput.ConnectedRoad, 30, MapOutput.PortTypeNum, 3, MapOutput.ArenaPort, 1],
	[MapOutput.SettlementNum, 22, MapOutput.WeaponsmithNum, 6, MapOutput.ConnectedNum, 18, MapOutput.ConnectedRoad, 27, MapOutput.PortTypeNum, 3, MapOutput.ArenaPort, 1],
	[MapOutput.SettlementNum, 22, MapOutput.WeaponsmithNum, 6, MapOutput.ConnectedNum, 16, MapOutput.ConnectedRoad, 24, MapOutput.PortTypeNum, 3, MapOutput.ArenaPort, 1],
	[MapOutput.SettlementNum, 22, MapOutput.WeaponsmithNum, 6, MapOutput.ConnectedRoad, 25, MapOutput.PortTypeNum, 2, MapOutput.ArenaPort, 1,
		MapOutput.ConnectedLargeSettlementsNum, 3, MapOutput.ConnectedLargeFortNum, 2, MapOutput.ConnectedPortNum, 1],
	// # 8
	[MapOutput.NoLostLargeSettlements, 1, MapOutput.PortTypeNum, 2, MapOutput.BuildNum, 57],
	[MapOutput.NoLostLargeSettlements, 1, MapOutput.ProductsValue, 7000, MapOutput.GemMineNum, 2, MapOutput.ConnectedNum, 12],
	[MapOutput.NoLostLargeSettlements, 1, MapOutput.ProductsValue, 7000, MapOutput.GemMineNum, 1, MapOutput.SaltMineNum, 2, MapOutput.ConnectedNum, 12],
	[MapOutput.NoLostLargeSettlements, 1, MapOutput.ProductsValue, 8000, MapOutput.ConnectedNum, 12],
	// [MapOutput.SettlementNum, 22, MapOutput.ProductsValue, 9900],
	// [MapOutput.SettlementNum, 22, MapOutput.AttachedNum, 96],
	// [MapOutput.SettlementNum, 22, MapOutput.BuildNum, 61],

	// [MapOutput.NoLostLargeSettlements, 1],
	// [MapOutput.NoLostLargeSettlements, 1, MapOutput.PortTypeNum, 2],
	// [MapOutput.NoLostLargeSettlements, 1, MapOutput.ArenaPort, 1, MapOutput.PortTypeNum, 2],
	// [MapOutput.NoLostLargeSettlements, 1, MapOutput.PortProductsValue, 3000],
	// [MapOutput.MeanDis, 55],
	// [MapOutput.SwampNum, 0],
	// [MapOutput.SettlementNum, 10],
	[MapOutput.ProductsValue, 10000],
	[MapOutput.BuildNum, 60],
];

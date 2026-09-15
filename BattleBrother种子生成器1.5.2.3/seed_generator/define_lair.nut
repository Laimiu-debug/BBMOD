local gt = this.getroottable();

# 红装属性宏定义
gt.SeedGenerator.NamedAttr <- {
	RegularDamage = 0,		// 伤害
	ArmorDamageMult = 1,	// 破甲
	ChanceToHitHead = 2,	// 爆头几率
	DirectDamageAdd = 3,	// 穿甲
	StaminaModifier = 4,	// 疲劳
	ShieldDamage = 5,		// 破盾
	AmmoMax = 6,			// 弹药上限
	AdditionalAccuracy = 7,	// 额外命中
	FatigueOnSkillUse = 8,	// 技能疲劳
	MeleeDefense = 9,		// 近战防御
	RangedDefense = 10,		// 远程防御
	Condition = 11,			// 耐久
	End = 12,
};
local NamedAttr = gt.SeedGenerator.NamedAttr;

gt.SeedGenerator.NamedAttrName <- {}; # 红装属性名称，日志打印用
local NamedAttrName = gt.SeedGenerator.NamedAttrName;

NamedAttrName[NamedAttr.RegularDamage] <- "RegularDamage";
NamedAttrName[NamedAttr.ArmorDamageMult] <- "ArmorDamageMult";
NamedAttrName[NamedAttr.ChanceToHitHead] <- "ChanceToHitHead";
NamedAttrName[NamedAttr.DirectDamageAdd] <- "DirectDamageAdd";
NamedAttrName[NamedAttr.StaminaModifier] <- "StaminaModifier";
NamedAttrName[NamedAttr.ShieldDamage] <- "ShieldDamage";
NamedAttrName[NamedAttr.AmmoMax] <- "AmmoMax";
NamedAttrName[NamedAttr.AdditionalAccuracy] <- "AdditionalAccuracy";
NamedAttrName[NamedAttr.FatigueOnSkillUse] <- "FatigueOnSkillUse";
NamedAttrName[NamedAttr.MeleeDefense] <- "MeleeDefense";
NamedAttrName[NamedAttr.RangedDefense] <- "RangedDefense";
NamedAttrName[NamedAttr.Condition] <- "Condition";

gt.SeedGenerator.NamedAttrNum <- NamedAttr.End;


# 红装类型宏定义
gt.SeedGenerator.NamedType <- {
	Helmet = 0,
	Armor = 1,
	Shield = 2,
	TwoHanded = 3,
	OneHanded = 4,
	RangedWeapon = 5,
	End = 6,
};
local NamedType = gt.SeedGenerator.NamedType;

gt.SeedGenerator.NamedTypeName <- {}; # 著名物品类型名称，日志打印用
local NamedTypeName = gt.SeedGenerator.NamedTypeName;

NamedTypeName[NamedType.Helmet] <- "Helmet";
NamedTypeName[NamedType.Armor] <- "Armor";
NamedTypeName[NamedType.Shield] <- "Shield";
NamedTypeName[NamedType.TwoHanded] <- "TwoHanded";
NamedTypeName[NamedType.OneHanded] <- "OneHanded";
NamedTypeName[NamedType.RangedWeapon] <- "RangedWeapon";

gt.SeedGenerator.NamedTypeNum <- NamedType.End;


# 营地驻军类型宏定义
gt.SeedGenerator.LairType <- {
	Bandit = 0,
	Nomad = 1,
	Barbarian = 2,
	Goblin = 3,
	Undead = 4,
	Orc = 5,
	Other = 6,
	End = 7,
};
local LairType = gt.SeedGenerator.LairType;

gt.SeedGenerator.LairTypeName <- {}; # 营地驻军类型名称，日志打印用
local LairTypeName = gt.SeedGenerator.LairTypeName;

LairTypeName[LairType.Bandit] <- "Bandit";
LairTypeName[LairType.Nomad] <- "Nomad";
LairTypeName[LairType.Barbarian] <- "Barbarian";
LairTypeName[LairType.Goblin] <- "Goblin";
LairTypeName[LairType.Undead] <- "Undead";
LairTypeName[LairType.Orc] <- "Orc";
LairTypeName[LairType.Other] <- "Other";

gt.SeedGenerator.LairTypeNum <- LairType.End;


# 城市地形类型宏定义
gt.SeedGenerator.SettlementType <- {
	Coast = 0,	# Fishing
	Farm = 1, 	# Farming
	Forest = 2,	# Lumber
	Mountains = 3,	# Mining
	Snow = 4,
	Steppe = 5,
	Swamp = 6,
	Tundra = 7,
	Desert = 8,
	End = 9,
};
local SettlementType = gt.SeedGenerator.SettlementType;

gt.SeedGenerator.SettlementTypeName <- {}; # 城市类型名称，日志打印用
local SettlementTypeName = gt.SeedGenerator.SettlementTypeName;

SettlementTypeName[SettlementType.Coast] <- "Coast";
SettlementTypeName[SettlementType.Farm] <- "Farm";
SettlementTypeName[SettlementType.Forest] <- "Forest";
SettlementTypeName[SettlementType.Mountains] <- "Mountains";
SettlementTypeName[SettlementType.Snow] <- "Snow";
SettlementTypeName[SettlementType.Steppe] <- "Steppe";
SettlementTypeName[SettlementType.Swamp] <- "Swamp";
SettlementTypeName[SettlementType.Tundra] <- "Tundra";
SettlementTypeName[SettlementType.Desert] <- "Desert";

gt.SeedGenerator.SettlementTypeNum <- SettlementType.End;

# 港口类型宏定义
gt.SeedGenerator.PortLocation <- {
	UpperLeft = 0,
	LowerLeft = 1,
	Middle = 2,
	UpperRight = 3,
	LowerRight = 4,
	End = 5,
};

gt.SeedGenerator.PortLocationNum <- gt.SeedGenerator.PortLocation.End;

# 连通信息宏定义
gt.SeedGenerator.ConnectedInfoEntry <- {
	SettlementsNum = 0,
	AvgRoadSize = 1,
	IsolatedCityNum = 2,
	TotalRoadSize = 3,
	PortNum = 4,
	CityNum = 5,
	ProductNum = 6,
	ProductSettlementsNum = 7,
	ProductValue = 8,
	ProductAvgValue = 9,
	LargeSettlementsNum= 10,
	MediumSettlementsNum = 11,
	SmallSettlementsNum = 12,
	LargeFortNum = 13,
	MediumFortNum = 14,
	SmallFortNum = 15,
	End = 16,
};
gt.SeedGenerator.ConnectedInfoEntryNum <- gt.SeedGenerator.ConnectedInfoEntry.End;

# 营地信息宏定义
gt.SeedGenerator.LairInfoEntry <- {
	LairName = 0,
	LairType = 1,
	Strength = 2,
	NearestSettlementName = 3,
	NearestSettlementDistance = 4,
	NearestSettlementDirection = 5,
	NamedItemsList = 6,
	End = 7,
};

gt.SeedGenerator.LairInfoEntryNum <- gt.SeedGenerator.LairInfoEntry.End;
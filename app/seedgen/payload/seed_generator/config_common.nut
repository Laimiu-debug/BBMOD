local gt = this.getroottable();

# 注意事项
# 初始红跟难度和起源都有关
# 逃兵属性在生成地图后生成，所以逃兵搜索很慢，跟城市生成模式一样
# 个别城市的港口信息有很小的概率会出错
# 有小几率会卡死，原版BUG，比如 NMIXPYAZXH 这个种子，农民团起源根本进不去

# 常用模式1 生成满足地图条件的种子
# GenerateSettlementMode = true
# OnlyPrintMatchingSettlement = true
# PrintLairInfo = false

# 常用模式2 生成满足人物条件的种子
# GenerateSettlementMode = false
# GenerateBrotherMode = true
# MatchingBrotherGenerateSettlement = false
# OnlyPrintMatchingSettlement = false
# PrintLairInfo = false

# 常用模式3 生成满足人物条件且满足地图条件的种子
# GenerateSettlementMode = false
# GenerateBrotherMode = true
# MatchingBrotherGenerateSettlement = true
# OnlyPrintMatchingSettlement = true

# 常用模式4 生成满足人物条件且满足红装条件的种子
# GenerateSettlementMode = false
# GenerateBrotherMode = true
# MatchingBrotherGenerateSettlement = true
# OnlyPrintMatchingSettlement = false
# PrintLairInfo = true
# PrintLairNamedDetail = true
# OnlyPrintMatchingLair = true

# 全开模式 生成满足人物条件且满足地图条件且满足红装条件的种子
# GenerateSettlementMode = false
# GenerateBrotherMode = true
# MatchingBrotherGenerateSettlement = true
# OnlyPrintMatchingSettlement = true
# PrintLairInfo = true
# PrintLairNamedDetail = true
# OnlyPrintMatchingLair = true

gt.SeedGenerator.CommonConfig <- {
	# 生成城市模式， 耗时较长， 与 GenerateBrotherMode 互斥， 优先级高
	GenerateSettlementMode = false,
	# 生成角色模式， 耗时短， 与 GenerateSettlementMode 互斥， 优先级低
	GenerateBrotherMode = true,

	# 生成满足要求的角色时生成对应的地图城市信息， 仅在 GenerateBrotherMode 为true下生效
	MatchingBrotherGenerateSettlement = true,
	# 仅输出满足城市条件的信息 在 GenerateSettlementMode 为true或 MatchingBrotherGenerateSettlement 为true下生效
	OnlyPrintMatchingSettlement = false,

	# 是否打印初始营地红信息， 注意初始红与起源和难度都有关系， 在 GenerateSettlementMode 或 MatchingBrotherGenerateSettlement 为true下生效
	PrintLairInfo = true,
	# 是否打印营地红详细信息（ 类型 属性 位置等） 仅在 PrintLairInfo 为true下生效
	PrintLairNamedDetail = true,
	# 仅输出满足营地条件的信息 仅在 PrintLairNamedDetail 为true下生效
	OnlyPrintMatchingLair = false,

	# 是否启用小写字母生成种子， 关闭将全部生成大写字母的种子 全大写种子数141万亿 大小写种子数14亿亿
	EnableLowercaseSeed = false,
	# 使用实际11级属性代替期望11级属性输出 逃兵无效
	UseBrotherLevel11RealAttr = true,
	# 快速角色生成模式 不支持逃兵
	FastBrotherGenerateMode = true,
};

gt.SeedGenerator.DebugConfig <- {
	DebugSeed = ["LVEMPYDYZM", "NMIXPYAZXH"],
	DebugMode = false,
};

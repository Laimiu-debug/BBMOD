
local gt = this.getroottable();

## 属性顺序		    			血量 决心 疲劳 近战 远程 近防 远防 主动
gt.SeedGenerator.NoStar <- 		[30, 30, 30,  20, 30,  20, 30, 40];		# 没星11级的期望值
gt.SeedGenerator.OneStar <- 	[35, 35, 35,  25, 35,  25, 35, 45];		# 一星11级的期望值
gt.SeedGenerator.TwoStar <- 	[40, 40, 40,  30, 40,  30, 40, 50];		# 二星11级的期望值
gt.SeedGenerator.ThreeStar <- 	[45, 45, 45,  35, 45,  35, 45, 55];		# 三星11级的期望值

gt.SeedGenerator.Attr <- {
    Hitpoints = 0,		# 血量
    Bravery = 1,		# 决心
    Stamina = 2,		# 疲劳
	MeleeSkill = 3,		# 近战
	RangedSkill = 4,	# 远程
	MeleeDefense = 5,	# 近防
	RangedDefense = 6,	# 远防
	Initiative = 7,		# 主动
	End = 8,
};

gt.SeedGenerator.Talents <- {
    Hitpoints = 0,		# 血量
    Bravery = 1,		# 决心
    Stamina = 2,		# 疲劳
	Initiative = 3,		# 主动
	MeleeSkill = 4,		# 近战
	RangedSkill = 5,	# 远程
	MeleeDefense = 6,	# 近防
	RangedDefense = 7,	# 远防
	End = 8,
};

local Attr = gt.SeedGenerator.Attr;

gt.SeedGenerator.AttrName <- {}; # 属性名称，输出用

local AttrName = gt.SeedGenerator.AttrName;

AttrName[Attr.Hitpoints] <- "Hitpoints";
AttrName[Attr.Bravery] <- "Bravery";
AttrName[Attr.Stamina] <- "Stamina";
AttrName[Attr.MeleeSkill] <- "MeleeSkill";
AttrName[Attr.RangedSkill] <- "RangedSkill";
AttrName[Attr.MeleeDefense] <- "MeleeDefense";
AttrName[Attr.RangedDefense] <- "RangedDefense";
AttrName[Attr.Initiative] <- "Initiative";

gt.SeedGenerator.AttrNum <- Attr.End; 		# 属性数量
gt.SeedGenerator.TalentsNum <- gt.SeedGenerator.Talents.End; 	# 属性数量
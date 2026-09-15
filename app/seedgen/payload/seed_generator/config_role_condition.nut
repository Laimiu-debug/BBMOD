::include("seed_generator/define_role");

# 职业名称
// RoleMelee = 0,	  # 近战
// RoleRange = 1,	  # 远程
// RoleGuard = 2,	  # 盾卫
// RoleThrow = 3,	  # 柄投
// RoleLeader = 4,    # 队长
// RoleDuel = 5,	  # 决斗
// RolePolearm = 6,   # 长柄
// RoleInitiative = 7,# 主动

local gt = this.getroottable();
local Role = gt.SeedGenerator.Role;
local RoleNum = gt.SeedGenerator.RoleNum;

gt.SeedGenerator.BroOutput <- {
	TeamScore = 0,				# 输出队伍平均职业分满足分数的结果
	RoleScore = 1,				# 输出个体职业分满足分数的结果
	AnyRoleScore = 2,			# 输出不要求职业（除了废废）的满足分数的结果
	RoleAttr = 3, 				# 输出个体属性满足要求的结果
	RoleTraitScore = 4, 		# 输出个体特性和职业分同时满足要求的结果
	RoleTraitScoreIndex = 5, 	# 输出对应索引的兄弟个体特性和职业分同时满足要求的结果 角斗士起源 狮子->0 熊->1 蛇->2
};

## 输出条件 满足任一条件则会输出结果
gt.SeedGenerator.BroOutputConditionArray <- {};
## 队伍构成 比如当最高职业分的角色为队长时，将占用一个队长位，若没有队长位了，就算其他角色队长职业分高也只能以其他职业分进行分配
gt.SeedGenerator.MaxRoleArray <- {};

local Any = -100;
local BroOutput = gt.SeedGenerator.BroOutput;
local BroOutputConditionArray = gt.SeedGenerator.BroOutputConditionArray;
local MaxRoleArray = gt.SeedGenerator.MaxRoleArray;

## 新战团 星位固定
BroOutputConditionArray["scenario.early_access"] <-
[
// [BroOutput.TeamScore, 0.78],
// [BroOutput.RoleScore, 0.83, 1, Role.RoleMelee],
// [BroOutput.RoleScore, 0.75, 2, Role.RoleMelee],
// [BroOutput.AnyRoleScore, 0.83, 2],

// [BroOutput.RoleScore, 0.78, 1, Role.RoleMelee],
// [BroOutput.RoleScore, 0.82, 1, Role.RoleRange],

[BroOutput.RoleTraitScoreIndex, 1, 0.78, Role.RoleMelee, "trait.iron_lungs", "trait.sure_footing"],
];
MaxRoleArray["scenario.early_access"] <- array(RoleNum, 0);
MaxRoleArray["scenario.early_access"][Role.RoleMelee] = 2;  		# 最多两个近战
MaxRoleArray["scenario.early_access"][Role.RoleGuard] = 1;  		# 最多一个盾卫
MaxRoleArray["scenario.early_access"][Role.RoleRange] = 1;  		# 最多一个远程
MaxRoleArray["scenario.early_access"][Role.RoleLeader] = 1; 		# 最多一个队长
MaxRoleArray["scenario.early_access"][Role.RoleUseless] = 10000; 	# 剩下都是废废

## 南方雇佣兵 星位固定
BroOutputConditionArray["scenario.southern_quickstart"] <-
[
[BroOutput.TeamScore, 0.78],
[BroOutput.RoleScore, 0.83, 1, Role.RoleMelee],
[BroOutput.RoleScore, 0.75, 2, Role.RoleMelee],
[BroOutput.AnyRoleScore, 0.83, 2],
];
MaxRoleArray["scenario.southern_quickstart"] <- array(RoleNum, 0);
MaxRoleArray["scenario.southern_quickstart"][Role.RoleMelee] = 2;  		# 最多两个近战
MaxRoleArray["scenario.southern_quickstart"][Role.RoleGuard] = 1;  		# 最多一个盾卫
MaxRoleArray["scenario.southern_quickstart"][Role.RoleRange] = 1;  		# 最多一个远程
MaxRoleArray["scenario.southern_quickstart"][Role.RoleLeader] = 1; 		# 最多一个队长
MaxRoleArray["scenario.southern_quickstart"][Role.RoleUseless] = 10000; 	# 剩下都是废废

## 贸易商队 星位固定
BroOutputConditionArray["scenario.trader"] <-
[
[BroOutput.TeamScore, 0.70],
];
MaxRoleArray["scenario.trader"] <- array(RoleNum, 0);
MaxRoleArray["scenario.trader"][Role.RoleMelee] = 2;
MaxRoleArray["scenario.trader"][Role.RoleGuard] = 1;
MaxRoleArray["scenario.trader"][Role.RoleUseless] = 10000;

## 平民民兵
BroOutputConditionArray["scenario.militia"] <-
[

// [BroOutput.RoleTraitScore, 0.90, 1, Role.RoleRange, "trait.determined", ""],
[BroOutput.RoleTraitScoreIndex, 0, 0.90, Role.RoleMelee, "trait.huge", ""],
[BroOutput.RoleTraitScoreIndex, 1, 0.90, Role.RoleMelee, "trait.huge", ""],

// [BroOutput.RoleScore, 0.90, 1, Role.RoleMelee],
// [BroOutput.RoleScore, 0.90, 1, Role.RoleRange],
// [BroOutput.RoleScore, 0.90, 1, Role.RoleDuel],

// [BroOutput.RoleScore, 0.75, 4, Role.RoleMelee],
// [BroOutput.RoleScore, 0.80, 3, Role.RoleMelee],
// [BroOutput.RoleScore, 0.85, 2, Role.RoleMelee],
// [BroOutput.RoleScore, 0.90, 1, Role.RoleMelee],

// // [BroOutput.RoleScore, 0.85, 1, Role.RoleMelee, 0.85, 1, Role.RoleRange],
// // [BroOutput.RoleScore, 0.85, 1, Role.RoleMelee, 0.85, 1, Role.RoleGuard],
// // [BroOutput.RoleScore, 0.85, 1, Role.RoleMelee, 0.85, 1, Role.RoleThrow],
// // [BroOutput.RoleScore, 0.85, 1, Role.RoleMelee, 0.85, 1, Role.RoleLeader],
// // [BroOutput.RoleScore, 0.85, 1, Role.RoleMelee, 0.85, 1, Role.RolePolearm],

// [BroOutput.RoleScore, 0.80, 2, Role.RoleMelee, 0.80, 1, Role.RoleRange], # 4
// [BroOutput.RoleScore, 0.80, 2, Role.RoleMelee, 0.80, 1, Role.RoleGuard],
// [BroOutput.RoleScore, 0.80, 2, Role.RoleMelee, 0.80, 1, Role.RoleThrow],
// [BroOutput.RoleScore, 0.80, 2, Role.RoleMelee, 0.80, 1, Role.RoleLeader],
// // [BroOutput.RoleScore, 0.80, 2, Role.RoleMelee, 0.80, 1, Role.RolePolearm],

// [BroOutput.AnyRoleScore, 0.75, 5],# 13 # 有五个任意职业分大于0.75 # 8
// [BroOutput.AnyRoleScore, 0.80, 4], # 有四个任意职业分大于0.80
// [BroOutput.AnyRoleScore, 0.85, 3], # 有三个任意职业分大于0.85
];
MaxRoleArray["scenario.militia"] <- array(RoleNum, 0);
MaxRoleArray["scenario.militia"][Role.RoleMelee] = 10000;  	# 不限制近战数量
MaxRoleArray["scenario.militia"][Role.RoleRange] = 2;  		# 最多一个远程
MaxRoleArray["scenario.militia"][Role.RoleGuard] = 2;  		# 最多两个盾卫
MaxRoleArray["scenario.militia"][Role.RoleThrow] = 1;  		# 最多一个柄投
MaxRoleArray["scenario.militia"][Role.RoleLeader] = 1; 		# 最多一个队长
MaxRoleArray["scenario.militia"][Role.RoleDuel] = 1;   		# 最多一个轻甲决斗
MaxRoleArray["scenario.militia"][Role.RolePolearm] = 2;   	# 最多两个长柄
MaxRoleArray["scenario.militia"][Role.RoleUseless] = 10000; 	# 剩下都是废废

## 偷猎者团队 星位固定
BroOutputConditionArray["scenario.rangers"] <-
[
// [BroOutput.TeamScore, 0.80],

[BroOutput.RoleScore, 0.98, 1, Role.RoleRange], # 有一个角色的远程职业分大于0.80
// [BroOutput.RoleScore, 0.85, 2, Role.RoleRange],
// [BroOutput.RoleScore, 0.80, 3, Role.RoleRange],
];
MaxRoleArray["scenario.rangers"] <- array(RoleNum, 0);
MaxRoleArray["scenario.rangers"][Role.RoleMelee] = 2;
MaxRoleArray["scenario.rangers"][Role.RoleRange] = 3;
MaxRoleArray["scenario.rangers"][Role.RoleThrow] = 1;
MaxRoleArray["scenario.rangers"][Role.RoleLeader] = 1;
MaxRoleArray["scenario.rangers"][Role.RoleUseless] = 10000;


## 宣誓者 星位固定
BroOutputConditionArray["scenario.paladins"] <-
[
// [BroOutput.TeamScore, 0.97],

[BroOutput.RoleScore, 0.95, 1, Role.RoleDuel], # 巨人
[BroOutput.RoleTraitScore, 0.94, 1, Role.RoleDuel, "", "trait.huge"], # 巨人

];
MaxRoleArray["scenario.paladins"] <- array(RoleNum, 0);
MaxRoleArray["scenario.paladins"][Role.RoleMelee] = 2;
MaxRoleArray["scenario.paladins"][Role.RoleLeader] = 1;
MaxRoleArray["scenario.paladins"][Role.RoleDuel] = 1;
MaxRoleArray["scenario.paladins"][Role.RoleUseless] = 10000;

## 逃兵 星位固定
BroOutputConditionArray["scenario.deserters"] <-
[[BroOutput.TeamScore, 0.15],
];
MaxRoleArray["scenario.deserters"] <- array(RoleNum, 0);
MaxRoleArray["scenario.deserters"][Role.RoleMelee] = 2;
MaxRoleArray["scenario.deserters"][Role.RolePolearm] = 1;
MaxRoleArray["scenario.deserters"][Role.RoleRange] = 1;
MaxRoleArray["scenario.deserters"][Role.RoleThrow] = 1;
MaxRoleArray["scenario.deserters"][Role.RoleUseless] = 10000;

## 北方掠夺者 星位固定
BroOutputConditionArray["scenario.raiders"] <-
[[BroOutput.TeamScore, 0.80],

[BroOutput.RoleScore, 0.83, 1, Role.RoleMelee],
[BroOutput.RoleScore, 0.83, 1, Role.RoleDuel],
[BroOutput.RoleTraitScore, 0.80, 1, Role.RoleMelee, "", "trait.huge"], # 巨人
];
MaxRoleArray["scenario.raiders"] <- array(RoleNum, 0);
MaxRoleArray["scenario.raiders"][Role.RoleMelee] = 4;
MaxRoleArray["scenario.raiders"][Role.RolePolearm] = 1;
MaxRoleArray["scenario.raiders"][Role.RoleLeader] = 1;
MaxRoleArray["scenario.raiders"][Role.RoleGuard] = 1;
MaxRoleArray["scenario.raiders"][Role.RoleUseless] = 10000;

## 解刨学家 星位固定
BroOutputConditionArray["scenario.anatomists"] <-
[
[## 			    人数  血量  决心  疲劳   近战  远程  近防  远防  主动 人数  血量  决心  疲劳   近战  远程  近防  远防  主动 
BroOutput.RoleAttr, 1,    55,  Any,  130,  85,  Any,  35,  Any,  Any,]
// [BroOutput.RoleTraitScore, 0.76, 1, Role.RoleMelee, "trait.dexterous", "trait.sure_footing"],
];
MaxRoleArray["scenario.anatomists"] <- array(RoleNum, 0);
MaxRoleArray["scenario.anatomists"][Role.RoleMelee] = 3;
MaxRoleArray["scenario.anatomists"][Role.RoleGuard] = 1;
MaxRoleArray["scenario.anatomists"][Role.RoleThrow] = 1;
MaxRoleArray["scenario.anatomists"][Role.RoleLeader] = 1;
MaxRoleArray["scenario.anatomists"][Role.RoleUseless] = 10000;

## 异教徒
BroOutputConditionArray["scenario.cultists"] <-
[
// [BroOutput.RoleScore, 0.82, 1, Role.RoleMelee,BroOutput.RoleScore, 1.00, 1, Role.RoleLeader],
[BroOutput.RoleScore, 0.90, 1, Role.RoleMelee],
[BroOutput.RoleScore, 0.80, 1, Role.RoleMelee,BroOutput.RoleScore, 0.75, 1, Role.RoleMelee],
[BroOutput.RoleScore, 0.77, 2, Role.RoleMelee],
[BroOutput.RoleScore, 0.74, 3, Role.RoleMelee],
[BroOutput.RoleScore, 0.71, 4, Role.RoleMelee],
// [BroOutput.RoleScore, 1.00, 1, Role.RoleDuel],
// [BroOutput.RoleScore, 1.00, 1, Role.RoleInitiative],
// [BroOutput.AnyRoleScore, 0.83, 2],

## 			        人数  血量  决心  疲劳   近战  远程  近防  远防  主动
// [BroOutput.RoleAttr, 1,   Any,  Any,  140,  95,  Any,  40,  Any,  Any,],
// [BroOutput.TeamScore, 0.75],	# 满足队伍职业平均分大于0.70的
// [BroOutput.AnyRoleScore, 0.80, 4], # 有四个任意职业分大于0.80

// [BroOutput.RoleScore, 0.65, 4, Role.RoleMelee],
// [BroOutput.RoleScore, 0.70, 3, Role.RoleMelee],
// [BroOutput.RoleScore, 0.75, 2, Role.RoleMelee],
// [BroOutput.RoleScore, 0.90, 1, Role.RoleMelee],

// [BroOutput.RoleScore, 0.70, 2, Role.RoleMelee, 0.70, 1, Role.RoleGuard ],
// [BroOutput.RoleScore, 0.70, 2, Role.RoleMelee, 0.70, 1, Role.RoleThrow ],
[BroOutput.RoleScore, 0.75, 2, Role.RoleMelee, 0.70, 1, Role.RoleRange ],
// [BroOutput.RoleScore, 0.70, 2, Role.RoleMelee, 0.70, 1, Role.RolePolearm ],
// [BroOutput.RoleScore, 0.70, 2, Role.RoleMelee, 0.90, 1, Role.RoleLeader ],

// [BroOutput.RoleScore, 0.80, 1, Role.RoleMelee], # 有一个角色的近战职业分大于0.80  异教徒0.80基本是吕布级别
// [BroOutput.RoleScore, 0.75, 2, Role.RoleMelee], # 有两个角色的近战职业分大于0.75
// [BroOutput.RoleScore, 0.70, 3, Role.RoleMelee], # 有三个角色的近战职业分大于0.70
// [BroOutput.RoleScore, 0.75, 2, Role.RoleThrow], # 有两个角色的柄投职业分大于0.75
// [BroOutput.RoleScore, 0.70, 3, Role.RoleThrow], # 有三个角色的柄投职业分大于0.70
// [BroOutput.RoleScore, 0.75, 1, Role.RoleMelee, 0.75, 1, Role.RoleGuard ], # 有一个角色的近战职业分大于0.75 同时有另一个角色的盾卫职业分大于0.75
// [BroOutput.RoleScore, 0.75, 1, Role.RoleMelee, 0.75, 1, Role.RoleThrow ], # 有一个角色的近战职业分大于0.75 同时有另一个角色的柄投职业分大于0.75
// [BroOutput.RoleScore, 0.70, 1, Role.RoleMelee, 0.70, 1, Role.RoleThrow, 0.70, 1, Role.RoleGuard ], # 有一个角色的近战职业分大于0.70 同时有另一个角色的柄投职业分大于0.70 再有一个角色盾卫职业分大于0.70

## 					   	人数  血量  决心  疲劳   近战  远程  近防  远防  主动  人数  血量  决心  疲劳   近战  远程  近防  远防  主动
// [BroOutput.RoleAttr, 2,    Any,  Any,  130,  90,  Any,  30,  Any,  Any, 1,    Any,  Any,  Any,  Any,  Any,  35,  Any,  Any ], # 有两个角色的进攻属性大于90，近防大于30 同时有一个角色近防大于35
## 					   	人数  血量  决心  疲劳   近战  远程  近防  远防  主动
// [BroOutput.RoleAttr, 3,    Any,  Any,  Any,  90,  Any,  Any,  Any,  Any], # 有三个角色的进攻属性大于90
];
MaxRoleArray["scenario.cultists"] <- array(RoleNum, 0);
MaxRoleArray["scenario.cultists"][Role.RoleMelee] = 4;
MaxRoleArray["scenario.cultists"][Role.RoleGuard] = 0;
MaxRoleArray["scenario.cultists"][Role.RoleLeader] = 1;
MaxRoleArray["scenario.cultists"][Role.RolePolearm] = 0;
MaxRoleArray["scenario.cultists"][Role.RoleRange] = 1;
MaxRoleArray["scenario.cultists"][Role.RoleThrow] = 0;
MaxRoleArray["scenario.cultists"][Role.RoleUseless] = 10000;
if (false)
{
MaxRoleArray["scenario.cultists"] <- array(RoleNum, 0);
MaxRoleArray["scenario.cultists"][Role.RoleMelee] = 4;
MaxRoleArray["scenario.cultists"][Role.RoleGuard] = 2;
MaxRoleArray["scenario.cultists"][Role.RoleLeader] = 1;
MaxRoleArray["scenario.cultists"][Role.RolePolearm] = 2;
MaxRoleArray["scenario.cultists"][Role.RoleRange] = 1;
MaxRoleArray["scenario.cultists"][Role.RoleThrow] = 1;
MaxRoleArray["scenario.cultists"][Role.RoleUseless] = 10000;
}

## 搜捕者 搜捕星位固定 奴隶不固定
BroOutputConditionArray["scenario.manhunters"] <-
[
// [BroOutput.TeamScore, 0.60],

[BroOutput.AnyRoleScore, 0.70, 4],
[BroOutput.AnyRoleScore, 0.72, 3],
[BroOutput.AnyRoleScore, 0.75, 2],
[BroOutput.RoleScore, 0.80, 1, Role.RoleMelee],
[BroOutput.RoleScore, 0.80, 1, Role.RoleGuard],
[BroOutput.RoleScore, 0.75, 1, Role.RoleMelee, 0.75, 1, Role.RoleGuard ],

];
MaxRoleArray["scenario.manhunters"] <- array(RoleNum, 0);
MaxRoleArray["scenario.manhunters"][Role.RoleMelee] = 3;
MaxRoleArray["scenario.manhunters"][Role.RoleGuard] = 2;
MaxRoleArray["scenario.manhunters"][Role.RoleLeader] = 1;
MaxRoleArray["scenario.manhunters"][Role.RoleRange] = 1;
MaxRoleArray["scenario.manhunters"][Role.RoleThrow] = 1;
MaxRoleArray["scenario.manhunters"][Role.RoleUseless] = 10000;

## 野兽杀手 星位固定
BroOutputConditionArray["scenario.beast_hunters"] <-
[[BroOutput.TeamScore, 0.81],
];
MaxRoleArray["scenario.beast_hunters"] <- array(RoleNum, 0);
MaxRoleArray["scenario.beast_hunters"][Role.RoleMelee] = 3;
MaxRoleArray["scenario.beast_hunters"][Role.RoleGuard] = 1;
MaxRoleArray["scenario.beast_hunters"][Role.RoleLeader] = 1;
MaxRoleArray["scenario.beast_hunters"][Role.RoleRange] = 1;
MaxRoleArray["scenario.beast_hunters"][Role.RoleThrow] = 1;
MaxRoleArray["scenario.beast_hunters"][Role.RoleUseless] = 10000;

## 角斗士 星位固定
BroOutputConditionArray["scenario.gladiators"] <-
[
// [BroOutput.TeamScore, 0.94],

// [BroOutput.RoleScore, 0.85, 2, Role.RoleMelee],
[BroOutput.RoleTraitScoreIndex, 2, 0.95, Role.RoleDuel, "trait.huge", ""], # 蛇哥带巨人
[BroOutput.RoleTraitScoreIndex, 2, 0.88, Role.RoleDuel, "trait.brute", ""], # 蛇哥带粗暴
[BroOutput.RoleTraitScoreIndex, 0, 1.00, Role.RoleMelee, "trait.huge", ""], # 狮哥带巨人
[BroOutput.RoleTraitScoreIndex, 0, 0.98, Role.RoleMelee, "trait.brute", ""], # 狮哥带粗暴
];
MaxRoleArray["scenario.gladiators"] <- array(RoleNum, 0);
MaxRoleArray["scenario.gladiators"][Role.RoleMelee] = 3;
MaxRoleArray["scenario.gladiators"][Role.RoleGuard] = 1;
MaxRoleArray["scenario.gladiators"][Role.RoleDuel] = 1;
MaxRoleArray["scenario.gladiators"][Role.RoleLeader] = 1;

## 独狼 星位固定
BroOutputConditionArray["scenario.lone_wolf"] <-
[

// [BroOutput.RoleTraitScore, 1.10, 1, Role.RoleMelee, "", "trait.drunkard"], # 稳步酒鬼
[BroOutput.RoleScore, 1.20, 1, Role.RoleMelee], # 只要神吕布
[BroOutput.RoleTraitScore, 1.12, 1, Role.RoleMelee, "trait.huge", "trait.drunkard"], # 巨人酒鬼
// [BroOutput.RoleTraitScore, 1.10, 1, Role.RoleMelee, "trait.sure_footing", "trait.drunkard"], # 稳步酒鬼
// [BroOutput.RoleTraitScore, 1.13, 1, Role.RoleMelee, "trait.sure_footing", "trait.paranoid"], # 稳步多疑（双防）
// [BroOutput.RoleTraitScore, 1.08, 1, Role.RoleMelee, "trait.sure_footing", "trait.fearless"], # 稳步无畏
// [BroOutput.RoleTraitScore, 1.11, 1, Role.RoleMelee, "trait.sure_footing", "trait.iron_lungs"], # 稳步铁肺
// [BroOutput.RoleTraitScore, 1.12, 1, Role.RoleMelee, "trait.sure_footing", "trait.huge"], # 稳步巨人
// [BroOutput.RoleTraitScore, 1.12, 1, Role.RoleMelee, "trait.sure_footing", "trait.determined"], # 稳步毅然
// [BroOutput.RoleTraitScore, 1.14, 1, Role.RoleMelee, "trait.sure_footing", "trait.dexterous"], # 稳步灵巧
// [BroOutput.RoleTraitScore, 1.10, 1, Role.RoleMelee, "trait.drunkard", "trait.determined"], # 毅然酒鬼
// [BroOutput.RoleTraitScore, 1.10, 1, Role.RoleMelee, "trait.determined", "trait.drunkard"], # 毅然酒鬼
// [BroOutput.RoleTraitScore, 1.12, 1, Role.RoleMelee, "trait.determined", "trait.huge"], # 毅然巨人
// [BroOutput.RoleTraitScore, 1.10, 1, Role.RoleMelee, "trait.tough", "trait.strong"], # 强壮
];
MaxRoleArray["scenario.lone_wolf"] <- array(RoleNum, 0);
MaxRoleArray["scenario.lone_wolf"][Role.RoleMelee] = 1;
MaxRoleArray["scenario.lone_wolf"][Role.RoleUseless] = 10000;

## 通用预设
BroOutputConditionArray["common"] <-
[[BroOutput.TeamScore, 0.70],	# 满足队伍职业平均分大于0.70的

];
MaxRoleArray["common"] <- array(RoleNum, 0);
MaxRoleArray["common"][Role.RoleMelee] = 10000;  	# 不限制近战数量
MaxRoleArray["common"][Role.RoleRange] = 1;  		# 最多一个远程
MaxRoleArray["common"][Role.RoleGuard] = 2;  		# 最多两个盾卫
MaxRoleArray["common"][Role.RoleThrow] = 1;  		# 最多一个柄投
MaxRoleArray["common"][Role.RoleLeader] = 1; 		# 最多一个队长
MaxRoleArray["common"][Role.RoleDuel] = 1;   		# 最多一个轻甲决斗
MaxRoleArray["common"][Role.RolePolearm] = 2;   	# 最多两个长柄
MaxRoleArray["common"][Role.RoleUseless] = 10000; 	# 剩下都是废废
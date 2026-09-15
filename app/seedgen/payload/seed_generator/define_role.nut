local gt = this.getroottable();

# 职业宏定义
gt.SeedGenerator.Role <- {
    RoleMelee = 0,	# 近战
    RoleRange = 1,	# 远程
	RoleGuard = 2,	# 盾卫
	RoleThrow = 3,	# 柄投
	RoleLeader = 4,	# 队长
	RoleDuel = 5,	# 决斗
	RolePolearm = 6,# 长柄
	RoleInitiative = 7,# 主动
	RoleUseless = 8,# 废废，增加职业记得保持废废在最后一个
};

local Role = gt.SeedGenerator.Role;

gt.SeedGenerator.RoleName <- {}; # 职业名称，日志打印用

local RoleName = gt.SeedGenerator.RoleName;

RoleName[Role.RoleMelee] <- "Melee";
RoleName[Role.RoleRange] <- "Range";
RoleName[Role.RoleGuard] <- "Guard";
RoleName[Role.RoleThrow] <- "Throw";
RoleName[Role.RoleLeader] <- "Leader";
RoleName[Role.RoleDuel] <- "Duel";
RoleName[Role.RolePolearm] <- "Polearm";
RoleName[Role.RoleInitiative] <- "Initiative";
RoleName[Role.RoleUseless] <- "Useless";

gt.SeedGenerator.RoleNum <- Role.RoleUseless + 1; # 职业数量

::include("seed_generator/define_common");
::include("seed_generator/define_role");

local gt = this.getroottable();

local Role = gt.SeedGenerator.Role;
local RoleNum = gt.SeedGenerator.RoleNum;

local Attr = gt.SeedGenerator.Attr;
local AttrNum = gt.SeedGenerator.AttrNum;

# 职业打分
## 属性顺序			  	 			 血量  决心 疲劳 近战  远程 近防 远防 主动
gt.SeedGenerator.MinAttrValue <- 	 [70,  50,  110, 65,  60,  20, 30, 130];		# 11级0.0分属性，低于该值额外扣分
gt.SeedGenerator.MaxAttrValue <-  	 [110, 95,  150, 95,  95,  45, 55, 175];  		# 11级1.0分属性，高于该值额外加分
gt.SeedGenerator.MidInitAttrValue <- [55,  35,  95,  52,  37,  3,  3,  105];		# 1级初始平均属性
gt.SeedGenerator.InitAttrGain <- 0.10; # 初始值增益 一个初始60攻无星的角色近战分数要大于初始45攻三星的角色近战分数

gt.SeedGenerator.RoleScoreTable <- {}; # 职业打分占比表
local RoleScoreTable = gt.SeedGenerator.RoleScoreTable;
## 该表表示每个职业的打分属性占比，比如近战血量占比10%， 决心5%, 疲劳20%, 近战35%, 近防30%, 占比加起来需要等于100%否则分数有问题
## 属性顺序			 		              血量   决心   疲劳   近战    远程    近防   远防   主动
RoleScoreTable[Role.RoleMelee]       <- [0.10,  0.05,  0.20,  0.35,  0.00,  0.30,  0.00,  0.00]; # 近战
RoleScoreTable[Role.RoleRange]       <- [0.10,  0.05,  0.25,  0.00,  0.50,  0.00,  0.00,  0.10]; # 远程
RoleScoreTable[Role.RoleGuard]       <- [0.15,  0.15,  0.25,  0.10,  0.00,  0.40,  0.00,  0.00]; # 盾卫
RoleScoreTable[Role.RoleThrow]       <- [0.10,  0.05,  0.20,  0.30,  0.35,  0.00,  0.00,  0.00]; # 柄投
RoleScoreTable[Role.RoleLeader]      <- [0.10,  0.40,  0.25,  0.25,  0.00,  0.00,  0.00,  0.00]; # 队长
RoleScoreTable[Role.RoleDuel]        <- [0.10,  0.05,  0.10,  0.35,  0.00,  0.25,  0.00,  0.15]; # 决斗
RoleScoreTable[Role.RolePolearm]     <- [0.15,  0.05,  0.30,  0.40,  0.00,  0.10,  0.00,  0.00]; # 长柄
RoleScoreTable[Role.RoleInitiative]  <- [0.10,  0.05,  0.05,  0.30,  0.00,  0.30,  0.00,  0.30]; # 主动

gt.SeedGenerator.LowestScore <- 0.6; # 当一个角色的被分配到的职业的分数低于LowestScore时会被改为废废职业


# 特性打分表
gt.SeedGenerator.TraitScoreTable <- {};
local TraitScoreTable = gt.SeedGenerator.TraitScoreTable;

## 病弱
TraitScoreTable["trait.ailing"] <- array(2);
TraitScoreTable["trait.ailing"][0] = array(AttrNum, 0);
TraitScoreTable["trait.ailing"][1] = array(RoleNum, -0.01); # 对所有职业进行扣分

## 勇敢
TraitScoreTable["trait.brave"] <- array(2);
TraitScoreTable["trait.brave"][0] = array(AttrNum, 0);
TraitScoreTable["trait.brave"][0][Attr.Bravery] = 5; 	# 对属性进行修正
TraitScoreTable["trait.brave"][1] = array(RoleNum, 0);

## 哮喘
TraitScoreTable["trait.asthmatic"] <- array(2);
TraitScoreTable["trait.asthmatic"][0] = array(AttrNum, 0);
TraitScoreTable["trait.asthmatic"][1] = array(RoleNum, -0.05);
TraitScoreTable["trait.asthmatic"][1][Role.RoleRange] = -0.03; # 远程和柄投扣分少一点
TraitScoreTable["trait.asthmatic"][1][Role.RoleThrow] = -0.03;

## 流血
TraitScoreTable["trait.bleeder"] <- array(2);
TraitScoreTable["trait.bleeder"][0] = array(AttrNum, 0);
TraitScoreTable["trait.bleeder"][1] = array(RoleNum, -0.02);

## 嗜血
TraitScoreTable["trait.bloodthirsty"] <- array(2);
TraitScoreTable["trait.bloodthirsty"][0] = array(AttrNum, 0);
TraitScoreTable["trait.bloodthirsty"][1] = array(RoleNum, 0.03);

## 粗暴
TraitScoreTable["trait.brute"] <- array(2);
TraitScoreTable["trait.brute"][0] = array(AttrNum, 0);
TraitScoreTable["trait.brute"][0][Attr.MeleeSkill] = -5;
TraitScoreTable["trait.brute"][1] = array(RoleNum, 0.07);
TraitScoreTable["trait.brute"][1][Role.RoleRange] = 0.00;
TraitScoreTable["trait.brute"][1][Role.RoleThrow] = 0.03;
TraitScoreTable["trait.brute"][1][Role.RoleGuard] = 0.02;

## 畸足
TraitScoreTable["trait.clubfooted"] <- array(2);
TraitScoreTable["trait.clubfooted"][0] = array(AttrNum, 0);
TraitScoreTable["trait.clubfooted"][1] = array(RoleNum, -0.05);
TraitScoreTable["trait.clubfooted"][1][Role.RoleRange] = -0.02;
TraitScoreTable["trait.clubfooted"][1][Role.RoleThrow] = -0.03;

## 笨拙
TraitScoreTable["trait.clumsy"] <- array(2);
TraitScoreTable["trait.clumsy"][0] = array(AttrNum, 0);
TraitScoreTable["trait.clumsy"][0][Attr.MeleeSkill] = -5;
TraitScoreTable["trait.clumsy"][1] = array(RoleNum, 0);

## 自大
TraitScoreTable["trait.cocky"] <- array(2);
TraitScoreTable["trait.cocky"][0] = array(AttrNum, 0);
TraitScoreTable["trait.cocky"][0][Attr.Bravery] = 5;
TraitScoreTable["trait.cocky"][0][Attr.MeleeDefense] = -5;
TraitScoreTable["trait.cocky"][0][Attr.RangedDefense] = -5;
TraitScoreTable["trait.cocky"][1] = array(RoleNum, 0);

## 邪教徒
TraitScoreTable["trait.cultist_fanatic"] <- array(2);
TraitScoreTable["trait.cultist_fanatic"][0] = array(AttrNum, 0);
TraitScoreTable["trait.cultist_fanatic"][0][Attr.Bravery] = 5;
TraitScoreTable["trait.cultist_fanatic"][1] = array(RoleNum, 0.01);

## 死愿
TraitScoreTable["trait.deathwish"] <- array(2);
TraitScoreTable["trait.deathwish"][0] = array(AttrNum, 0);
TraitScoreTable["trait.deathwish"][1] = array(RoleNum, 0.02);

## 毅然
TraitScoreTable["trait.determined"] <- array(2);
TraitScoreTable["trait.determined"][0] = array(AttrNum, 0);
TraitScoreTable["trait.determined"][1] = array(RoleNum, 0.05);

## 灵巧
TraitScoreTable["trait.dexterous"] <- array(2);
TraitScoreTable["trait.dexterous"][0] = array(AttrNum, 0);
TraitScoreTable["trait.dexterous"][0][Attr.MeleeSkill] = 5;
TraitScoreTable["trait.dexterous"][1] = array(RoleNum, 0);

## 蠢笨
TraitScoreTable["trait.dumb"] <- array(2);
TraitScoreTable["trait.dumb"][0] = array(AttrNum, 0);
TraitScoreTable["trait.dumb"][1] = array(RoleNum, -0.05);

## 鹰眼
TraitScoreTable["trait.eagle_eyes"] <- array(2);
TraitScoreTable["trait.eagle_eyes"][0] = array(AttrNum, 0);
TraitScoreTable["trait.eagle_eyes"][1] = array(RoleNum, 0);
TraitScoreTable["trait.eagle_eyes"][1][Role.RoleRange] = 0.03;
TraitScoreTable["trait.eagle_eyes"][1][Role.RoleThrow] = 0.01;

## 害怕野兽
TraitScoreTable["trait.fear_beasts"] <- array(2);
TraitScoreTable["trait.fear_beasts"][0] = array(AttrNum, 0);
TraitScoreTable["trait.fear_beasts"][1] = array(RoleNum, -0.015);

## 害怕绿皮
TraitScoreTable["trait.fear_greenskins"] <- array(2);
TraitScoreTable["trait.fear_greenskins"][0] = array(AttrNum, 0);
TraitScoreTable["trait.fear_greenskins"][1] = array(RoleNum, -0.015);

## 害怕亡灵
TraitScoreTable["trait.fear_undead"] <- array(2);
TraitScoreTable["trait.fear_undead"][0] = array(AttrNum, 0);
TraitScoreTable["trait.fear_undead"][1] = array(RoleNum, -0.015);

## 憎恨野兽
TraitScoreTable["trait.hate_beasts"] <- array(2);
TraitScoreTable["trait.hate_beasts"][0] = array(AttrNum, 0);
TraitScoreTable["trait.hate_beasts"][1] = array(RoleNum, 0.015);

## 憎恨绿皮
TraitScoreTable["trait.hate_greenskins"] <- array(2);
TraitScoreTable["trait.hate_greenskins"][0] = array(AttrNum, 0);
TraitScoreTable["trait.hate_greenskins"][1] = array(RoleNum, 0.015);

## 憎恨亡灵
TraitScoreTable["trait.hate_undead"] <- array(2);
TraitScoreTable["trait.hate_undead"][0] = array(AttrNum, 0);
TraitScoreTable["trait.hate_undead"][1] = array(RoleNum, 0.015);

## 无畏
TraitScoreTable["trait.fearless"] <- array(2);
TraitScoreTable["trait.fearless"][0] = array(AttrNum, 0);
TraitScoreTable["trait.fearless"][0][Attr.Bravery] = 10;
TraitScoreTable["trait.fearless"][1] = array(RoleNum, 0);

## 脆弱
TraitScoreTable["trait.fragile"] <- array(2);
TraitScoreTable["trait.fragile"][0] = array(AttrNum, 0);
TraitScoreTable["trait.fragile"][0][Attr.Hitpoints] = -10;
TraitScoreTable["trait.fragile"][1] = array(RoleNum, 0);

## 巨人
TraitScoreTable["trait.huge"] <- array(2);
TraitScoreTable["trait.huge"][0] = array(AttrNum, 0);
TraitScoreTable["trait.huge"][0][Attr.MeleeDefense] = -5;
TraitScoreTable["trait.huge"][0][Attr.RangedDefense] = -5;
TraitScoreTable["trait.huge"][1] = array(RoleNum, 0.12);
TraitScoreTable["trait.huge"][1][Role.RoleGuard] = 0.05;
TraitScoreTable["trait.huge"][1][Role.RoleThrow] = 0.05;
TraitScoreTable["trait.huge"][1][Role.RoleRange] = -0.01;

## 急躁
TraitScoreTable["trait.impatient"] <- array(2);
TraitScoreTable["trait.impatient"][0] = array(AttrNum, 0);
TraitScoreTable["trait.impatient"][1] = array(RoleNum, 0.01);

## 铁下巴
TraitScoreTable["trait.iron_jaw"] <- array(2);
TraitScoreTable["trait.iron_jaw"][0] = array(AttrNum, 0);
TraitScoreTable["trait.iron_jaw"][1] = array(RoleNum, 0.03);

## 铁肺
TraitScoreTable["trait.iron_lungs"] <- array(2);
TraitScoreTable["trait.iron_lungs"][0] = array(AttrNum, 0);
TraitScoreTable["trait.iron_lungs"][1] = array(RoleNum, 0.05);
TraitScoreTable["trait.iron_lungs"][1][Role.RoleRange] = 0.03;
TraitScoreTable["trait.iron_lungs"][1][Role.RoleThrow] = 0.03;

## 无常
TraitScoreTable["trait.irrational"] <- array(2);
TraitScoreTable["trait.irrational"][0] = array(AttrNum, 0);
TraitScoreTable["trait.irrational"][1] = array(RoleNum, 0);

## 忠诚
TraitScoreTable["trait.loyal"] <- array(2);
TraitScoreTable["trait.loyal"][0] = array(AttrNum, 0);
TraitScoreTable["trait.loyal"][1] = array(RoleNum, 0.01);

## 不忠
TraitScoreTable["trait.disloyal"] <- array(2);
TraitScoreTable["trait.disloyal"][0] = array(AttrNum, 0);
TraitScoreTable["trait.disloyal"][1] = array(RoleNum, -0.01);

## 夜猫子
TraitScoreTable["trait.night_owl"] <- array(2);
TraitScoreTable["trait.night_owl"][0] = array(AttrNum, 0);
TraitScoreTable["trait.night_owl"][1] = array(RoleNum, 0.01);
TraitScoreTable["trait.night_owl"][1][Role.RoleRange] = 0.03;
TraitScoreTable["trait.night_owl"][1][Role.RoleThrow] = 0.02;

## 乐观
TraitScoreTable["trait.optimist"] <- array(2);
TraitScoreTable["trait.optimist"][0] = array(AttrNum, 0);
TraitScoreTable["trait.optimist"][1] = array(RoleNum, 0.02);

## 悲观
TraitScoreTable["trait.pessimist"] <- array(2);
TraitScoreTable["trait.pessimist"][0] = array(AttrNum, 0);
TraitScoreTable["trait.pessimist"][1] = array(RoleNum, -0.02);

## 多疑
TraitScoreTable["trait.paranoid"] <- array(2);
TraitScoreTable["trait.paranoid"][0] = array(AttrNum, 0);
TraitScoreTable["trait.paranoid"][0][Attr.MeleeDefense] = 5;
TraitScoreTable["trait.paranoid"][0][Attr.RangedDefense] = 5;
TraitScoreTable["trait.paranoid"][0][Attr.Initiative] = -30;
TraitScoreTable["trait.paranoid"][1] = array(RoleNum, 0);

## 迅捷
TraitScoreTable["trait.quick"] <- array(2);
TraitScoreTable["trait.quick"][0] = array(AttrNum, 0);
TraitScoreTable["trait.quick"][0][Attr.Initiative] = 10;
TraitScoreTable["trait.quick"][1] = array(RoleNum, 0);

## 近视
TraitScoreTable["trait.short_sighted"] <- array(2);
TraitScoreTable["trait.short_sighted"][0] = array(AttrNum, 0);
TraitScoreTable["trait.short_sighted"][1] = array(RoleNum, -0.01);
TraitScoreTable["trait.short_sighted"][1][Role.RoleRange] = -0.05;
TraitScoreTable["trait.short_sighted"][1][Role.RoleThrow] = -0.02;

## 斯巴达
TraitScoreTable["trait.spartan"] <- array(2);
TraitScoreTable["trait.spartan"][0] = array(AttrNum, 0);
TraitScoreTable["trait.spartan"][1] = array(RoleNum, 0.01);

## 强壮
TraitScoreTable["trait.strong"] <- array(2);
TraitScoreTable["trait.strong"][0] = array(AttrNum, 0);
TraitScoreTable["trait.strong"][0][Attr.Stamina] = 10;
TraitScoreTable["trait.strong"][1] = array(RoleNum, 0);

## 迷信
TraitScoreTable["trait.superstitious"] <- array(2);
TraitScoreTable["trait.superstitious"][0] = array(AttrNum, 0);
TraitScoreTable["trait.superstitious"][1] = array(RoleNum, -0.02);

## 稳步
TraitScoreTable["trait.sure_footing"] <- array(2);
TraitScoreTable["trait.sure_footing"][0] = array(AttrNum, 0);
TraitScoreTable["trait.sure_footing"][0][Attr.MeleeDefense] = 5;
TraitScoreTable["trait.sure_footing"][1] = array(RoleNum, 0);

## 幸存者
TraitScoreTable["trait.survivor"] <- array(2);
TraitScoreTable["trait.survivor"][0] = array(AttrNum, 0);
TraitScoreTable["trait.survivor"][1] = array(RoleNum, 0.02);

## 闪避
TraitScoreTable["trait.swift"] <- array(2);
TraitScoreTable["trait.swift"][0] = array(AttrNum, 0);
TraitScoreTable["trait.swift"][0][Attr.RangedDefense] = 5;
TraitScoreTable["trait.swift"][1] = array(RoleNum, 0);

## 矮小
TraitScoreTable["trait.tiny"] <- array(2);
TraitScoreTable["trait.tiny"][0] = array(AttrNum, 0);
TraitScoreTable["trait.tiny"][0][Attr.MeleeDefense] = 5;
TraitScoreTable["trait.tiny"][0][Attr.RangedDefense] = 5;
TraitScoreTable["trait.tiny"][1] = array(RoleNum, -0.15);
TraitScoreTable["trait.tiny"][1][Role.RoleRange] = 0.00;
TraitScoreTable["trait.tiny"][1][Role.RoleGuard] = -0.05;
TraitScoreTable["trait.tiny"][1][Role.RoleThrow] = -0.08;

## 坚韧
TraitScoreTable["trait.tough"] <- array(2);
TraitScoreTable["trait.tough"][0] = array(AttrNum, 0);
TraitScoreTable["trait.tough"][0][Attr.Hitpoints] = 10;
TraitScoreTable["trait.tough"][1] = array(RoleNum, 0);

## 肥胖
TraitScoreTable["trait.fat"] <- array(2);
TraitScoreTable["trait.fat"][0] = array(AttrNum, 0);
TraitScoreTable["trait.fat"][0][Attr.Hitpoints] = 10;
TraitScoreTable["trait.fat"][0][Attr.Stamina] = -10;
TraitScoreTable["trait.fat"][1] = array(RoleNum, 0);

## 鼹鼠
TraitScoreTable["trait.weasel"] <- array(2);
TraitScoreTable["trait.weasel"][0] = array(AttrNum, 0);
TraitScoreTable["trait.weasel"][1] = array(RoleNum, 0.01);

## 团队精神
TraitScoreTable["trait.teamplayer"] <- array(2);
TraitScoreTable["trait.teamplayer"][0] = array(AttrNum, 0);
TraitScoreTable["trait.teamplayer"][1] = array(RoleNum, 0.01);
TraitScoreTable["trait.teamplayer"][1][Role.RoleRange] = 0.02;
TraitScoreTable["trait.teamplayer"][1][Role.RoleThrow] = 0.015;

## 幸运
TraitScoreTable["trait.lucky"] <- array(2);
TraitScoreTable["trait.lucky"][0] = array(AttrNum, 0);
TraitScoreTable["trait.lucky"][1] = array(RoleNum, 0.02);

## 贪吃
TraitScoreTable["trait.gluttonous"] <- array(2);
TraitScoreTable["trait.gluttonous"][0] = array(AttrNum, 0);
TraitScoreTable["trait.gluttonous"][1] = array(RoleNum, -0.01);

## 矫健
TraitScoreTable["trait.athletic"] <- array(2);
TraitScoreTable["trait.athletic"][0] = array(AttrNum, 0);
TraitScoreTable["trait.athletic"][1] = array(RoleNum, 0.05);
TraitScoreTable["trait.athletic"][1][Role.RoleRange] = 0.02;
TraitScoreTable["trait.athletic"][1][Role.RoleThrow] = 0.03;

## 聪明
TraitScoreTable["trait.bright"] <- array(2);
TraitScoreTable["trait.bright"][0] = array(AttrNum, 0);
TraitScoreTable["trait.bright"][1] = array(RoleNum, 0.03);

## 迟疑
TraitScoreTable["trait.hesitant"] <- array(2);
TraitScoreTable["trait.hesitant"][0] = array(AttrNum, 0);
TraitScoreTable["trait.hesitant"][0][Attr.Initiative] = -10;
TraitScoreTable["trait.hesitant"][1] = array(RoleNum, 0);

## 贪婪
TraitScoreTable["trait.greedy"] <- array(2);
TraitScoreTable["trait.greedy"][0] = array(AttrNum, 0);
TraitScoreTable["trait.greedy"][1] = array(RoleNum, -0.015);

## 酒鬼
TraitScoreTable["trait.drunkard"] <- array(2);
TraitScoreTable["trait.drunkard"][0] = array(AttrNum, 0);
TraitScoreTable["trait.drunkard"][0][Attr.MeleeSkill] = -5;
TraitScoreTable["trait.drunkard"][0][Attr.RangedSkill] = -10;
TraitScoreTable["trait.drunkard"][0][Attr.Bravery] = 5;
TraitScoreTable["trait.drunkard"][1] = array(RoleNum, 0.10);
TraitScoreTable["trait.drunkard"][1][Role.RoleGuard] = 0.05;
TraitScoreTable["trait.drunkard"][1][Role.RoleRange] = -0.02;
TraitScoreTable["trait.drunkard"][1][Role.RoleThrow] = 0.05;

## 畏缩
TraitScoreTable["trait.dastard"] <- array(2);
TraitScoreTable["trait.dastard"][0] = array(AttrNum, 0);
TraitScoreTable["trait.dastard"][1] = array(RoleNum, -0.05);

## 不安
TraitScoreTable["trait.insecure"] <- array(2);
TraitScoreTable["trait.insecure"][0] = array(AttrNum, 0);
TraitScoreTable["trait.insecure"][1] = array(RoleNum, -0.02);

## 夜盲
TraitScoreTable["trait.night_blind"] <- array(2);
TraitScoreTable["trait.night_blind"][0] = array(AttrNum, 0);
TraitScoreTable["trait.night_blind"][1] = array(RoleNum, -0.01);
TraitScoreTable["trait.night_blind"][1][Role.RoleRange] = -0.05;
TraitScoreTable["trait.night_blind"][1][Role.RoleThrow] = -0.02;

## 懦弱
TraitScoreTable["trait.craven"] <- array(2);
TraitScoreTable["trait.craven"][0] = array(AttrNum, 0);
TraitScoreTable["trait.craven"][0][Attr.Bravery] = -10;
TraitScoreTable["trait.craven"][1] = array(RoleNum, 0);

## 胆小
TraitScoreTable["trait.fainthearted"] <- array(2);
TraitScoreTable["trait.fainthearted"][0] = array(AttrNum, 0);
TraitScoreTable["trait.fainthearted"][0][Attr.Bravery] = -5;
TraitScoreTable["trait.fainthearted"][1] = array(RoleNum, 0);

## 年迈
TraitScoreTable["trait.old"] <- array(2);
TraitScoreTable["trait.old"][0] = array(AttrNum, 0);
TraitScoreTable["trait.old"][0][Attr.Stamina] = -10;
TraitScoreTable["trait.old"][0][Attr.Initiative] = -10;
TraitScoreTable["trait.old"][0][Attr.Hitpoints] = -10;
TraitScoreTable["trait.old"][0][Attr.Bravery] = 10;
TraitScoreTable["trait.old"][1] = array(RoleNum, -0.01);
TraitScoreTable["trait.old"][1][Role.RoleRange] = -0.05;
TraitScoreTable["trait.old"][1][Role.RoleThrow] = -0.02;

## 玩家
TraitScoreTable["trait.player"] <- array(2);
TraitScoreTable["trait.player"][0] = array(AttrNum, 0);
TraitScoreTable["trait.player"][0][Attr.Bravery] = 10;
TraitScoreTable["trait.player"][1] = array(RoleNum, 0);

## 角斗士
TraitScoreTable["trait.arena_fighter"] <- array(2);
TraitScoreTable["trait.arena_fighter"][0] = array(AttrNum, 0);
TraitScoreTable["trait.arena_fighter"][0][Attr.Bravery] = 5;
TraitScoreTable["trait.arena_fighter"][1] = array(RoleNum, 0);

## 角斗士特殊荣耀
TraitScoreTable["trait.glorious"] <- array(2);
TraitScoreTable["trait.glorious"][0] = array(AttrNum, 0);
TraitScoreTable["trait.glorious"][1] = array(RoleNum, 0);
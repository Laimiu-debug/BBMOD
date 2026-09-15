
::include("seed_generator/define_lair");

// 红装属性
// RegularDamage = 0,		// 伤害
// ArmorDamageMult = 1,		// 破甲
// ChanceToHitHead = 2,		// 爆头几率
// DirectDamageAdd = 3,		// 穿甲
// StaminaModifier = 4,		// 疲劳
// ShieldDamage = 5,		// 破盾
// AmmoMax = 6,				// 弹药上限
// AdditionalAccuracy = 7,	// 额外命中
// FatigueOnSkillUse = 8,	// 技能疲劳
// MeleeDefense = 9,		// 近战防御
// RangedDefense = 10,		// 远程防御
// Condition = 11,			// 耐久

// 红装类型
// armor 	护甲
// helmet	头盔
// shield	护盾
// weapon 	武器
// one_hand 单手
// two_hand 双手
// range 	远程

local gt = this.getroottable();
local NamedAttr = gt.SeedGenerator.NamedAttr;
local NamedAttrNum = gt.SeedGenerator.NamedAttrNum;

gt.SeedGenerator.LairOutput <- {
	NamedNumber = 0, 	# 红装总数量满足要求
	NamedAttrValue = 1, # 红装满足对应属性和roll值
	NamedAttrValueBroOutput = 2, # 红装满足对应属性和roll值，同时满足对应的角色输出条件
	NamedAttrValueStrength = 3, # 红装满足对应属性和roll值和营地强度值 <=150 小营地 <=250 中营地 <=500 大营地
};

local LairOutput = gt.SeedGenerator.LairOutput;

## 输出条件 满足任一条件则会输出结果
gt.SeedGenerator.LairOutputConditionArray <- [
[LairOutput.NamedNumber, 40],

// [LairOutput.NamedAttrValue, "one_hand", 1, NamedAttr.RegularDamage, 0, NamedAttr.DirectDamageAdd, 0, "two_hand", 1, NamedAttr.RegularDamage, 0, NamedAttr.DirectDamageAdd, 0], #

// 新战团
// [LairOutput.NamedAttrValueBroOutput, 0, "weapon", 4, NamedAttr.RegularDamage, 0, NamedAttr.DirectDamageAdd, 0], #
// [LairOutput.NamedAttrValueBroOutput, 0, "weapon", 3, NamedAttr.RegularDamage, 25, NamedAttr.DirectDamageAdd, 25], #
// [LairOutput.NamedAttrValueBroOutput, 0, "weapon", 2, NamedAttr.RegularDamage, 50, NamedAttr.DirectDamageAdd, 50], #
// [LairOutput.NamedAttrValueBroOutput, 0, "weapon", 1, NamedAttr.RegularDamage, 75, NamedAttr.DirectDamageAdd, 75], #

// [LairOutput.NamedAttrValue, "weapon.named_javelin", 2, NamedAttr.RegularDamage, 0, NamedAttr.DirectDamageAdd, 0],
// [LairOutput.NamedAttrValue, "weapon.named_throwing_axe", 2, NamedAttr.RegularDamage, 0, NamedAttr.DirectDamageAdd, 0],
// [LairOutput.NamedAttrValue, "weapon.named_javelin", 1, NamedAttr.RegularDamage, 0, NamedAttr.DirectDamageAdd, 0,
// 										"weapon.named_throwing_axe", 1, NamedAttr.RegularDamage, 0, NamedAttr.DirectDamageAdd, 0],
// [LairOutput.NamedAttrValue, "weapon.named_javelin", 1, NamedAttr.RegularDamage, 75, NamedAttr.DirectDamageAdd, 75],

// 角斗士
// [LairOutput.NamedAttrValueBroOutput, 0, "weapon.named_fencing_sword", 1, NamedAttr.RegularDamage, 75, NamedAttr.DirectDamageAdd, 75], # 蛇哥带巨人，有一把伤穿刺剑
// [LairOutput.NamedAttrValueBroOutput, 0, "weapon.named_greatsword", 1, NamedAttr.RegularDamage, 75, NamedAttr.DirectDamageAdd, 75], # 蛇哥带巨人，有一把伤穿大剑
// [LairOutput.NamedAttrValueBroOutput, 0, "weapon.named_qatal_dagger", 1, NamedAttr.RegularDamage, 75, NamedAttr.DirectDamageAdd, 75], # 蛇哥带巨人，有一把伤穿南匕
// [LairOutput.NamedAttrValueBroOutput, 1, "weapon.named_greatsword", 1, NamedAttr.RegularDamage, 75, NamedAttr.ChanceToHitHead, 75], # 蛇哥带粗暴，有一把伤头大剑
// [LairOutput.NamedAttrValueBroOutput, 2, "weapon.named_greataxe", 1, NamedAttr.RegularDamage, 75, NamedAttr.DirectDamageAdd, 75], # 狮哥带巨人，有一把伤穿大斧
// [LairOutput.NamedAttrValueBroOutput, 2, "weapon.named_heavy_rusty_axe", 1, NamedAttr.RegularDamage, 75, NamedAttr.DirectDamageAdd, 75], # 狮哥带巨人，有一把伤穿大斧
// [LairOutput.NamedAttrValueBroOutput, 3, "weapon.named_greatsword", 1, NamedAttr.RegularDamage, 75, NamedAttr.ChanceToHitHead, 75], #狮哥带粗暴，有一把伤头大剑
// // [LairOutput.NamedAttrValueBroOutput, 2, "two_hand", 1, NamedAttr.RegularDamage, 75, NamedAttr.DirectDamageAdd, 75], # 狮哥带巨人，有一把伤穿双手

// 偷猎者
// [LairOutput.NamedAttrValue, "weapon.named_crossbow", 1, NamedAttr.RegularDamage, 75, NamedAttr.DirectDamageAdd, 75],
// [LairOutput.NamedAttrValue, "weapon.named_crossbow", 1, NamedAttr.RegularDamage, 75, NamedAttr.AdditionalAccuracy, 75],
// [LairOutput.NamedAttrValue, "weapon.named_warbow", 1, NamedAttr.RegularDamage, 75, NamedAttr.DirectDamageAdd, 75],
// [LairOutput.NamedAttrValue, "weapon.named_warbow", 1, NamedAttr.RegularDamage, 75, NamedAttr.AdditionalAccuracy, 75],
// [LairOutput.NamedAttrValue, "weapon.named_handgonne", 1, NamedAttr.RegularDamage, 75, NamedAttr.DirectDamageAdd, 75],
// [LairOutput.NamedAttrValue, "weapon.named_handgonne", 1, NamedAttr.RegularDamage, 75, NamedAttr.AdditionalAccuracy, 75],

// [LairOutput.NamedAttrValue, "weapon.named_javelin", 1, NamedAttr.RegularDamage, 75, NamedAttr.DirectDamageAdd, 75],
// [LairOutput.NamedAttrValue, "weapon.named_throwing_axe", 1, NamedAttr.RegularDamage, 75, NamedAttr.DirectDamageAdd, 75],
// [LairOutput.NamedAttrValue, "weapon.named_javelin", 1, NamedAttr.RegularDamage, 75, NamedAttr.AmmoMax, 75],
// [LairOutput.NamedAttrValue, "weapon.named_throwing_axe", 1, NamedAttr.RegularDamage, 75, NamedAttr.AmmoMax, 75],

// 独狼
// [LairOutput.NamedAttrValue, "weapon.named_greataxe", 1, NamedAttr.RegularDamage, 75, NamedAttr.DirectDamageAdd, 75], # 独狼斧
// [LairOutput.NamedAttrValue, "weapon.named_heavy_rusty_axe", 1, NamedAttr.RegularDamage, 75, NamedAttr.DirectDamageAdd, 75], # 独狼斧
// [LairOutput.NamedAttrValue, "weapon.named_orc_axe", 1, NamedAttr.RegularDamage, 50, NamedAttr.DirectDamageAdd, 50], #
// [LairOutput.NamedAttrValue, "one_hand", 1, NamedAttr.RegularDamage, 50, NamedAttr.DirectDamageAdd, 50], #
// [LairOutput.NamedAttrValue, "two_hand", 1, NamedAttr.RegularDamage, 50, NamedAttr.DirectDamageAdd, 50], #

// 民兵团
// [LairOutput.NamedAttrValueBroOutput, 0, "one_hand", 1, NamedAttr.RegularDamage, 75, NamedAttr.DirectDamageAdd, 75], #
// [LairOutput.NamedAttrValueBroOutput, 0, "two_hand", 1, NamedAttr.RegularDamage, 75, NamedAttr.DirectDamageAdd, 75], #

// [LairOutput.NamedAttrValueBroOutput, 1, "weapon.named_crossbow", 1, NamedAttr.RegularDamage, 75, NamedAttr.DirectDamageAdd, 75],
// [LairOutput.NamedAttrValueBroOutput, 1, "weapon.named_warbow", 1, NamedAttr.RegularDamage, 75, NamedAttr.DirectDamageAdd, 75],
// [LairOutput.NamedAttrValueBroOutput, 1, "weapon.named_warbow", 1, NamedAttr.RegularDamage, 75, NamedAttr.AdditionalAccuracy, 75],
// [LairOutput.NamedAttrValueBroOutput, 1, "weapon.named_warbow", 1, NamedAttr.DirectDamageAdd, 75, NamedAttr.AdditionalAccuracy, 75],
// [LairOutput.NamedAttrValueBroOutput, 1, "weapon.named_javelin", 1, NamedAttr.RegularDamage, 75, NamedAttr.DirectDamageAdd, 75],

// [LairOutput.NamedAttrValueBroOutput, 2, "weapon.named_fencing_sword", 1, NamedAttr.RegularDamage, 75, NamedAttr.DirectDamageAdd, 75],
// [LairOutput.NamedAttrValueBroOutput, 2, "weapon.named_qatal_dagger", 1, NamedAttr.RegularDamage, 75, NamedAttr.DirectDamageAdd, 75],
// [LairOutput.NamedAttrValueBroOutput, 2, "weapon.named_qatal_dagger", 1, NamedAttr.FatigueOnSkillUse, 75, NamedAttr.DirectDamageAdd, 75],
// [LairOutput.NamedAttrValueBroOutput, 2, "weapon.named_qatal_dagger", 1, NamedAttr.RegularDamage, 75, NamedAttr.FatigueOnSkillUse, 75],
// [LairOutput.NamedAttrValueStrength, 150, "weapon", 2, NamedAttr.RegularDamage, 75, NamedAttr.DirectDamageAdd, 75], # 小营地两件伤穿武器

// 解刨
// [LairOutput.NamedAttrValue, "weapon.named_two_handed_mace", 2, NamedAttr.RegularDamage, 0, NamedAttr.DirectDamageAdd, 0], #
// [LairOutput.NamedAttrValue, "two_hand", 2, NamedAttr.RegularDamage, 75, NamedAttr.DirectDamageAdd, 75], #
// [LairOutput.NamedAttrValue, "weapon", 1, NamedAttr.RegularDamage, 75, NamedAttr.DirectDamageAdd, 75], #
// [LairOutput.NamedAttrValue, "weapon.named_swordlance", 2, NamedAttr.RegularDamage, 0, NamedAttr.DirectDamageAdd, 0], #
// [LairOutput.NamedAttrValue, "weapon.named_warscythe", 2, NamedAttr.RegularDamage, 0, NamedAttr.DirectDamageAdd, 0], #
// [LairOutput.NamedAttrValue, "weapon.named_swordlance", 1, NamedAttr.RegularDamage, 0, NamedAttr.DirectDamageAdd, 0, "weapon.named_warscythe", 1, NamedAttr.RegularDamage, 0, NamedAttr.DirectDamageAdd, 0], #
// [LairOutput.NamedAttrValue, "weapon.named_orc_cleaver", 1, NamedAttr.RegularDamage, 75, NamedAttr.DirectDamageAdd, 75], # 4
// [LairOutput.NamedAttrValue, "weapon.named_cleaver", 1, NamedAttr.RegularDamage, 75, NamedAttr.DirectDamageAdd, 75], #
// [LairOutput.NamedAttrValue, "weapon.named_swordlance", 1, NamedAttr.RegularDamage, 75, NamedAttr.DirectDamageAdd, 75], # 6
// [LairOutput.NamedAttrValue, "weapon.named_warscythe", 1, NamedAttr.RegularDamage, 75, NamedAttr.DirectDamageAdd, 75], #
// [LairOutput.NamedAttrValue, "weapon", 4, NamedAttr.RegularDamage, 0, NamedAttr.DirectDamageAdd, 0], #　8
// [LairOutput.NamedAttrValue, "weapon", 3, NamedAttr.RegularDamage, 25, NamedAttr.DirectDamageAdd, 25], #
// [LairOutput.NamedAttrValue, "weapon", 2, NamedAttr.RegularDamage, 50, NamedAttr.DirectDamageAdd, 50], #

// 宣誓
// [LairOutput.NamedAttrValue, "weapon.named_fencing_sword", 1, NamedAttr.RegularDamage, 75, NamedAttr.DirectDamageAdd, 75], # 带巨人，有一把伤穿刺剑
// [LairOutput.NamedAttrValue, "weapon.named_greatsword", 1, NamedAttr.RegularDamage, 75, NamedAttr.DirectDamageAdd, 75], # 带巨人，有一把伤穿大剑
// [LairOutput.NamedAttrValue, "weapon.named_qatal_dagger", 1, NamedAttr.RegularDamage, 75, NamedAttr.DirectDamageAdd, 75], # 带巨人，有一把伤穿南匕
// [LairOutput.NamedAttrValue, "weapon.named_swordlance", 1, NamedAttr.RegularDamage, 75, NamedAttr.DirectDamageAdd, 75], # 带巨人，有一把伤穿刮刀
// [LairOutput.NamedAttrValue, "weapon.named_warscythe", 1, NamedAttr.RegularDamage, 75, NamedAttr.DirectDamageAdd, 75], # 带巨人，有一把伤穿刮刀
// [LairOutput.NamedAttrValue, "weapon", 4, NamedAttr.RegularDamage, 0, NamedAttr.DirectDamageAdd, 0], #　6
// [LairOutput.NamedAttrValue, "weapon", 3, NamedAttr.RegularDamage, 25, NamedAttr.DirectDamageAdd, 25], #
// [LairOutput.NamedAttrValue, "weapon", 2, NamedAttr.RegularDamage, 50, NamedAttr.DirectDamageAdd, 50], #

// 北方掠夺者
// [LairOutput.NamedAttrValue, "one_hand", 1, NamedAttr.RegularDamage, 75, NamedAttr.DirectDamageAdd, 75], #
// [LairOutput.NamedAttrValue, "two_hand", 1, NamedAttr.RegularDamage, 75, NamedAttr.DirectDamageAdd, 75], #

// 异教徒
// [LairOutput.NamedAttrValue, "weapon", 4, NamedAttr.RegularDamage, 0, NamedAttr.DirectDamageAdd, 0], #　
// [LairOutput.NamedAttrValue, "weapon", 3, NamedAttr.RegularDamage, 25, NamedAttr.DirectDamageAdd, 25], #
// [LairOutput.NamedAttrValue, "weapon", 2, NamedAttr.RegularDamage, 50, NamedAttr.DirectDamageAdd, 50], #
// [LairOutput.NamedAttrValue, "weapon", 1, NamedAttr.RegularDamage, 75, NamedAttr.DirectDamageAdd, 75], #

[LairOutput.NamedAttrValue, "weapon.named_greatsword", 1, NamedAttr.RegularDamage, 70, NamedAttr.DirectDamageAdd, 70],
[LairOutput.NamedAttrValue, "weapon.named_shamshir", 1, NamedAttr.RegularDamage, 70, NamedAttr.DirectDamageAdd, 70],
[LairOutput.NamedAttrValue, "weapon.named_sword", 1, NamedAttr.RegularDamage, 70, NamedAttr.DirectDamageAdd, 70],
];
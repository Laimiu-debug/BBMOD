::include("seed_generator/define_score");

local gt = this.getroottable();

local getTraitAttrAndScore;
local getTraitAttrAndScoreFast;

# 计算角色职业分数
gt.SeedGenerator.getBroScore <- function(bro)
{
	local bp = bro.getBaseProperties();
	local role_initattr_maxattr_score = array(3);
	role_initattr_maxattr_score[0] = array(AttrNum, 0);
	role_initattr_maxattr_score[1] = array(AttrNum, 0);
	role_initattr_maxattr_score[2] = array(RoleNum, 0);

	# 获取角色的特性属性修正和特性分数
	local trait_attr_score = getTraitAttrAndScore(bro);

	# 计算角色的开局属性（包括特性的属性）
	role_initattr_maxattr_score[0][Attr.Hitpoints] = bp.Hitpoints + trait_attr_score[0][Attr.Hitpoints];
	role_initattr_maxattr_score[0][Attr.Bravery] = bp.Bravery + trait_attr_score[0][Attr.Bravery];
	role_initattr_maxattr_score[0][Attr.Stamina] = bp.Stamina + trait_attr_score[0][Attr.Stamina];
	role_initattr_maxattr_score[0][Attr.MeleeSkill] = bp.MeleeSkill + trait_attr_score[0][Attr.MeleeSkill];
	role_initattr_maxattr_score[0][Attr.RangedSkill] = bp.RangedSkill + trait_attr_score[0][Attr.RangedSkill];
	role_initattr_maxattr_score[0][Attr.MeleeDefense] = bp.MeleeDefense + trait_attr_score[0][Attr.MeleeDefense];
	role_initattr_maxattr_score[0][Attr.RangedDefense] = bp.RangedDefense + trait_attr_score[0][Attr.RangedDefense];
	role_initattr_maxattr_score[0][Attr.Initiative] = bp.Initiative + trait_attr_score[0][Attr.Initiative];

	# 计算角色的11级属性
	local talents = bro.getTalents();
	role_initattr_maxattr_score[1][Attr.Hitpoints] = role_initattr_maxattr_score[0][Attr.Hitpoints] + NoStar[Attr.Hitpoints] + 5 * talents[this.Const.Attributes.Hitpoints];
	role_initattr_maxattr_score[1][Attr.Bravery] = role_initattr_maxattr_score[0][Attr.Bravery] + NoStar[Attr.Bravery] + 5 * talents[this.Const.Attributes.Bravery];
	role_initattr_maxattr_score[1][Attr.Stamina] = role_initattr_maxattr_score[0][Attr.Stamina] + NoStar[Attr.Stamina] + 5 * talents[this.Const.Attributes.Fatigue];
	role_initattr_maxattr_score[1][Attr.MeleeSkill] = role_initattr_maxattr_score[0][Attr.MeleeSkill] + NoStar[Attr.MeleeSkill] + 5 * talents[this.Const.Attributes.MeleeSkill];
	role_initattr_maxattr_score[1][Attr.RangedSkill] = role_initattr_maxattr_score[0][Attr.RangedSkill] + NoStar[Attr.RangedSkill] + 5 * talents[this.Const.Attributes.RangedSkill];
	role_initattr_maxattr_score[1][Attr.MeleeDefense] = role_initattr_maxattr_score[0][Attr.MeleeDefense] + NoStar[Attr.MeleeDefense] + 5 * talents[this.Const.Attributes.MeleeDefense];
	role_initattr_maxattr_score[1][Attr.RangedDefense] = role_initattr_maxattr_score[0][Attr.RangedDefense] + NoStar[Attr.RangedDefense] + 5 * talents[this.Const.Attributes.RangedDefense];
	role_initattr_maxattr_score[1][Attr.Initiative] = role_initattr_maxattr_score[0][Attr.Initiative] + NoStar[Attr.Initiative] + 5 * talents[this.Const.Attributes.Initiative];

	for(local i = 0; i < RoleNum - 1; i++)
	{
		role_initattr_maxattr_score[2][i] = 0.0;

		# 计算初始增益分数
		for (local j = 0; j < AttrNum; j++)
		{
			role_initattr_maxattr_score[2][i] += RoleScoreTable[i][j] * (role_initattr_maxattr_score[0][j] - MidInitAttrValue[j]) / (MaxAttrValue[j] - MinAttrValue[j]) * InitAttrGain;
		}

		# 计算11级分数
		for (local j = 0; j < AttrNum; j++)
		{
			role_initattr_maxattr_score[2][i] += RoleScoreTable[i][j] * (role_initattr_maxattr_score[1][j] - MinAttrValue[j]) / (MaxAttrValue[j] - MinAttrValue[j]);
		}

		# 计算特性分数
		role_initattr_maxattr_score[2][i] += trait_attr_score[1][i];
	}
	return role_initattr_maxattr_score;
}

gt.SeedGenerator.getBroScoreFast <- function(bro)
{
	local bp = bro["Attr"];
	local role_initattr_maxattr_score = array(3);
	role_initattr_maxattr_score[0] = array(AttrNum, 0);
	role_initattr_maxattr_score[1] = array(AttrNum, 0);
	role_initattr_maxattr_score[2] = array(RoleNum, 0);

	# 获取角色的特性属性修正和特性分数
	local trait_attr_score = getTraitAttrAndScoreFast(bro);

	# 计算角色的开局属性（包括特性的属性）
	role_initattr_maxattr_score[0][Attr.Hitpoints] = bp[Attr.Hitpoints] + trait_attr_score[0][Attr.Hitpoints];
	role_initattr_maxattr_score[0][Attr.Bravery] = bp[Attr.Bravery] + trait_attr_score[0][Attr.Bravery];
	role_initattr_maxattr_score[0][Attr.Stamina] = bp[Attr.Stamina] + trait_attr_score[0][Attr.Stamina];
	role_initattr_maxattr_score[0][Attr.MeleeSkill] = bp[Attr.MeleeSkill] + trait_attr_score[0][Attr.MeleeSkill];
	role_initattr_maxattr_score[0][Attr.RangedSkill] = bp[Attr.RangedSkill] + trait_attr_score[0][Attr.RangedSkill];
	role_initattr_maxattr_score[0][Attr.MeleeDefense] = bp[Attr.MeleeDefense] + trait_attr_score[0][Attr.MeleeDefense];
	role_initattr_maxattr_score[0][Attr.RangedDefense] = bp[Attr.RangedDefense] + trait_attr_score[0][Attr.RangedDefense];
	role_initattr_maxattr_score[0][Attr.Initiative] = bp[Attr.Initiative] + trait_attr_score[0][Attr.Initiative];

	# 计算角色的11级属性
	if(CommonConfig.UseBrotherLevel11RealAttr && "Level11TalentsAdd" in bro)
	{
		role_initattr_maxattr_score[1][Attr.Hitpoints] = role_initattr_maxattr_score[0][Attr.Hitpoints] + bro["Level11TalentsAdd"][Talents.Hitpoints];
		role_initattr_maxattr_score[1][Attr.Bravery] = role_initattr_maxattr_score[0][Attr.Bravery] + bro["Level11TalentsAdd"][Talents.Bravery];
		role_initattr_maxattr_score[1][Attr.Stamina] = role_initattr_maxattr_score[0][Attr.Stamina] + bro["Level11TalentsAdd"][Talents.Stamina];
		role_initattr_maxattr_score[1][Attr.MeleeSkill] = role_initattr_maxattr_score[0][Attr.MeleeSkill] + bro["Level11TalentsAdd"][Talents.MeleeSkill];
		role_initattr_maxattr_score[1][Attr.RangedSkill] = role_initattr_maxattr_score[0][Attr.RangedSkill] + bro["Level11TalentsAdd"][Talents.RangedSkill];
		role_initattr_maxattr_score[1][Attr.MeleeDefense] = role_initattr_maxattr_score[0][Attr.MeleeDefense] + bro["Level11TalentsAdd"][Talents.MeleeDefense];
		role_initattr_maxattr_score[1][Attr.RangedDefense] = role_initattr_maxattr_score[0][Attr.RangedDefense] + bro["Level11TalentsAdd"][Talents.RangedDefense];
		role_initattr_maxattr_score[1][Attr.Initiative] = role_initattr_maxattr_score[0][Attr.Initiative] + bro["Level11TalentsAdd"][Talents.Initiative];
	}
	else
	{
		local talents = bro["Talents"];
		role_initattr_maxattr_score[1][Attr.Hitpoints] = role_initattr_maxattr_score[0][Attr.Hitpoints] + NoStar[Attr.Hitpoints] + 5 * talents[this.Const.Attributes.Hitpoints];
		role_initattr_maxattr_score[1][Attr.Bravery] = role_initattr_maxattr_score[0][Attr.Bravery] + NoStar[Attr.Bravery] + 5 * talents[this.Const.Attributes.Bravery];
		role_initattr_maxattr_score[1][Attr.Stamina] = role_initattr_maxattr_score[0][Attr.Stamina] + NoStar[Attr.Stamina] + 5 * talents[this.Const.Attributes.Fatigue];
		role_initattr_maxattr_score[1][Attr.MeleeSkill] = role_initattr_maxattr_score[0][Attr.MeleeSkill] + NoStar[Attr.MeleeSkill] + 5 * talents[this.Const.Attributes.MeleeSkill];
		role_initattr_maxattr_score[1][Attr.RangedSkill] = role_initattr_maxattr_score[0][Attr.RangedSkill] + NoStar[Attr.RangedSkill] + 5 * talents[this.Const.Attributes.RangedSkill];
		role_initattr_maxattr_score[1][Attr.MeleeDefense] = role_initattr_maxattr_score[0][Attr.MeleeDefense] + NoStar[Attr.MeleeDefense] + 5 * talents[this.Const.Attributes.MeleeDefense];
		role_initattr_maxattr_score[1][Attr.RangedDefense] = role_initattr_maxattr_score[0][Attr.RangedDefense] + NoStar[Attr.RangedDefense] + 5 * talents[this.Const.Attributes.RangedDefense];
		role_initattr_maxattr_score[1][Attr.Initiative] = role_initattr_maxattr_score[0][Attr.Initiative] + NoStar[Attr.Initiative] + 5 * talents[this.Const.Attributes.Initiative];
	}

	for(local i = 0; i < RoleNum - 1; i++)
	{
		role_initattr_maxattr_score[2][i] = 0.0;

		# 计算初始增益分数
		for (local j = 0; j < AttrNum; j++)
		{
			role_initattr_maxattr_score[2][i] += RoleScoreTable[i][j] * (role_initattr_maxattr_score[0][j] - MidInitAttrValue[j]) / (MaxAttrValue[j] - MinAttrValue[j]) * InitAttrGain;
		}

		# 计算11级分数
		for (local j = 0; j < AttrNum; j++)
		{
			role_initattr_maxattr_score[2][i] += RoleScoreTable[i][j] * (role_initattr_maxattr_score[1][j] - MinAttrValue[j]) / (MaxAttrValue[j] - MinAttrValue[j]);
		}

		# 计算特性分数
		role_initattr_maxattr_score[2][i] += trait_attr_score[1][i];
	}
	return role_initattr_maxattr_score;
}


# 计算特性属性修正和分数
getTraitAttrAndScore = function(bro)
{
	local trait_attr_score = array(2);
	trait_attr_score[0] = array(AttrNum, 0);
	trait_attr_score[1] = array(RoleNum, 0);
	foreach(s in bro.m.Skills.m.Skills )
	{
		if (s.getType() == this.Const.SkillType.Trait)
		{
			if(s.getID() in TraitScoreTable)
			{
				for(local i = 0; i < AttrNum; i++)
				{
					trait_attr_score[0][i] += TraitScoreTable[s.getID()][0][i];
				}
				for(local i = 0; i < RoleNum; i++)
				{
					trait_attr_score[1][i] += TraitScoreTable[s.getID()][1][i];
				}
			}
			else
				this.logInfo("Unknown Traits: " + s.getID());
		}
	}
	return trait_attr_score;
}


getTraitAttrAndScoreFast = function(bro)
{
	local trait_attr_score = array(2);
	trait_attr_score[0] = array(AttrNum, 0);
	trait_attr_score[1] = array(RoleNum, 0);
	foreach(s in bro["Traits"] )
	{
		if(s in TraitScoreTable)
		{
			for(local i = 0; i < AttrNum; i++)
			{
				trait_attr_score[0][i] += TraitScoreTable[s][0][i];
			}
			for(local i = 0; i < RoleNum; i++)
			{
				trait_attr_score[1][i] += TraitScoreTable[s][1][i];
			}
		}
		else
			this.logInfo("Unknown Traits: " + s);
	}
	return trait_attr_score;
}

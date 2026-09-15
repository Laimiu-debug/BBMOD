::include("seed_generator/define_common");
::include("seed_generator/function_brother_output_check");

local gt = this.getroottable();
gt.SeedGenerator.LoopPrintInterval <- 1000;

local generateCultistsBrotherFast;
local generateMilitiaBrotherFast;
local generateLoneWolfBrotherFast;
local generateTraderBrotherFast;
local generateEarlyAccessBrotherFast;
local generateSouthernQuickstartBrotherFast;
local generateRangersBrotherFast;
local generatePaladinsBrotherFast;
local generateRaidersBrotherFast;
local generateAnatomistsBrotherFast;
local generateBeastHuntersBrotherFast;
local generateGladiatorBrotherFast;
local generateManhuntersBrotherFast;

local generateBrotherLevel11Attr;

local setStartValuesExFast;
local getTraitAttrAndScoreFast;

local trait_dict = {};

# 根据种子生成角色
gt.SeedGenerator.generateBrother <- function(seedString, world_state, disable_fast_mode = false)
{
	local origin = world_state.m.CampaignSettings.StartingScenario.getID();
	if(!disable_fast_mode && CommonConfig.FastBrotherGenerateMode && origin == "scenario.cultists")
	{
		gt.SeedGenerator.LoopPrintInterval = 10000;
		local bros =  generateCultistsBrotherFast(seedString);

		if(CommonConfig.UseBrotherLevel11RealAttr)
		{
			this.Math.rand(0, 1);
			generateBrotherLevel11Attr(bros);
		}
		return bros;
	}
	else if(!disable_fast_mode && CommonConfig.FastBrotherGenerateMode && origin == "scenario.militia")
	{
		gt.SeedGenerator.LoopPrintInterval = 5000;
		local bros =  generateMilitiaBrotherFast(seedString);
		if(CommonConfig.UseBrotherLevel11RealAttr)
		{
			for(local i = 0; i < 4; i++)
				this.Math.rand(0, 1);
			generateBrotherLevel11Attr(bros);
		}
		return bros;
	}
	else if(!disable_fast_mode && CommonConfig.FastBrotherGenerateMode && origin == "scenario.lone_wolf")
	{
		gt.SeedGenerator.LoopPrintInterval = 20000;
		local bros =  generateLoneWolfBrotherFast(seedString);
		if(CommonConfig.UseBrotherLevel11RealAttr)
		{
			this.Math.rand(0, 1);
			generateBrotherLevel11Attr(bros);
		}
		return bros;
	}
	else if(!disable_fast_mode && CommonConfig.FastBrotherGenerateMode && origin == "scenario.trader")
	{
		gt.SeedGenerator.LoopPrintInterval = 10000;
		local bros =  generateTraderBrotherFast(seedString);
		if(CommonConfig.UseBrotherLevel11RealAttr)
		{
			for(local i = 0; i < 8; i++)
				this.Math.rand(0, 1);
			generateBrotherLevel11Attr(bros);
		}
		return bros;
	}
	else if(!disable_fast_mode && CommonConfig.FastBrotherGenerateMode && origin == "scenario.early_access")
	{
		gt.SeedGenerator.LoopPrintInterval = 10000;
		local bros =  generateEarlyAccessBrotherFast(seedString);
		if(CommonConfig.UseBrotherLevel11RealAttr)
		{
			for(local i = 0; i < 2; i++)
				this.Math.rand(0, 1);
			generateBrotherLevel11Attr(bros);
		}
		return bros;
	}
	else if(!disable_fast_mode && CommonConfig.FastBrotherGenerateMode && origin == "scenario.southern_quickstart")
	{
		gt.SeedGenerator.LoopPrintInterval = 10000;
		local bros =  generateSouthernQuickstartBrotherFast(seedString);
		if(CommonConfig.UseBrotherLevel11RealAttr)
		{
			for(local i = 0; i < 2; i++)
				this.Math.rand(0, 1);
			generateBrotherLevel11Attr(bros);
		}
		return bros;
	}
	else if(!disable_fast_mode && CommonConfig.FastBrotherGenerateMode && origin == "scenario.rangers")
	{
		gt.SeedGenerator.LoopPrintInterval = 10000;
		local bros =  generateRangersBrotherFast(seedString);
		if(CommonConfig.UseBrotherLevel11RealAttr)
		{
			for(local i = 0; i < 2; i++)
				this.Math.rand(0, 1);
			generateBrotherLevel11Attr(bros);
		}
		return bros;
	}
	else if(!disable_fast_mode && CommonConfig.FastBrotherGenerateMode && origin == "scenario.paladins")
	{
		gt.SeedGenerator.LoopPrintInterval = 10000;
		local bros =  generatePaladinsBrotherFast(seedString);
		if(CommonConfig.UseBrotherLevel11RealAttr)
		{
			for(local i = 0; i < 1; i++)
				this.Math.rand(0, 1);
			generateBrotherLevel11Attr(bros);
		}
		return bros;
	}
	else if(!disable_fast_mode && CommonConfig.FastBrotherGenerateMode && origin == "scenario.raiders")
	{
		gt.SeedGenerator.LoopPrintInterval = 10000;
		local bros =  generateRaidersBrotherFast(seedString);
		if(CommonConfig.UseBrotherLevel11RealAttr)
		{
			for(local i = 0; i < 4; i++)
				this.Math.rand(0, 1);
			generateBrotherLevel11Attr(bros);
		}
		return bros;
	}
	else if(!disable_fast_mode && CommonConfig.FastBrotherGenerateMode && origin == "scenario.anatomists")
	{
		gt.SeedGenerator.LoopPrintInterval = 10000;
		local bros =  generateAnatomistsBrotherFast(seedString);
		if(CommonConfig.UseBrotherLevel11RealAttr)
		{
			for(local i = 0; i < 6; i++)
				this.Math.rand(0, 1);
			generateBrotherLevel11Attr(bros);
		}
		return bros;
	}
	else if(!disable_fast_mode && CommonConfig.FastBrotherGenerateMode && origin == "scenario.beast_hunters")
	{
		gt.SeedGenerator.LoopPrintInterval = 10000;
		local bros =  generateBeastHuntersBrotherFast(seedString);
		if(CommonConfig.UseBrotherLevel11RealAttr)
		{
			for(local i = 0; i < 4; i++)
				this.Math.rand(0, 1);
			generateBrotherLevel11Attr(bros);
		}
		return bros;
	}
	else if(!disable_fast_mode && CommonConfig.FastBrotherGenerateMode && origin == "scenario.gladiators")
	{
		gt.SeedGenerator.LoopPrintInterval = 10000;
		local bros =  generateGladiatorBrotherFast(seedString);
		if(CommonConfig.UseBrotherLevel11RealAttr)
		{
			for(local i = 0; i < 2; i++)
				this.Math.rand(0, 1);
			generateBrotherLevel11Attr(bros);
		}
		return bros;
	}
	else if(!disable_fast_mode && CommonConfig.FastBrotherGenerateMode && origin == "scenario.manhunters")
	{
		gt.SeedGenerator.LoopPrintInterval = 5000;
		local bros =  generateManhuntersBrotherFast(seedString);
		if(CommonConfig.UseBrotherLevel11RealAttr)
		{
			for(local i = 0; i < 4; i++)
				this.Math.rand(0, 1);
			generateBrotherLevel11Attr(bros);
		}
		return bros;
	}
	else
	{
		// this.World.Assets.getStash().clear();
		// this.World.Assets.getStash().resize(99);
		// world_state.m.Assets.init();
		// this.World.FactionManager.createFactions();
		// this.World.EntityManager.buildRoadAmbushSpots();

		this.Math.seedRandomString(seedString);

		if (world_state.m.CampaignSettings != null)
		{
			if(origin == "scenario.deserters")
			{
				this.World.Assets.getStash().clear();
				this.World.Assets.getStash().resize(99);
				this.World.clearScene();
				this.World.EntityManager.clear();
				this.World.FactionManager.clear();
				generateSettlement(seedString);
				this.Math.seedRandomString(seedString);
				world_state.m.Assets.setCampaignSettings(world_state.m.CampaignSettings);
				world_state.m.CampaignSettings.StartingScenario.onSpawnPlayer();
			}
			else
			{
				world_state.m.Assets.setCampaignSettings(world_state.m.CampaignSettings);
			}
			// world_state.m.CampaignSettings.StartingScenario.onInit();
			// this.World.uncoverFogOfWar(this.getPlayer().getTile().Pos, 900.0);
		}
		return null;
	}
	return null;
}

generateBrotherLevel11Attr = function(bros)
{
	foreach (bro in bros)
	{
		if(bros.len() == 1)
		{
			for(local i = 0; i < 5; i++)
				this.Math.rand(0, 1);
		}
		else
		{
			for(local i = 0; i < 6; i++)
				this.Math.rand(0, 1);
		}

		bro["Level11TalentsAdd"] <- array(TalentsNum, 0);
		for( local i = 0; i != TalentsNum; i = ++i )
		{
			for( local j = 0; j < 10; j = ++j )
			{
				bro["Level11TalentsAdd"][i] += this.Math.rand(this.Const.AttributesLevelUp[i].Min + (bro["Talents"][i] == 3 ? 2 : bro["Talents"][i]),
					this.Const.AttributesLevelUp[i].Max + (bro["Talents"][i] == 3 ? 1 : 0));
			}
		}
	}
}

generateCultistsBrotherFast = function(seedString)
{
	this.Math.seedRandomString(seedString);

	local bros = [];
	local names = [];
	for( local i = 0; i < 4; i = ++i )
	{
		local bro = {};
		bro["Name"] <- "";

		# 3
		for(local j = 0; j < 3; j++)
			this.Math.rand(0, 1);

		for(local j = 0; j < 1; j++)
			this.Math.rand(0, 1);

		while (names.find(bro["Name"]) != null)
		{
			bro["Name"] = this.Const.Strings.CharacterNames[this.Math.rand(0, this.Const.Strings.CharacterNames.len() - 1)]
		}
		names.push(bro["Name"]);
		bros.push(bro);
	}

	setStartValuesExFast(bros[0], bros.len(), ["cultist_background"]);
	for(local i = 0; i < 3; i++)
		this.Math.rand(0, 1);

	setStartValuesExFast(bros[1], bros.len(), ["cultist_background"]);
	for(local i = 0; i < 4; i++)
		this.Math.rand(0, 1);

	setStartValuesExFast(bros[2], bros.len(), ["cultist_background"]);
	for(local i = 0; i < 2; i++)
		this.Math.rand(0, 1);

	setStartValuesExFast(bros[3], bros.len(), ["cultist_background"]);
	for(local i = 0; i < 3; i++)
		this.Math.rand(0, 1);

	return bros;
}

generateMilitiaBrotherFast = function(seedString)
{
	this.Math.seedRandomString(seedString);

	local bros = [];
	local names = [];
	for( local i = 0; i < 12; i = ++i )
	{
		local bro = {};
		bro["Name"] <- "";
		for(local j = 0; j < 3; j++)
			this.Math.rand(0, 1);

		while (names.find(bro["Name"]) != null)
		{
			bro["Name"] = this.Const.Strings.CharacterNames[this.Math.rand(0, this.Const.Strings.CharacterNames.len() - 1)]
		}
		names.push(bro["Name"]);
		bros.push(bro);
	}

	setStartValuesExFast(bros[0], bros.len(), ["farmhand_background"]);
	for(local i = 0; i < 1; i++)
		this.Math.rand(0, 1);
	setStartValuesExFast(bros[1], bros.len(), ["farmhand_background"]);
	for(local i = 0; i < 1; i++)
		this.Math.rand(0, 1);
	for(local i = 0; i < 1; i++)
		this.Math.rand(0, 1);
	setStartValuesExFast(bros[2], bros.len(), ["poacher_background"]);
	for(local i = 0; i < 1; i++)
		this.Math.rand(0, 1);
	for(local i = 0; i < 1; i++)
		this.Math.rand(0, 1);
	setStartValuesExFast(bros[3], bros.len(), ["vagabond_background", "thief_background", "gambler_background"]);
	for(local i = 0; i < 1; i++)
		this.Math.rand(0, 1);
	setStartValuesExFast(bros[4], bros.len(), ["daytaler_background"]);
	for(local i = 0; i < 1; i++)
		this.Math.rand(0, 1);
	setStartValuesExFast(bros[5], bros.len(), ["miller_background"]);
	for(local i = 0; i < 1; i++)
		this.Math.rand(0, 1);
	setStartValuesExFast(bros[6], bros.len(), ["fisherman_background"]);
	setStartValuesExFast(bros[7], bros.len(), ["militia_background"]);
	setStartValuesExFast(bros[8], bros.len(), ["minstrel_background"]);
	for(local i = 0; i < 1; i++)
		this.Math.rand(0, 1);

	setStartValuesExFast(bros[9], bros.len(), ["daytaler_background"]);
	setStartValuesExFast(bros[10], bros.len(), ["militia_background"]);
	setStartValuesExFast(bros[11], bros.len(), ["butcher_background", "tailor_background", "shepherd_background"]);

	return bros;
}

generateLoneWolfBrotherFast = function(seedString)
{
	this.Math.seedRandomString(seedString);

	local bros = [];
	local bro = {};
	bro["Name"] <- "";
	for(local j = 0; j < 3; j++)
		this.Math.rand(0, 1);
	bros.push(bro);

	setStartValuesExFast(bros[0], bros.len(), ["hedge_knight_background"]);

	# after setStartValuesEx: +2 buildDescription(true) + +2 setTitle
	for(local j = 0; j < 14; j++)
		this.Math.rand(0, 1);

	for(local j = 0; j < 1; j++)
		this.Math.rand(0, 1);
	local index = null;
	index = bros[0]["Traits"].find("trait.survivor");
	if( index != null )
		bros[0]["Traits"].remove(index);
	index = bros[0]["Traits"].find("trait.greedy");
	if( index != null )
		bros[0]["Traits"].remove(index);
	index = bros[0]["Traits"].find("trait.loyal");
	if( index != null )
		bros[0]["Traits"].remove(index);
	index = bros[0]["Traits"].find("trait.disloyal");
	if( index != null )
		bros[0]["Traits"].remove(index);
	bros[0]["Traits"].push("trait.player");

	bros[0]["Attr"][Attr.MeleeDefense] -= 2;
	bros[0]["Talents"] = array(AttrNum, 0);
	bros[0]["Talents"][Talents.MeleeDefense] = 2;
	bros[0]["Talents"][Talents.Stamina] = 3;
	bros[0]["Talents"][Talents.MeleeSkill] = 3;

	{
		// fillAttributeLevelUpValues
		for( local i = 0; i != AttrNum; i = ++i )
		{
			for( local j = 0; j < 10; j = ++j )
			{
				this.Math.rand(this.Const.AttributesLevelUp[i].Min + (bro["Talents"][i] == 3 ? 2 : bros[0]["Talents"][i]),
					this.Const.AttributesLevelUp[i].Max + (bros[0]["Talents"][i] == 3 ? 1 : 0));
			}
		}
	}

	for(local j = 0; j < 4; j++)
			this.Math.rand(0, 1);
	return bros;
}

generateTraderBrotherFast = function(seedString)
{
	this.Math.seedRandomString(seedString);

	local bros = [];
	local names = [];
	for( local i = 0; i < 2; i = ++i )
	{
		local bro = {};
		bro["Name"] <- "";
		for(local j = 0; j < 3; j++)
			this.Math.rand(0, 1);

		while (names.find(bro["Name"]) != null)
		{
			bro["Name"] = this.Const.Strings.CharacterNames[this.Math.rand(0, this.Const.Strings.CharacterNames.len() - 1)]
		}
		names.push(bro["Name"]);
		bros.push(bro);
	}

	setStartValuesExFast(bros[0], bros.len(), ["caravan_hand_background"]);
	bros[0]["Talents"] = array(AttrNum, 0);
	bros[0]["Talents"][Talents.MeleeSkill] = 2;
	bros[0]["Talents"][Talents.MeleeDefense] = 1;
	bros[0]["Talents"][Talents.Stamina] = 1;


	setStartValuesExFast(bros[1], bros.len(), ["caravan_hand_background"]);
	bros[1]["Talents"] = array(AttrNum, 0);
	bros[1]["Talents"][Talents.MeleeSkill] = 2;
	bros[1]["Talents"][Talents.MeleeDefense] = 1;
	bros[1]["Talents"][Talents.Hitpoints] = 1;
	for(local j = 0; j < 1; j++)
		this.Math.rand(0, 1);
	return bros;
}

generateEarlyAccessBrotherFast = function(seedString)
{
	this.Math.seedRandomString(seedString);

	local bros = [];
	local names = [];
	for( local i = 0; i < 3; i = ++i )
	{
		local bro = {};
		bro["Name"] <- "";
		for(local j = 0; j < 3; j++)
			this.Math.rand(0, 1);

		while (names.find(bro["Name"]) != null)
		{
			bro["Name"] = this.Const.Strings.CharacterNames[this.Math.rand(0, this.Const.Strings.CharacterNames.len() - 1)]
		}
		names.push(bro["Name"]);
		bros.push(bro);
	}

	bros[0]["Talents"] <- array(AttrNum, 0);
	bros[0]["Talents"][Talents.Hitpoints] = 2;
	bros[0]["Talents"][Talents.Stamina] = 1;
	bros[0]["Talents"][Talents.Bravery] = 1;
	setStartValuesExFast(bros[0], bros.len(), ["companion_1h_background"], true, "1h");


	bros[1]["Talents"] <- array(AttrNum, 0);
	bros[1]["Talents"][Talents.MeleeSkill] = 2;
	bros[1]["Talents"][Talents.MeleeDefense] = 1;
	bros[1]["Talents"][Talents.Bravery] = 1;
	setStartValuesExFast(bros[1], bros.len(), ["companion_2h_background"], true, "2h");

	bros[2]["Talents"] <- array(AttrNum, 0);
	bros[2]["Talents"][Talents.RangedSkill] = 2;
	bros[2]["Talents"][Talents.RangedDefense] = 1;
	bros[2]["Talents"][Talents.Initiative] = 1;
	setStartValuesExFast(bros[2], bros.len(), ["companion_ranged_background"], true, "ranged");
	return bros;
}


generateSouthernQuickstartBrotherFast = function(seedString)
{
	this.Math.seedRandomString(seedString);

	local bros = [];
	local names = [];
	for( local i = 0; i < 3; i = ++i )
	{
		local bro = {};
		bro["Name"] <- "";
		for(local j = 0; j < 3; j++)
			this.Math.rand(0, 1);

		while (names.find(bro["Name"]) != null)
		{
			bro["Name"] = this.Const.Strings.CharacterNames[this.Math.rand(0, this.Const.Strings.CharacterNames.len() - 1)]
		}
		names.push(bro["Name"]);
		bros.push(bro);
	}

	bros[0]["Talents"] <- array(AttrNum, 0);
	bros[0]["Talents"][Talents.Hitpoints] = 2;
	bros[0]["Talents"][Talents.Stamina] = 1;
	bros[0]["Talents"][Talents.Bravery] = 1;
	setStartValuesExFast(bros[0], bros.len(), ["companion_1h_southern_background"], true, "1hs");


	bros[1]["Talents"] <- array(AttrNum, 0);
	bros[1]["Talents"][Talents.MeleeSkill] = 2;
	bros[1]["Talents"][Talents.MeleeDefense] = 1;
	bros[1]["Talents"][Talents.Bravery] = 1;
	setStartValuesExFast(bros[1], bros.len(), ["companion_2h_southern_background"], true, "2hs");

	bros[2]["Talents"] <- array(AttrNum, 0);
	bros[2]["Talents"][Talents.RangedSkill] = 2;
	bros[2]["Talents"][Talents.RangedDefense] = 1;
	bros[2]["Talents"][Talents.Initiative] = 1;
	setStartValuesExFast(bros[2], bros.len(), ["companion_ranged_southern_background"], true, "rangeds");
	return bros;
}

generateRangersBrotherFast = function(seedString)
{
	this.Math.seedRandomString(seedString);

	local bros = [];
	local names = [];
	for( local i = 0; i < 3; i = ++i )
	{
		local bro = {};
		bro["Name"] <- "";
		for(local j = 0; j < 3; j++)
			this.Math.rand(0, 1);

		while (names.find(bro["Name"]) != null)
		{
			bro["Name"] = this.Const.Strings.CharacterNames[this.Math.rand(0, this.Const.Strings.CharacterNames.len() - 1)]
		}
		names.push(bro["Name"]);
		bros.push(bro);
	}

	setStartValuesExFast(bros[0], bros.len(), ["hunter_background"]);
	bros[0]["Talents"] = array(AttrNum, 0);
	bros[0]["Talents"][Talents.RangedSkill] = 2;
	bros[0]["Talents"][Talents.RangedDefense] = 1;
	bros[0]["Talents"][Talents.Initiative] = 1;

	setStartValuesExFast(bros[1], bros.len(), ["poacher_background"]);
	bros[1]["Talents"] = array(AttrNum, 0);
	bros[1]["Talents"][Talents.RangedSkill] = 2;
	bros[1]["Talents"][Talents.Stamina] = 1;
	bros[1]["Talents"][Talents.Initiative] = 1;
	for(local j = 0; j < 1; j++)
			this.Math.rand(0, 1);

	setStartValuesExFast(bros[2], bros.len(), ["poacher_background"]);
	bros[2]["Talents"] = array(AttrNum, 0);
	bros[2]["Talents"][Talents.RangedSkill] = 2;
	bros[2]["Talents"][Talents.Bravery] = 1;
	bros[2]["Talents"][Talents.Initiative] = 1;
	for(local j = 0; j < 1; j++)
			this.Math.rand(0, 1);
	return bros;
}

generatePaladinsBrotherFast = function(seedString)
{
	this.Math.seedRandomString(seedString);

	local bros = [];
	local names = [];
	for( local i = 0; i < 2; i = ++i )
	{
		local bro = {};
		bro["Name"] <- "";
		for(local j = 0; j < 3; j++)
			this.Math.rand(0, 1);
		bros.push(bro);
	}

	setStartValuesExFast(bros[0], bros.len(), ["old_paladin_background"], false, "old");
	bros[0]["Traits"].push("trait.old");
	bros[0]["Talents"] = array(AttrNum, 0);
	bros[0]["Talents"][Talents.Bravery] = 3;
	bros[0]["Talents"][Talents.MeleeSkill] = 1;
	bros[0]["Talents"][Talents.RangedDefense] = 2;
	for(local j = 0; j < 5; j++)
		this.Math.rand(0, 1);

	setStartValuesExFast(bros[1], bros.len(), ["paladin_background"]);
	bros[1]["Talents"] = array(AttrNum, 0);
	bros[1]["Talents"][Talents.Initiative] = 3;
	bros[1]["Talents"][Talents.MeleeSkill] = 2;
	bros[1]["Talents"][Talents.MeleeDefense] = 1;
	for(local j = 0; j < 5; j++)
		this.Math.rand(0, 1);
	return bros;
}

generateRaidersBrotherFast = function(seedString)
{
	this.Math.seedRandomString(seedString);

	local bros = [];
	local names = [];
	for( local i = 0; i < 4; i = ++i )
	{
		local bro = {};
		bro["Name"] <- "";
		for(local j = 0; j < 3; j++)
			this.Math.rand(0, 1);
		bros.push(bro);
	}

	setStartValuesExFast(bros[0], bros.len(), ["barbarian_background"]);
	bros[0]["Talents"] = array(AttrNum, 0);
	bros[0]["Talents"][Talents.MeleeSkill] = 2;
	bros[0]["Talents"][Talents.Hitpoints] = 2;
	bros[0]["Talents"][Talents.Stamina] = 1;
	for(local j = 0; j < 5; j++)
		this.Math.rand(0, 1);

	setStartValuesExFast(bros[1], bros.len(), ["barbarian_background"]);
	bros[1]["Talents"] = array(AttrNum, 0);
	bros[1]["Talents"][Talents.MeleeSkill] = 2;
	bros[1]["Talents"][Talents.Hitpoints] = 1;
	bros[1]["Talents"][Talents.Stamina] = 2;
	for(local j = 0; j < 3; j++)
		this.Math.rand(0, 1);

	setStartValuesExFast(bros[2], bros.len(), ["barbarian_background"]);
	bros[2]["Talents"] = array(AttrNum, 0);
	bros[2]["Talents"][Talents.MeleeSkill] = 1;
	bros[2]["Talents"][Talents.MeleeDefense] = 2;
	bros[2]["Talents"][Talents.Hitpoints] = 2;
	for(local j = 0; j < 2; j++)
		this.Math.rand(0, 1);

	setStartValuesExFast(bros[3], bros.len(), ["monk_background"]);
	bros[3]["Talents"] = array(AttrNum, 0);
	bros[3]["Talents"][Talents.Bravery] = 3;
	return bros;
}

generateAnatomistsBrotherFast = function(seedString)

{
	this.Math.seedRandomString(seedString);

	local bros = [];
	local names = [];
	for( local i = 0; i < 3; i = ++i )
	{
		local bro = {};
		bro["Name"] <- "";
		for(local j = 0; j < 3; j++)
			this.Math.rand(0, 1);
		bros.push(bro);
	}

	setStartValuesExFast(bros[0], bros.len(), ["anatomist_background"]);
	bros[0]["Talents"] = array(AttrNum, 0);
	bros[0]["Talents"][Talents.Bravery] = 1;
	bros[0]["Talents"][Talents.MeleeSkill] = 2;
	bros[0]["Talents"][Talents.RangedSkill] = 2;
	for(local j = 0; j < 2; j++)
		this.Math.rand(0, 1);

	setStartValuesExFast(bros[1], bros.len(), ["anatomist_background"]);
	bros[1]["Talents"] = array(AttrNum, 0);
	bros[1]["Talents"][Talents.Hitpoints] = 2;
	bros[1]["Talents"][Talents.Initiative] = 3;
	bros[1]["Talents"][Talents.MeleeSkill] = 1;
	for(local j = 0; j < 3; j++)
		this.Math.rand(0, 1);

	setStartValuesExFast(bros[2], bros.len(), ["anatomist_background"]);
	bros[2]["Talents"] = array(AttrNum, 0);
	bros[2]["Talents"][Talents.Bravery] = 2;
	bros[2]["Talents"][Talents.MeleeDefense] = 3;
	bros[2]["Talents"][Talents.RangedDefense] = 3;
	for(local j = 0; j < 3; j++)
		this.Math.rand(0, 1);
	return bros;
}

generateBeastHuntersBrotherFast = function(seedString)
{
	this.Math.seedRandomString(seedString);

	local bros = [];
	local names = [];
	for( local i = 0; i < 3; i = ++i )
	{
		local bro = {};
		bro["Name"] <- "";
		for(local j = 0; j < 3; j++)
			this.Math.rand(0, 1);
		while (names.find(bro["Name"]) != null)
		{
			bro["Name"] = this.Const.Strings.CharacterNames[this.Math.rand(0, this.Const.Strings.CharacterNames.len() - 1)]
		}
		names.push(bro["Name"]);
		bros.push(bro);
	}

	setStartValuesExFast(bros[0], bros.len(), ["beast_hunter_background"]);
	this.Math.rand(0, 1);
	bros[0]["Talents"] = array(AttrNum, 0);
	bros[0]["Talents"][Talents.MeleeSkill] = 2;
	bros[0]["Talents"][Talents.MeleeDefense] = 1;
	bros[0]["Talents"][Talents.Stamina] = 1;
	for(local j = 0; j < 2; j++)
		this.Math.rand(0, 1);

	setStartValuesExFast(bros[1], bros.len(), ["beast_hunter_background"]);
	this.Math.rand(0, 1);
	bros[1]["Talents"] = array(AttrNum, 0);
	bros[1]["Talents"][Talents.Stamina] = 2;
	bros[1]["Talents"][Talents.MeleeSkill] = 1;
	bros[1]["Talents"][Talents.Bravery] = 1;
	for(local j = 0; j < 1; j++)
		this.Math.rand(0, 1);

	setStartValuesExFast(bros[2], bros.len(), ["beast_hunter_background"]);
	for(local j = 0; j < 2; j++)
		this.Math.rand(0, 1);
	bros[2]["Talents"] = array(AttrNum, 0);
	bros[2]["Talents"][Talents.RangedSkill] = 2;
	bros[2]["Talents"][Talents.RangedDefense] = 1;
	bros[2]["Talents"][Talents.Stamina] = 1;
	for(local j = 0; j < 4; j++)
		this.Math.rand(0, 1);
	return bros;
}

generateGladiatorBrotherFast = function(seedString)
{
	this.Math.seedRandomString(seedString);

	local bros = [];
	local names = [];
	for( local i = 0; i < 3; i = ++i )
	{
		local bro = {};
		bro["Name"] <- "";
		for(local j = 0; j < 3; j++)
			this.Math.rand(0, 1);
		bros.push(bro);
		setStartValuesExFast(bros[i], bros.len(), ["gladiator_origin_background"], false, "_origin");
		local index = null;
		index = bros[i]["Traits"].find("trait.survivor");
		if( index != null )
			bros[i]["Traits"].remove(index);
		index = bros[i]["Traits"].find("trait.greedy");
		if( index != null )
			bros[i]["Traits"].remove(index);
		index = bros[i]["Traits"].find("trait.loyal");
		if( index != null )
			bros[i]["Traits"].remove(index);
		index = bros[i]["Traits"].find("trait.disloyal");
		if( index != null )
			bros[i]["Traits"].remove(index);
		bros[i]["Traits"].push("trait.arena_fighter");
		this.Math.rand(0, 1);
	}

	bros[0]["Talents"] = array(AttrNum, 0);
	bros[0]["Talents"][Talents.MeleeDefense] = 2;
	bros[0]["Talents"][Talents.Stamina] = 2;
	bros[0]["Talents"][Talents.MeleeSkill] = 3;
	for(local j = 0; j < 7; j++)
		this.Math.rand(0, 1);
	for(local j = 0; j < 60; j++)
		this.Math.rand(0, 1);
	for(local j = 0; j < 6; j++)
		this.Math.rand(0, 1);

	bros[1]["Talents"] = array(AttrNum, 0);
	bros[1]["Talents"][Talents.Hitpoints] = 3;
	bros[1]["Talents"][Talents.Stamina] = 2;
	bros[1]["Talents"][Talents.Bravery] = 2;
	for(local j = 0; j < 7; j++)
		this.Math.rand(0, 1);
	for(local j = 0; j < 60; j++)
		this.Math.rand(0, 1);
	for(local j = 0; j < 7; j++)
		this.Math.rand(0, 1);

	bros[2]["Talents"] = array(AttrNum, 0);
	bros[2]["Talents"][Talents.MeleeDefense] = 2;
	bros[2]["Talents"][Talents.Initiative] = 3;
	bros[2]["Talents"][Talents.MeleeSkill] = 2;
	for(local j = 0; j < 7; j++)
		this.Math.rand(0, 1);
	for(local j = 0; j < 60; j++)
		this.Math.rand(0, 1);
	for(local j = 0; j < 6; j++)
		this.Math.rand(0, 1);

	for(local j = 0; j < 18; j++)
		this.Math.rand(0, 1);
	return bros;
}

generateManhuntersBrotherFast = function(seedString)
{
	this.Math.seedRandomString(seedString);

	local bros = [];
	local names = [];
	for( local i = 0; i < 6; i = ++i )
	{
		local bro = {};
		bro["Name"] <- "";
		for(local j = 0; j < 3; j++)
			this.Math.rand(0, 1);
		bros.push(bro);
	}

	setStartValuesExFast(bros[0], bros.len(), ["manhunter_background"]);
	bros[0]["Talents"] = array(AttrNum, 0);
	bros[0]["Talents"][Talents.MeleeSkill] = 1;
	bros[0]["Talents"][Talents.Bravery] = 2;
	bros[0]["Talents"][Talents.RangedDefense] = 1;
	bros[0]["Traits"].clear();
	for(local j = 0; j < 9; j++)
		this.Math.rand(0, 1);

	setStartValuesExFast(bros[1], bros.len(), ["manhunter_background"]);
	bros[1]["Talents"] = array(AttrNum, 0);
	bros[1]["Talents"][Talents.Stamina] = 2;
	bros[1]["Talents"][Talents.MeleeSkill] = 1;
	bros[1]["Talents"][Talents.Hitpoints] = 1;
	for(local j = 0; j < 11; j++)
		this.Math.rand(0, 1);

	setStartValuesExFast(bros[2], bros.len(), ["slave_southern_background"]);
	local index = null;
	index = bros[2]["Traits"].find("trait.dumb");
	if( index != null )
		bros[2]["Traits"].remove(index);
	index = bros[2]["Traits"].find("trait.bright");
	if( index == null )
		bros[2]["Traits"].push("trait.bright");
	for(local j = 0; j < 12; j++)
		this.Math.rand(0, 1);

	setStartValuesExFast(bros[3], bros.len(), ["slave_background"]);
	for(local j = 0; j < 9; j++)
		this.Math.rand(0, 1);

	setStartValuesExFast(bros[4], bros.len(), ["slave_southern_background"]);
	for(local j = 0; j < 9; j++)
		this.Math.rand(0, 1);

	setStartValuesExFast(bros[5], bros.len(), ["slave_southern_background"]);
	for(local j = 0; j < 9; j++)
		this.Math.rand(0, 1);

	return bros;
}

setStartValuesExFast = function(bro, bros_len, backgrounds, is_untalented = false, background_id_sign = "")
{
	# 1.5.2.3 buildDescription 新增 randomvizier 名字模板，每次调用固定多消耗2次rand，故6->8、5->7
	local build_description_i = 8;
	if(bros_len == 1)
		build_description_i = 7;
	local background = this.new("scripts/skills/backgrounds/" + backgrounds[this.Math.rand(0, backgrounds.len() - 1)]);
	local background_id = background.m.ID + background_id_sign;

	local a = {
		Hitpoints = [
			50,
			60
		],
		Bravery = [
			30,
			40
		],
		Stamina = [
			90,
			100
		],
		MeleeSkill = [
			47,
			57
		],
		RangedSkill = [
			32,
			42
		],
		MeleeDefense = [
			0,
			5
		],
		RangedDefense = [
			0,
			5
		],
		Initiative = [
			100,
			110
		]
	};

	local c = background.onChangeAttributes();
	a.Hitpoints[0] += c.Hitpoints[0];
	a.Hitpoints[1] += c.Hitpoints[1];
	a.Bravery[0] += c.Bravery[0];
	a.Bravery[1] += c.Bravery[1];
	a.Stamina[0] += c.Stamina[0];
	a.Stamina[1] += c.Stamina[1];
	a.MeleeSkill[0] += c.MeleeSkill[0];
	a.MeleeSkill[1] += c.MeleeSkill[1];
	a.MeleeDefense[0] += c.MeleeDefense[0];
	a.MeleeDefense[1] += c.MeleeDefense[1];
	a.RangedSkill[0] += c.RangedSkill[0];
	a.RangedSkill[1] += c.RangedSkill[1];
	a.RangedDefense[0] += c.RangedDefense[0];
	a.RangedDefense[1] += c.RangedDefense[1];
	a.Initiative[0] += c.Initiative[0];
	a.Initiative[1] += c.Initiative[1];

	local title_flag = false;

	{
		// before setTitle -> if onAdded need more rand
		if(background_id == "background.barbarian")
		{
			bro["Name"] = this.Math.rand(0, this.Const.Strings.BarbarianNames.len() - 1);
		}

		if (!title_flag && background.m.LastNames.len() != 0 && this.Math.rand(0, 1) == 1)
		{
			this.Math.rand(0, background.m.LastNames.len() - 1);
			title_flag = true;
			// buildDescription if bro == 1 i = 5 else i = 6
			for(local i = 0; i < build_description_i; i++)
				this.Math.rand(0, 1);
		}

		if (!title_flag && background.m.Titles.len() != 0 && this.Math.rand(0, 3) == 3)
		{
			this.Math.rand(0, background.m.Titles.len() - 1);
			title_flag = true;
			// buildDescription if bro == 1 i = 5 else i = 6
			for(local i = 0; i < build_description_i; i++)
				this.Math.rand(0, 1);
		}

		// after setTitle -> if onAdded need more rand
		if(background_id == "background.hedge_knight")
		{
			if (this.Math.rand(0, 2) == 2)
			{
				this.Math.rand(0, this.Const.Strings.HedgeKnightTitles.len() - 1);
				title_flag = true;
				// buildDescription if bro == 1 i = 5
				for(local i = 0; i < build_description_i; i++)
					this.Math.rand(0, 1);
			}
		}
		else if(background_id == "background.militia")
		{
			if (this.Math.rand(0, 4) == 4)
			{
				this.Math.rand(0, this.Const.Strings.MilitiaTitles.len() - 1);
				title_flag = true;
				for(local i = 0; i < build_description_i; i++)
					this.Math.rand(0, 1);
			}
		}
		else if(background_id == "background.companion1h" || background_id == "background.companion2h" || background_id == "background.companionranged"
			|| background_id == "background.companion1hs" || background_id == "background.companion2hs" || background_id == "background.companionrangeds")
		{
			if (this.Math.rand(0, 3) == 3)
			{
				this.Math.rand(0, this.Const.Strings.SellswordTitles.len() - 1);
				title_flag = true;
				for(local i = 0; i < build_description_i; i++)
					this.Math.rand(0, 1);
			}
		}
		else if(background_id == "background.gladiator" || background_id == "background.gladiator_origin")
		{
			if (this.Math.rand(1, 2) == 2)
			{
				this.Math.rand(0, this.Const.Strings.GladiatorTitles.len() - 1);
				title_flag = true;
				for(local i = 0; i < build_description_i; i++)
					this.Math.rand(0, 1);
			}
		}
	}

	{
		// buildAttributes
		bro["Attr"] <- array(AttrNum, 0);
		bro["Attr"][Attr.Hitpoints] = this.Math.rand(a.Hitpoints[0], a.Hitpoints[1]);
		bro["Attr"][Attr.Bravery] = this.Math.rand(a.Bravery[0], a.Bravery[1]);
		bro["Attr"][Attr.Stamina] = this.Math.rand(a.Stamina[0], a.Stamina[1]);
		bro["Attr"][Attr.MeleeSkill] = this.Math.rand(a.MeleeSkill[0], a.MeleeSkill[1]);
		bro["Attr"][Attr.RangedSkill] = this.Math.rand(a.RangedSkill[0], a.RangedSkill[1]);
		bro["Attr"][Attr.MeleeDefense] = this.Math.rand(a.MeleeDefense[0], a.MeleeDefense[1]);
		bro["Attr"][Attr.RangedDefense] = this.Math.rand(a.RangedDefense[0], a.RangedDefense[1]);
		bro["Attr"][Attr.Initiative] = this.Math.rand(a.Initiative[0], a.Initiative[1]);
	}

	{
		// buildDescription
		for(local i = 0; i < build_description_i; i++)
			this.Math.rand(0, 1);
	}

	{
		if(bro["Name"] == "")
			this.Math.rand(0, 1);
		local maxTraits = this.Math.rand(this.Math.rand(0, 1) == 0 ? 0 : 1, 2);
		local traits = [
			background
		];

		for( local i = 0; i < maxTraits; i = ++i )
		{
			for( local j = 0; j < 10; j = ++j )
			{
				local trait = this.Const.CharacterTraits[this.Math.rand(0, this.Const.CharacterTraits.len() - 1)];
				local nextTrait = false;

				for( local k = 0; k < traits.len(); k = ++k )
				{
					if (traits[k].getID() == trait[0] || traits[k].isExcluded(trait[0]))
					{
						nextTrait = true;
						break;
					}
				}

				if (!nextTrait)
				{
					if(trait[0] in trait_dict)
					{
						this.Math.rand(0, 1);
						traits.push(trait_dict[trait[0]]);
					}
					else
					{
						trait_dict[trait[0]] <- this.new(trait[1]);
						traits.push(trait_dict[trait[0]]);
					}
					break;
				}
			}
		}

		for( local i = 1; i < traits.len(); i = ++i )
		{
			if (!title_flag && traits[i].m.Titles.len() != 0 && this.Math.rand(1, 100) <= 10)
			{
				this.Math.rand(0, traits[i].m.Titles.len() - 1);
				for(local i = 0; i < build_description_i; i++)
					this.Math.rand(0, 1);
				title_flag = true;
			}
		}

		bro["Traits"] <- [];
		for( local i = 0; i < traits.len(); i = ++i )
		{
			if(traits[i].getID() == "background.cultist")
				bro["Traits"].push("trait.cultist_fanatic");
			else
			{
				if(traits[i].getID().find("background") == null)
					bro["Traits"].push(traits[i].getID());
			}
		}
	}

	{
		// addEquipment
		if(background_id == "background.farmhand")
		{
			local r;
			r = this.Math.rand(0, 3);
			if(r != 3)
				this.Math.rand(0, 1);

			r = this.Math.rand(0, 1);
			if(r == 0)
				this.Math.rand(0, 1);
			else
			{
				this.Math.rand(0, 1);
				this.Math.rand(0, 1);
				this.Math.rand(0, 1);
			}

			r = this.Math.rand(0, 2);
			if(r == 0)
			{
				this.Math.rand(0, 1);
			}
		}
		else if(background_id == "background.poacher")
		{
			local r;
			r = this.Math.rand(1, 100);

			if (r <= 50)
			{
				this.Math.rand(0, 1);
				// this.Math.rand(0, 1); // ammo ?
			}
			else if (r <= 80)
			{
				this.Math.rand(0, 1);
			}
			else
			{
				this.Math.rand(0, 1);
				// this.Math.rand(0, 1); // ammo ?
			}

			r = this.Math.rand(0, 4); // add to bag
			if (r <= 1)
				this.Math.rand(0, 1);

			r = this.Math.rand(0, 2);
			this.Math.rand(0, 1);

			this.Math.rand(0, 1);
			this.Math.rand(0, 1);
		}
		else if(background_id == "background.vagabond")
		{
			local r;
			r = this.Math.rand(0, 3);
			if(r <= 1)
				this.Math.rand(0, 1);

			r = this.Math.rand(0, 3);
			this.Math.rand(0, 1);

			r = this.Math.rand(0, 2);
			if(r == 0)
			{
				this.Math.rand(0, 1);
				this.Math.rand(0, 1);
			}
			else if(r == 1)
			{
				this.Math.rand(0, 1);
			}
		}
		else if(background_id == "background.thief")
		{
			local r;
			r = this.Math.rand(0, 1);
			this.Math.rand(0, 1);

			r = this.Math.rand(0, 2);
			if(r == 2)
			{
				this.Math.rand(0, 1);
				this.Math.rand(0, 1);
			}
			else
			{
				this.Math.rand(0, 1);
			}

			r = this.Math.rand(0, 1);
			this.Math.rand(0, 1);
			this.Math.rand(0, 1);
		}
		else if(background_id == "background.gambler")
		{
			local r;
			r = this.Math.rand(0, 4);

			if(r == 0)
				this.Math.rand(0, 1);
			else
			{
				this.Math.rand(0, 1);
				this.Math.rand(0, 1);
			}

			r = this.Math.rand(0, 3);
			if(r == 0)
				this.Math.rand(0, 1);
		}
		else if(background_id == "background.daytaler")
		{
			local r;
			r = this.Math.rand(0, 4);
			if(r <= 1)
				this.Math.rand(0, 1);

			r = this.Math.rand(0, 1);
			if(r == 0)
				this.Math.rand(0, 1);
			else
			{
				this.Math.rand(0, 1);
				this.Math.rand(0, 1);
				this.Math.rand(0, 1);
			}

			r = this.Math.rand(0, 4);
			if(r == 0)
			{
				this.Math.rand(0, 1);
				this.Math.rand(0, 1);
			}
		}
		else if(background_id == "background.miller")
		{
			local r;
			r = this.Math.rand(0, 4);
			if(r <= 1)
				this.Math.rand(0, 1);

			this.Math.rand(0, 1);
			this.Math.rand(0, 1);
			this.Math.rand(0, 1);
		}
		else if(background_id == "background.fisherman")
		{
			local r;
			r = this.Math.rand(0, 1);
			if(r == 0)
				this.Math.rand(0, 1);
			this.Math.rand(0, 1);

			r = this.Math.rand(0, 2);
			if(r <= 1)
			{
				this.Math.rand(0, 1);
			}
			else
			{
				this.Math.rand(0, 1);
				this.Math.rand(0, 1);
				this.Math.rand(0, 1);
			}

			r = this.Math.rand(0, 1);
			if(r == 0)
				this.Math.rand(0, 1);
		}
		else if(background_id == "background.militia")
		{
			local r;
			r = this.Math.rand(0, 5);
			this.Math.rand(0, 1);
			local m = this.Math.rand(1, 100); // getItemAtSlot always null?
			if(m <= 50)
				this.Math.rand(0, 1);

			r = this.Math.rand(0, 4);
			if(r == 4)
			{
				this.Math.rand(0, 1);
				this.Math.rand(0, 1);
			}
			else
			{
				this.Math.rand(0, 1);
			}

			r = this.Math.rand(0, 6);
			if(r <= 4)
			{
				this.Math.rand(0, 1);
			}
		}
		else if(background_id == "background.minstrel")
		{
			this.Math.rand(0, 1);
			this.Math.rand(0, 1);
			this.Math.rand(0, 1);

			local r;
			r = this.Math.rand(0, 1);
			if(r == 0)
				this.Math.rand(0, 1);

			r = this.Math.rand(1, 100);
			if(r <= 60)
				this.Math.rand(0, 1);
		}
		else if(background_id == "background.butcher")
		{
			local r;
			r = this.Math.rand(0, 2);
			this.Math.rand(0, 1);

			this.Math.rand(0, 1);
		}
		else if(background_id == "background.tailor")
		{
			this.Math.rand(0, 1);
			this.Math.rand(0, 1);

			local r;
			r = this.Math.rand(0, 1);
			if(r == 0)
				this.Math.rand(0, 1);
		}
		else if(background_id == "background.shepherd")
		{
			local r;
			if (this.Math.rand(1, 100) <= 66)
			{
				this.Math.rand(0, 1);
			}

			r = this.Math.rand(0, 2);
			if(r == 0)
			{
				this.Math.rand(0, 1);
				this.Math.rand(0, 1);
				this.Math.rand(0, 1);
			}
			else
			{
				this.Math.rand(0, 1);
			}
			this.Math.rand(0, 1);
		}
		else if(background_id == "background.caravan_hand")
		{
			local r;
			r = this.Math.rand(0, 4);
			this.Math.rand(0, 1);

			r = this.Math.rand(0, 4);
			this.Math.rand(0, 1);

			r = this.Math.rand(0, 2);
			if(r == 1)
			{
				this.Math.rand(0, 1);
				this.Math.rand(0, 1);
			}
			else if(r == 2)
			{
				this.Math.rand(0, 1);
			}
		}
		else if(background_id == "background.hedge_knight")
		{
			local r;
			r = this.Math.rand(0, 2);
			this.Math.rand(0, 1);

			r = this.Math.rand(0, 4);
			if(r == 0)
			{
				this.Math.rand(0, 1);
				this.Math.rand(0, 1);
			}
			else
				this.Math.rand(0, 1);

			r = this.Math.rand(0, 4);
			if(r == 2)
			{
				this.Math.rand(0, 1);
			}
			else
			{
				this.Math.rand(0, 1);
				this.Math.rand(0, 1);
			}
		}
		else if(background_id == "background.cultist")
		{
			local r;
			r = this.Math.rand(0, 1);
			this.Math.rand(0, 1);

			r = this.Math.rand(0, 3);
			this.Math.rand(0, 1);

			r = this.Math.rand(0, 2);
			if(r == 2)
			{
				this.Math.rand(0, 1);
				this.Math.rand(0, 1);
			}
			else
			{
				this.Math.rand(0, 1);
			}
		}
		else if(background_id == "background.companion1h")
		{
			this.Math.rand(0, 1);
			this.Math.rand(0, 1);
			this.Math.rand(0, 1);
			local r;
			r = this.Math.rand(0, 2);
			this.Math.rand(0, 1);

			r = this.Math.rand(0, 3);
			this.Math.rand(0, 1);
		}
		else if(background_id == "background.companion2h")
		{
			local r;
			this.Math.rand(0, 1);

			r = this.Math.rand(0, 2);
			this.Math.rand(0, 1);

			r = this.Math.rand(0, 1);
			this.Math.rand(0, 1);
			this.Math.rand(0, 1);
		}
		else if(background_id == "background.companionranged")
		{
			this.Math.rand(0, 1);
			// this.Math.rand(0, 1); // ammo ?
			this.Math.rand(0, 1); // add to bag knife

			local r;
			r = this.Math.rand(0, 1);
			this.Math.rand(0, 1);
		}
		else if(background_id == "background.companion1hs")
		{
			this.Math.rand(0, 1);
			this.Math.rand(0, 1);
			this.Math.rand(0, 1);

			local r = this.Math.rand(0, 2);
			this.Math.rand(0, 1);

			r = this.Math.rand(0, 2);
			if(r == 2)
			{
				this.Math.rand(0, 1);
				this.Math.rand(0, 1);
				this.Math.rand(0, 1);
			}
			else
			{
				this.Math.rand(0, 1);
			}
		}
		else if(background_id == "background.companion2hs")
		{
			local r;
			this.Math.rand(0, 1);

			r = this.Math.rand(0, 2);
			this.Math.rand(0, 1);

			r = this.Math.rand(0, 2);
			if(r == 2)
			{
				this.Math.rand(0, 1);
				this.Math.rand(0, 1);
				this.Math.rand(0, 1);
			}
			else
			{
				this.Math.rand(0, 1);
			}
		}
		else if(background_id == "background.companionrangeds")
		{
			local r;
			this.Math.rand(0, 1);
			// this.Math.rand(0, 1); // ammo ?
			this.Math.rand(0, 1); // add to bag knife

			r = this.Math.rand(0, 2);
			this.Math.rand(0, 1);

			this.Math.rand(0, 1);
			this.Math.rand(0, 1);
			this.Math.rand(0, 1);
		}
		else if(background_id == "background.hunter")
		{
			local r;
			this.Math.rand(0, 1);
			// this.Math.rand(0, 1); // ammo ?

			r = this.Math.rand(0, 1);
			if( r == 0 )
				this.Math.rand(0, 1);

			r = this.Math.rand(0, 2);
			this.Math.rand(0, 1);

			r = this.Math.rand(0, 1);
			if(r == 0)
			{
				this.Math.rand(0, 1);
				this.Math.rand(0, 1);
			}
			else
				this.Math.rand(0, 1);
		}
		else if(background_id == "background.paladin" || background_id == "background.paladinold")
		{
			local r;
			r = this.Math.rand(0, 13);
			this.Math.rand(0, 1);

			if(r < 5 && this.Math.rand(1, 100) <= 75)
			{
				this.Math.rand(0, 1);
				this.Math.rand(0, 1);
				this.Math.rand(0, 1);
			}

			r = this.Math.rand(0, 5);
			this.Math.rand(0, 1);

			r = this.Math.rand(0, 5);
			this.Math.rand(0, 1);
		}
		else if(background_id == "background.barbarian")
		{
			local r;
			r = this.Math.rand(1, 3);
			this.Math.rand(0, 1);

			r = this.Math.rand(0, 3);
			this.Math.rand(0, 1);

			r = this.Math.rand(0, 3);
			if(r == 1)
			{
				this.Math.rand(0, 1);
				this.Math.rand(0, 1);
			}
			else if(r == 0 || r == 2)
			{
				this.Math.rand(0, 1);
			}
		}
		else if(background_id == "background.monk")
		{
			this.Math.rand(0, 1);
		}
		else if(background_id == "background.anatomist")
		{
			local r;
			r = this.Math.rand(0, 3);
			this.Math.rand(0, 1);

			r = this.Math.rand(0, 5);
			this.Math.rand(0, 1);

			r = this.Math.rand(0, 5);
			this.Math.rand(0, 1);
		}
		else if(background_id == "background.beast_slayer")
		{
			local r;
			r = this.Math.rand(1, 4);
			if(r == 1)
			{
				this.Math.rand(0, 1);
				this.Math.rand(0, 1);
			}
			else
			{
				this.Math.rand(0, 1);
			}

			if (this.Math.rand(1, 100) <= 50)
			{
				this.Math.rand(0, 1);
			}

			r = this.Math.rand(0, 2);
			this.Math.rand(0, 1);

			r = this.Math.rand(0, 1);
			if(r == 0)
			{
				this.Math.rand(0, 1);
				this.Math.rand(0, 1);
			}
		}
		else if(background_id == "background.gladiator_origin")
		{

		}
		else if(background_id == "background.manhunter")
		{
			local r;
			r = this.Math.rand(0, 3);
			this.Math.rand(0, 1);
			this.Math.rand(0, 1);

			r = this.Math.rand(0, 1);
			this.Math.rand(0, 1);

			r = this.Math.rand(0, 1);
			if(r == 0)
			{
				this.Math.rand(0, 1);
				this.Math.rand(0, 1);
			}
		}
		else if(background_id == "background.slave")
		{
			local r;
			r = this.Math.rand(0, 4);
			if(r <= 1)
			{
				this.Math.rand(0, 1);
			}
		}
		else
		{
			this.logInfo("Not Find BackgroundID: " + background_id);
		}
	}

	{
		// setAppearance
		if(background.m.HairColors != null)
		{
			this.Math.rand(0, background.m.HairColors.len() - 1);
			if (background.m.Faces != null)
			{
				this.Math.rand(0, background.m.Faces.len() - 1)
			}
			if (this.Math.rand(0, background.m.Hairs.len()) != background.m.Hairs.len())
			{
				this.Math.rand(0, background.m.Hairs.len() - 1);
			}
			if (this.Math.rand(1, 100) <= background.m.BeardChance)
			{
				this.Math.rand(0, background.m.Beards.len() - 1)
			}
			if (background.m.Bodies != null)
			{
				this.Math.rand(0, background.m.Bodies.len() - 1);
			}

			// if onSetAppearance need more rand
			if(background_id == "background.hedge_knight")
			{
				this.Math.rand(1, 100);
				this.Math.rand(1, 100);
			}
			else if(background_id == "background.cultist")
			{
				this.Math.rand(1, 100);
				this.Math.rand(1, 100);
			}
			else if(background_id == "background.paladin")
			{
				this.Math.rand(1, 100);
				this.Math.rand(1, 100);
			}
			else if(background_id == "background.barbarian")
			{
				if (this.Math.rand(1, 100) <= 66)
				{
					this.Math.rand(0, 1);
				}
				if (this.Math.rand(1, 100) <= 66)
				{
					this.Math.rand(0, 1);
				}
			}
			else if(background_id == "background.beast_slayer")
			{
				this.Math.rand(1, 100);
				this.Math.rand(1, 100);
			}
			else if(background_id == "background.gladiator" || background_id == "background.gladiator_origin")
			{
				this.Math.rand(1, 100);
				this.Math.rand(1, 100);
			}
			else if(background_id == "background.slave")
			{
				this.Math.rand(1, 100);
			}
		}
	}

	{
		// buildDescription if bro == 1 i = 5 else i = 6
		for(local i = 0; i< build_description_i; i++)
			this.Math.rand(0, 1);
	}

	{
		// fillTalentValues
		if(!is_untalented)
		{
			bro["Talents"] <- array(AttrNum, 0);
			for( local done = 0; done < 3;  )
			{
				local i = this.Math.rand(0, AttrNum - 1);
				if (bro["Talents"][i] == 0 && background.getExcludedTalents().find(i) == null)
				{
					local r = this.Math.rand(1, 100);

					if (r <= 60)
					{
						bro["Talents"][i] = 1;
					}
					else if (r <= 90)
					{
						bro["Talents"][i] = 2;
					}
					else
					{
						bro["Talents"][i] = 3;
					}

					done = ++done;
				}
			}
		}
	}

	{
		// fillAttributeLevelUpValues
		for( local i = 0; i != AttrNum; i = ++i )
		{
			for( local j = 0; j < 10; j = ++j )
			{
				this.Math.rand(this.Const.AttributesLevelUp[i].Min + (bro["Talents"][i] == 3 ? 2 : bro["Talents"][i]),
					this.Const.AttributesLevelUp[i].Max + (bro["Talents"][i] == 3 ? 1 : 0));
			}
		}
	}
}


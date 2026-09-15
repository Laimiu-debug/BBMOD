local gt = this.getroottable();

local LowestScore = gt.SeedGenerator.LowestScore;

local Attr = gt.SeedGenerator.Attr;
local AttrNum = gt.SeedGenerator.AttrNum;

local CommonConfig = gt.SeedGenerator.CommonConfig;
local DebugConfig = gt.SeedGenerator.DebugConfig;

local Role = gt.SeedGenerator.Role;
local RoleName = gt.SeedGenerator.RoleName;
local RoleNum = gt.SeedGenerator.RoleNum;
local BroOutput = gt.SeedGenerator.BroOutput;
local BroOutputConditionArray = gt.SeedGenerator.BroOutputConditionArray;
local MaxRoleArray = gt.SeedGenerator.MaxRoleArray;

local BroSortEntry = gt.SeedGenerator.BroSortEntry;
local BroScoreEntry = gt.SeedGenerator.BroScoreEntry;
local BroSortEntryNum = gt.SeedGenerator.BroSortEntryNum;
local BroEntryNum = gt.SeedGenerator.BroEntryNum;

gt.SeedGenerator.map_output_type <- -1;
gt.SeedGenerator.lair_output_type <- -1;
gt.SeedGenerator.bro_output_type <- -1;

local broScoreSortByDescend = function(first, second)
{
	if(first[BroSortEntry.RoleScore] > second[BroSortEntry.RoleScore]) return -1;
	if(first[BroSortEntry.RoleScore] < second[BroSortEntry.RoleScore]) return 1;
	return 0;
}

local startNewCampaign = function()
{
	this.setAutoPause(true);
	this.Time.setVirtualTime(0);
	this.m.IsRunningUpdatesWhilePaused = true;
	this.setPause(true);
	this.Math.seedRandomString(this.m.CampaignSettings.Seed);
	local origin = this.m.CampaignSettings.StartingScenario.getID();

	local loop_idx = 0;
	local bro_output_idx = 0;
	local change_seed_timer = 0;
	local max_team_avg_score = 0;
	local sum_team_avg_score = 0;
	local avg_team_avg_score = 0;
	local sum_avg_role_score = array(RoleNum, 0);
	local avg_role_score = array(RoleNum, 0);
	local max_role_score = array(RoleNum, 0);
	local debug_index = 0;

	local run_at_least_once_flag = false;
	local change_seed_interval = 10;

	if(CommonConfig.GenerateSettlementMode)
	{
		CommonConfig.GenerateBrotherMode = false;
	}
	if(!CommonConfig.PrintLairInfo)
	{
		CommonConfig.PrintLairNamedDetail = false;
		CommonConfig.OnlyPrintMatchingLair = false;
	}
	if(!CommonConfig.PrintLairNamedDetail)
	{
		CommonConfig.OnlyPrintMatchingLair = false;
	}

	while(true)
	{
		if(loop_idx % gt.SeedGenerator.LoopPrintInterval == 0)
		{
			change_seed_timer++;
			if(change_seed_timer % change_seed_interval == 0)
			{

				local time_seed_string = "";
				time_seed_string += this.Time.getExactTime();
				for( local i = 0; i < 10; i++)
				{
					local rand = this.Math.rand(0, 25)
					time_seed_string += (65 + rand).tochar();
				}
				change_seed_timer = 0;
				this.Math.seedRandomString(time_seed_string);
			}
			local role_avg_score_info = "";
			for(local i = 0; i < RoleNum; i++)
			{
				avg_role_score[i] = sum_avg_role_score[i] / (loop_idx + 1)
				role_avg_score_info = role_avg_score_info + " " + RoleName[i] + ":" + avg_role_score[i] + ":" + max_role_score[i];
			}
			avg_team_avg_score = sum_team_avg_score / (loop_idx + 1);
			this.logInfo("LoopIdx: " + loop_idx + "(" + bro_output_idx + ")" + " " + max_team_avg_score + " " + avg_team_avg_score + role_avg_score_info);
		}

		local seedString = "";
		for(local i = 0; i < 10; i++)
		{
			local rand = this.Math.rand(0, 25)
			if(!CommonConfig.EnableLowercaseSeed || this.Math.rand(0, 1) == 0)
				seedString += (65 + rand).tochar();
			else
				seedString += (97 + rand).tochar();
		}

		if(DebugConfig.DebugMode)
		{
			if(debug_index == DebugConfig.DebugSeed.len())
				local i = 1 / 0;
			seedString = DebugConfig.DebugSeed[debug_index++];
		}
		this.m.CampaignSettings.Seed = seedString;

		gt.SeedGenerator.map_output_type = -1;
		gt.SeedGenerator.lair_output_type = -1;
		gt.SeedGenerator.bro_output_type = -1;
		if(CommonConfig.GenerateSettlementMode || !run_at_least_once_flag)
		{
			run_at_least_once_flag = true;
			gt.SeedGenerator.map_output_type = gt.SeedGenerator.generateSettlement(seedString, this);
			// this.m.Assets.init();
			// this.World.FactionManager.createFactions();
			// this.World.EntityManager.buildRoadAmbushSpots();
			// this.World.FactionManager.runSimulation();
		}

		if(CommonConfig.GenerateSettlementMode)
		{
			if(!CommonConfig.OnlyPrintMatchingSettlement || gt.SeedGenerator.map_output_type >= 0)
			{
				if(CommonConfig.PrintLairInfo)
				{
					gt.SeedGenerator.generateBrother(seedString, this, true); // 需要打印红信息需要运行一次对齐
					this.m.CampaignSettings.StartingScenario.onSpawnPlayer();
					if(gt.SeedGenerator.EndlessLoopFlag)
					{
						gt.SeedGenerator.EndlessLoopFlag = false;
						this.World.Assets.getStash().clear();
						this.World.Assets.getStash().resize(99);
						this.World.clearScene();
						this.World.EntityManager.clear();
						this.World.FactionManager.clear();
						continue;
					}
					this.World.FactionManager.runSimulation();
					gt.SeedGenerator.lair_output_type = gt.SeedGenerator.generateLairInfo();
				}
				if(!CommonConfig.OnlyPrintMatchingLair || gt.SeedGenerator.lair_output_type >= 0)
				{
					this.logInfo("Seed: " + seedString + " LoopIdx:" + loop_idx + " MapOutputType:" + gt.SeedGenerator.map_output_type + " LairOutputType:" + gt.SeedGenerator.lair_output_type);

					if(CommonConfig.PrintLairInfo)
					{
						gt.SeedGenerator.printLairInfo();
					}
					gt.SeedGenerator.printSettlementInfo();
					this.logInfo("CRLF");
				}
			}
			// this.m.Assets.destroy();
			this.World.Assets.getStash().clear();
			this.World.Assets.getStash().resize(99);
			this.World.clearScene();
			this.World.EntityManager.clear();
			this.World.FactionManager.clear();
		}

		// this.logInfo("getOrigin " + this.World.Assets.getOrigin().getID())

		if(CommonConfig.GenerateBrotherMode)
		{
			local bros = null;
			bros = gt.SeedGenerator.generateBrother(seedString, this);
			local roster = null;
			if(bros == null)
			{
			 	roster = this.World.getPlayerRoster();
			 	bros = roster.getAll();
			}
			local bros_len = bros.len();
			local bros_sort_entries = array(bros_len * RoleNum); 	# 排序用的数组
			local bros_entries = array(bros_len);		   	# 存放分数的数组
			for(local i = 0; i < bros_len; i++)
			{
				for(local k = 0; k < RoleNum; k++)
				{
					bros_sort_entries[RoleNum * i + k] = array(BroSortEntryNum, 0); # 分别存放 角色索引 职业分数 职业索引
					bros_sort_entries[RoleNum * i + k][BroSortEntry.BroIndex] = i;
				}
				bros_entries[i] = array(BroEntryNum, 0); # 分别存放 最高职业分数 最高职业分数索引 最匹配职业分数 最匹配职业索引 初始属性 11级属性 特性
			}
			for(local i = 0; i < bros_len; i++)
			{
				local role_initattr_maxattr_score_ = null;
				if(roster == null)
				 	role_initattr_maxattr_score_ = gt.SeedGenerator.getBroScoreFast(bros[i]);
				else
				 	role_initattr_maxattr_score_ = gt.SeedGenerator.getBroScore(bros[i]);
				local max_score_ = -1.0;
				local max_index_ = 0;
				for(local k = 0; k < RoleNum; k++)
				{
					local score = role_initattr_maxattr_score_[2][k];
					if(score > max_score_)
					{
						max_score_ =  score;
						max_index_ = k;
					}
					bros_sort_entries[RoleNum * i + k][BroSortEntry.RoleScore] = score;
					bros_sort_entries[RoleNum * i + k][BroSortEntry.RoleIndex] = k;
				}
				bros_entries[i][BroScoreEntry.MaxRoleScore] = max_score_;
				bros_entries[i][BroScoreEntry.MaxRoleScoreType] = max_index_;
				bros_entries[i][BroScoreEntry.InitAttr] = role_initattr_maxattr_score_[0].slice(0);
				bros_entries[i][BroScoreEntry.MaxAttr] = role_initattr_maxattr_score_[1].slice(0);

				if(roster == null)
					bros_entries[i][BroScoreEntry.Trait] = bros[i]["Traits"].slice(0);
				else
				{
					local trait_array = [""];
					foreach(s in bros[i].m.Skills.m.Skills )
					{
						if (s.getType() == this.Const.SkillType.Trait)
						{
							trait_array.append(s.getID());
						}
					}
					bros_entries[i][BroScoreEntry.Trait] = trait_array.slice(0);
				}
			}

			local least_bro_num_ = bros_len;
			local role_array = array(RoleNum, 0);
			local bro_array_ = array(bros_len, RoleNum - 1); # 还剩的角色待分配职业分数
			local bros_sort_entries_copy_ = array(bros_len * RoleNum);
			for(local i = 0; i < bros_len * RoleNum; i++)
			{
				bros_sort_entries_copy_[i] = bros_sort_entries[i].slice(0);
			}
			local team_score_sum_ = 0;
			local team_score_avg_ = 0;

			local max_role_array;
			if(origin in MaxRoleArray)
				max_role_array = MaxRoleArray[origin];
			else
				max_role_array = MaxRoleArray["common"];

			while(least_bro_num_)
			{
				bros_sort_entries_copy_.sort(broScoreSortByDescend);
				local bro_index_ = bros_sort_entries_copy_[0][BroSortEntry.BroIndex];
				local bro_score_ = bros_sort_entries_copy_[0][BroSortEntry.RoleScore]
				local role_type_ = bros_sort_entries_copy_[0][BroSortEntry.RoleIndex];
				if(role_array[role_type_] < max_role_array[role_type_])
				{
					least_bro_num_--;
					bro_array_[bro_index_] = 0;
					for(local i = 0; i < bros_len * RoleNum; i++)
					{
						if(bros_sort_entries_copy_[i][BroSortEntry.BroIndex] == bro_index_)
							bros_sort_entries_copy_[i][BroSortEntry.RoleScore] = 0;
					}

					if(bro_score_ < LowestScore)
					{
						bros_entries[bro_index_][BroScoreEntry.BestRoleScore] = bro_score_;
						bros_entries[bro_index_][BroScoreEntry.BestRoleScoreType] = Role.RoleUseless;
						role_array[Role.RoleUseless]++;
					}
					else
					{
						bros_entries[bro_index_][BroScoreEntry.BestRoleScore] = bro_score_;
						bros_entries[bro_index_][BroScoreEntry.BestRoleScoreType] = role_type_;
						role_array[role_type_]++;
					}
					team_score_sum_ += bros_entries[bro_index_][BroScoreEntry.BestRoleScore];
				}
				else
				{
					bro_array_[bro_index_]--;
					if(bro_array_[bro_index_] == 0)
					{
						least_bro_num_--;
						bros_entries[bro_index_][BroScoreEntry.BestRoleScore] = bro_score_;
						bros_entries[bro_index_][BroScoreEntry.BestRoleScoreType] = Role.RoleUseless;
						role_array[Role.RoleUseless]++;
						team_score_sum_ += bros_entries[bro_index_][BroScoreEntry.BestRoleScore];
					}
					bros_sort_entries_copy_[0][BroSortEntry.RoleScore] = 0;
				}
			}


			if(DebugConfig.DebugMode)
			{
				this.logInfo("Team Score: " + team_score_sum_ + " " + team_score_sum_ / bros_len);
				for(local i = 0; i < bros_len; i++)
				{
					local score_info = "Bro Score: " + i + " ";
					score_info += "Best Score: " +  RoleName[bros_entries[i][BroScoreEntry.BestRoleScoreType]] + ":" + bros_entries[i][BroScoreEntry.BestRoleScore] + "   ";
					score_info += "Max Score: " +  RoleName[bros_entries[i][BroScoreEntry.MaxRoleScoreType]] + ":" + bros_entries[i][BroScoreEntry.MaxRoleScore] + "   ";
					for(local k = 0; k < RoleNum; k++)
					{
						score_info += RoleName[k] + ":" + bros_sort_entries[RoleNum * i + k][BroSortEntry.RoleScore] + " ";
					}
					this.logInfo(score_info);
				}
			}

			team_score_avg_ = team_score_sum_ / bros_len;
			gt.SeedGenerator.bro_output_type = gt.SeedGenerator.broOutputCheck(this, bros_sort_entries, bros_entries, team_score_avg_);

			local avg_role_score_tmp = array(RoleNum, 0);
			for(local i = 0; i < bros_len; i++)
			{
				for(local k = 0; k < RoleNum; k++)
				{
					local score = bros_sort_entries[RoleNum * i + k][BroSortEntry.RoleScore];
					if(score > max_role_score[k])
						max_role_score[k] = score;
					avg_role_score_tmp[k] += score;
				}
			}
			for(local k = 0; k < RoleNum; k++)
			{
				sum_avg_role_score[k] += avg_role_score_tmp[k] / bros_len;
			}


			sum_team_avg_score += team_score_avg_;
			if(team_score_avg_ > max_team_avg_score)
				max_team_avg_score = team_score_avg_;

			if(gt.SeedGenerator.bro_output_type >= 0)
			{
				bro_output_idx++;
				if(!CommonConfig.MatchingBrotherGenerateSettlement)
				{
					this.logInfo("Seed: " + seedString + " LoopIdx:" + loop_idx + " BroOutputType:" + gt.SeedGenerator.bro_output_type);
					gt.SeedGenerator.printBroInfo(roster, role_array, team_score_avg_, bros_len, bros, bros_entries);
					this.logInfo("CRLF");
				}
				else
				{
					// this.m.Assets.destroy();
					this.World.Assets.getStash().clear();
					this.World.Assets.getStash().resize(99);
					this.World.clearScene();
					this.World.EntityManager.clear();
					this.World.FactionManager.clear();
					gt.SeedGenerator.map_output_type = gt.SeedGenerator.generateSettlement(seedString, this);

					// if(roster != null)
					// 	roster.clear();
					// this.World.EntityManager.buildRoadAmbushSpots();

					if(CommonConfig.OnlyPrintMatchingSettlement)
					{
						if( gt.SeedGenerator.map_output_type >= 0)
						{
							if(CommonConfig.PrintLairInfo)
							{
								gt.SeedGenerator.generateBrother(seedString, this, true); // 需要打印红信息需要运行一次对齐
								if(origin != "scenario.deserters")
									this.m.CampaignSettings.StartingScenario.onSpawnPlayer();
								if(gt.SeedGenerator.EndlessLoopFlag)
								{
									gt.SeedGenerator.EndlessLoopFlag = false;
									this.World.Assets.getStash().clear();
									this.World.Assets.getStash().resize(99);
									this.World.clearScene();
									this.World.EntityManager.clear();
									this.World.FactionManager.clear();
									continue;
								}
								this.World.FactionManager.runSimulation();
								gt.SeedGenerator.lair_output_type = gt.SeedGenerator.generateLairInfo();
							}
							if(!CommonConfig.OnlyPrintMatchingLair || gt.SeedGenerator.lair_output_type >= 0)
							{
								this.logInfo("Seed: " + seedString + " LoopIdx:" + loop_idx + " BroOutputType:" + gt.SeedGenerator.bro_output_type + " MapOutputType:" + gt.SeedGenerator.map_output_type + " LairOutputType:" + gt.SeedGenerator.lair_output_type);
								gt.SeedGenerator.printBroInfo(roster, role_array, team_score_avg_, bros_len, bros, bros_entries);

								if(roster != null)
									roster.clear();
								if(CommonConfig.PrintLairInfo)
								{
									gt.SeedGenerator.printLairInfo();
								}
								gt.SeedGenerator.printSettlementInfo();
								this.logInfo("CRLF");
							}
						}
					}
					else
					{
						if(CommonConfig.PrintLairInfo)
						{
							gt.SeedGenerator.generateBrother(seedString, this, true); // 需要打印红信息需要运行一次对齐
							if(origin != "scenario.deserters")
								this.m.CampaignSettings.StartingScenario.onSpawnPlayer();
							if(gt.SeedGenerator.EndlessLoopFlag)
							{
								gt.SeedGenerator.EndlessLoopFlag = false;
								this.World.Assets.getStash().clear();
								this.World.Assets.getStash().resize(99);
								this.World.clearScene();
								this.World.EntityManager.clear();
								this.World.FactionManager.clear();
								continue;
							}
							this.World.FactionManager.runSimulation();
							gt.SeedGenerator.lair_output_type = gt.SeedGenerator.generateLairInfo();
						}
						if(!CommonConfig.OnlyPrintMatchingLair || gt.SeedGenerator.lair_output_type >= 0)
						{
							this.logInfo("Seed: " + seedString + " LoopIdx:" + loop_idx + " BroOutputType:" + gt.SeedGenerator.bro_output_type + " MapOutputType:" + gt.SeedGenerator.map_output_type + " LairOutputType:" + gt.SeedGenerator.lair_output_type);
							gt.SeedGenerator.printBroInfo(roster, role_array, team_score_avg_, bros_len, bros, bros_entries);

							if(roster != null)
								roster.clear();
							if(CommonConfig.PrintLairInfo)
							{
								gt.SeedGenerator.printLairInfo();
							}
							gt.SeedGenerator.printSettlementInfo();
							this.logInfo("CRLF");
						}
					}

					// this.m.Assets.destroy();
					this.World.Assets.getStash().clear();
					this.World.Assets.getStash().resize(99);
					this.World.clearScene();
					this.World.EntityManager.clear();
					this.World.FactionManager.clear();
				}
			}
			if(roster != null)
				roster.clear();
		}

		loop_idx++;
	}
}

::mods_hookClass("states/world_state",
  function(o) { ::mods_override(o, "startNewCampaign", startNewCampaign); });

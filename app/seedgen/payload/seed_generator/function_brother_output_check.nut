::include("seed_generator/define_role");

local gt = this.getroottable();

gt.SeedGenerator.BroSortEntry <- {
	BroIndex = 0,
	RoleScore = 1,
	RoleIndex = 2,
	End = 3,
};
gt.SeedGenerator.BroSortEntryNum <- gt.SeedGenerator.BroSortEntry.End;

gt.SeedGenerator.BroScoreEntry <- {
	MaxRoleScore = 0,
	MaxRoleScoreType = 1,
	BestRoleScore = 2,
	BestRoleScoreType = 3,
	InitAttr = 4,
	MaxAttr = 5,
	Trait = 6,
	End = 7,
};
gt.SeedGenerator.BroEntryNum <- gt.SeedGenerator.BroScoreEntry.End;

# 根据输出条件计算是否输出该种子
gt.SeedGenerator.broOutputCheck <- function(wolrd_state, bros_sort_entries, bros_entries, team_score_avg)
{
	local output_type = -1;
	// local origin = this.World.Assets.getOrigin().getID();
	local origin = wolrd_state.m.CampaignSettings.StartingScenario.getID();
	local output_condition;
	if(origin in BroOutputConditionArray)
		output_condition = BroOutputConditionArray[origin];
	else
		output_condition = BroOutputConditionArray["common"];
	for(local i = 0; i < output_condition.len(); i++)
	{
		local cond = output_condition[i];
		if(cond[0] == BroOutput.TeamScore)
		{
			if(team_score_avg > cond[1])
			{
				output_type = i;
				return output_type;
			}
		}
		else if(cond[0] == BroOutput.RoleScore)
		{
			local cond_size = 3;
			local bros_num = bros_entries.len();
			local bros_use_flag = array(bros_num, 0);
			local cond_num = (cond.len() - 1) / cond_size;
			for(local j = 0; j < cond_num; j++)
			{
				local role_thold = cond[1 + cond_size * j + 0];
				local request_num = cond[1 + cond_size * j + 1];
				local role_type = cond[1 + cond_size * j + 2];
				for(local k = 0; k < bros_num; k++)
				{
					if(bros_use_flag[k] > 0)
						continue;
					if(request_num == 0)
						break;
					local score_ = bros_sort_entries[RoleNum * k + role_type][BroSortEntry.RoleScore];
					if(score_ > role_thold)
					{
						request_num--;
						bros_use_flag[k] = 1;
					}
				}
				if(request_num > 0)
					break;
				if(j == (cond_num - 1) && request_num == 0)
				{
					output_type = i;
					return output_type;
				}
			}
		}
		else if(cond[0] == BroOutput.AnyRoleScore)
		{
			local cond_size = 2;
			local bros_num = bros_entries.len();
			local bros_use_flag = array(bros_num, 0);
			local cond_num = (cond.len() - 1) / cond_size;
			for(local j = 0; j < cond_num; j++)
			{
				local role_thold = cond[1 + cond_size * j + 0];
				local request_num = cond[1 + cond_size * j + 1];
				// local role_type = cond[1 + cond_size * j + 2];
				for(local k = 0; k < bros_num; k++)
				{
					if(bros_use_flag[k] > 0)
						continue;
					if(request_num == 0)
						break;
					local score_ = bros_entries[k][BroScoreEntry.BestRoleScore];
					local role_type = bros_entries[k][BroScoreEntry.BestRoleScoreType];
					// local score_ = bros_sort_entries[RoleNum * k + role_type][BroSortEntry.RoleScore];
					if(role_type != Role.RoleUseless && score_ > role_thold)
					{
						request_num--;
						bros_use_flag[k] = 1;
					}
				}
				if(request_num > 0)
					break;
				if(j == (cond_num - 1) && request_num == 0)
				{
					output_type = i;
					return output_type;
				}
			}
		}
		else if(cond[0] == BroOutput.RoleAttr)
		{
			local cond_size = (AttrNum + 1);
			local bros_num = bros_entries.len();
			local bros_use_flag = array(bros_num, 0);
			local cond_num = (cond.len() - 1) / cond_size;
			for(local j = 0; j < cond_num; j++)
			{
				local request_num = cond[1 + cond_size * j + 0];
				local attr_thold = cond.slice(1 + cond_size * j + 1, 1 + cond_size * j + 1 + AttrNum);
				for(local k = 0; k < bros_num; k++)
				{
					if(bros_use_flag[k] > 0)
						continue;
					if(request_num == 0)
						break;
					local pass_flag = true;
					for(local l = 0; l < AttrNum; l++)
					{
						if(attr_thold[l] > bros_entries[k][BroScoreEntry.MaxAttr][l])
						{
							pass_flag = false;
							break;
						}
					}

					if(pass_flag)
					{
						request_num--;
						bros_use_flag[k] = 1;
					}
				}
				if(request_num > 0)
					break;
				if(j == (cond_num - 1) && request_num == 0)
				{
					output_type = i;
					return output_type;
				}
			}
		}
		else if(cond[0] == BroOutput.BrotherFilter)
		{
			// Every counted brother must satisfy the whole rule. No RNG calls.
			local remaining = cond[1];
			foreach(brother in bros_entries)
			{
				local pass = true;
				for(local attribute = 0; attribute < AttrNum; attribute++)
					if(brother[BroScoreEntry.MaxAttr][attribute] < cond[2][attribute]) pass = false;
				if(!pass) continue;
				local held = brother[BroScoreEntry.Trait];
				foreach(trait in cond[4])
					if(held.find(trait) != null) pass = false;
				if(!pass) continue;
				local found = 0;
				foreach(trait in cond[3])
					if(held.find(trait) != null) found++;
				if(cond[3].len() > 0 && (cond[5] ? found != cond[3].len() : found == 0)) continue;
				remaining--;
				if(remaining == 0) return i;
			}
		}
		else if(cond[0] == BroOutput.RoleTraitScore)
		{
			local cond_size = 5;
			local bros_num = bros_entries.len();
			local bros_use_flag = array(bros_num, 0);
			local cond_num = (cond.len() - 1) / cond_size;
			for(local j = 0; j < cond_num; j++)
			{
				local role_thold = cond[1 + cond_size * j + 0];
				local request_num = cond[1 + cond_size * j + 1];
				local role_type = cond[1 + cond_size * j + 2];
				local match_trait = cond.slice(1 + cond_size * j + 3, 1 + 5 * j + cond_size);
				for(local k = 0; k < bros_num; k++)
				{
					if(bros_use_flag[k] > 0)
						continue;
					if(request_num == 0)
						break;
					local score_ = bros_sort_entries[RoleNum * k + role_type][BroSortEntry.RoleScore];
					if(score_ > role_thold)
					{
						local pass_flag = true;
						foreach (trait in match_trait)
						{
							if(trait == "")
								continue;
							if(bros_entries[k][BroScoreEntry.Trait].find(trait) == null)
							{
								pass_flag = false;
								break;
							}
						}
						if(pass_flag)
						{
							request_num--;
							bros_use_flag[k] = 1;
						}
					}
				}
				if(request_num > 0)
					break;
				if(j == (cond_num - 1) && request_num == 0)
				{
					output_type = i;
					return output_type;
				}
			}
		}
		else if(cond[0] == BroOutput.RoleTraitScoreIndex)
		{
			local cond_size = 5;
			local bros_num = bros_entries.len();
			local cond_num = (cond.len() - 1) / cond_size;
			local pass_flag = true;
			for(local j = 0; j < cond_num; j++)
			{
				local bro_index = cond[1 + cond_size * j + 0];
				local role_thold = cond[1 + cond_size * j + 1];
				local role_type = cond[1 + cond_size * j + 2];
				local match_trait = cond.slice(1 + cond_size * j + 3, 1 + cond_size * j + cond_size);
				if((bro_index + 1) > bros_num)
				{
					this.logError("Bro index larger than limit");
					continue;
				}
				local score_ = bros_sort_entries[RoleNum * bro_index + role_type][BroSortEntry.RoleScore];
				if(score_ > role_thold)
				{
					foreach (trait in match_trait)
					{
						if(trait == "")
							continue;
						if(bros_entries[bro_index][BroScoreEntry.Trait].find(trait) == null)
						{
							pass_flag = false;
							break;
						}
					}
				}
				else
				{
					pass_flag = false;
				}
				if(!pass_flag)
					break;
				if(j == (cond_num - 1) && pass_flag == true)
				{
					output_type = i;
					return output_type;
				}
			}
		}
		else
		{
			this.logError("unknown bro output conditon type");
		}
	}
	return output_type;
}

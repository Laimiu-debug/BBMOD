::include("seed_generator/define_lair");

local gt = this.getroottable();

local checkNamedAttrMatch = function(id, request_attr_dict, item)
{
	// this.logInfo("checkNamedAttrMatch: " + id);
	local match = false;
	local request_attr_num = request_attr_dict[id].len();
	if(gt.SeedGenerator.NamedIndexDict[item.m.NamedInitIndex][0] in request_attr_dict[id])
	{
		local rate = this.Math.round(100.0 * (gt.SeedGenerator.NamedIndexDict[item.m.NamedInitIndex][1] * 1.0 - gt.SeedGenerator.NamedIndexDict[item.m.NamedInitIndex][2])
			/ (gt.SeedGenerator.NamedIndexDict[item.m.NamedInitIndex][3] - gt.SeedGenerator.NamedIndexDict[item.m.NamedInitIndex][2]));
		if(rate >= request_attr_dict[id][gt.SeedGenerator.NamedIndexDict[item.m.NamedInitIndex][0]])
		{
			request_attr_num--;
		}
	}
	if(gt.SeedGenerator.NamedIndexDict[item.m.NamedInitIndex][4] in request_attr_dict[id])
	{
		local rate = this.Math.round(100.0 * (gt.SeedGenerator.NamedIndexDict[item.m.NamedInitIndex][5] * 1.0 - gt.SeedGenerator.NamedIndexDict[item.m.NamedInitIndex][6])
			/ (gt.SeedGenerator.NamedIndexDict[item.m.NamedInitIndex][7] - gt.SeedGenerator.NamedIndexDict[item.m.NamedInitIndex][6]));
		if(rate >= request_attr_dict[id][gt.SeedGenerator.NamedIndexDict[item.m.NamedInitIndex][4]])
		{
			request_attr_num--;
		}
	}

	if(request_attr_num <= 0)
	{
		match = true;
	}
	return match;
}

gt.SeedGenerator.lairOutoutCheck <- function()
{
	local output_type = -1;
	foreach( i, cond in LairOutputConditionArray )
	{
		if(cond[0] == LairOutput.NamedAttrValue || cond[0] == LairOutput.NamedAttrValueBroOutput || cond[0] == LairOutput.NamedAttrValueStrength
			|| cond[0] == LairOutput.NamedNumber)
		{
			local cond_size = 6;
			local cond_num = (cond.len() - 1) / cond_size;
			local request_num_dict = {};
			local request_attr_dict = {};
			local request_total_num = 0;
			local skip = 1;
			local request_strength = 1000;
			if(cond[0] == LairOutput.NamedAttrValueBroOutput)
			{
				local request_bro_output_type = cond[1];
				if(request_bro_output_type != bro_output_type)
					continue;
				skip = 2;
			}
			if(cond[0] == LairOutput.NamedAttrValueStrength)
			{
				request_strength = cond[1];
				skip = 2;
			}
			if(cond[0] == LairOutput.NamedNumber)
			{
				request_total_num = cond[1];
				if(named_total_num >= request_total_num)
				{
					output_type = i;
					return output_type;
				}
				else
					continue;
			}

			for(local j = 0; j < cond_num; j++)
			{
				local request_name = cond[skip + cond_size * j + 0];
				local request_num = cond[skip + cond_size * j + 1];
				local request_attr1 = cond[skip + cond_size * j + 2];
				local request_attr_thr1 = cond[skip + cond_size * j + 3];
				local request_attr2 = cond[skip + cond_size * j + 4];
				local request_attr_thr2 = cond[skip + cond_size * j + 5];
				request_num_dict[request_name] <- request_num;
				request_attr_dict[request_name] <- {};
				if(request_attr1 != "")
					request_attr_dict[request_name][request_attr1] <- request_attr_thr1;
				if(request_attr2 != "")
					request_attr_dict[request_name][request_attr2] <- request_attr_thr2;
				request_total_num += request_num;
			}

			foreach( lair_info in lair_info_list )
			{
				if(request_strength < lair_info[LairInfoEntry.Strength])
				{
					continue;
				}
				if(request_total_num <= 0)
					break;
				foreach(item in lair_info[LairInfoEntry.NamedItemsList])
				{
					if(request_total_num <= 0)
						break;
					if(item.isItemType(this.Const.Items.ItemType.Helmet)) // 头盔
					{
						if( "helmet" in request_num_dict || item.m.ID in request_num_dict )
						{
							local id = "helmet";
							if(item.m.ID in request_num_dict)
								id = item.m.ID;
							if(request_num_dict[id] <= 0)
								continue;
							if(checkNamedAttrMatch(id, request_attr_dict, item))
							{
								request_num_dict[id]--;
								request_total_num--;
								continue;
							}
						}
					}
					else if(item.isItemType(this.Const.Items.ItemType.Armor)) // 护甲
					{
						if( "armor" in request_num_dict || item.m.ID in request_num_dict )
						{
							local id = "armor";
							if(item.m.ID in request_num_dict)
								id = item.m.ID;
							if(request_num_dict[id] <= 0)
								continue;
							if(checkNamedAttrMatch(id, request_attr_dict, item))
							{
								request_num_dict[id]--;
								request_total_num--;
								continue;
							}
						}
					}
					else if(item.isItemType(this.Const.Items.ItemType.Shield)) // 护盾
					{
						if( "shield" in request_num_dict || item.m.ID in request_num_dict )
						{
							local id = "shield";
							if(item.m.ID in request_num_dict)
								id = item.m.ID;
							if(request_num_dict[id] <= 0)
								continue;
							if(checkNamedAttrMatch(id, request_attr_dict, item))
							{
								request_num_dict[id]--;
								request_total_num--;
								continue;
							}
						}
					}
					else if(item.isItemType(this.Const.Items.ItemType.MeleeWeapon) && item.isItemType(this.Const.Items.ItemType.TwoHanded)) // 双手近战
					{
						if( "two_hand" in request_num_dict || "weapon" in request_num_dict || item.m.ID in request_num_dict )
						{
							local id = "two_hand";
							if("weapon" in request_num_dict)
								id = "weapon";
							if(item.m.ID in request_num_dict)
								id = item.m.ID;
							if(request_num_dict[id] <= 0)
								continue;
							if(checkNamedAttrMatch(id, request_attr_dict, item))
							{
								request_num_dict[id]--;
								request_total_num--;
								continue;
							}
						}
					}
					else if(item.isItemType(this.Const.Items.ItemType.MeleeWeapon) && item.isItemType(this.Const.Items.ItemType.OneHanded)) // 单手近战
					{
						if( "one_hand" in request_num_dict || "weapon" in request_num_dict || item.m.ID in request_num_dict )
						{
							local id = "one_hand";
							if("weapon" in request_num_dict)
								id = "weapon";
							if(item.m.ID in request_num_dict)
								id = item.m.ID;
							if(request_num_dict[id] <= 0)
								continue;
							if(checkNamedAttrMatch(id, request_attr_dict, item))
							{
								request_num_dict[id]--;
								request_total_num--;
								continue;
							}
						}
					}
					else if(item.isItemType(this.Const.Items.ItemType.RangedWeapon)) // 远程武器
					{
						if( "range" in request_num_dict || "weapon" in request_num_dict || item.m.ID in request_num_dict )
						{
							local id = "range";
							if("weapon" in request_num_dict)
								id = "weapon";
							if(item.m.ID in request_num_dict)
								id = item.m.ID;
							if(request_num_dict[id] <= 0)
								continue;
							if(checkNamedAttrMatch(id, request_attr_dict, item))
							{
								request_num_dict[id]--;
								request_total_num--;
								continue;
							}
						}
					}
				}
			}

			if(request_total_num <= 0)
			{
				output_type = i;
				return output_type;
			}
		}
		else
		{
			this.logError("unknown lair output conditon type");
		}
	}
	return output_type;
}
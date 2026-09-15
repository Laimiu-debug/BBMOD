::include("seed_generator/define_lair");

local gt = this.getroottable();

gt.SeedGenerator.mapOutputCheck <- function()
{
    local output_type = -1;
    foreach( i, cond in MapOutputConditionArray )
    {
        local cond_num = cond.len() / 2;
        local cond_match = true;
        for( local j = 0; j < cond_num; j++)
        {
            local cond_type = cond[2*j];
            local cond_value = cond[2*j + 1];
            if(cond_type == MapOutput.SettlementNum)
            {
                if(settlements_num < cond_value)
                {
                    cond_match = false;
                    break;
                }
            }
            else if(cond_type == MapOutput.PortNum)
            {
                if(port_num < cond_value)
                {
                    cond_match = false;
                    break;
                }
            }
            else if(cond_type == MapOutput.CityPortNum)
            {
                if(city_port_num < cond_value)
                {
                    cond_match = false;
                    break;
                }
            }
            else if(cond_type == MapOutput.PortMeanDis)
            {
                if(settlement_port_avg_dis > cond_value)
                {
                    cond_match = false;
                    break;
                }
            }
            else if(cond_type == MapOutput.MeanDis)
            {
                if(settlement_avg_dis > cond_value)
                {
                    cond_match = false;
                    break;
                }
            }
            else if(cond_type == MapOutput.ArenaPort)
            {
                if(arena_port < cond_value)
                {
                    cond_match = false;
                    break;
                }
            }
            else if(cond_type == MapOutput.ProductsNum)
            {
                if(products_num < cond_value)
                {
                    cond_match = false;
                    break;
                }
            }
            else if(cond_type == MapOutput.ProductsValue)
            {
                if(products_total_value < cond_value)
                {
                    cond_match = false;
                    break;
                }
            }
            else if(cond_type == MapOutput.PortProductsValue)
            {
                if(products_port_total_value < cond_value)
                {
                    cond_match = false;
                    break;
                }
            }
            else if(cond_type == MapOutput.ConnectedNum)
            {
                if(connected_info[ConnectedInfoEntry.SettlementsNum] < cond_value)
                {
                    cond_match = false;
                    break;
                }
            }
            else if(cond_type == MapOutput.ConnectedRoad)
            {
                if(connected_info[ConnectedInfoEntry.AvgRoadSize] > cond_value)
                {
                    cond_match = false;
                    break;
                }
            }
            else if(cond_type == MapOutput.BuildNum)
            {
                if(build_num < cond_value)
                {
                    cond_match = false;
                    break;
                }
            }
            else if(cond_type == MapOutput.AttachedNum)
            {
                if(attached_num < cond_value)
                {
                    cond_match = false;
                    break;
                }
            }
            else if(cond_type == MapOutput.UpperLeftPortNum)
            {
                if(port_location[PortLocation.UpperLeft] < cond_value)
                {
                    cond_match = false;
                    break;
                }
            }
            else if(cond_type == MapOutput.LowerLeftPortNum)
            {
                if(port_location[PortLocation.LowerLeft] < cond_value)
                {
                    cond_match = false;
                    break;
                }
            }
            else if(cond_type == MapOutput.MiddlePortNum)
            {
                if(port_location[PortLocation.Middle] < cond_value)
                {
                    cond_match = false;
                    break;
                }
            }
            else if(cond_type == MapOutput.UpperRightPortNum)
            {
                if(port_location[PortLocation.UpperRight] < cond_value)
                {
                    cond_match = false;
                    break;
                }
            }
            else if(cond_type == MapOutput.LowerRightPortNum)
            {
                if(port_location[PortLocation.LowerRight] < cond_value)
                {
                    cond_match = false;
                    break;
                }
            }
            else if(cond_type == MapOutput.PortTypeNum)
            {
                local port_type_num = 0;
                for( local i = 0; i < PortLocationNum; i++ )
                {
                    if(port_location[i] > 0)
                        port_type_num++;
                }
                if(port_type_num < cond_value)
                {
                    cond_match = false;
                    break;
                }
            }
            else if(cond_type == MapOutput.ArmorsmithNum)
            {
                if(armorsmith_num < cond_value)
                {
                    cond_match = false;
                    break;
                }
            }
            else if(cond_type == MapOutput.WeaponsmithNum)
            {
                if(weaponsmith_num < cond_value)
                {
                    cond_match = false;
                    break;
                }
            }
            else if(cond_type == MapOutput.FletchernNum)
            {
                if(fletcher_num < cond_value)
                {
                    cond_match = false;
                    break;
                }
            }
            else if(cond_type == MapOutput.ConnectedLargeSettlementsNum)
            {
                if(connected_info[ConnectedInfoEntry.LargeSettlementsNum] < cond_value)
                {
                    cond_match = false;
                    break;
                }
            }
            else if(cond_type == MapOutput.ConnectedLargeFortNum)
            {
                if(connected_info[ConnectedInfoEntry.LargeFortNum] < cond_value)
                {
                    cond_match = false;
                    break;
                }
            }
            else if(cond_type == MapOutput.ConnectedPortNum)
            {
                if(connected_info[ConnectedInfoEntry.PortNum] < cond_value)
                {
                    cond_match = false;
                    break;
                }
            }
            else if(cond_type == MapOutput.SwampNum)
            {
                if(settlements_type_num[SettlementType.Swamp] < cond_value)
                {
                    cond_match = false;
                    break;
                }
            }
            else if(cond_type == MapOutput.SnowNum)
            {
                if(settlements_type_num[SettlementType.Snow] < cond_value)
                {
                    cond_match = false;
                    break;
                }
            }
            else if(cond_type == MapOutput.TundraNum)
            {
                if(settlements_type_num[SettlementType.Tundra] < cond_value)
                {
                    cond_match = false;
                    break;
                }
            }
            else if(cond_type == MapOutput.NoLostLargeSettlements)
            {
                if(cond_value > 0)
                {
                    if(large_fort_num != 2 || large_settlement_num != 3 || city_num != 3)
                    {
                        cond_match = false;
                        break;
                    }
                }
            }
            else if(cond_type == MapOutput.GemMineNum)
            {
                if(cond_value > 0)
                {
                    if(attached_id_num_dict["attached_location.gem_mine"] < cond_value)
                    {
                        cond_match = false;
                        break;
                    }
                }
            }
            else if(cond_type == MapOutput.SaltMineNum)
            {
                if(cond_value > 0)
                {
                    if(attached_id_num_dict["attached_location.salt_mine"] < cond_value)
                    {
                        cond_match = false;
                        break;
                    }
                }
            }
            else
            {
                cond_match = false;
                this.logError("unknown map output conditon type");
            }
        }

        if(cond_match)
        {
            output_type = i;
            break;
        }
    }
    return output_type;
}
// No random calls or item mutations: consume the original recorded affixes.
::include("seed_generator/config_weapon_rating");
local gt = this.getroottable();

gt.SeedGenerator.weaponAffixRolls <- function(item)
{
    if (!("NamedInitIndex" in item.m) || !(item.m.NamedInitIndex in NamedIndexDict)) return null;
    local values = NamedIndexDict[item.m.NamedInitIndex];
    if (values.len() != 8) return null;
    local rolls = {};
    for (local offset = 0; offset <= 4; offset += 4)
    {
        if (values[offset + 3] <= values[offset + 2] || values[offset] in rolls) return null;
        local rate = this.Math.round(100.0 * (values[offset + 1] - values[offset + 2])
            / (values[offset + 3] - values[offset + 2])).tointeger();
        if (rate < 0 || rate > 100) return null;
        rolls[values[offset]] <- rate;
    }
    return rolls;
};

gt.SeedGenerator.rateNamedWeapon <- function(item, rolls = null)
{
    if (!(item.m.ID in WeaponRatingEligible)) return null;
    if (rolls == null) rolls = weaponAffixRolls(item);
    if (rolls == null || rolls.len() != 2) return null;
    local eligible = WeaponRatingEligible[item.m.ID];
    local numerator = 0, qualitySum = 0;
    foreach (attribute, raw in rolls)
    {
        if (eligible.find(attribute) == null) return null;
        local quality = attribute == NamedAttr.StaminaModifier ? 100 - raw : raw;
        qualitySum += quality;
        numerator += WeaponRatingWeights[attribute] * (100 + quality);
    }
    local first = 0, second = 0;
    foreach (attribute in eligible)
    {
        local weight = WeaponRatingWeights[attribute];
        if (weight > first) { second = first; first = weight; }
        else if (weight > second) second = weight;
    }
    local denominator = 2 * (first + second);
    return [((numerator + denominator / 2) / denominator).tointeger(), ((qualitySum + 1) / 2).tointeger()];
};

local matchesType = function(item, kind)
{
    local flags = this.Const.Items.ItemType;
    local ranged = item.isItemType(flags.RangedWeapon);
    local melee = item.isItemType(flags.MeleeWeapon);
    if (!ranged && !melee) return false;
    if (kind == "weapon" || kind == item.m.ID) return true;
    if (kind == "range") return ranged;
    if (kind == "one_hand") return melee && item.isItemType(flags.OneHanded);
    if (kind == "two_hand") return melee && item.isItemType(flags.TwoHanded);
    return false;
};

// row: [type, count, damage, penetration, useful score, roll quality]; -1 = any.
local matchesRow = function(item, row)
{
    if (!matchesType(item, row[0])) return false;
    if (row[2] < 0 && row[3] < 0 && row[4] < 0 && row[5] < 0) return true;
    local rolls = gt.SeedGenerator.weaponAffixRolls(item);
    if (rolls == null) return false;
    local attributes = gt.SeedGenerator.NamedAttr;
    if (row[2] >= 0 && (!(attributes.RegularDamage in rolls) || rolls[attributes.RegularDamage] < row[2])) return false;
    if (row[3] >= 0 && (!(attributes.DirectDamageAdd in rolls) || rolls[attributes.DirectDamageAdd] < row[3])) return false;
    if (row[4] >= 0 || row[5] >= 0)
    {
        local rating = gt.SeedGenerator.rateNamedWeapon(item, rolls);
        if (rating == null || rating[0] < row[4] || rating[1] < row[5]) return false;
    }
    return true;
};

gt.SeedGenerator.checkWeaponFilter <- function(cond)
{
    if (cond.len() < 9 || (cond.len() - 3) % 6 != 0 || named_total_num < cond[1]) return false;
    local items = [];
    foreach (lair in lair_info_list)
        foreach (item in lair[LairInfoEntry.NamedItemsList])
            if (items.find(item) == null) items.append(item);
    local rows = [], candidates = [], requested = 0;
    for (local offset = 3; offset < cond.len(); offset += 6)
    {
        local row = cond.slice(offset, offset + 6);
        local eligible = [];
        foreach (index, item in items) if (matchesRow(item, row)) eligible.append(index);
        if (cond[2] == "any")
        {
            if (eligible.len() >= row[1]) return true;
        }
        else if (eligible.len() < row[1]) return false;
        rows.append(row);
        candidates.append(eligible);
        requested += row[1];
    }
    if (cond[2] != "all" || requested > items.len()) return false;

    // Capacitated bipartite matching. Reassign an earlier broad request when
    // a later specific request needs its item; never count one item twice.
    // A row is visited once per search, bounding recursion by at most 20 rows.
    local owners = array(items.len(), -1);
    local assign = null;
    assign = function(row, seen)
    {
        if (seen[row]) return false;
        seen[row] = true;
        foreach (index in candidates[row])
        {
            if (owners[index] < 0 || assign(owners[index], seen))
            {
                owners[index] = row;
                return true;
            }
        }
        return false;
    };
    foreach (index, row in rows)
        for (local count = 0; count < row[1]; count++)
            if (!assign(index, array(rows.len(), false))) { assign = null; return false; }
    // Break the recursive closure's self-reference before the next seed.
    assign = null;
    return true;
};

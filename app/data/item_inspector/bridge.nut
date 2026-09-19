// Independently authored, read-only BBMOD tooltip bridge. No item creation or RNG.
::BBMODItemInspector <- {
    Sequence = 0,
    Token = null,
    Snapshot = null,
    function member(_object, _key)
    {
        // Game members can be WeakTableRef instances. `key in object` does not
        // consult their _get delegate even though object[key] reads correctly.
        try { return _object[_key]; } catch (error) { return null; }
    },
    function quote(_value)
    {
        local result = "\"";
        foreach (c in _value.tostring())
        {
            if (c == 34) result += "\\\"";
            else if (c == 92) result += "\\\\";
            else if (c < 32) result += " ";
            else result += c.tochar();
        }
        return result + "\"";
    },
    function read(_item)
    {
        // Only copy primitive fields. Never call getName/getTooltip from here.
        local fields = ["ConditionMax", "StaminaModifier", "RegularDamage", "RegularDamageMax",
            "ArmorDamageMult", "DirectDamageMult", "DirectDamageAdd", "ChanceToHitHead", "ShieldDamage",
            "AmmoMax", "AdditionalAccuracy", "FatigueOnSkillUse", "MeleeDefense", "RangedDefense"];
        local m = _item.m;
        local stats = "", attachment = null;
        attachment = this.member(m, "Upgrade");
        foreach (key in fields)
        {
            local value = this.member(m, key);
            if (attachment != null)
            {
                local previous = null;
                if (key == "ConditionMax") previous = this.member(attachment.m, "PreviousCondition");
                if (key == "StaminaModifier") previous = this.member(attachment.m, "PreviousStamina");
                if (typeof previous == "integer" || typeof previous == "float") value = previous;
            }
            if (typeof value != "integer" && typeof value != "float") continue;
            if (stats.len() != 0) stats += ",";
            stats += this.quote(key) + ":" + value;
        }
        this.Snapshot = ",\"id\":" + this.quote(m.ID) +
            ",\"name\":" + this.quote(m.Name) + ",\"named\":" +
            ((_item.isItemType(::Const.Items.ItemType.Named)) ? "true" : "false") +
            ",\"attachment\":" + (attachment == null ? "false" : "true") +
            ",\"stats\":{" + stats + "}";
    },
    function emit(_body)
    {
        this.Sequence++;
        ::logInfo("BBMOD_ITEM_V1 {\"schema\":1,\"seq\":" + this.Sequence + _body + "}");
    }
};
::mods_hookNewObject("ui/screens/tooltip/tooltip_events", function(o) {
    local original = o.tactical_helper_addHintsToTooltip;
    o.tactical_helper_addHintsToTooltip = function(_activeEntity, _entity, _item, _itemOwner, _ignoreStashLocked = false)
    {
        local result = original(_activeEntity, _entity, _item, _itemOwner, _ignoreStashLocked);
        // A bridge failure must never break the game's original tooltip.
        try { if (::BBMODItemInspector.Token != null) ::BBMODItemInspector.read(_item); }
        catch (error) { ::logWarning("BBMOD item inspector: " + error); }
        return result;
    };
});
::mods_hookNewObject("ui/screens/tooltip/modules/tooltip", function(o) {
    // The ordinary UI bridge returns the original tooltip unchanged. Capture is
    // restricted to this one query; unrelated tooltip builds cannot replace it.
    o.bbmodInspectorQuery <- function(_data)
    {
        local bridge = ::BBMODItemInspector;
        if (typeof _data != "array" || _data.len() != 4) return null;
        local token = _data[3];
        if (typeof token != "integer" || token <= 0) return null;
        bridge.Token = token;
        bridge.Snapshot = null;
        local result;
        try { result = this.onQueryUIItemTooltipData([_data[0], _data[1], _data[2]]); }
        catch (error) { bridge.Token = null; bridge.Snapshot = null; throw error; }
        bridge.Token = null;
        if (bridge.Snapshot != null)
            bridge.emit(",\"kind\":\"item\",\"token\":" + token + bridge.Snapshot);
        bridge.Snapshot = null;
        return result;
    };
    o.bbmodInspectorHover <- function(_data)
    {
        if (typeof _data != "array" || _data.len() != 3 || typeof _data[0] != "integer" ||
            _data[0] <= 0 || typeof _data[1] != "bool") return;
        local bounds = "null";
        if (_data[1])
        {
            if (typeof _data[2] != "array" || _data[2].len() != 6) return;
            bounds = "[";
            foreach (i, value in _data[2])
            {
                if (typeof value != "integer" && typeof value != "float") return;
                if (i > 0) bounds += ",";
                bounds += value;
            }
            bounds += "]";
        }
        ::BBMODItemInspector.emit(",\"kind\":\"hover\",\"token\":" + _data[0] +
            ",\"visible\":" + (_data[1] ? "true" : "false") + ",\"bounds\":" + bounds);
    };
});
::logInfo("BBMOD item inspector ready v3");

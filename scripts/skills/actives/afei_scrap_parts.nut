this.afei_scrap_parts <- this.inherit("scripts/skills/skill", {
	m = {},
	function create()
	{
		this.m.ID = "actives.afei_scrap_parts";
		this.m.Name = "地精出身·余料";
		this.m.Description = "抹茶在名册时：每累计实际消耗 7 点工具用于维修，获得 1 次余料减免（最多存 3）。下次至少原需 2 工具的合法维修自动少耗 1。";
		this.m.Icon = "ui/orientation/shortsword_orientation.png";
		this.m.Type = this.Const.SkillType.Special;
		this.m.IsActive = false;
	}
	function getTooltip()
	{
		local charges = this.World.Flags.getAsInt("afei_scrap_charges");
		local prog = this.World.Flags.getAsInt("afei_scrap_progress");
		return [
			{ id = 1, type = "title", text = this.getName() },
			{ id = 2, type = "description", text = this.getDescription() },
			{ id = 10, type = "text", icon = "ui/icons/asset_armor_parts.png", text = "余料减免：" + charges + " / 3 · 累计进度 " + prog + " / 7" }
		];
	}
});

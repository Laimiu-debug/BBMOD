this.afei_captain_background <- this.inherit("scripts/skills/backgrounds/character_background", {
	m = {},
	function create()
	{
		this.character_background.create();
		this.m.ID = "background.afei_captain";
		this.m.Name = "远征团长";
		this.m.Icon = "ui/backgrounds/background_15.png";
		this.m.BackgroundDescription = "靠讲战报换晚饭的团长。旗面很大，名册只有三行——他把墨擦在裤子上签字：少了什么先找我。";
		this.m.GoodEnding = "黑旗上仍写着他的名字。";
		this.m.BadEnding = "名册上的这一行被墨水轻轻划去。";
		this.m.HiringCost = 0;
		this.m.DailyCost = 6;
		this.m.Excluded = [
			"trait.greedy",
			"trait.disloyal"
		];
		this.m.Faces = this.Const.Faces.AllMale;
		this.m.Hairs = this.Const.Hair.AllMale;
		this.m.HairColors = this.Const.HairColors.All;
		this.m.Beards = this.Const.Beards.All;
		this.m.Bodies = this.Const.Bodies.Muscular;
	}

	function onBuildDescription()
	{
		return this.m.BackgroundDescription;
	}

	function onChangeAttributes()
	{
		return {
			Hitpoints = [0, 0],
			Bravery = [0, 0],
			Stamina = [0, 0],
			MeleeSkill = [0, 0],
			RangedSkill = [0, 0],
			MeleeDefense = [0, 0],
			RangedDefense = [0, 0],
			Initiative = [0, 0]
		};
	}

	function onAddEquipment()
	{
		local items = this.getContainer().getActor().getItems();
		items.equip(this.new("scripts/items/weapons/wooden_stick"));
		items.equip(this.new("scripts/items/shields/wooden_shield"));
		items.equip(this.new("scripts/items/armor/tattered_surcoat"));
		items.equip(this.new("scripts/items/helmets/aketon_cap"));
	}
});

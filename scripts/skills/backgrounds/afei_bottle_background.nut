this.afei_bottle_background <- this.inherit("scripts/skills/backgrounds/character_background", {
	m = {},
	function create()
	{
		this.character_background.create();
		this.m.ID = "background.afei_bottle";
		this.m.Name = "瓶队前锋";
		this.m.Icon = "ui/backgrounds/background_19.png";
		this.m.BackgroundDescription = "烟港泥地球场上第一个往人缝里冲的人。护具裂了也不肯先退。";
		this.m.GoodEnding = "黑旗上仍写着他的名字。";
		this.m.BadEnding = "名册上的这一行被墨水轻轻划去。";
		this.m.HiringCost = 200;
		this.m.DailyCost = 24;
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
			Hitpoints = [
				0,
				0
			],
			Bravery = [
				0,
				0
			],
			Stamina = [
				0,
				0
			],
			MeleeSkill = [
				0,
				0
			],
			RangedSkill = [
				0,
				0
			],
			MeleeDefense = [
				0,
				0
			],
			RangedDefense = [
				0,
				0
			],
			Initiative = [
				0,
				0
			]
		};
	}

	function onAddEquipment()
	{
		// 设定：短剑与木盾；身甲60、头盔30
		local items = this.getContainer().getActor().getItems();
		items.equip(this.new("scripts/items/weapons/shortsword"));
		items.equip(this.new("scripts/items/shields/wooden_shield"));
		items.equip(this.new("scripts/items/armor/padded_leather"));
		items.equip(this.new("scripts/items/helmets/padded_nasal_helmet"));
	}
});

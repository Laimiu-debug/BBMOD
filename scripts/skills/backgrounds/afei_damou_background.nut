this.afei_damou_background <- this.inherit("scripts/skills/backgrounds/character_background", {
	m = {},
	function create()
	{
		this.character_background.create();
		this.m.ID = "background.afei_damou";
		this.m.Name = "驿站牵线人";
		this.m.Icon = "ui/backgrounds/afei_c03.png";
		this.m.BackgroundDescription = "总说认识一个大哥的前排。来了算谁的人，走的时候能不能把钱结清——两条都写在团约上。";
		this.m.GoodEnding = "黑旗上仍写着他的名字。";
		this.m.BadEnding = "名册上的这一行被墨水轻轻划去。";
		this.m.HiringCost = 0;
		this.m.DailyCost = 16;
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
		// 设定：短矛与木盾；身甲80、头盔40
		local items = this.getContainer().getActor().getItems();
		items.equip(this.new("scripts/items/weapons/militia_spear"));
		items.equip(this.new("scripts/items/shields/wooden_shield"));
		items.equip(this.new("scripts/items/armor/basic_mail_shirt"));
		items.equip(this.new("scripts/items/helmets/nasal_helmet"));
	}
});

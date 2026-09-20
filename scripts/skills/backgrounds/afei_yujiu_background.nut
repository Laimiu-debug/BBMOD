this.afei_yujiu_background <- this.inherit("scripts/skills/backgrounds/character_background", {
	m = {},
	function create()
	{
		this.character_background.create();
		this.m.ID = "background.afei_yujiu";
		this.m.Name = "渡口守夜";
		this.m.Icon = "ui/backgrounds/background_19.png";
		this.m.BackgroundDescription = "听见车轮就点灯。少收一枚钱要赔，多放一辆超载的车也要赔。";
		this.m.GoodEnding = "黑旗上仍写着他的名字。";
		this.m.BadEnding = "名册上的这一行被墨水轻轻划去。";
		this.m.HiringCost = 180;
		this.m.DailyCost = 10;
		this.m.Excluded = ["trait.greedy", "trait.disloyal"];
		this.m.Faces = this.Const.Faces.AllMale;
		this.m.Hairs = this.Const.Hair.AllMale;
		this.m.HairColors = this.Const.HairColors.All;
		this.m.Beards = this.Const.Beards.All;
		this.m.Bodies = this.Const.Bodies.Muscular;
	}
	function onBuildDescription() { return this.m.BackgroundDescription; }
	function onChangeAttributes()
	{
		return { Hitpoints=[0,0], Bravery=[0,0], Stamina=[0,0], MeleeSkill=[0,0], RangedSkill=[0,0], MeleeDefense=[0,0], RangedDefense=[0,0], Initiative=[0,0] };
	}
	function onAddEquipment()
	{
		local items = this.getContainer().getActor().getItems();
		items.equip(this.new("scripts/items/weapons/militia_spear"));
		items.equip(this.new("scripts/items/shields/buckler_shield"));
		items.equip(this.new("scripts/items/armor/padded_surcoat"));
		items.equip(this.new("scripts/items/helmets/aketon_cap"));
	}
});

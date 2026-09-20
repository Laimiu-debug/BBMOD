this.afei_shuaizi_background <- this.inherit("scripts/skills/backgrounds/character_background", {
	m = {},
	function create()
	{
		this.character_background.create();
		this.m.ID = "background.afei_shuaizi";
		this.m.Name = "守门鼓手";
		this.m.Icon = "ui/backgrounds/background_19.png";
		this.m.BackgroundDescription = "四拍走一车，八拍再开另一边。横杆磨出的掌茧能握住鼓槌。";
		this.m.GoodEnding = "黑旗上仍写着他的名字。";
		this.m.BadEnding = "名册上的这一行被墨水轻轻划去。";
		this.m.HiringCost = 240;
		this.m.DailyCost = 12;
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
		items.equip(this.new("scripts/items/weapons/bludgeon"));
		items.equip(this.new("scripts/items/shields/wooden_shield"));
		items.equip(this.new("scripts/items/armor/basic_mail_shirt"));
		items.equip(this.new("scripts/items/helmets/nasal_helmet"));
	}
});

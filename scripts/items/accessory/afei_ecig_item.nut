this.afei_ecig_item <- this.inherit("scripts/items/accessory/accessory", {
	m = {},
	function create()
	{
		this.accessory.create();
		this.m.ID = "accessory.afei_ecig";
		this.m.Name = "电子烟";
		this.m.Description = "阿飞的特殊饰品。战斗中可抽一口回血；不消耗、不毁坏，可反复使用。仅阿飞装备时可用。";
		this.m.SlotType = this.Const.ItemSlot.Accessory;
		this.m.ItemType = this.Const.Items.ItemType.Accessory;
		this.m.IsDroppedAsLoot = false;
		this.m.ShowOnCharacter = false;
		this.m.IconLarge = "";
		this.m.Icon = "accessory_14.png";
		this.m.Value = 0;
	}

	function getTooltip()
	{
		local result = [
			{
				id = 1,
				type = "title",
				text = this.getName()
			},
			{
				id = 2,
				type = "description",
				text = this.getDescription()
			},
			{
				id = 66,
				type = "text",
				text = this.getValueString()
			},
			{
				id = 3,
				type = "image",
				image = this.getIcon()
			},
			{
				id = 10,
				type = "text",
				icon = "ui/icons/health.png",
				text = "战斗技能：恢复 [color=" + this.Const.UI.Color.PositiveValue + "]20[/color] 生命（每回合一次）"
			},
			{
				id = 11,
				type = "text",
				icon = "ui/icons/special.png",
				text = "无限次使用：不消耗、不毁坏"
			},
			{
				id = 12,
				type = "text",
				icon = "ui/icons/warning.png",
				text = "仅阿飞可用"
			}
		];
		return result;
	}

	function playInventorySound(_eventType)
	{
		this.Sound.play("sounds/cloth_01.wav", this.Const.Sound.Volume.Inventory);
	}

	function onEquip()
	{
		this.accessory.onEquip();
		this.addSkill(this.new("scripts/skills/actives/afei_ecig_puff"));
	}
});

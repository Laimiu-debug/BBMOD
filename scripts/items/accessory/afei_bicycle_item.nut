this.afei_bicycle_item <- this.inherit("scripts/items/accessory/accessory", {
	m = {},
	function create()
	{
		this.accessory.create();
		this.m.ID = "accessory.afei_bicycle";
		this.m.Name = "自行车";
		this.m.Description = "阿飞随身带着的一辆旧车。车铃还响，踏板有点涩。\n\n小酒瓶若离队，可选择遗弃此车：阿飞永久获得经验获取 [color=#1e781e]×1.2[/color]（全战役仅一次）。未遗弃则保留物品，但不会获得该倍率。";
		this.m.SlotType = this.Const.ItemSlot.Accessory;
		this.m.ItemType = this.Const.Items.ItemType.Accessory;
		this.m.IsDroppedAsLoot = false;
		this.m.ShowOnCharacter = false;
		this.m.IconLarge = "";
		this.m.Icon = "accessory_09.png";
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
				icon = "ui/icons/xp_received.png",
				text = "遗弃后：阿飞经验获取 [color=" + this.Const.UI.Color.PositiveValue + "]×1.2[/color]（仅一次）"
			},
			{
				id = 11,
				type = "text",
				icon = "ui/icons/special.png",
				text = "装备本身不提供移速或先攻加成"
			}
		];
		return result;
	}

	function playInventorySound(_eventType)
	{
		this.Sound.play("sounds/cloth_01.wav", this.Const.Sound.Volume.Inventory);
	}
});

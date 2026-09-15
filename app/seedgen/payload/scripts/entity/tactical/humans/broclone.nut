this.broclone <- this.inherit("scripts/entity/tactical/human", {
	m = {},
	function create()
	{
		if (!("CloneCount" in this.Tactical.State.m))
		{
			this.Tactical.State.m.CloneCount <- 0;
		}
		local brothers = this.World.getPlayerRoster().getAll();
		local curbro = brothers[this.Tactical.State.m.CloneCount];
		//this.logDebug("oncreate"); 
		
		this.m.Type = this.Const.EntityType.BountyHunter;
		this.m.BloodType = this.Const.BloodType.Red;
		this.m.XP = curbro.getLevel() * 30;
		this.human.create();
		this.m.Faces = this.Const.Faces.AllMale;
		this.m.Hairs = this.Const.Hair.AllMale;
		this.m.HairColors = this.Const.HairColors.All;
		this.m.Beards = this.Const.Beards.All;
		if (curbro.hasRangedWeapon())
		{
			this.m.AIAgent = this.new("scripts/ai/tactical/agents/bounty_hunter_ranged_agent");
			this.m.AIAgent.addBehavior(this.new("scripts/ai/tactical/behaviors/ai_attack_handgonne"));
		}
		else
		{
			this.m.AIAgent = this.new("scripts/ai/tactical/agents/bounty_hunter_melee_agent");
		}
		this.m.AIAgent.setActor(this);
	}

	function onInit()
	{
		local brothers = this.World.getPlayerRoster().getAll();
		local curbro = brothers[this.Tactical.State.m.CloneCount];
		this.human.onInit();
		//this.logDebug("oninit"); 
		local b = this.m.BaseProperties;
		b.setValues(curbro.m.BaseProperties);
		this.m.ActionPoints = b.ActionPoints;
		this.m.Hitpoints = b.Hitpoints;
		this.m.CurrentProperties = clone b;
		this.m.Body = curbro.m.Body;
		this.m.Ethnicity = curbro.m.Ethnicity;
		this.m.Gender = curbro.m.Gender;
		this.m.Name = curbro.m.Name;
		this.m.Title = curbro.m.Title;
		local sprites = ["body",
			"head",
			"beard",
			"hair",
			"tattoo_body",
			"tattoo_head",
			"beard_top"
		];
		for( local i = 0; i < sprites.len(); i = ++i )
		{
			if (curbro.getSprite(sprites[i]).HasBrush)
			{
				this.getSprite(sprites[i]).setBrush(curbro.getSprite(sprites[i]).getBrush().Name);
			}
			else
			{
				this.getSprite(sprites[i]).resetBrush();
				continue;
			}
		} 
		this.getSprite("hair").Color = curbro.getSprite("hair").Color;
		this.getSprite("beard").Color = curbro.getSprite("beard").Color;
		
		foreach( skill in curbro.getSkills().m.Skills )
		{
			if ((skill.isType(this.Const.SkillType.Trait) || skill.isType(this.Const.SkillType.Perk) || skill.isType(this.Const.SkillType.PermanentInjury) || skill.isType(this.Const.SkillType.TemporaryInjury)) && !skill.isType(this.Const.SkillType.Background) && skill.m.ID != "perk.gifted") //
			{
				if (!skill.isType(this.Const.SkillType.Special) && !skill.isType(this.Const.SkillType.Active) && (!skill.isType(this.Const.SkillType.StatusEffect) || (skill.isType(this.Const.SkillType.StatusEffect) && skill.isType(this.Const.SkillType.Perk)) || (skill.isType(this.Const.SkillType.StatusEffect) && skill.isType(this.Const.SkillType.Trait))) && 
				!skill.isType(this.Const.SkillType.Item)) //!skill.isType(this.Const.SkillType.Racial) && 
				{
					//this.logDebug("skill "+this.IO.scriptFilenameByHash(skill.ClassNameHash)); 
					this.m.Skills.add(this.new(this.IO.scriptFilenameByHash(skill.ClassNameHash)));
				}
			}
		}
	}

	function assignRandomEquipment()
	{
		//this.logDebug("onequip"); 
		local brothers = this.World.getPlayerRoster().getAll();
		local curbro = brothers[this.Tactical.State.m.CloneCount];
		local itemz = curbro.m.Items;
		for( local i = 0; i < this.Const.ItemSlot.COUNT; i = ++i )
		{
			for( local j = 0; j < this.Const.ItemSlotSpaces[i]; j = ++j )
			{
				local curitem = itemz.m.Items[i][j];
				if (curitem != null && curitem != -1)
				{
					local newitem = this.new(this.IO.scriptFilenameByHash(curitem.ClassNameHash));
					newitem.m.Variant = curitem.m.Variant;
					if(curitem.isItemType(this.Const.Items.ItemType.Armor))
					{
						if (curitem.m.Upgrade != null)
						{
							newitem.setUpgrade(this.new(this.IO.scriptFilenameByHash(curitem.m.Upgrade.ClassNameHash)));
							//newitem.m.Upgrade.setArmor(newitem);
						}
					}
					newitem.updateVariant();
					if (this.Const.ItemSlotSpaces[i] == 1)
					{
						this.m.Items.equip(newitem);
					}
					else
					{
						this.m.Items.addToBag(newitem);
					}
					//this.logDebug("equipped "+this.IO.scriptFilenameByHash(curitem.ClassNameHash)); 
				}
			}
		}
		this.getSkills().update();
		this.Tactical.State.m.CloneCount = this.Tactical.State.m.CloneCount + 1;
		if (this.Tactical.State.m.CloneCount == brothers.len())
		{
			this.Tactical.State.m.CloneCount = 0;
		}
	}

});


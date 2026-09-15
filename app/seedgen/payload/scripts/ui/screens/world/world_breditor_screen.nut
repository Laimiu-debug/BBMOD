this.world_breditor_screen <- {
	m = {
		JSHandle = null,
		Visible = null,
		Animating = null,
		OnConnectedListener = null,
		OnDisconnectedListener = null,
		OnClosePressedListener = null
	},
	function isVisible()
	{
		return this.m.Visible != null && this.m.Visible == true;
	}

	function isAnimating()
	{
		if (this.m.Animating != null)
		{
			return this.m.Animating == true;
		}
		else
		{
			return false;
		}
	}

	function setOnConnectedListener( _listener )
	{
		this.m.OnConnectedListener = _listener;
	}

	function setOnDisconnectedListener( _listener )
	{
		this.m.OnDisconnectedListener = _listener;
	}

	function setOnClosePressedListener( _listener )
	{
		this.m.OnClosePressedListener = _listener;
	}

	function clearEventListener()
	{
		this.m.OnConnectedListener = null;
		this.m.OnDisconnectedListener = null;
		this.m.OnClosePressedListener = null;
	}

	function create()
	{
		this.m.Visible = false;
		this.m.Animating = false;
		this.m.JSHandle = this.UI.connect("WorldBreditorScreen", this);
	}

	function destroy()
	{
		this.clearEventListener();
		this.m.JSHandle = this.UI.disconnect(this.m.JSHandle);
	}

	function show( _withSlideAnimation = false )
	{
		if (this.m.JSHandle != null)
		{
			this.Tooltip.hide();
			this.m.JSHandle.asyncCall("show", this.queryRosterInformation());
		}
	}

	function hide( _withSlideAnimation = false )
	{
		if (this.m.JSHandle != null)
		{
			this.Tooltip.hide();
			this.m.JSHandle.asyncCall("hide", _withSlideAnimation);
		}
	}

	function onScreenConnected()
	{
		if (this.m.OnConnectedListener != null)
		{
			this.m.OnConnectedListener();
		}
	}

	function onScreenDisconnected()
	{
		if (this.m.OnDisconnectedListener != null)
		{
			this.m.OnDisconnectedListener();
		}
	}

	function onScreenShown()
	{
		this.m.Visible = true;
		this.m.Animating = false;
	}

	function onScreenHidden()
	{
		this.m.Visible = false;
		this.m.Animating = false;
		this.cantyouhaveonewaytocloseit();
	}

	function onScreenAnimating()
	{
		this.m.Animating = true;
	}

	function onClose()
	{
		if (this.m.OnClosePressedListener != null)
		{
			this.m.OnClosePressedListener();
		}
		this.cantyouhaveonewaytocloseit();
	}
	
	function cantyouhaveonewaytocloseit()
	{
 		local brothers = this.World.getPlayerRoster().getAll();
		foreach( b in brothers )
		{
			if(b.getTitle() == "ImmaBreditorBug")
			{
				this.World.getPlayerRoster().remove(b);
			}
			else
			{
				b.getSkills().update();
			}
			//this.logDebug("done");
		}; 
	}

	function queryRosterInformation(_id = null)
	{
		local fakebro = this.World.getPlayerRoster().create("scripts/entity/tactical/player");
		fakebro.setStartValuesEx(["cripple_background"]);
		fakebro.setTitle("ImmaBreditorBug");
		fakebro.setName("SendLog");
		
		local brothers = this.World.getPlayerRoster().getAll();
		local roster = [];
		//this.logDebug("1");
		local basestats = {
			Hitpoints = [50,60],
			Bravery = [30,40],
			Stamina = [90,100],
			MeleeSkill = [47,57],
			RangedSkill = [32,42],
			MeleeDefense = [0,5],
			RangedDefense = [0,5],
			Initiative = [100,110]
		};
		local traitstemp = this.Const.CharacterTraits;
		local extratraits = prepareyourtraits();
 		local injuries = this.Const.Injury.Permanent;
		local traits = [];
		foreach( trtmp in traitstemp )
		{
			traits.push(trtmp);
		} 
		foreach( trtxtr in extratraits )
		{
			traits.push(trtxtr);
		} 
		foreach( inj in injuries )
		{
			local injfixed = [inj.ID, "scripts/skills/"+inj.Script];
			traits.push(injfixed);
		} 
		
		local thirdvalue = null;
		local traitstemp = null;
		foreach( tr in traits )
		{
			traitstemp = this.new(tr[1]);
			thirdvalue = traitstemp.getIconColored();
			tr.push(thirdvalue);
			if (!fakebro.getSkills().hasSkill(tr[0]))
			{
				fakebro.getSkills().add(this.new(tr[1]));
			}
		}
		
		foreach( b in brothers )
		{
			if (_id != null && _id != b.getID())
			{continue;}
			local background = b.getBackground();
			local additionalstats = background.onChangeAttributes();
			//local properties = b.getCurrentProperties();
			
			local broskills = b.getSkills(); //b.getSkills().query(this.Const.SkillType.Trait),
			local brotraits = [];
			foreach( tr in traits )
			{
				if (broskills.hasSkill(tr[0]))
				{
					brotraits.push(tr);
				}
			}
			
			local e = {
				ID = b.getID(),
				Name = b.getName(),
				ImagePath = b.getImagePath(),
				ImageOffsetX = b.getImageOffsetX(),
				ImageOffsetY = b.getImageOffsetY(),
				Background = background.getID(),
				BackgroundImagePath = background.getIconColored(),
				BackgroundText = background.getDescription(),
				XpValue = b.getXP(),
				Level = b.getLevel(),
				LevelUps = b.m.LevelUps,
				PerkPoints = b.getPerkPoints(),
				Hitpoints = {
					Max = b.getBaseProperties().Hitpoints,
					MaxPlus = b.getHitpointsMax(),
					Talent = b.getTalents()[this.Const.Attributes.Hitpoints],
					BLimit = basestats.Hitpoints[1] + additionalstats.Hitpoints[1],
				},
				Stamina = {
					Max = b.getBaseProperties().Stamina,
					MaxPlus = b.getFatigueMax(),
					Talent = b.getTalents()[this.Const.Attributes.Fatigue],
					BLimit = basestats.Stamina[1] + additionalstats.Stamina[1],
				},
				Initiative = {
					Max = b.getBaseProperties().Initiative,
					MaxPlus = b.getInitiative(),
					Talent = b.getTalents()[this.Const.Attributes.Initiative],
					BLimit = basestats.Initiative[1] + additionalstats.Initiative[1],
				},
				Bravery = {
					Max = b.getBaseProperties().Bravery,
					MaxPlus = b.getBravery(),
					Talent = b.getTalents()[this.Const.Attributes.Bravery],
					BLimit = basestats.Bravery[1] + additionalstats.Bravery[1],
				},
				MeleeSkill = {
					Max = b.getBaseProperties().MeleeSkill,
					MaxPlus = b.m.CurrentProperties.getMeleeSkill(),
					Talent = b.getTalents()[this.Const.Attributes.MeleeSkill],
					BLimit = basestats.MeleeSkill[1] + additionalstats.MeleeSkill[1],
				},
				RangedSkill = {
					Max = b.getBaseProperties().RangedSkill,
					MaxPlus = b.m.CurrentProperties.getRangedSkill(),
					Talent = b.getTalents()[this.Const.Attributes.RangedSkill],
					BLimit = basestats.RangedSkill[1] + additionalstats.RangedSkill[1],
				},
				MeleeDefense = {
					Max = b.getBaseProperties().MeleeDefense,
					MaxPlus = b.m.CurrentProperties.getMeleeDefense(),
					Talent = b.getTalents()[this.Const.Attributes.MeleeDefense],
					BLimit = basestats.MeleeDefense[1] + additionalstats.MeleeDefense[1],
				},
				RangedDefense = {
					Max = b.getBaseProperties().RangedDefense,
					MaxPlus = b.m.CurrentProperties.getRangedDefense(),
					Talent = b.getTalents()[this.Const.Attributes.RangedDefense],
					BLimit = basestats.RangedDefense[1] + additionalstats.RangedDefense[1],
				},
				ActionPoints = b.getActionPointsMax(),
				DailyWage = b.getDailyCost(),
				DailyFood = b.getDailyFood(),
				Traits = brotraits,
			};
			if (_id != null && _id == b.getID())
			{return e;}
			roster.push(e);
		}

		return {
			Title = "兄弟编辑器",
			//SubTitle = "Edit characteristics of your soldiers",
			Roster = roster,
			Traits = traits,
			Backgrounds = prepareyourbgs(),
			NamedItems = prepareNI(),
			//Assets = this.m.Parent.queryAssetsInformation()
		};
	}
	
	function onChangeAttributes( _result )
	{
		//this.logDebug("id "+_result.BroId+", stat "+_result.StatName+", value "+_result.Value);
		local brothers = this.World.getPlayerRoster().getAll();
		foreach( b in brothers )
		{
			if (b.getID() == _result.BroId)
			{
				if (_result.StatName == "PerkPoints")
				{
					b.m.PerkPoints = _result.Value;
					break;
				}
				else if (_result.StatName == "DailyWage")
				{
					b.getBaseProperties().DailyWage = b.getBaseProperties().DailyWage - (b.m.CurrentProperties.DailyWage - _result.Value);
					//this.logDebug("getBaseProperties "+b.getBaseProperties()[_result.StatName]+", getDailyCost "+b.getDailyCost()+", CurrentProperties "+b.m.CurrentProperties[_result.StatName]);
					break;
				}
				else
				{
					b.getBaseProperties()[_result.StatName] = _result.Value;
					break;
				} 
			}
		};
	}
	
	function onChangeTalents( _result )
	{
		local talentconstants = 
		{
			Hitpoints = this.Const.Attributes.Hitpoints,
			Stamina = this.Const.Attributes.Fatigue,
			Initiative = this.Const.Attributes.Initiative,
			Bravery = this.Const.Attributes.Bravery,
			MeleeSkill = this.Const.Attributes.MeleeSkill,
			RangedSkill = this.Const.Attributes.RangedSkill,
			MeleeDefense = this.Const.Attributes.MeleeDefense,
			RangedDefense = this.Const.Attributes.RangedDefense,
		}
		local talentconst = talentconstants[_result.StatName];
		
		local brothers = this.World.getPlayerRoster().getAll();
		foreach( b in brothers )
		{
			if (b.getID() == _result.BroId)
			{
				b.m.Talents[talentconst] = _result.TalentValue;
				b.m.Attributes.clear();
				b.fillAttributeLevelUpValues(this.Const.XP.MaxLevelWithPerkpoints - b.getLevel() + b.m.LevelUps);
				break;
			}
		};
	}
	
	function onChangeTraits( _result )
	{
		//this.logDebug("broid:"+_result.BroId+", TraitId:"+_result.TraitId+", TraitLink:"+_result.TraitLink+", YN:"+_result.YesOrNo);
		local brothers = this.World.getPlayerRoster().getAll();
		foreach( b in brothers )
		{
			if (b.getID() == _result.BroId)
			{
				if (_result.YesOrNo == 1)
				{
					b.getSkills().add(this.new(_result.TraitLink));
				}
				else if (_result.YesOrNo == 0)
				{
					b.getSkills().removeByID(_result.TraitId);
				}
				break;
			}
		};
	}
	
	function onChooseBG( _result )
	{
		local result = null;
		local brothers = this.World.getPlayerRoster().getAll();
		foreach( b in brothers )
		{
			if (b.getID() == _result.BroId)
			{
				local XPbackup = b.m.XP;
				local Levelbackup = b.m.Level;
				local LevelUpsbackup = b.m.LevelUps;
				local PerkPointsBackup = b.m.PerkPoints;
				local TitleBackup = b.m.Title;
				local bg = this.new(_result.TraitLink);
				local BackgroundText = b.getBackground().getDescription();
				b.getSkills().removeByID(b.getBackground().getID());
				b.getSkills().add(bg);
				b.getBackground().m.Description = BackgroundText;
				b.getBackground().m.RawDescription = BackgroundText;
				local additionalstats = b.getBackground().onChangeAttributes();
				b.m.XP = XPbackup;
				b.m.Level = Levelbackup;
				b.m.LevelUps = LevelUpsbackup;
				b.m.PerkPoints = PerkPointsBackup;
				b.m.Title = TitleBackup;
				result = 
				{
					BackgroundImagePath = bg.getIconColored(),
				};
				//background.buildDescription();
				//background.onSetAppearance();
				break;
			}
		};
		return result;
	}
	
	function SaveBio( _result )
	{
		local brothers = this.World.getPlayerRoster().getAll();
		foreach( b in brothers )
		{
			if (b.getID() == _result.BroId)
			{
				b.getBackground().m.Description = _result.Bio;
				b.getBackground().m.RawDescription = _result.Bio;
				break;
			}
		};
	}
	
	function OnGiveXP( _result )
	{
		local result = null;

		local brothers = this.World.getPlayerRoster().getAll();
		foreach( b in brothers )
		{
			if (b.getID() == _result.BroId)
			{
				local nextlevelXP = b.getXPForNextLevel() - b.m.XP;
				b.m.XP += nextlevelXP;
				b.m.CombatStats.XPGained += nextlevelXP;
				b.updateLevel();
				b.getSkills().update();
				result = 
				{
					Level = b.getLevel(),
					LevelUps = b.m.LevelUps,
					PerkPoints = b.getPerkPoints(),
					DailyWage = b.getDailyCost(),
				};
				break;
			}
		};
		return result;
	}
	
	function OnGiveOP( _result )
	{
		local result = null;

		local brothers = this.World.getPlayerRoster().getAll();
		foreach( b in brothers )
		{
			if (b.getID() == _result.BroId)
			{
				local booze = this.new("scripts/items/misc/potion_of_oblivion_item").onUse(b);
				result = 
				{
					PerkPoints = b.getPerkPoints(),
				};
				break;
			}
		};
		return result;
	}
	
	function OnGiveYF( _result )
	{
		local result = 0;
		local brothers = this.World.getPlayerRoster().getAll();
		foreach( b in brothers )
		{
			if (b.getID() == _result.BroId)
			{
				b.improveMood(10.0, "Who needs reasons for happiness?");
				local booze = this.new("scripts/items/special/fountain_of_youth_item").onUse(b);
 				b.getSprite("permanent_injury_1").setBrush("");
				b.getSprite("permanent_injury_2").setBrush("");
				b.getSprite("permanent_injury_3").setBrush("");
				b.getSprite("permanent_injury_4").setBrush(""); 
				break;
			}
		};
		return result;
	}
	
	function NIReroll( _result )
	{
		local result = 0;
		local item = this.new(_result.Item);
		local stats = 
		{
			Weapons = 
			{
				Stats = ["ConditionMax", "StaminaModifier", "RegularDamage", "RegularDamageMax", "ArmorDamageMult", "DirectDamageAdd", "FatigueOnSkillUse", "ChanceToHitHead", "ShieldDamage", "AdditionalAccuracy", "AmmoMax"],
			},
			Shields = 
			{
				Stats = ["ConditionMax", "StaminaModifier", "MeleeDefense", "RangedDefense", "FatigueOnSkillUse"],
			},
			Armor = 
			{
				Stats = ["ConditionMax", "StaminaModifier"],
			},
			Helmets = 
			{
				Stats = ["ConditionMax", "StaminaModifier"],
			},
		};
		if (_result.ItemType != "Legendary" && _result.ItemType != "Alchemy" && _result.ItemType != "Misc" && item.m.NameList.len() > 0)
		{
			item.setName(item.createRandomName());
		}
		if (item.m.ID == "armor.body.heraldic_armor")
		{
			item.setFaction(this.Math.rand(1, 10));
		}
		else if (item.m.ID == "armor.head.faction_helm" || item.m.ID == "armor.head.greatsword_faction_helm")
		{
			item.setVariant(this.Math.rand(1, 10));
		}
		result = 
		{
			ID = item.m.ID,
			Name = item.m.Name,
			Variant = item.m.Variant,
			IconLarge = item.m.Icon,
			Room = this.World.Assets.getStash().getNumberOfEmptySlots(),
			Irrelevant = [],
			Current = {},
		};
		if (item.m.ID == "armor.body.heraldic_armor")
		{
			result.Variant = item.m.Faction;
		}
		if (_result.ItemType != "Legendary" && _result.ItemType != "Alchemy" && _result.ItemType != "Misc")
		{
			if (item.isItemType(this.Const.Items.ItemType.Weapon))
			{
				if (item.m.ShieldDamage <= 0) {result.Irrelevant.push("ShieldDamage");}
				if (item.m.AmmoMax <= 0) {result.Irrelevant.push("AmmoMax");}
				if (!item.isItemType(this.Const.Items.ItemType.RangedWeapon)) {result.Irrelevant.push("AdditionalAccuracy");}
				if (item.isItemType(this.Const.Items.ItemType.Ammo)) {result.Irrelevant.push("ConditionMax");}
			}
			local statsneeded = stats[_result.ItemType].Stats;
			foreach(stat in statsneeded)
			{
				if (result.Irrelevant.find(stat) == null)
				{
					result.Current[stat] <- item.m[stat];
					if(stat == "ArmorDamageMult")
					{
						result.Current.ArmorDamageMult = this.Math.round(result.Current.ArmorDamageMult*100);
					}
					else if(stat == "DirectDamageAdd")
					{
						result.Current.DirectDamageAdd = this.Math.round((result.Current.DirectDamageAdd+item.m.DirectDamageMult)*100);
					}
				}
			}
		}
		
		return result;
	}
	
	function AddNI( _result )
	{
		local result = 0;
		local item = null;
		
		if (this.World.Assets.getStash().getNumberOfEmptySlots() > 0)
		{
			if (_result.ItemType == "Legendary" || _result.ItemType == "Alchemy" || _result.ItemType == "Misc")
			{
				item = this.new(_result.Item);
				if (item.m.ID == "armor.body.heraldic_armor")
				{
					item.setFaction(_result.Stats.Variant);
				}
				else if (item.m.ID == "armor.head.faction_helm" || item.m.ID == "armor.head.greatsword_faction_helm")
				{
					item.setVariant(_result.Stats.Variant);
				}
				this.World.Assets.getStash().add(item);
			}
			else
			{
				item = this.new(_result.Item);
				this.World.Assets.getStash().add(item);
				foreach(stat, value in _result.Stats)
				{
					if(stat == "ArmorDamageMult")
					{
						item.m[stat] = value*0.01;
					}
					else if(stat == "DirectDamageAdd")
					{
						item.m[stat] = value * 0.01 - item.m.DirectDamageMult;
					}
					else
					{
						item.m[stat] = value;
					}
					
					if(stat == "AmmoMax")
					{
						item.m.Ammo = item.m.AmmoMax;
					}
				}
				item.m.Condition = item.m.ConditionMax;
				item.updateVariant();
			}
		}

		result = 
		{
			Room = this.World.Assets.getStash().getNumberOfEmptySlots(),
		};
		return result;
	}
	
	function ExportBro( _result )
	{
		local result = "";
		local splitchar = "%!";
		local sprites = ["body",
			"head",
			"beard",
			"hair",
			"tattoo_body",
			"tattoo_head",
			"beard_top"
		];
		if (_result.MainS){result = result + "mainstatsbredata";}
		if (_result.LifeStats){result = result + "lifestatsbredata";}
		if (_result.Gear){result = result + "gearbredata";}
		result = result + splitchar;
		
		local brothers = this.World.getPlayerRoster().getAll();
		foreach( b in brothers )
		{
			if (b.getID() == _result.BroId)
			{
				if (_result.MainS)
				{
					//player.nut - skipped lifetime statistics, not sure if it's needed
					result = result + b.m.Level + splitchar;
					result = result + b.m.PerkPoints + splitchar;
					result = result + b.m.PerkPointsSpent + splitchar;
					result = result + b.m.LevelUps + splitchar;
					for( local i = 0; i != this.Const.Attributes.COUNT; i = ++i )
					{
						result = result + b.m.Talents[i] + splitchar;
					}
					for( local i = 0; i != this.Const.Attributes.COUNT; i = ++i )
					{
						result = result + b.m.Attributes[i].len() + splitchar;
						foreach( a in b.m.Attributes[i] )
						{
							result = result + a + splitchar;
						}
					}
					//------------------------------------------------------------------------------------------------
					//human.nut
					result = result + b.m.Body + splitchar;
					result = result + b.m.Ethnicity + splitchar;
					result = result + b.m.Gender + splitchar;
					result = result + b.m.VoiceSet + splitchar;
					//extra
					for( local i = 0; i < sprites.len(); i = ++i )
					{
						if (b.getSprite(sprites[i]).HasBrush)
						{
							result = result + "true" + splitchar;
							result = result + b.getSprite(sprites[i]).getBrush().Name + splitchar;
						}
						else
						{
							result = result + "false" + splitchar;
						}
					} 
					//------------------------------------------------------------------------------------------------
					//actor.nut
					result = result + b.m.BaseProperties.ActionPoints + splitchar;
					result = result + b.m.BaseProperties.Hitpoints + splitchar;
					result = result + b.m.BaseProperties.Bravery + splitchar;
					result = result + b.m.BaseProperties.Stamina + splitchar;
					result = result + b.m.BaseProperties.MeleeSkill + splitchar;
					result = result + b.m.BaseProperties.RangedSkill + splitchar;
					result = result + b.m.BaseProperties.MeleeDefense + splitchar;
					result = result + b.m.BaseProperties.RangedDefense + splitchar;
					result = result + b.m.BaseProperties.Initiative + splitchar;
					result = result + b.m.BaseProperties.DailyWage + splitchar;
					result = result + b.m.BaseProperties.DailyFood + splitchar;				
					result = result + b.m.Name + splitchar;
					result = result + b.m.Title + splitchar;
					result = result + b.getHitpointsPct() + splitchar;
					result = result + b.m.XP + splitchar;
					//------------------------------------------------------------------------------------------------
					//entity.nut - flags - fuck them
					//skill container
					local skillz = b.getSkills();
					local numSkills = 0;
					foreach( skill in skillz.m.Skills )
					{
						if (skill.isSerialized() && (!skill.isType(this.Const.SkillType.Injury) || skill.isType(this.Const.SkillType.PermanentInjury)) && !skill.isType(this.Const.SkillType.DrugEffect)){numSkills = ++numSkills;}
					}
					result = result + numSkills + splitchar;
					foreach( skill in skillz.m.Skills )
					{
						if (skill.isSerialized() && (!skill.isType(this.Const.SkillType.Injury) || skill.isType(this.Const.SkillType.PermanentInjury)) && !skill.isType(this.Const.SkillType.DrugEffect))
						{
							result = result + this.IO.scriptFilenameByHash(skill.ClassNameHash) + splitchar;
							//skill.nut
							result = result + skill.m.IsNew + splitchar;
							if (skill.isType(this.Const.SkillType.Background))
							{
								result = result + skill.m.Description + splitchar;
								result = result + skill.m.RawDescription + splitchar;
								result = result + skill.m.Level + splitchar;
								result = result + skill.m.DailyCostMult + splitchar;
							}
							if (skill.m.ID == "trait.pit_fighter" || skill.m.ID == "trait.arena_fighter" || skill.m.ID == "trait.arena_veteran")
							{	result = result + b.getFlags().getAsInt("ArenaFights") + splitchar;
								result = result + b.getFlags().getAsInt("ArenaFightsWon") + splitchar;}
						}
					}
					result = result + "Finish" + splitchar;
				}
				
				if (_result.LifeStats)
				{
					result = result + "LSBBegin" + splitchar;
					result = result + b.m.LifetimeStats.Kills + splitchar;
					result = result + b.m.LifetimeStats.Battles + splitchar;
					result = result + b.m.LifetimeStats.BattlesWithoutMe + splitchar;
					result = result + b.m.LifetimeStats.MostPowerfulVanquishedType + splitchar;
					result = result + b.m.LifetimeStats.MostPowerfulVanquished + splitchar;
					result = result + b.m.LifetimeStats.MostPowerfulVanquishedXP + splitchar;
					result = result + b.m.LifetimeStats.FavoriteWeapon + splitchar;
					result = result + b.m.LifetimeStats.FavoriteWeaponUses + splitchar;
					result = result + b.m.LifetimeStats.CurrentWeaponUses + splitchar;
					result = result + "Finish" + splitchar;
				}
				
				if (_result.Gear)
				{
					result = result + "EqBBegin" + splitchar;
					local itemz = b.m.Items;
					//item container
					//result = result + itemz.m.UnlockedBagSlots + splitchar;
					local numItems = 0;
					for( local i = 0; i < this.Const.ItemSlot.COUNT; i = ++i )
					{
						for( local j = 0; j < this.Const.ItemSlotSpaces[i]; j = ++j )
						{
							if (itemz.m.Items[i][j] != null && itemz.m.Items[i][j] != -1){numItems = ++numItems;}
						}
					}
					result = result + numItems + splitchar;
					for( local i = 0; i < this.Const.ItemSlot.COUNT; i = ++i )
					{
						for( local j = 0; j < this.Const.ItemSlotSpaces[i]; j = ++j )
						{
							local curitem = itemz.m.Items[i][j];
							if (curitem != null && curitem != -1)
							{
								result = result + curitem.getCurrentSlotType() + splitchar;
								result = result + this.IO.scriptFilenameByHash(curitem.ClassNameHash) + splitchar;
								local HS = false;
								if ("HiddenString" in curitem.m){HS = true;
								result = result + curitem.m.HiddenString + splitchar;}
								//item.nut
								result = result + curitem.m.IsToBeRepaired + splitchar;
								result = result + curitem.m.Variant + splitchar;
								result = result + curitem.m.Condition + splitchar;
								result = result + curitem.m.PriceMult + splitchar;
								result = result + curitem.m.MagicNumber + splitchar;
								result = result + curitem.m.Name + splitchar; //not from item.nut, not always serialized but pretty much every item should have it
								if(curitem.isItemType(this.Const.Items.ItemType.Ammo) && !curitem.isItemType(this.Const.Items.ItemType.Weapon)) //throwing weapons age gonna be serialized with other weapons
								{result = result + curitem.m.Ammo + splitchar;}
								if(curitem.isItemType(this.Const.Items.ItemType.Weapon))
								{	result = result + curitem.m.Ammo + splitchar;
									if(curitem.isItemType(this.Const.Items.ItemType.Named) || HS == true)
									{
										result = result + curitem.m.ConditionMax + splitchar;
										result = result + curitem.m.StaminaModifier + splitchar;
										result = result + curitem.m.RegularDamage + splitchar;
										result = result + curitem.m.RegularDamageMax + splitchar;
										result = result + curitem.m.ArmorDamageMult + splitchar;
										result = result + curitem.m.ChanceToHitHead + splitchar;
										result = result + curitem.m.ShieldDamage + splitchar;
										result = result + curitem.m.AdditionalAccuracy + splitchar;
										result = result + curitem.m.DirectDamageAdd + splitchar;
										result = result + curitem.m.FatigueOnSkillUse + splitchar;
										result = result + curitem.m.AmmoMax + splitchar;}
								}
								if(curitem.isItemType(this.Const.Items.ItemType.Shield))
								{	
									if(curitem.isItemType(this.Const.Items.ItemType.Named) || HS == true)
									{	result = result + curitem.m.ConditionMax + splitchar;
										result = result + curitem.m.StaminaModifier + splitchar;
										result = result + curitem.m.MeleeDefense + splitchar;
										result = result + curitem.m.RangedDefense + splitchar;
										result = result + curitem.m.FatigueOnSkillUse + splitchar;}
									if(curitem.m.ID == "shield.faction_kite_shield" || curitem.m.ID == "shield.faction_heater_shield")
									{	result = result + curitem.m.Faction + splitchar;}
								}
								if(curitem.isItemType(this.Const.Items.ItemType.Helmet)) //excluded condition because it's already serialized in the item section
								{	
									if(curitem.isItemType(this.Const.Items.ItemType.Named) || HS == true)
									{	result = result + curitem.m.ConditionMax + splitchar;
										result = result + curitem.m.StaminaModifier + splitchar;}
								}
								if(curitem.isItemType(this.Const.Items.ItemType.Armor)) //for some reason the game serializes CM and SM even for regular armor
								{	result = result + curitem.m.ConditionMax + splitchar;
									result = result + curitem.m.StaminaModifier + splitchar;
									if (curitem.m.Upgrade != null)
									{	result = result + true + splitchar;
										result = result + this.IO.scriptFilenameByHash(curitem.m.Upgrade.ClassNameHash) + splitchar;
										result = result + curitem.m.Upgrade.m.IsToBeRepaired + splitchar;
										result = result + curitem.m.Upgrade.m.Variant + splitchar;
										result = result + curitem.m.Upgrade.m.Condition + splitchar;
										result = result + curitem.m.Upgrade.m.PriceMult + splitchar;
										result = result + curitem.m.Upgrade.m.MagicNumber + splitchar;
										result = result + curitem.m.Upgrade.m.Name + splitchar;
										result = result + curitem.m.Upgrade.m.PreviousCondition + splitchar;
										result = result + curitem.m.Upgrade.m.PreviousStamina + splitchar;}
									else
									{result = result + false + splitchar;}
									if(curitem.m.ID == "armor.body.heraldic_armor")
									{	result = result + curitem.m.Faction + splitchar;}
								}
								
								
								
							}
						}
					}
					result = result + "Finish" + splitchar;
				} //gear end
				break;
			}
		};
		//result = result + "ImportFinished";
		this.logDebug(""+result);
		return result;
	}
	
	function ImportBro( _result )
	{
		local result = "Error01";
		local stringarray = this.ImportBroFixString(_result.IString);
		if (stringarray.len() < 5)
		{
			return result;
		}
		local hasMS = false;
		local hasLS = false;
		local hasGS = false;
		if (this.String.contains(stringarray[0], "mainstatsbredata")){hasMS = true && _result.MainS;}
		if (this.String.contains(stringarray[0], "lifestatsbredata")){hasLS = true && _result.LifeStats;}
		if (this.String.contains(stringarray[0], "gearbredata")){hasGS = true && _result.Gear;}
		local iesettings = {hasMS = hasMS,
			hasLS = hasLS,
			hasGS = hasGS,
		};
		if (!hasMS && !hasLS && !hasGS)
		{
			return "Cannot do that!";
		}
/* 		this.logDebug("hasMS "+hasMS+", _result.MainS "+_result.MainS+", string "+this.String.contains(stringarray[0], "mainstatsbredata"));
		this.logDebug("hasLS "+hasLS+", _result.LifeStats "+_result.LifeStats+", string "+this.String.contains(stringarray[0], "lifestatsbredata"));
		this.logDebug("hasGS "+hasGS+", _result.Gear "+_result.Gear+", string "+this.String.contains(stringarray[0], "gearbredata")); */
		
		local temprosterbro = this.World.getTemporaryRoster().create("scripts/entity/tactical/player");
		local testresult = null;
		try {testresult = this.ImportBroProcessBro(temprosterbro, stringarray, iesettings);}
		catch (err) {result = "Error02";};
		if (testresult != "Finish")
		{
			return result;
		}
		this.World.getTemporaryRoster().clear();
		local brothers = this.World.getPlayerRoster().getAll();
		foreach( b in brothers )
		{
			if (b.getID() == _result.BroId)
			{
				testresult = this.ImportBroProcessBro(b, stringarray, iesettings);
				this.logDebug(""+testresult);
				
				local skillz = b.getSkills();
				skillz.update();
				result = iesettings;
				if(hasGS){result.ImagePath <- b.getImagePath();}
				break;
			}
		};
		return result;
	}
	
	function ImportBroFixString( _result )
	{
		local result = [];
		//local splitchar = "%!";
		//local stringarray = split(_result, splitchar);
		local curvalue = null;
		foreach(kkey, vvalue in _result)
		{
			if (vvalue == "true"){result.push(true);}
			else if (vvalue == "false"){result.push(false);}
			else if (vvalue.find(".") && vvalue.len() < 15)
			{
				try {curvalue = vvalue.tofloat();}
				catch (err) {curvalue = vvalue;};
				result.push(curvalue);
			}	
			else if (vvalue.len() < 10)
			{
				try {curvalue = vvalue.tointeger();}
				catch (err) {curvalue = vvalue;};
				result.push(curvalue);
			}
			else {result.push(vvalue);}
		}
 		//foreach(kkey, vvalue in result){this.logDebug("key "+kkey+", type "+typeof(vvalue)+", value "+vvalue);} 
		return result;
	}
	
	function ImportBroProcessBro(b, stringarray, _iesettings)
	{
		local result = null;
		local sprites = ["body",
			"head",
			"beard",
			"hair",
			"tattoo_body",
			"tattoo_head",
			"beard_top"
		];
		local LSBBegin = 0;
		local EqBBegin = 0;
		foreach(_key, _value in stringarray)
		{
			if (_value == "LSBBegin" && _iesettings.hasLS) 
			{LSBBegin = _key+1}
			if (_value == "EqBBegin" && _iesettings.hasGS) 
			{EqBBegin = _key+1}
		}
		local leo = 1;
		if (_iesettings.hasMS)
		{
			//player.nut
			b.m.Level = stringarray[leo]; leo = ++leo;
			b.m.PerkPoints = stringarray[leo]; leo = ++leo;
			b.m.PerkPointsSpent = stringarray[leo]; leo = ++leo;
			b.m.LevelUps = stringarray[leo]; leo = ++leo;
			b.m.Talents.resize(this.Const.Attributes.COUNT, 0);
			for( local i = 0; i != this.Const.Attributes.COUNT; i = ++i )
			{
				b.m.Talents[i] = stringarray[leo]; leo = ++leo;
			}
			b.m.Attributes.resize(this.Const.Attributes.COUNT);
			for( local i = 0; i != this.Const.Attributes.COUNT; i = ++i )
			{
				b.m.Attributes[i] = [];
				local curattr = stringarray[leo]; leo = ++leo;
				b.m.Attributes[i].resize(curattr);
				for( local j = 0; j != curattr; j = ++j )
				{
					b.m.Attributes[i][j] = stringarray[leo]; leo = ++leo;
				}
			}
			//------------------------------------------------------------------------------------------------
			//human.nut
			b.m.Body = stringarray[leo]; leo = ++leo;
			b.m.Ethnicity = stringarray[leo]; leo = ++leo;
			b.m.Gender = stringarray[leo]; leo = ++leo;
			b.m.VoiceSet = stringarray[leo]; leo = ++leo;
			b.m.Sound[this.Const.Sound.ActorEvent.NoDamageReceived] = this.Const.HumanSounds[b.m.VoiceSet].NoDamageReceived;
			b.m.Sound[this.Const.Sound.ActorEvent.DamageReceived] = this.Const.HumanSounds[b.m.VoiceSet].DamageReceived;
			b.m.Sound[this.Const.Sound.ActorEvent.Death] = this.Const.HumanSounds[b.m.VoiceSet].Death;
			b.m.Sound[this.Const.Sound.ActorEvent.Fatigue] = this.Const.HumanSounds[b.m.VoiceSet].Fatigue;
			b.m.Sound[this.Const.Sound.ActorEvent.Flee] = this.Const.HumanSounds[b.m.VoiceSet].Fatigue;
			//extra
			local cursprite = null;
			for( local i = 0; i < sprites.len(); i = ++i )
			{
				cursprite = stringarray[leo]; leo = ++leo;
				if (cursprite)
				{
					b.getSprite(sprites[i]).setBrush(stringarray[leo]); leo = ++leo;
				}
				else
				{
					b.getSprite(sprites[i]).resetBrush();
					continue;
				}
			} 
			//------------------------------------------------------------------------------------------------
			//actor.nut
			b.m.BaseProperties.ActionPoints = stringarray[leo]; leo = ++leo;
			b.m.BaseProperties.Hitpoints = stringarray[leo]; leo = ++leo;
			b.m.BaseProperties.Bravery = stringarray[leo]; leo = ++leo;
			b.m.BaseProperties.Stamina = stringarray[leo]; leo = ++leo;
			b.m.BaseProperties.MeleeSkill = stringarray[leo]; leo = ++leo;
			b.m.BaseProperties.RangedSkill = stringarray[leo]; leo = ++leo;
			b.m.BaseProperties.MeleeDefense = stringarray[leo]; leo = ++leo;
			b.m.BaseProperties.RangedDefense = stringarray[leo]; leo = ++leo;
			b.m.BaseProperties.Initiative = stringarray[leo]; leo = ++leo;
			b.m.BaseProperties.DailyWage = stringarray[leo]; leo = ++leo;
			b.m.BaseProperties.DailyFood = stringarray[leo]; leo = ++leo;
			b.m.Name = stringarray[leo]; leo = ++leo;
			b.m.Title = stringarray[leo]; leo = ++leo;
			b.setHitpointsPct(this.Math.maxf(0.0, stringarray[leo])); leo = ++leo;
			b.m.XP = stringarray[leo]; leo = ++leo;
			//------------------------------------------------------------------------------------------------
			//entity.nut - flags - fuck them
			//skill container
			local skillz = b.getSkills();
			skillz.m.IsUpdating = true;
			local numSkills = stringarray[leo]; leo = ++leo;
			foreach( skill in skillz.m.Skills )
			{
				if (skill.isType(this.Const.SkillType.Background) || skill.isType(this.Const.SkillType.Trait) || skill.isType(this.Const.SkillType.Perk) || skill.isType(this.Const.SkillType.PermanentInjury) || skill.isType(this.Const.SkillType.TemporaryInjury))
				{
					if (!skill.isType(this.Const.SkillType.Special) && !skill.isType(this.Const.SkillType.Active) && (!skill.isType(this.Const.SkillType.StatusEffect) || (skill.isType(this.Const.SkillType.StatusEffect) && skill.isType(this.Const.SkillType.Perk)) || (skill.isType(this.Const.SkillType.StatusEffect) && skill.isType(this.Const.SkillType.Trait))) && 
					!skill.isType(this.Const.SkillType.Item)) //!skill.isType(this.Const.SkillType.Racial) && 
					{
						skill.removeSelf();
					}
				}
			}
			b.getFlags().set("ArenaFights", 0); 
			b.getFlags().set("ArenaFightsWon", 0); 
			for( local i = 0; i < numSkills; i = ++i )
			{
				//this.logDebug("leo "+stringarray[leo]);
				local skill = this.new(stringarray[leo]); leo = ++leo;
				//skill.nut
				skill.m.IsNew = stringarray[leo]; leo = ++leo;
				if (skill.isType(this.Const.SkillType.Background))
				{
					skill.m.Description = stringarray[leo]; leo = ++leo;
					skill.m.RawDescription = stringarray[leo]; leo = ++leo;
					skill.m.Level = stringarray[leo]; leo = ++leo;
					skill.m.DailyCostMult = stringarray[leo]; leo = ++leo;
				}
				if (skill.m.ID == "perk.gifted") {skill.m.IsApplied = true;}
				if (skill.m.ID == "trait.pit_fighter" || skill.m.ID == "trait.arena_fighter" || skill.m.ID == "trait.arena_veteran")	
				{	b.getFlags().set("ArenaFights", stringarray[leo]); leo = ++leo;
					b.getFlags().set("ArenaFightsWon", stringarray[leo]); leo = ++leo;}
				skillz.add(skill);
			}
			skillz.m.IsUpdating = false;
			if (stringarray[leo] != "Finish"){return null}
		}
		
		if (_iesettings.hasLS && LSBBegin != 0)
		{
			if (stringarray[leo] == "Finish" || leo == 1){leo = LSBBegin}
			b.m.LifetimeStats.Kills = stringarray[leo]; leo = ++leo;
			b.m.LifetimeStats.Battles = stringarray[leo]; leo = ++leo;
			b.m.LifetimeStats.BattlesWithoutMe = stringarray[leo]; leo = ++leo;
			b.m.LifetimeStats.MostPowerfulVanquishedType = stringarray[leo]; leo = ++leo;
			b.m.LifetimeStats.MostPowerfulVanquished = stringarray[leo]; leo = ++leo;
			b.m.LifetimeStats.MostPowerfulVanquishedXP = stringarray[leo]; leo = ++leo;
			b.m.LifetimeStats.FavoriteWeapon = stringarray[leo]; leo = ++leo;
			b.m.LifetimeStats.FavoriteWeaponUses = stringarray[leo]; leo = ++leo;
			b.m.LifetimeStats.CurrentWeaponUses = stringarray[leo]; leo = ++leo;
			if (stringarray[leo] != "Finish"){return null}
		}
		
		if (_iesettings.hasGS && EqBBegin != 0)
		{
			if (stringarray[leo] == "Finish" || leo == 1){leo = EqBBegin}
			local itemz = b.m.Items;
			itemz.clear();
			//item container
			
			itemz.m.UnlockedBagSlots = b.getSkills().hasSkill("perk.bags_and_belts") ? 4 : 2;
			//itemz.m.UnlockedBagSlots = stringarray[leo]; leo = ++leo;
			local numItems = stringarray[leo]; leo = ++leo;
			for( local i = 0; i < numItems; i = ++i )
			{
				local slotType = stringarray[leo]; leo = ++leo;
				//this.logDebug("leoname "+leo+" value "+stringarray[leo]);
				local curitem = this.new(stringarray[leo]); leo = ++leo;
				local HS = false;
				if ("HiddenString" in curitem.m){HS = true;
				curitem.m.HiddenString = stringarray[leo]; leo = ++leo;}
				//item.nut
				curitem.m.IsToBeRepaired = stringarray[leo]; leo = ++leo;
				curitem.m.Variant = stringarray[leo]; leo = ++leo;
				curitem.m.Condition = stringarray[leo]; leo = ++leo;
				curitem.m.PriceMult = stringarray[leo]; leo = ++leo;
				curitem.m.MagicNumber = stringarray[leo]; leo = ++leo;
				curitem.m.Name = stringarray[leo]; leo = ++leo;
				if(curitem.isItemType(this.Const.Items.ItemType.Ammo) && !curitem.isItemType(this.Const.Items.ItemType.Weapon)) //throwing weapons are gonna be serialized with other weapons
				{curitem.m.Ammo = stringarray[leo]; leo = ++leo;}
				if(curitem.isItemType(this.Const.Items.ItemType.Weapon))
				{	curitem.m.Ammo = stringarray[leo]; leo = ++leo;
					if(curitem.isItemType(this.Const.Items.ItemType.Named) || HS == true)
					{
						curitem.m.ConditionMax = stringarray[leo]; leo = ++leo;
						curitem.m.StaminaModifier = stringarray[leo]; leo = ++leo;
						curitem.m.RegularDamage = stringarray[leo]; leo = ++leo;
						curitem.m.RegularDamageMax = stringarray[leo]; leo = ++leo;
						curitem.m.ArmorDamageMult = stringarray[leo]; leo = ++leo;
						curitem.m.ChanceToHitHead = stringarray[leo]; leo = ++leo;
						curitem.m.ShieldDamage = stringarray[leo]; leo = ++leo;
						curitem.m.AdditionalAccuracy = stringarray[leo]; leo = ++leo;
						curitem.m.DirectDamageAdd = stringarray[leo]; leo = ++leo;
						curitem.m.FatigueOnSkillUse = stringarray[leo]; leo = ++leo;
						curitem.m.AmmoMax = stringarray[leo]; leo = ++leo;}
					curitem.m.Condition = this.Math.minf(curitem.m.ConditionMax, curitem.m.Condition);	
					if(curitem.m.Ammo != 0 && curitem.m.AmmoMax == 0)
					{	curitem.m.AmmoMax = curitem.m.Ammo;	}
				}
				if(curitem.isItemType(this.Const.Items.ItemType.Shield))
				{	
					if(curitem.isItemType(this.Const.Items.ItemType.Named) || HS == true)
					{	curitem.m.ConditionMax = stringarray[leo]; leo = ++leo;
						curitem.m.StaminaModifier = stringarray[leo]; leo = ++leo;
						curitem.m.MeleeDefense = stringarray[leo]; leo = ++leo;
						curitem.m.RangedDefense = stringarray[leo]; leo = ++leo;
						curitem.m.FatigueOnSkillUse = stringarray[leo]; leo = ++leo;}
					if(curitem.m.ID == "shield.faction_kite_shield" || curitem.m.ID == "shield.faction_heater_shield")
					{	curitem.m.Faction = stringarray[leo]; leo = ++leo;}
					curitem.m.Condition = this.Math.minf(curitem.m.ConditionMax, curitem.m.Condition);	
				}
				if(curitem.isItemType(this.Const.Items.ItemType.Helmet)) //excluded condition because it's already serialized in the item section
				{	
					if(curitem.isItemType(this.Const.Items.ItemType.Named) || HS == true)
					{	curitem.m.ConditionMax = stringarray[leo]; leo = ++leo;
						curitem.m.StaminaModifier = stringarray[leo]; leo = ++leo;}
					curitem.m.Condition = this.Math.minf(curitem.m.ConditionMax, curitem.m.Condition);
				}
				if(curitem.isItemType(this.Const.Items.ItemType.Armor)) //for some reason the game serializes CM and SM even for regular armor
				{	curitem.m.ConditionMax = stringarray[leo]; leo = ++leo;
					curitem.m.StaminaModifier = stringarray[leo]; leo = ++leo;
					if (stringarray[leo] == true)
					{	leo = ++leo;
						curitem.m.Upgrade = this.new(stringarray[leo]); leo = ++leo;
						curitem.m.Upgrade.m.IsToBeRepaired = stringarray[leo]; leo = ++leo;
						curitem.m.Upgrade.m.Variant = stringarray[leo]; leo = ++leo;
						curitem.m.Upgrade.m.Condition = stringarray[leo]; leo = ++leo;
						curitem.m.Upgrade.m.PriceMult = stringarray[leo]; leo = ++leo;
						curitem.m.Upgrade.m.MagicNumber = stringarray[leo]; leo = ++leo;
						curitem.m.Name = stringarray[leo]; leo = ++leo;
						curitem.m.Upgrade.setArmor(curitem);
						curitem.m.Upgrade.m.PreviousCondition = stringarray[leo]; leo = ++leo;
						curitem.m.Upgrade.m.PreviousStamina = stringarray[leo]; leo = ++leo;}
					else
					{leo = ++leo;}
					curitem.m.Condition = this.Math.minf(curitem.m.ConditionMax, curitem.m.Condition);
					if(curitem.m.ID == "armor.body.heraldic_armor")
					{curitem.m.Faction = stringarray[leo]; leo = ++leo;}
				}
				curitem.updateVariant();
				local win = false;
				if (slotType == this.Const.ItemSlot.Bag)
				{win = itemz.addToBag(curitem);}
				else
				{win = itemz.equip(curitem);} //to hell with overflown items
			}
			if (stringarray[leo] != "Finish"){return null}
		} //gear end
		
		result = stringarray[leo];
		return result;
	}
	
	function DyeMyHair( _result )
	{
		local result = 0;
		local brothers = this.World.getPlayerRoster().getAll();
		foreach(charact, value in _result.Color)
		{if (value < 48 || (value > 57 && value < 65) || (value > 90 && value < 97) || value > 122)
			{return "Bad color!";}
		};
		foreach( b in brothers )
		{
			if (b.getID() == _result.BroId)
			{
				if (_result.Type == "Hair"){b.getSprite("hair").Color = this.createColor("#"+_result.Color);}
				if (_result.Type == "Beard"){b.getSprite("beard").Color = this.createColor("#"+_result.Color); 
				b.getSprite("beard_top").Color = this.createColor("#"+_result.Color);}
				b.getSkills().update();
				result = {
					ImagePath = b.getImagePath(),
				};
				break;
			}
		};
		return result;
	}
	
	function BreditorCalculateSTR( _result )
	{
		local result = "战力：";
		this.World.State.getPlayer().updateStrength();
		
		local contract = this.new("scripts/contracts/contract").getScaledDifficultyMult() * 100;
		contract = contract.tointeger() *0.01;
		local factionaction = this.new("scripts/factions/faction_action").getScaledDifficultyMult() * 100;
		factionaction = factionaction.tointeger() *0.01;
		result = result + this.World.State.getPlayer().getStrength() + " / " + contract + " / " + factionaction;
		return result;
	}
	
	function MirrorBattle( _result )
	{
/* 		local b = this.World.getPlayerRoster().getAll()[0];
		local report = "Members of b.getSprite('hair').getclass():\n";
		foreach(member, value in b.getSprite("hair").getclass())
		{
			report = report + "member "+member+", type "+typeof(value)+", value "+value+"\n";
			if (typeof(value) == "table" || typeof(value) == "array")
			{
				foreach(kkey, vvalue in value)
				{
					report = report + "__key "+kkey+", type "+typeof(vvalue)+", value "+vvalue+"\n";
					if (typeof(vvalue) == "table" || typeof(vvalue) == "array")
					{
						foreach(kkkey, vvvalue in vvalue)
						{
							report = report + "____key "+kkkey+", type "+typeof(vvvalue)+", value "+vvvalue+"\n";
						}
					}
				}
			}
		}
		this.logDebug(report); */
		
		
 		this.onClose();
		local brothers = this.World.getPlayerRoster().getAll();
		local properties = this.World.State.getLocalCombatProperties(this.World.State.getPlayer().getPos());
		properties.CombatID = "Event";
		properties.Music = this.Const.Music.BanditTracks;
		properties.IsAutoAssigningBases = false;
		properties.Entities = [];
 		foreach( b in brothers )
		{
			local unit = clone this.Const.World.Spawn.Troops.BountyHunter;
			unit.Faction <- this.Const.Faction.Enemy;
			unit.Script = "scripts/entity/tactical/humans/broclone";
			unit.Strength = b.getLevel() * 3;
			unit.Cost = unit.Strength;
			properties.Entities.push(unit);
		} 
		this.World.State.startScriptedCombat(properties, false, true, true); 
	}
				
/* 				
				 */
	
/* 				local itemz = b.m.Items;
				for( local i = 0; i < this.Const.ItemSlot.COUNT; i = ++i )
				{
					for( local j = 0; j < this.Const.ItemSlotSpaces[i]; j = ++j )
					{
						if (itemz.m.Items[i][j] != null && itemz.m.Items[i][j] != -1)
						{
							local item = itemz.m.Items[i][j];
							if (i == this.Const.ItemSlot.Bag)
							{	itemz.removeFromBag(item);
								itemz.addToBag(item);	}
							else
							{	itemz.unequip(item);
								itemz.equip(item);	}
						}
					}
				} */
	
	function BDUpdateAttributes(_result)
	{
		local result = 0;
		local basestats = {
			Hitpoints = [50,60],
			Bravery = [30,40],
			Stamina = [90,100],
			MeleeSkill = [47,57],
			RangedSkill = [32,42],
			MeleeDefense = [0,5],
			RangedDefense = [0,5],
			Initiative = [100,110]
		};
		local brothers = this.World.getPlayerRoster().getAll();
		foreach( b in brothers )
		{
			if (b.getID() == _result.BroId)
			{
				b.getSkills().update();
				local background = b.getBackground();
				local additionalstats = background.onChangeAttributes();
				result = {
					PerkPoints = b.getPerkPoints(),
					Hitpoints = {
						Max = b.getBaseProperties().Hitpoints,
						MaxPlus = b.getHitpointsMax(),
						Talent = b.getTalents()[this.Const.Attributes.Hitpoints],
						BLimit = basestats.Hitpoints[1] + additionalstats.Hitpoints[1],
					},
					Stamina = {
						Max = b.getBaseProperties().Stamina,
						MaxPlus = b.getFatigueMax(),
						Talent = b.getTalents()[this.Const.Attributes.Fatigue],
						BLimit = basestats.Stamina[1] + additionalstats.Stamina[1],
					},
					Initiative = {
						Max = b.getBaseProperties().Initiative,
						MaxPlus = b.getInitiative(),
						Talent = b.getTalents()[this.Const.Attributes.Initiative],
						BLimit = basestats.Initiative[1] + additionalstats.Initiative[1],
					},
					Bravery = {
						Max = b.getBaseProperties().Bravery,
						MaxPlus = b.getBravery(),
						Talent = b.getTalents()[this.Const.Attributes.Bravery],
						BLimit = basestats.Bravery[1] + additionalstats.Bravery[1],
					},
					MeleeSkill = {
						Max = b.getBaseProperties().MeleeSkill,
						MaxPlus = b.m.CurrentProperties.getMeleeSkill(),
						Talent = b.getTalents()[this.Const.Attributes.MeleeSkill],
						BLimit = basestats.MeleeSkill[1] + additionalstats.MeleeSkill[1],
					},
					RangedSkill = {
						Max = b.getBaseProperties().RangedSkill,
						MaxPlus = b.m.CurrentProperties.getRangedSkill(),
						Talent = b.getTalents()[this.Const.Attributes.RangedSkill],
						BLimit = basestats.RangedSkill[1] + additionalstats.RangedSkill[1],
					},
					MeleeDefense = {
						Max = b.getBaseProperties().MeleeDefense,
						MaxPlus = b.m.CurrentProperties.getMeleeDefense(),
						Talent = b.getTalents()[this.Const.Attributes.MeleeDefense],
						BLimit = basestats.MeleeDefense[1] + additionalstats.MeleeDefense[1],
					},
					RangedDefense = {
						Max = b.getBaseProperties().RangedDefense,
						MaxPlus = b.m.CurrentProperties.getRangedDefense(),
						Talent = b.getTalents()[this.Const.Attributes.RangedDefense],
						BLimit = basestats.RangedDefense[1] + additionalstats.RangedDefense[1],
					},
					ActionPoints = b.getActionPointsMax(),
					DailyWage = b.getDailyCost(),
					DailyFood = b.getDailyFood(),
				};
			}
		};
		return result;
	}
	
	function prepareyourtraits()
	{
		local traits = [
			[
				"trait.addict",
				"scripts/skills/traits/addict_trait"
			],
			[
				"trait.cultist_fanatic",
				"scripts/skills/traits/cultist_fanatic_trait"
			],
			[
				"trait.cultist_zealot",
				"scripts/skills/traits/cultist_zealot_trait"
			],
			[
				"trait.cultist_acolyte",
				"scripts/skills/traits/cultist_acolyte_trait"
			],
			[
				"trait.cultist_disciple",
				"scripts/skills/traits/cultist_disciple_trait"
			],
			[
				"trait.cultist_chosen",
				"scripts/skills/traits/cultist_chosen_trait"
			],
			[
				"trait.cultist_prophet",
				"scripts/skills/traits/cultist_prophet_trait"
			],
	 		[
				"trait.glorious",
				"scripts/skills/traits/glorious_endurance_trait"
			],
			[
				"trait.glorious",
				"scripts/skills/traits/glorious_quickness_trait"
			],
			[
				"trait.glorious",
				"scripts/skills/traits/glorious_resolve_trait"
			], 
	 		[
				"trait.pit_fighter",
				"scripts/skills/traits/arena_pit_fighter_trait"
			],
			[
				"trait.arena_fighter",
				"scripts/skills/traits/arena_fighter_trait"
			],
			[
				"trait.arena_veteran",
				"scripts/skills/traits/arena_veteran_trait"
			], 
			[
				"trait.mad",
				"scripts/skills/traits/mad_trait"
			],
			[
				"trait.old",
				"scripts/skills/traits/old_trait"
			],
			[
				"trait.player",
				"scripts/skills/traits/player_character_trait"
			],
			[
				"trait.oath_of_camaraderie",
				"scripts/skills/traits/oath_of_camaraderie_trait"
			],
			[
				"trait.oath_of_distinction",
				"scripts/skills/traits/oath_of_distinction_trait"
			],
			[
				"trait.oath_of_dominion",
				"scripts/skills/traits/oath_of_dominion_trait"
			],
			[
				"trait.oath_of_endurance",
				"scripts/skills/traits/oath_of_endurance_trait"
			],
			[
				"trait.oath_of_fortification",
				"scripts/skills/traits/oath_of_fortification_trait"
			],
			[
				"trait.oath_of_honor",
				"scripts/skills/traits/oath_of_honor_trait"
			],
			[
				"trait.oath_of_humility",
				"scripts/skills/traits/oath_of_humility_trait"
			],
			[
				"trait.oath_of_righteousness",
				"scripts/skills/traits/oath_of_righteousness_trait"
			],
			[
				"trait.oath_of_sacrifice",
				"scripts/skills/traits/oath_of_sacrifice_trait"
			],
			[
				"trait.oath_of_valor",
				"scripts/skills/traits/oath_of_valor_trait"
			],
			[
				"trait.oath_of_vengeance",
				"scripts/skills/traits/oath_of_vengeance_trait"
			],
			[
				"trait.oath_of_wrath",
				"scripts/skills/traits/oath_of_wrath_trait"
			],
		];
	return traits;
	}
	
 	function prepareyourbgs() //NO BARBARIAN! BARBARIAN BAD!
	{
		local bgs = [
			["background.adventurous_noble","scripts/skills/backgrounds/adventurous_noble_background","ui/backgrounds/background_06.png"],
			["background.apprentice","scripts/skills/backgrounds/apprentice_background","ui/backgrounds/background_40.png"],
			["background.assassin","scripts/skills/backgrounds/assassin_background","ui/backgrounds/background_53.png"],
			["background.assassin_southern","scripts/skills/backgrounds/assassin_southern_background","ui/backgrounds/background_53.png"],
			//["background.barbarian","scripts/skills/backgrounds/barbarian_background","ui/backgrounds/background_58.png"],
			["background.bastard","scripts/skills/backgrounds/bastard_background","ui/backgrounds/background_37.png"],
			["background.beast_slayer","scripts/skills/backgrounds/beast_hunter_background","ui/backgrounds/background_57.png"],
			["background.beggar","scripts/skills/backgrounds/beggar_background","ui/backgrounds/background_18.png"],
			["background.belly_dancer","scripts/skills/backgrounds/belly_dancer_background","ui/backgrounds/background_64.png"],
			["background.bowyer","scripts/skills/backgrounds/bowyer_background","ui/backgrounds/background_29.png"],
			["background.brawler","scripts/skills/backgrounds/brawler_background","ui/backgrounds/background_27.png"],
			["background.butcher","scripts/skills/backgrounds/butcher_background","ui/backgrounds/background_43.png"],
			["background.caravan_hand","scripts/skills/backgrounds/caravan_hand_background","ui/backgrounds/background_12.png"],
			["background.companion","scripts/skills/backgrounds/companion_1h_background","ui/traits/trait_icon_32.png"],
			["background.companion","scripts/skills/backgrounds/companion_2h_background","ui/traits/trait_icon_32.png"],
			["background.companion","scripts/skills/backgrounds/companion_ranged_background","ui/traits/trait_icon_32.png"],
			["background.converted_cultist","scripts/skills/backgrounds/converted_cultist_background","ui/backgrounds/background_34.png"],
			["background.cripple","scripts/skills/backgrounds/cripple_background","ui/backgrounds/background_51.png"],
			["background.crucified","scripts/skills/backgrounds/crucified_background","ui/backgrounds/background_65.png"],
			["background.crusader","scripts/skills/backgrounds/crusader_background","ui/backgrounds/background_54.png"],
			["background.cultist","scripts/skills/backgrounds/cultist_background","ui/backgrounds/background_34.png"],
			["background.daytaler","scripts/skills/backgrounds/daytaler_background","ui/backgrounds/background_36.png"],
			["background.deserter","scripts/skills/backgrounds/deserter_background","ui/backgrounds/background_07.png"],
			["background.disowned_noble","scripts/skills/backgrounds/disowned_noble_background","ui/backgrounds/background_08.png"],
			["background.eunuch","scripts/skills/backgrounds/eunuch_background","ui/backgrounds/background_52.png"],
			["background.farmhand","scripts/skills/backgrounds/farmhand_background","ui/backgrounds/background_09.png"],
			["background.fisherman","scripts/skills/backgrounds/fisherman_background","ui/backgrounds/background_15.png"],
			["background.flagellant","scripts/skills/backgrounds/flagellant_background","ui/backgrounds/background_26.png"],
			["background.gambler","scripts/skills/backgrounds/gambler_background","ui/backgrounds/background_20.png"],
			["background.gladiator","scripts/skills/backgrounds/gladiator_background","ui/backgrounds/background_61.png"],
			["background.gravedigger","scripts/skills/backgrounds/gravedigger_background","ui/backgrounds/background_28.png"],
			["background.graverobber","scripts/skills/backgrounds/graverobber_background","ui/backgrounds/background_25.png"],
			["background.hedge_knight","scripts/skills/backgrounds/hedge_knight_background","ui/backgrounds/background_33.png"],
			["background.historian","scripts/skills/backgrounds/historian_background","ui/backgrounds/background_47.png"],
			["background.houndmaster","scripts/skills/backgrounds/houndmaster_background","ui/backgrounds/background_50.png"],
			["background.hunter","scripts/skills/backgrounds/hunter_background","ui/backgrounds/background_22.png"],
			["background.juggler","scripts/skills/backgrounds/juggler_background","ui/backgrounds/background_14.png"],
			["background.killer_on_the_run","scripts/skills/backgrounds/killer_on_the_run_background","ui/backgrounds/background_02.png"],
			["background.kings_guard","scripts/skills/backgrounds/kings_guard_background","ui/backgrounds/background_59.png"],
			["background.lumberjack","scripts/skills/backgrounds/lumberjack_background","ui/backgrounds/background_04.png"],
			["background.manhunter","scripts/skills/backgrounds/manhunter_background","ui/backgrounds/background_62.png"],
			["background.mason","scripts/skills/backgrounds/mason_background","ui/backgrounds/background_17.png"],
			["background.messenger","scripts/skills/backgrounds/messenger_background","ui/backgrounds/background_46.png"],
			["background.militia","scripts/skills/backgrounds/militia_background","ui/backgrounds/background_35.png"],
			["background.miller","scripts/skills/backgrounds/miller_background","ui/backgrounds/background_05.png"],
			["background.miner","scripts/skills/backgrounds/miner_background","ui/backgrounds/background_45.png"],
			["background.minstrel","scripts/skills/backgrounds/minstrel_background","ui/backgrounds/background_42.png"],
			["background.monk","scripts/skills/backgrounds/monk_background","ui/backgrounds/background_13.png"],
			["background.monk_turned_flagellant","scripts/skills/backgrounds/monk_turned_flagellant_background","ui/backgrounds/background_26.png"],
			["background.nomad","scripts/skills/backgrounds/nomad_background","ui/backgrounds/background_63.png"],
			["background.orc_slayer","scripts/skills/backgrounds/orc_slayer_background","ui/backgrounds/background_55.png"],
			["background.pacified_flagellant","scripts/skills/backgrounds/pacified_flagellant_background","ui/backgrounds/background_13.png"],
			["background.peddler","scripts/skills/backgrounds/peddler_background","ui/backgrounds/background_19.png"],
			["background.pimp","scripts/skills/backgrounds/pimp_background","ui/backgrounds/background_56.png"],
			["background.poacher","scripts/skills/backgrounds/poacher_background","ui/backgrounds/background_21.png"],
			["background.raider","scripts/skills/backgrounds/raider_background","ui/backgrounds/background_49.png"],
			["background.ratcatcher","scripts/skills/backgrounds/ratcatcher_background","ui/backgrounds/background_41.png"],
			["background.refugee","scripts/skills/backgrounds/refugee_background","ui/backgrounds/background_38.png"],
			["background.retired_soldier","scripts/skills/backgrounds/retired_soldier_background","ui/backgrounds/background_24.png"],
			["background.sellsword","scripts/skills/backgrounds/sellsword_background","ui/backgrounds/background_10.png"],
			["background.servant","scripts/skills/backgrounds/servant_background","ui/backgrounds/background_16.png"],
			["background.shepherd","scripts/skills/backgrounds/shepherd_background","ui/backgrounds/background_44.png"],
			["background.slave","scripts/skills/backgrounds/slave_background","ui/backgrounds/background_60.png"],
			["background.squire","scripts/skills/backgrounds/squire_background","ui/backgrounds/background_03.png"],
			["background.swordmaster","scripts/skills/backgrounds/swordmaster_background","ui/backgrounds/background_30.png"],
			["background.tailor","scripts/skills/backgrounds/tailor_background","ui/backgrounds/background_48.png"],
			["background.thief","scripts/skills/backgrounds/thief_background","ui/backgrounds/background_11.png"],
			["background.vagabond","scripts/skills/backgrounds/vagabond_background","ui/backgrounds/background_32.png"],
			["background.wildman","scripts/skills/backgrounds/wildman_background","ui/backgrounds/background_31.png"],
			["background.witchhunter","scripts/skills/backgrounds/witchhunter_background","ui/backgrounds/background_23.png"],
			["background.anatomist","scripts/skills/backgrounds/anatomist_background","ui/backgrounds/background_70.png"],
			["background.paladin","scripts/skills/backgrounds/paladin_background","ui/backgrounds/background_69.png"],
			["background.lindwurm_slayer","scripts/skills/backgrounds/lindwurm_slayer_background","ui/backgrounds/background_71.png"],
			//["background.regent_in_absentia","scripts/skills/backgrounds/regent_in_absentia_background","ui/backgrounds/background_06.png"],
		];
		return bgs;
	} 
	
 	function prepareNI() 
	{
		//this.World.Assets.getStash().getFirstEmptySlot()
		local namedstuff =
		{
			CurrentItem = {
				ConditionMax = null,
				StaminaModifier = null,
				MeleeDefense = null,
				RangedDefense = null,
				FatigueOnSkillUse = null,
				RegularDamage = null,
				RegularDamageMax = null,
				ArmorDamageMult = null,
				DirectDamageAdd = null,
				ChanceToHitHead = null,
				ShieldDamage = null,
				AdditionalAccuracy = null,
				AmmoMax = null,
			},
			Items = 
			{
				Weapons = 
				{
					Stats = ["ConditionMax", "StaminaModifier", "RegularDamage", "RegularDamageMax", "ArmorDamageMult", "DirectDamageAdd", "FatigueOnSkillUse", "ChanceToHitHead", "ShieldDamage", "AdditionalAccuracy", "AmmoMax"],
					Ref = "scripts/items/weapons/named/",
					Unwanted = "named_weapon",
					List = [],
				},
				Shields = 
				{
					Stats = ["ConditionMax", "StaminaModifier", "MeleeDefense", "RangedDefense", "FatigueOnSkillUse"],
					Ref = "scripts/items/shields/named/",
					Unwanted = "named_shield",
					List = [],
				},
				Armor = 
				{
					Stats = ["ConditionMax", "StaminaModifier"],
					Ref = "scripts/items/armor/named/",
					Unwanted = "named_armor",
					List = [],
				},
				Helmets = 
				{
					Stats = ["ConditionMax", "StaminaModifier"],
					Ref = "scripts/items/helmets/named/",
					Unwanted = "named_helmet",
					List = [],
				},
				Legendary = 
				{
					//Stats = [],
					List = ["scripts/items/armor/legendary/armor_of_davkul",
					"scripts/items/armor/legendary/emperors_armor",
					"scripts/items/armor/legendary/ijirok_armor",
					"scripts/items/helmets/legendary/emperors_countenance",
					"scripts/items/helmets/legendary/ijirok_helmet",
					"scripts/items/helmets/legendary/mask_of_davkul",
					"scripts/items/helmets/physician_mask",
					"scripts/items/armor/special/heraldic_armor",
					"scripts/items/helmets/faction_helm",
					"scripts/items/helmets/greatsword_faction_helm",
					"scripts/items/shields/legendary/gilders_embrace_shield",
					"scripts/items/shields/special/craftable_kraken_shield",
					"scripts/items/weapons/legendary/lightbringer_sword",
					"scripts/items/weapons/legendary/obsidian_dagger",
					"scripts/items/shields/special/craftable_schrat_shield",
					"scripts/items/accessory/legendary/cursed_crystal_skull",
					"scripts/items/accessory/undead_trophy_item",
					"scripts/items/accessory/orc_trophy_item",
					"scripts/items/accessory/goblin_trophy_item",
					"scripts/items/accessory/sergeant_badge_item",
					"scripts/items/accessory/hexen_trophy_item",
					"scripts/items/accessory/heavily_armored_wardog_item",
					"scripts/items/accessory/heavily_armored_warhound_item",
					"scripts/items/accessory/wolf_item",
					"scripts/items/accessory/falcon_item",
					"scripts/items/special/golden_goose_item",
					"scripts/items/accessory/oathtaker_skull_01_item",
					"scripts/items/accessory/oathtaker_skull_02_item",
					"scripts/items/helmets/greatsword_hat",
					"scripts/items/helmets/greatsword_faction_helm",
					"scripts/items/helmets/sallet_helmet",
					"scripts/items/helmets/full_helm",
					"scripts/items/helmets/adorned_full_helm",
					"scripts/items/helmets/oriental/assassin_head_wrap",
					"scripts/items/helmets/oriental/blade_dancer_head_wrap",
					"scripts/items/helmets/oriental/assassin_face_mask",
					"scripts/items/armor/oriental/assassin_robe",
					"scripts/items/armor/reinforced_leather_tunic",
					"scripts/items/armor/oriental/padded_mail_and_lamellar_hauberk",
					"scripts/items/armor/adorned_heavy_mail_hauberk",
					],
				},
				Alchemy = 
				{
					List = ["scripts/items/accessory/antidote_item",
					"scripts/items/accessory/berserker_mushrooms_item",
					"scripts/items/accessory/cat_potion_item",
					"scripts/items/accessory/iron_will_potion_item",
					"scripts/items/accessory/lionheart_potion_item",
					"scripts/items/accessory/night_vision_elixir_item",
					"scripts/items/accessory/poison_item",
					"scripts/items/accessory/spider_poison_item",
					"scripts/items/accessory/recovery_potion_item",
					"scripts/items/misc/miracle_drug_item",
					"scripts/items/misc/anatomist/alp_potion_item",
					"scripts/items/misc/anatomist/ancient_priest_potion_item",
					"scripts/items/misc/anatomist/apotheosis_potion_item",
					"scripts/items/misc/anatomist/direwolf_potion_item",
					"scripts/items/misc/anatomist/fallen_hero_potion_item",
					"scripts/items/misc/anatomist/geist_potion_item",
					"scripts/items/misc/anatomist/goblin_grunt_potion_item",
					"scripts/items/misc/anatomist/goblin_overseer_potion_item",
					"scripts/items/misc/anatomist/goblin_shaman_potion_item",
					"scripts/items/misc/anatomist/hexe_potion_item",
					"scripts/items/misc/anatomist/honor_guard_potion_item",
					"scripts/items/misc/anatomist/hyena_potion_item",
					"scripts/items/misc/anatomist/ifrit_potion_item",
					"scripts/items/misc/anatomist/ijirok_potion_item",
					"scripts/items/misc/anatomist/kraken_potion_item",
					"scripts/items/misc/anatomist/lindwurm_potion_item",
					"scripts/items/misc/anatomist/lorekeeper_potion_item",
					"scripts/items/misc/anatomist/nachzehrer_potion_item",
					"scripts/items/misc/anatomist/necromancer_potion_item",
					"scripts/items/misc/anatomist/necrosavant_potion_item",
					"scripts/items/misc/anatomist/orc_berserker_potion_item",
					"scripts/items/misc/anatomist/orc_warlord_potion_item",
					"scripts/items/misc/anatomist/orc_warrior_potion_item",
					"scripts/items/misc/anatomist/orc_young_potion_item",
					"scripts/items/misc/anatomist/rachegeist_potion_item",
					"scripts/items/misc/anatomist/schrat_potion_item",
					"scripts/items/misc/anatomist/serpent_potion_item",
					"scripts/items/misc/anatomist/skeleton_warrior_potion_item",
					"scripts/items/misc/anatomist/unhold_potion_item",
					"scripts/items/misc/anatomist/webknecht_potion_item",
					"scripts/items/misc/anatomist/wiederganger_potion_item",
					"scripts/items/misc/anatomist/research_notes_beasts_item",
					"scripts/items/misc/anatomist/research_notes_greenskins_item",
					"scripts/items/misc/anatomist/research_notes_legendary_item",
					"scripts/items/misc/anatomist/research_notes_undead_item",
					],
				},
				Misc = 
				{
					List = ["scripts/items/armor_upgrades/additional_padding_upgrade",
					"scripts/items/armor_upgrades/barbarian_horn_upgrade",
					"scripts/items/armor_upgrades/bone_platings_upgrade",
					"scripts/items/armor_upgrades/direwolf_pelt_upgrade",
					"scripts/items/armor_upgrades/heavy_gladiator_upgrade",
					"scripts/items/armor_upgrades/horn_plate_upgrade",
					"scripts/items/armor_upgrades/hyena_fur_upgrade",
					"scripts/items/armor_upgrades/light_gladiator_upgrade",
					"scripts/items/armor_upgrades/light_padding_replacement_upgrade",
					"scripts/items/armor_upgrades/lindwurm_scales_upgrade",
					"scripts/items/armor_upgrades/protective_runes_upgrade",
					"scripts/items/armor_upgrades/serpent_skin_upgrade",
					"scripts/items/armor_upgrades/unhold_fur_upgrade",
					"scripts/items/misc/unhold_hide_item",
					"scripts/items/misc/vampire_dust_item",
					"scripts/items/tools/smoke_bomb_item",
					"scripts/items/tools/fire_bomb_item",
					"scripts/items/tools/daze_bomb_item",
					"scripts/items/tools/holy_water_item",
					"scripts/items/tools/reinforced_throwing_net",
					"scripts/items/tools/acid_flask_item",
					"scripts/items/accessory/bandage_item",
					"scripts/items/supplies/cured_rations_item",
					],
				},
			},
		};
		foreach(type, value in namedstuff.Items)
		{
			if (type != "Legendary" && type != "Alchemy" && type != "Misc")
			{
				value.List = this.IO.enumerateFiles(value.Ref); //array
				local unwantedind = value.List.find(value.Ref+value.Unwanted);
				if (unwantedind != null)
				{
					value.List.remove(unwantedind)
				}
			}
		}
		return namedstuff;
	} 
	
	function PrintFrontEndReport( _result )
	{
		this.logDebug(_result); 
		//  SQ.call(this.mSQHandle, 'PrintFrontEndReport', "oilala");
		//  SQ.call(self.mSQHandle, 'PrintFrontEndReport', "oilala");
		// this.mSQHandle is a number = # of screen in registerScreens()
	}
	
	function onEntrySelected( _entityID )
	{
/* 		local roster = this.World.getTemporaryRoster();
		roster.clear();
		local temp = roster.create("scripts/entity/tactical/human");
		temp.copySpritesFrom(this.Tactical.getEntityByID(_entityID), [
			"body",
			"head",
			"beard",
			"hair",
			"tattoo_body",
			"beard_top"
		]);
		temp.setDirty(true);
		return temp.getImagePath(); */
	}

};


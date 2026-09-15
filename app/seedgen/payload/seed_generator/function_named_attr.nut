::include("seed_generator/define_lair");

local gt = this.getroottable();

gt.SeedGenerator.NamedIndex <- 0;
gt.SeedGenerator.NamedIndexDict <- {};

local NamedAttr = gt.SeedGenerator.NamedAttr;

local randomizeValues_Weapon = function()
{
	gt.SeedGenerator.NamedIndexDict[gt.SeedGenerator.NamedIndex] <- [];

	if (this.m.ConditionMax > 1)
	{
		this.m.Condition = this.Math.round(this.m.Condition * this.Math.rand(90, 140) * 0.01) * 1.0;
		this.m.ConditionMax = this.m.Condition;
	}

	local available = [];
	available.push(function ( _i )
	{
		local f = this.Math.rand(110, 130);
		gt.SeedGenerator.NamedIndexDict[gt.SeedGenerator.NamedIndex].extend([NamedAttr.RegularDamage, f, 110, 130]);
		_i.m.RegularDamage = this.Math.round(_i.m.RegularDamage * f * 0.01);
		_i.m.RegularDamageMax = this.Math.round(_i.m.RegularDamageMax * f * 0.01);
	});
	available.push(function ( _i )
	{
		local r = this.Math.rand(10, 30);
		gt.SeedGenerator.NamedIndexDict[gt.SeedGenerator.NamedIndex].extend([NamedAttr.ArmorDamageMult, r, 10, 30]);
		_i.m.ArmorDamageMult = _i.m.ArmorDamageMult + r * 0.01;
	});

	if (this.m.ChanceToHitHead > 0)
	{
		available.push(function ( _i )
		{
			local r = this.Math.rand(10, 20);
			gt.SeedGenerator.NamedIndexDict[gt.SeedGenerator.NamedIndex].extend([NamedAttr.ChanceToHitHead, r, 10, 20]);
			_i.m.ChanceToHitHead = _i.m.ChanceToHitHead + r;
		});
	}

	available.push(function ( _i )
	{
		local r = this.Math.rand(8, 16);
		gt.SeedGenerator.NamedIndexDict[gt.SeedGenerator.NamedIndex].extend([NamedAttr.DirectDamageAdd, r, 8, 16]);
		_i.m.DirectDamageAdd = _i.m.DirectDamageAdd + r * 0.01;
	});

	if (this.m.StaminaModifier <= -10)
	{
		available.push(function ( _i )
		{
			local r = this.Math.rand(50, 80);
			gt.SeedGenerator.NamedIndexDict[gt.SeedGenerator.NamedIndex].extend([NamedAttr.StaminaModifier, r, 50, 80]);
			_i.m.StaminaModifier = this.Math.round(_i.m.StaminaModifier * r * 0.01);
		});
	}

	if (this.m.ShieldDamage >= 16)
	{
		available.push(function ( _i )
		{
			local r = this.Math.rand(150, 200);
			gt.SeedGenerator.NamedIndexDict[gt.SeedGenerator.NamedIndex].extend([NamedAttr.ShieldDamage, r, 150, 200]);
			_i.m.ShieldDamage = this.Math.round(_i.m.ShieldDamage * r * 0.01);
		});
	}

	if (this.m.AmmoMax > 0)
	{
		available.push(function ( _i )
		{
			local r = this.Math.rand(1, 3);
			gt.SeedGenerator.NamedIndexDict[gt.SeedGenerator.NamedIndex].extend([NamedAttr.AmmoMax, r, 1, 3]);
			_i.m.AmmoMax = _i.m.AmmoMax + r;
			_i.m.Ammo = _i.m.AmmoMax;
		});
	}

	if (this.m.AdditionalAccuracy != 0 || this.isItemType(this.Const.Items.ItemType.RangedWeapon))
	{
		available.push(function ( _i )
		{
			local r = this.Math.rand(5, 15);
			gt.SeedGenerator.NamedIndexDict[gt.SeedGenerator.NamedIndex].extend([NamedAttr.AdditionalAccuracy, r, 5, 15]);
			_i.m.AdditionalAccuracy = _i.m.AdditionalAccuracy + r;
		});
	}

	available.push(function ( _i )
	{
		local r = this.Math.rand(1, 3);
		gt.SeedGenerator.NamedIndexDict[gt.SeedGenerator.NamedIndex].extend([NamedAttr.FatigueOnSkillUse, r, 1, 3]);
		_i.m.FatigueOnSkillUse = _i.m.FatigueOnSkillUse - r;
	});

	for( local n = 2; n != 0 && available.len() != 0; n = --n )
	{
		local r = this.Math.rand(0, available.len() - 1);
		available[r](this);
		available.remove(r);
	}
	this.m.NamedInitIndex = gt.SeedGenerator.NamedIndex;
	gt.SeedGenerator.NamedIndex++;
}

local randomizeValues_Shield = function()
{
	gt.SeedGenerator.NamedIndexDict[gt.SeedGenerator.NamedIndex] <- [];

	local available = [];
	available.push(function ( _i )
	{
		local r = this.Math.rand(120, 140);
		gt.SeedGenerator.NamedIndexDict[gt.SeedGenerator.NamedIndex].extend([NamedAttr.MeleeDefense, r, 120, 140]);
		_i.m.MeleeDefense = this.Math.round(_i.m.MeleeDefense * r * 0.01);
	});
	available.push(function ( _i )
	{
		local r = this.Math.rand(120, 140);
		gt.SeedGenerator.NamedIndexDict[gt.SeedGenerator.NamedIndex].extend([NamedAttr.RangedDefense, r, 120, 140]);
		_i.m.RangedDefense = this.Math.round(_i.m.RangedDefense * r * 0.01);
	});
	available.push(function ( _i )
	{
		local r = this.Math.rand(1, 3);
		gt.SeedGenerator.NamedIndexDict[gt.SeedGenerator.NamedIndex].extend([NamedAttr.FatigueOnSkillUse, r, 1, 3]);
		_i.m.FatigueOnSkillUse = _i.m.FatigueOnSkillUse - r;
	});
	available.push(function ( _i )
	{
		local r = this.Math.rand(120, 160);
		gt.SeedGenerator.NamedIndexDict[gt.SeedGenerator.NamedIndex].extend([NamedAttr.Condition, r, 120, 160]);
		_i.m.Condition = this.Math.round(_i.m.Condition * r * 0.01) * 1.0;
		_i.m.ConditionMax = _i.m.Condition;
	});
	available.push(function ( _i )
	{
		local r = this.Math.rand(70, 90);
		gt.SeedGenerator.NamedIndexDict[gt.SeedGenerator.NamedIndex].extend([NamedAttr.StaminaModifier, r, 70, 90]);
		_i.m.StaminaModifier = this.Math.round(_i.m.StaminaModifier * r * 0.01);
	});

	for( local n = 2; n != 0 && available.len() != 0; n = --n )
	{
		local r = this.Math.rand(0, available.len() - 1);
		available[r](this);
		available.remove(r);
	}
	this.m.NamedInitIndex = gt.SeedGenerator.NamedIndex;
	gt.SeedGenerator.NamedIndex++;
}

local randomizeValues_Helmet = function()
{
	local r1 = this.Math.rand(1, 4);
	local r2 = this.Math.rand(110, 125);
	gt.SeedGenerator.NamedIndexDict[gt.SeedGenerator.NamedIndex] <- [NamedAttr.StaminaModifier, r1, 1, 4, NamedAttr.Condition, r2, 110, 125];

	this.m.StaminaModifier = this.Math.min(-4, this.m.StaminaModifier + r1);
	this.m.Condition = this.Math.floor(this.m.Condition * r2 * 0.01) * 1.0;
	this.m.ConditionMax = this.m.Condition;
	this.m.NamedInitIndex = gt.SeedGenerator.NamedIndex;
	gt.SeedGenerator.NamedIndex++;
}

local randomizeValues_Armor = function()
{
	local r1 = this.Math.rand(3, 9);
	local r2 = this.Math.rand(110, 125);
	gt.SeedGenerator.NamedIndexDict[gt.SeedGenerator.NamedIndex] <- [NamedAttr.StaminaModifier, r1, 3, 9, NamedAttr.Condition, r2, 110, 125];

	this.m.StaminaModifier = this.Math.min(-8, this.m.StaminaModifier + r1);
	this.m.Condition = this.Math.floor(this.m.Condition * r2 * 0.01) * 1.0;
	this.m.ConditionMax = this.m.Condition;
	this.m.NamedInitIndex = gt.SeedGenerator.NamedIndex;
	gt.SeedGenerator.NamedIndex++;
}

::mods_hookClass("items/item",
  function(o) { ::mods_addField(o, "item", "NamedInitIndex", 0); });

::mods_hookClass("items/weapons/named/named_weapon",
  function(o) { ::mods_override(o, "randomizeValues", randomizeValues_Weapon); });

::mods_hookClass("items/shields/named/named_shield",
  function(o) { ::mods_override(o, "randomizeValues", randomizeValues_Shield); });

::mods_hookClass("items/helmets/named/named_helmet",
  function(o) { ::mods_override(o, "randomizeValues", randomizeValues_Helmet); });

::mods_hookClass("items/armor/named/named_armor",
  function(o) { ::mods_override(o, "randomizeValues", randomizeValues_Armor); });
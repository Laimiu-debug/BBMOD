this.afei_bottle_breakthrough <- this.inherit("scripts/skills/skill", {
	m = {
		CooldownUntil = 0
	},
	function create()
	{
		this.m.ID = "actives.afei_bottle_breakthrough";
		this.m.Name = "瓶队突破";
		this.m.Description = "准备一次突破：下一次单手近战武器单体攻击命中 +10，攻击后近防 -5 至下次自身行动开始。4 行动点、18 疲劳，冷却两轮。不消耗团队号令。\n\n[color=#8f2525]阶段1：[/color] 以「预备加成」近似设定中的替换基础攻击；完整武器技结算待实机校正。";
		this.m.Icon = "skills/active_01.png";
		this.m.IconDisabled = "skills/active_01_sw.png";
		this.m.Overlay = "active_01";
		this.m.Type = this.Const.SkillType.Active;
		this.m.Order = this.Const.SkillOrder.Any;
		this.m.IsSerialized = false;
		this.m.IsActive = true;
		this.m.IsTargeted = false;
		this.m.IsStacking = false;
		this.m.IsAttack = false;
		this.m.ActionPointCost = 4;
		this.m.FatigueCost = 18;
		this.m.MinRange = 0;
		this.m.MaxRange = 0;
	}

	function isUsable()
	{
		if (!this.skill.isUsable() || ::AfeiExpedition.getRound() < this.m.CooldownUntil)
		{
			return false;
		}

		local weapon = this.getContainer().getActor().getItems().getItemAtSlot(this.Const.ItemSlot.Mainhand);

		if (weapon == null || !weapon.isItemType(this.Const.Items.ItemType.MeleeWeapon) || weapon.isItemType(this.Const.Items.ItemType.TwoHanded))
		{
			return false;
		}

		return !this.getContainer().hasSkill("effects.afei_bottle_breakthrough_ready");
	}

	function onUse(_user, _targetTile)
	{
		_user.getSkills().add(this.new("scripts/skills/effects/afei_bottle_breakthrough_ready"));
		this.m.CooldownUntil = ::AfeiExpedition.getRound() + 2;
		return true;
	}

	function onCombatStarted()
	{
		this.m.CooldownUntil = 0;
	}
});

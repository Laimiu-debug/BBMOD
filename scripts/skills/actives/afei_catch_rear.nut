this.afei_catch_rear <- this.inherit("scripts/skills/skill", {
	m = {
		CooldownUntil = 0
	},
	function create()
	{
		this.m.ID = "actives.afei_catch_rear";
		this.m.Name = "接住后排";
		this.m.Description = "须持弓。选择 2–4 格敌人射击（伤害 50%），并给其相邻一名友军撤步标记：近防 +6，离开该敌人控制区时免除其脱离攻击。";
		this.m.Icon = "skills/active_119.png";
		this.m.IconDisabled = "skills/active_119_sw.png";
		this.m.Type = this.Const.SkillType.Active;
		this.m.Order = this.Const.SkillOrder.OffensiveTargeted;
		this.m.IsActive = true;
		this.m.IsTargeted = true;
		this.m.IsAttack = true;
		this.m.IsRanged = true;
		this.m.IsWeaponSkill = true;
		this.m.ActionPointCost = 4;
		this.m.FatigueCost = 18;
		this.m.MinRange = 2;
		this.m.MaxRange = 4;
	}
	function isUsable()
	{
		if (!this.skill.isUsable()) return false;
		if (::AfeiExpedition.getRound() < this.m.CooldownUntil) return false;
		local items = this.getContainer().getActor().getItems();
		local main = items.getItemAtSlot(this.Const.ItemSlot.Mainhand);
		return main != null && main.isItemType(this.Const.Items.ItemType.RangedWeapon);
	}
	function onVerifyTarget(_originTile, _targetTile)
	{
		if (!this.skill.onVerifyTarget(_originTile, _targetTile)) return false;
		local t = _targetTile.getEntity();
		return t != null && t.isAlive() && !t.isAlliedWith(this.getContainer().getActor());
	}
	function onAnySkillUsed(_skill, _targetEntity, _properties)
	{
		if (_skill == this)
		{
			_properties.DamageTotalMult *= 0.5;
		}
	}
	function onUse(_user, _targetTile)
	{
		local target = _targetTile.getEntity();
		if (target == null) return false;
		this.attackEntity(_user, target);
		local ally = null;
		local myFaction = _user.getFaction();
		for (local dir = 0; dir < 6; dir++)
		{
			if (!_targetTile.hasNextTile(dir)) continue;
			local t = _targetTile.getNextTile(dir);
			if (t == null || !t.IsOccupiedByActor) continue;
			local e = t.getEntity();
			if (e != null && e.isAlive() && e.isAlliedWith(_user) && e.getID() != _user.getID())
			{
				ally = e;
				break;
			}
		}
		if (ally != null)
		{
			local old = ally.getSkills().getSkillByID("effects.afei_withdraw_mark");
			if (old != null) old.removeSelf();
			local mark = this.new("scripts/skills/effects/afei_withdraw_mark_effect");
			mark.setEnemyID(target.getID());
			ally.getSkills().add(mark);
			ally.getFlags().set("afei_withdraw_enemy", target.getID());
			_user.getFlags().set("afei_catch_rear_used", true);
		}
		this.m.CooldownUntil = ::AfeiExpedition.getRound() + 3;
		return true;
	}
	function onCombatStarted()
	{
		this.m.CooldownUntil = 0;
	}
});

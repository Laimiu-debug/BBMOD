this.afei_pokemon <- this.inherit("scripts/skills/skill", {
	m = {
		CooldownUntil = 0
	},
	function create()
	{
		this.m.ID = "actives.afei_pokemon";
		this.m.Name = "保可梦";
		this.m.Description = "指定四格内一名伙伴：远防 +8 两轮（成长后再 +4 近防）。期间记录威胁；你对该威胁的首次远程命中 +8。被护者闪避单体攻击时你可恢复疲劳。";
		this.m.Icon = "skills/active_119.png";
		this.m.IconDisabled = "skills/active_119_sw.png";
		this.m.Type = this.Const.SkillType.Active;
		this.m.Order = this.Const.SkillOrder.Any;
		this.m.IsActive = true;
		this.m.IsTargeted = true;
		this.m.IsAttack = false;
		this.m.ActionPointCost = 4;
		this.m.FatigueCost = 16;
		this.m.MinRange = 1;
		this.m.MaxRange = 4;
	}
	function isUsable()
	{
		if (!this.skill.isUsable())
		{
			return false;
		}
		return ::AfeiExpedition.getRound() >= this.m.CooldownUntil;
	}
	function onVerifyTarget(_originTile, _targetTile)
	{
		if (!this.skill.onVerifyTarget(_originTile, _targetTile))
		{
			return false;
		}
		local t = _targetTile.getEntity();
		return t != null && t.isAlive() && t.isAlliedWith(this.getContainer().getActor()) && t.getID() != this.getContainer().getActor().getID();
	}
	function onUse(_user, _targetTile)
	{
		local target = _targetTile.getEntity();
		local old = target.getSkills().getSkillByID("effects.afei_pokemon");
		if (old != null)
		{
			old.removeSelf();
		}
		local effect = this.new("scripts/skills/effects/afei_pokemon_effect");
		effect.setWatcher(_user.getID());
		target.getSkills().add(effect);
		_user.getFlags().set("afei_pokemon_ward", target.getID());
		this.m.CooldownUntil = ::AfeiExpedition.getRound() + 3;
		return true;
	}
	function onAnySkillUsed(_skill, _targetEntity, _properties)
	{
		if (_skill == null || !_skill.isAttack() || !_skill.isRanged() || _targetEntity == null)
		{
			return;
		}
		local wardId = this.getContainer().getActor().getFlags().get("afei_pokemon_ward");
		if (wardId == null)
		{
			return;
		}
		foreach (a in this.Tactical.Entities.getInstancesOfFaction(this.getContainer().getActor().getFaction()))
		{
			if (a == null || a.getID() != wardId)
			{
				continue;
			}
			local eff = a.getSkills().getSkillByID("effects.afei_pokemon");
			if (eff != null && eff.m.ThreatID == _targetEntity.getID())
			{
				_properties.RangedSkill += 8;
			}
			break;
		}
	}
	function onCombatStarted()
	{
		this.m.CooldownUntil = 0;
		this.getContainer().getActor().getFlags().set("afei_pokemon_ward", null);
	}
});

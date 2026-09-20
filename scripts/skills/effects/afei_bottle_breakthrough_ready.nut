this.afei_bottle_breakthrough_ready <- this.inherit("scripts/skills/skill", {
	m = {
		Pending = true
	},
	function create()
	{
		this.m.ID = "effects.afei_bottle_breakthrough_ready";
		this.m.Name = "瓶队突破（预备）";
		this.m.Description = "下一次单手近战单体攻击命中 +10；攻击后获得近防空当。";
		this.m.Icon = "skills/status_effect_01.png";
		this.m.Type = this.Const.SkillType.StatusEffect;
		this.m.IsActive = false;
		this.m.IsStacking = false;
		this.m.IsRemovedAfterBattle = true;
	}

	function onAnySkillUsed(_skill, _targetEntity, _properties)
	{
		if (this.m.Pending && _skill != null && _skill.isAttack() && !_skill.isRanged())
		{
			_properties.MeleeSkill += 10;
		}
	}

	function onAnySkillExecuted(_skill, _targetTile, _targetEntity, _forFree)
	{
		if (this.m.Pending && _skill != null && _skill.isAttack() && !_skill.isRanged())
		{
			this.m.Pending = false;
			local actor = this.getContainer().getActor();
			this.removeSelf();
			actor.getSkills().add(this.new("scripts/skills/effects/afei_bottle_breakthrough_penalty"));
		}
	}
});

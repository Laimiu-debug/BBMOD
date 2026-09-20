this.afei_gaga_ready_effect <- this.inherit("scripts/skills/skill", {
	m = {
		Pending = true
	},
	function create()
	{
		this.m.ID = "effects.afei_gaga_ready";
		this.m.Name = "嘎嘎冲（预备）";
		this.m.Description = "下一次单手近战单体攻击：护甲伤害 +10%；默认命中 -5（成长后取消命中惩罚）。";
		this.m.Icon = "skills/status_effect_01.png";
		this.m.Type = this.Const.SkillType.StatusEffect;
		this.m.IsRemovedAfterBattle = true;
	}
	function onAnySkillUsed(_skill, _targetEntity, _properties)
	{
		if (!this.m.Pending || _skill == null || !_skill.isAttack() || _skill.isRanged())
		{
			return;
		}
		local actor = this.getContainer().getActor();
		if (!actor.getFlags().get("afei_gaga_no_hit_pen") && !this.World.Flags.get(::AfeiExpedition.Flags.GrowthDone + "C13"))
		{
			_properties.MeleeSkill -= 5;
		}
		_properties.DamageArmorMult *= 1.1;
	}
	function onAnySkillExecuted(_skill, _targetTile, _targetEntity, _forFree)
	{
		if (!this.m.Pending || _skill == null || !_skill.isAttack() || _skill.isRanged())
		{
			return;
		}
		this.m.Pending = false;
		local actor = this.getContainer().getActor();
		actor.getFlags().set("afei_gaga_used", true);
		this.removeSelf();
	}
});

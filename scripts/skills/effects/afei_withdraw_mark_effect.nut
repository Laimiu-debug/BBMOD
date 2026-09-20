this.afei_withdraw_mark_effect <- this.inherit("scripts/skills/skill", {
	m = {
		EnemyID = null,
		TurnsLeft = 1
	},
	function create()
	{
		this.m.ID = "effects.afei_withdraw_mark";
		this.m.Name = "撤步标记";
		this.m.Description = "下次单格离开标记敌人控制区时，免除来自该敌人的脱离攻击。";
		this.m.Icon = "skills/status_effect_34.png";
		this.m.Type = this.Const.SkillType.StatusEffect;
		this.m.IsRemovedAfterBattle = true;
	}
	function setEnemyID(_id)
	{
		this.m.EnemyID = _id;
	}
	function onUpdate(_properties)
	{
		_properties.MeleeDefense += 6;
		::AfeiExpedition.noteOriginDefense(this.getContainer().getActor(), 6, 0);
		try { _properties.IsIgnoringZoneOfControlAlways = true; } catch (error1) {}
		try { _properties.IsImmuneToZoneOfControl = true; } catch (error2) {}
	}
	function onTurnEnd()
	{
		if (--this.m.TurnsLeft <= 0) this.removeSelf();
	}
});

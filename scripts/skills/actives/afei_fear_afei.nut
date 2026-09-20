this.afei_fear_afei <- this.inherit("scripts/skills/skill", {
	m = { Armed = false },
	function create()
	{
		this.m.ID = "actives.afei_fear_afei";
		this.m.Name = "恐飞派";
		this.m.Description = "每战第一次成为阿飞号令受益者：立即恢复 8 疲劳，本轮下次武器攻击命中 -5。怼一句后清除惩罚。";
		this.m.Icon = "ui/orientation/shortsword_orientation.png";
		this.m.Type = this.Const.SkillType.Special;
		this.m.IsActive = false;
	}
	function onUpdate(_properties)
	{
		if (this.m.Armed) { _properties.MeleeSkill -= 5; _properties.RangedSkill -= 5; }
	}
	function triggerFromAfeiOrder()
	{
		if (this.getContainer().getActor().getFlags().get("afei_fear_triggered")) { return; }
		local actor = this.getContainer().getActor();
		actor.getFlags().set("afei_fear_triggered", true);
		local recover = ::AfeiExpedition.consumeFatigueRecoverBudget(8);
		actor.setFatigue(this.Math.max(0, actor.getFatigue() - recover));
		this.m.Armed = true;
	}
	function clearPenalty() { this.m.Armed = false; }
	function onTurnEnd() { this.m.Armed = false; }
	function onCombatStarted()
	{
		this.m.Armed = false;
		this.getContainer().getActor().getFlags().set("afei_fear_triggered", false);
	}
});

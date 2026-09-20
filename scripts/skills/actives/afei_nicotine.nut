this.afei_nicotine <- this.inherit("scripts/skills/skill", {
	m = { IsSpent = false, Debt = 0 },
	function create()
	{
		this.m.ID = "actives.afei_nicotine";
		this.m.Name = "尼古丁";
		this.m.Description = "每战一次。立即移除 15 点已积累疲劳；随后两次行动开始的恢复各 -5。";
		this.m.Icon = "skills/active_41.png";
		this.m.IconDisabled = "skills/active_41_sw.png";
		this.m.Type = this.Const.SkillType.Active;
		this.m.IsActive = true;
		this.m.IsTargeted = false;
		this.m.ActionPointCost = 2;
		this.m.FatigueCost = 0;
	}
	function isUsable()
	{
		if (!this.skill.isUsable() || this.m.IsSpent) { return false; }
		return this.getContainer().getActor().getFatigue() >= 15;
	}
	function onUse(_user, _targetTile)
	{
		_user.setFatigue(this.Math.max(0, _user.getFatigue() - 15));
		this.m.IsSpent = true;
		this.m.Debt = 2;
		return true;
	}
	function onTurnStart()
	{
		if (this.m.Debt > 0)
		{
			local actor = this.getContainer().getActor();
			// approximate: add 5 fatigue as reduced recovery
			actor.setFatigue(this.Math.min(actor.getFatigueMax(), actor.getFatigue() + 5));
			this.m.Debt -= 1;
		}
	}
	function onCombatStarted() { this.m.IsSpent = false; this.m.Debt = 0; }
});

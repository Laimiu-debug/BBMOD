this.afei_return_arrow <- this.inherit("scripts/skills/skill", {
	m = {
		UsedThisRound = false
	},
	function create()
	{
		this.m.ID = "actives.afei_return_arrow";
		this.m.Name = "回头箭";
		this.m.Description = "本轮完成足够普通移动后，第一次远程武器攻击命中 +7（成长后所需移动降为 1 格）。";
		this.m.Icon = "ui/orientation/shortsword_orientation.png";
		this.m.Type = this.Const.SkillType.Special;
		this.m.IsActive = false;
		this.m.IsStacking = false;
	}
	function getNeededMove()
	{
		local actor = this.getContainer().getActor();
		if (actor.getFlags().get("afei_late_aim_1") || this.World.Flags.get(::AfeiExpedition.Flags.GrowthDone + "C12"))
		{
			return 1;
		}
		return 2;
	}
	function onTurnStart()
	{
		this.m.UsedThisRound = false;
		this.getContainer().getActor().getFlags().set("afei_tiles_moved_round", 0);
	}
	function onCombatStarted()
	{
		this.m.UsedThisRound = false;
		this.getContainer().getActor().getFlags().set("afei_tiles_moved_round", 0);
	}
	function onAnySkillUsed(_skill, _targetEntity, _properties)
	{
		if (this.m.UsedThisRound || _skill == null || !_skill.isAttack() || !_skill.isRanged())
		{
			return;
		}
		local moved = this.getContainer().getActor().getFlags().getAsInt("afei_tiles_moved_round");
		if (moved < this.getNeededMove())
		{
			return;
		}
		_properties.RangedSkill += 7;
		::AfeiExpedition.noteOriginHit(this.getContainer().getActor(), 0, 7);
	}
	function onAnySkillExecuted(_skill, _targetTile, _targetEntity, _forFree)
	{
		if (this.m.UsedThisRound || _skill == null || !_skill.isAttack() || !_skill.isRanged())
		{
			return;
		}
		local moved = this.getContainer().getActor().getFlags().getAsInt("afei_tiles_moved_round");
		if (moved < this.getNeededMove())
		{
			return;
		}
		this.m.UsedThisRound = true;
	}
});

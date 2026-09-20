this.afei_abacus_mark_effect <- this.inherit("scripts/skills/skill", {
	m = {
		TurnsLeft = 2
	},
	function create()
	{
		this.m.ID = "effects.afei_abacus_mark";
		this.m.Name = "记账";
		this.m.Description = "下一次受到的友军单体武器攻击命中 +10（命中或未中均消耗）。由地精算盘施加；命中修正见 preload 钩子。";
		this.m.Icon = "skills/status_effect_62.png";
		this.m.Type = this.Const.SkillType.StatusEffect;
		this.m.IsActive = false;
		this.m.IsStacking = false;
		this.m.IsRemovedAfterBattle = true;
	}

	function getTooltip()
	{
		return [
			{
				id = 1,
				type = "title",
				text = this.getName()
			},
			{
				id = 2,
				type = "description",
				text = this.getDescription()
			},
			{
				id = 10,
				type = "text",
				icon = "ui/icons/hitchance.png",
				text = "剩余 " + this.m.TurnsLeft + " 轮"
			}
		];
	}

	function onTurnEnd()
	{
		if (--this.m.TurnsLeft <= 0)
		{
			this.removeSelf();
		}
	}
});

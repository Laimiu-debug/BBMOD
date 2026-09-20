this.afei_abacus_mark <- this.inherit("scripts/skills/skill", {
	m = {
		CooldownUntil = 0
	},
	function create()
	{
		this.m.ID = "actives.afei_abacus_mark";
		this.m.Name = "地精算盘";
		this.m.Description = "给四格内一名可见敌人记账。下一次友军对该目标的单体武器攻击命中 +10。不消耗团队号令。冷却两轮。G02 前同时只保留一组；G02 后每组最多两个不同敌人。";
		this.m.Icon = "skills/active_70.png";
		this.m.IconDisabled = "skills/active_70_sw.png";
		this.m.Overlay = "active_70";
		this.m.Type = this.Const.SkillType.Active;
		this.m.Order = this.Const.SkillOrder.UtilityTargeted;
		this.m.IsSerialized = false;
		this.m.IsActive = true;
		this.m.IsTargeted = true;
		this.m.IsStacking = false;
		this.m.IsAttack = false;
		this.m.ActionPointCost = 3;
		this.m.FatigueCost = 10;
		this.m.MinRange = 1;
		this.m.MaxRange = 4;
	}

	function isUsable()
	{
		return this.skill.isUsable() && ::AfeiExpedition.getRound() >= this.m.CooldownUntil;
	}

	function onVerifyTarget(_originTile, _targetTile)
	{
		if (!this.skill.onVerifyTarget(_originTile, _targetTile))
		{
			return false;
		}

		local target = _targetTile.getEntity();
		return target != null && target.isAlive() && !target.isAlliedWith(this.getContainer().getActor());
	}

	function onUse(_user, _targetTile)
	{
		local target = _targetTile.getEntity();
		local dual = this.World.Flags.get("afei_abacus_dual") || this.World.Flags.get(::AfeiExpedition.Flags.GrowthDone + "C02");

		if (!dual)
		{
			try
			{
				local all = this.Tactical.Entities.getAllInstancesAsArray();

				foreach (a in all)
				{
					local old = a.getSkills().getSkillByID("effects.afei_abacus_mark");

					if (old != null)
					{
						old.removeSelf();
					}
				}
			}
			catch (error)
			{
				local old = target.getSkills().getSkillByID("effects.afei_abacus_mark");

				if (old != null)
				{
					old.removeSelf();
				}
			}
		}
		else
		{
			local marked = 0;

			try
			{
				foreach (a in this.Tactical.Entities.getAllInstancesAsArray())
				{
					if (a != null && a.getSkills().hasSkill("effects.afei_abacus_mark"))
					{
						marked += 1;
					}
				}
			}
			catch (error2)
			{
			}

			if (marked >= 2 && !target.getSkills().hasSkill("effects.afei_abacus_mark"))
			{
				// 去掉最早的一个近似：清掉任一旧标记腾名额
				try
				{
					foreach (a in this.Tactical.Entities.getAllInstancesAsArray())
					{
						local old = a.getSkills().getSkillByID("effects.afei_abacus_mark");

						if (old != null)
						{
							old.removeSelf();
							break;
						}
					}
				}
				catch (error3)
				{
				}
			}
		}

		if (!target.getSkills().hasSkill("effects.afei_abacus_mark"))
		{
			target.getSkills().add(this.new("scripts/skills/effects/afei_abacus_mark_effect"));
		}

		this.m.CooldownUntil = ::AfeiExpedition.getRound() + 2;
		return true;
	}

	function onCombatStarted()
	{
		this.m.CooldownUntil = 0;
	}
});

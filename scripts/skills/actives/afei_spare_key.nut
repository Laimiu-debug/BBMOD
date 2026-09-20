this.afei_spare_key <- this.inherit("scripts/skills/skill", {
	m = {
		CooldownUntil = 0,
		IsSpent = false
	},
	function create()
	{
		this.m.ID = "actives.afei_spare_key";
		this.m.Name = "备用钥匙";
		this.m.Description = "解除自身或相邻友军身上的网缚/定身类效果（每战一次，冷却两轮）。";
		this.m.Icon = "skills/active_119.png";
		this.m.IconDisabled = "skills/active_119_sw.png";
		this.m.Type = this.Const.SkillType.Active;
		this.m.Order = this.Const.SkillOrder.Any;
		this.m.IsActive = true;
		this.m.IsTargeted = true;
		this.m.IsAttack = false;
		this.m.ActionPointCost = 3;
		this.m.FatigueCost = 10;
		this.m.MinRange = 0;
		this.m.MaxRange = 1;
	}
	function isUsable()
	{
		if (!this.skill.isUsable())
		{
			return false;
		}

		if (this.m.IsSpent)
		{
			return false;
		}

		if (::AfeiExpedition.getRound() < this.m.CooldownUntil)
		{
			return false;
		}

		return true;
	}
	function onVerifyTarget(_originTile, _targetTile)
	{
		if (!this.skill.onVerifyTarget(_originTile, _targetTile))
		{
			return false;
		}

		local t = _targetTile.getEntity();
		return t != null && t.isAlive() && t.isAlliedWith(this.getContainer().getActor());
	}
	function onUse(_user, _targetTile)
	{
		local t = _targetTile.getEntity();
		local ids = [
			"effects.net",
			"effects.web",
			"effects.rooted",
			"effects.rooted_effect",
			"effects.sleeping",
			"effects.stunned",
			"effects.insect_swarm"
		];
		local removed = 0;

		foreach (id in ids)
		{
			local e = t.getSkills().getSkillByID(id);

			if (e != null)
			{
				e.removeSelf();
				removed += 1;
			}
		}

		try
		{
			local skills = t.getSkills().getAllSkillsOfType(this.Const.SkillType.StatusEffect);

			foreach (s in skills)
			{
				if (s == null)
				{
					continue;
				}

				local sid = s.getID();

				if (sid.find("net") != null || sid.find("web") != null || sid.find("root") != null)
				{
					s.removeSelf();
					removed += 1;
				}
			}
		}
		catch (error)
		{
		}

		t.getFlags().set("afei_net_free", t.getFlags().getAsInt("afei_net_free") + 1);
		this.m.IsSpent = true;
		this.m.CooldownUntil = ::AfeiExpedition.getRound() + 2;
		return true;
	}
	function onCombatStarted()
	{
		this.m.CooldownUntil = 0;
		this.m.IsSpent = false;
	}
});

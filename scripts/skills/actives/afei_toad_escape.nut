this.afei_toad_escape <- this.inherit("scripts/skills/skill", {
	m = {
		IsSpent = false
	},
	function create()
	{
		this.m.ID = "actives.afei_toad_escape";
		this.m.Name = "蛤蟆";
		this.m.Description = "每战一次。生命不高于最大值一半，或邻接至少两名敌人时，可移至相邻同高合法空地，免除此步脱离攻击。不消耗团队号令。";
		this.m.Icon = "skills/active_42.png";
		this.m.IconDisabled = "skills/active_42_sw.png";
		this.m.Overlay = "active_42";
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
		this.m.MaxRange = 1;
	}

	function isUsable()
	{
		if (!this.skill.isUsable() || this.m.IsSpent)
		{
			return false;
		}

		local actor = this.getContainer().getActor();
		local hpLow = actor.getHitpointsPct() <= 0.5;
		local enemies = 0;
		local myTile = actor.getTile();

		for (local i = 0; i < 6; i++)
		{
			if (myTile.hasNextTile(i))
			{
				local t = myTile.getNextTile(i);

				if (t.IsOccupiedByActor && !t.getEntity().isAlliedWith(actor))
				{
					enemies++;
				}
			}
		}

		return hpLow || enemies >= 2;
	}

	function onVerifyTarget(_originTile, _targetTile)
	{
		if (!this.skill.onVerifyTarget(_originTile, _targetTile))
		{
			return false;
		}

		if (_targetTile.IsOccupiedByActor || !_targetTile.IsEmpty)
		{
			return false;
		}

		if (_targetTile.Level > _originTile.Level)
		{
			return false;
		}

		return true;
	}

	function onUse(_user, _targetTile)
	{
		this.m.IsSpent = true;
		this.Tactical.getNavigator().teleport(_user, _targetTile, null, null, false);
		return true;
	}

	function onCombatStarted()
	{
		this.m.IsSpent = false;
	}
});

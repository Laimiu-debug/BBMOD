::mods_registerMod("mod_breditor", 1.0, "Breditor");

::mods_queue("mod_breditor", null, function() {
/* 	::mods_registerJS("world_breditor_screen.js");
 	::mods_registerCSS("world_breditor_screen.css"); */

	
	::mods_hookNewObjectOnce("states/world_state", function(o) {
	  local ws_init_ui = o.onInitUI;
	  o.onInitUI = function()
	  {
		ws_init_ui();
		this.m.WorldBreditorScreen <- this.new("scripts/ui/screens/world/world_breditor_screen");
		this.m.WorldBreditorScreen.setOnClosePressedListener(this.town_screen_main_dialog_module_onLeaveButtonClicked.bindenv(this));
		this.initLoadingScreenHandler();
	  }
	});
	
	::mods_hookNewObjectOnce("states/world_state", function(o) {
	  local ws_destroy_ui = o.onDestroyUI;
	  o.onDestroyUI = function()
	  {
		ws_destroy_ui();
		this.m.WorldBreditorScreen.destroy();
		this.m.WorldBreditorScreen = null;
	  }
	});
	
	::mods_hookNewObjectOnce("ui/screens/tooltip/tooltip_events", function(o) {
	  local queryTooltipData = o.general_queryUIElementTooltipData;
	  o.general_queryUIElementTooltipData = function(entityId, elementId, elementOwner)
	  {
		local tooltip = queryTooltipData(entityId, elementId, elementOwner);
		if(tooltip != null) return tooltip;
		if(elementId == "breditor-talent-tooltip")
		{
		  return [
			{
			  id = 1,
			  type = "title",
			  text = "属性天赋"
			},
			{
			  id = 2,
			  type = "description",
			  text = "点击以在不同天赋级别上循环。0-1-2-3-0-1-2-3-..."
			},
		  ];
		}
/* 		else if(elementId == "breditor-stats-tooltip")
		{
		  return [
			{
			  id = 1,
			  type = "title",
			  text = "Attributes"
			},
 			{
			  id = 2,
			  type = "description",
			  text = "Current value of the respective attribute (without any bonuses from traits or equipment) // maximum possible starting value of the respective attribute for a character of this particular background."
			}, 
		  ];
		} */
		else if(elementId == "breditor-xp-tooltip")
		{
		  return [
			{
			  id = 1,
			  type = "title",
			  text = "原地升级"
			},
 			{
			  id = 2,
			  type = "description",
			  text = "给予目前这个兄弟正好能够升到下一级的经验。"
			}, 
		  ];
		}
		else if(elementId == "breditor-pp-tooltip")
		{
		  return [
			{
			  id = 1,
			  type = "title",
			  text = "特技点"
			},
 			{
			  id = 2,
			  type = "description",
			  text = "这里显示你的特技点数量。"
			}, 
		  ];
		}
		else if(elementId == "breditor-op-tooltip")
		{
		  return [
			{
			  id = 1,
			  type = "title",
			  text = "洗点"
			},
 			{
			  id = 2,
			  type = "description",
			  text = "点击立刻喝下一瓶遗忘药水。"
			}, 
		  ];
		}
		else if(elementId == "breditor-yf-tooltip")
		{
		  return [
			{
			  id = 1,
			  type = "title",
			  text = "不老泉"
			},
 			{
			  id = 2,
			  type = "description",
			  text = "点击立刻喝下不老泉的水，它可以治疗你的所有伤势并提升心情。"
			}, 
		  ];
		}
		else if(elementId == "breditor-bg-tooltip")
		{
		  return [
			{
			  id = 1,
			  type = "title",
			  text = "背景"
			},
 			{
			  id = 2,
			  type = "description",
			  text = "将特性面板切换到背景面板以修改兄弟的背景。也可以再切换回来。"
			}, //\n[b][color=" + this.Const.UI.Color.NegativeValue + "]Warning! Changing background may change your level, even reduce it. That is just how some backgrounds work.[/color][/b]
		  ];
		}
		else if(elementId == "breditor-background-tooltip")
		{
		  local bgtemp = this.new(elementOwner);
		  return [
			{
			  id = 1,
			  type = "title",
			  text = bgtemp.m.Name,
			},
 			{
			  id = 2,
			  type = "description",
			  text = bgtemp.m.BackgroundDescription,
			}, 
		  ];
		}
		else if(elementId == "breditor-nicategory-tooltip")
		{
		  return [
			{
			  id = 1,
			  type = "title",
			  text = "特殊物品分类"
			},
 			{
			  id = 2,
			  type = "description",
			  text = "选择一项物品分类。"
			}, 
		  ];
		}
		else if(elementId == "breditor-niupdateimage-tooltip")
		{
		  return [
			{
			  id = 1,
			  type = "title",
			  text = "重掷"
			},
 			{
			  id = 2,
			  type = "description",
			  text = "重新随机生成物品，可以作为第一步来选择想要的物品外观。"
			}, 
		  ];
		}
		else if(elementId == "breditor-nifinalize-tooltip")
		{
		  return [
			{
			  id = 1,
			  type = "title",
			  text = "添置物品"
			},
 			{
			  id = 2,
			  type = "description",
			  text = "把这件物品加入你的仓库。"
			}, 
		  ];
		}
		else if(elementId == "breditor-partystrength-tooltip")
		{
		  return [
			{
			  id = 1,
			  type = "title",
			  text = "团队战力"
			},
 			{
			  id = 2,
			  type = "description",
			  text = "计算你的：\n- 团队战力\n- 合同难度系数\n- 敌方团队难度系数"
			}, 
		  ];
		}
		else if(elementId == "breditor-mirrorbattle-tooltip")
		{
		  return [
			{
			  id = 1,
			  type = "title",
			  text = "镜像战斗"
			},
 			{
			  id = 2,
			  type = "description",
			  text = "与你战团的镜像大战一场！\n(并非正常的游戏内容，仅用于测试与娱乐)"
			}, 
		  ];
		}
		else if(elementId == "breditor-haircolor-tooltip")
		{
		  return [
			{
			  id = 1,
			  type = "title",
			  text = "发色"
			},
 			{
			  id = 2,
			  type = "description",
			  text = "与导入导出系统无关。如果你在导入导出的窗口粘贴(CTRL+V)或输入6位颜色代码然后按下这个按钮，当前兄弟的头发会被染成对应颜色。\n染发无法导入导出或撤销，只能用新的颜色取代。染发相当于在你在理发店选择的发色上又套了一层颜色，所以你无法将黑发染成白色。(使用白色代码 ffffff = 没有用染发)。"
			}, 
		  ];
		}
		else if(elementId == "breditor-beardcolor-tooltip")
		{
		  return [
			{
			  id = 1,
			  type = "title",
			  text = "须色"
			},
 			{
			  id = 2,
			  type = "description",
			  text = "与导入导出系统无关。如果你在导入导出的窗口粘贴(CTRL+V)或输入6位颜色代码然后按下这个按钮，当前兄弟的胡须会被染成对应颜色。\n染须无法导入导出或撤销，只能用新的颜色取代。染须相当于在你在理发店选择的须色上又套了一层颜色，所以你无法将黑须染成白色。(使用白色代码 ffffff = 没有用染发)。"
			}, 
		  ];
		}
		else if(elementId == "breditor-impexpstats-tooltip")
		{
		  return [
			{
			  id = 1,
			  type = "title",
			  text = "导出主要属性"
			},
 			{
			  id = 2,
			  type = "description",
			  text = "是或否 - 决定导出的字符串中是否包含你兄弟的[b][color=" + this.Const.UI.Color.PositiveValue + "]主要属性[/color][/b](具体包含属性值，特性，特技，等级，经验，外观，天赋)。点击切换。"
			}, 
		  ];
		}
		else if(elementId == "breditor-impexplifestats-tooltip")
		{
		  return [
			{
			  id = 1,
			  type = "title",
			  text = "导出生涯统计"
			},
 			{
			  id = 2,
			  type = "description",
			  text = "是或否 - 决定导出的字符串中是否包含你兄弟的[b][color=" + this.Const.UI.Color.PositiveValue + "]生涯统计[/color][/b] - 例如杀敌数和参战数。点击切换。"
			}, 
		  ];
		}
		else if(elementId == "breditor-impexpgear-tooltip")
		{
		  return [
			{
			  id = 1,
			  type = "title",
			  text = "导出装备"
			},
 			{
			  id = 2,
			  type = "description",
			  text = "是或否 - 决定导出的字符串中是否包含你兄弟目前的 [b][color=" + this.Const.UI.Color.PositiveValue + "]装备[/color][/b]。这只会记录物品大的类别和标准数据，不会记录特殊物品的特殊数值。点击切换。"
			}, 
		  ];
		}
		else if(elementId == "breditor-broexport-tooltip")
		{
		  return [
			{
			  id = 1,
			  type = "title",
			  text = "导出"
			},
 			{
			  id = 2,
			  type = "description",
			  text = "点击生成一段包含当前兄弟信息的字符串。之后点选字符串所在区域按下CTRL+A再按CTRL+C以将其保存至剪切板。"
			}, 
		  ];
		}
		else if(elementId == "breditor-broimport-tooltip")
		{
		  return [
			{
			  id = 1,
			  type = "title",
			  text = "导入"
			},
 			{
			  id = 2,
			  type = "description",
			  text = "用前须知，按下CTRL+A再按CTRL+V将一段包含一个兄弟信息的字符串粘贴进上方的区域(如果里面还没有需要的字符串)。[b][color=" + this.Const.UI.Color.NegativeValue + "]一定要确认里面除了纯净的字符串外没有多余的字符。[/color][/b]\n之后按下这个按钮便可以将你选择的兄弟替换。\n[b][color=" + this.Const.UI.Color.NegativeValue + "]彻底不推荐在不同版本的游戏间导入导出角色，在打了不同MOD的游戏之间了直接论外。[/color][/b]"
			}, 
		  ];
		}
		return null;
	  }
	});
	
	::mods_hookNewObjectOnce("states/world_state", function(o) {
	  local keyHandler = o.helper_handleContextualKeyInput;
	  o.helper_handleContextualKeyInput = function(key)
	  {
		if(!keyHandler(key) && key.getState() == 0)
		{
		  if (key.getKey() == 34 && key.getModifier() == 1) //SHIFT + X
			if (!this.m.MenuStack.hasBacksteps() && !this.m.CharacterScreen.isVisible() && !this.m.WorldTownScreen.isVisible() && !this.m.EventScreen.isVisible() && !this.m.EventScreen.isAnimating())
			{
				this.setAutoPause(true);
				this.m.CustomZoom = this.World.getCamera().Zoom;
				this.World.getCamera().zoomTo(1.0, 4.0);
				this.Tooltip.hide();
				this.m.WorldScreen.hide();
				this.m.WorldBreditorScreen.show();
				this.Cursor.setCursor(this.Const.UI.Cursor.Hand);
				this.m.MenuStack.push(function ()
				{
					this.World.getCamera().zoomTo(this.m.CustomZoom, 4.0);
					this.m.WorldBreditorScreen.hide();
					this.m.WorldScreen.show();
					this.Cursor.setCursor(this.Const.UI.Cursor.Hand);
					this.setAutoPause(false);
				}, function ()
				{
					return !this.m.RelationsScreen.isAnimating();
				});
				return true;
			}
		}
	  }
	});
	
	
	
	
});



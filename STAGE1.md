# 完整内容包进度（v2.6）

原「阶段1」文档升级为 **B1–B7 完整内容包** 对照。

## Legacy 对齐

新增 scenario / 事件 / 技能 / 饰品 / 立绘 gfx；**无**官方同路径覆盖；无 Modern/MSU。

## B 标准对照

| ID | 标准 | 状态 |
|----|------|------|
| B1 | 30 人可招、身份唯一 | **是**（C01–C31 编号保留但跳过 C24；`afei_named_id` / hasNamed） |
| B2 | R01–R20/R22–R28、G（无 G24）、M01–M09 | **是** |
| B3 | 嘉豪≤16、觉醒、阿飞死亡停止 | **是**（recordJiahao / tryAwakenAfei / AfeiDead） |
| B4 | M09 驻营 39/20/19 | **是**（事件启用 + 驻营标记/日薪35%） |
| B5 | 号令/疲劳恢复上限 | **部分**（号令 2/3；疲劳恢复预算 20；叠加未全测） |
| B6 | 中文进 MOD | **是** |
| B7 | 文档化 | **是**（本文件 + README） |

## v2.5 增量（保留）

| 项 | 说明 |
|----|------|
| 五人大哥 | C04/C05/C06/C13/C25 天赋合计 **9 星**，八维与日薪按晚游向上调 |
| 电子烟 | `accessory.afei_ecig`：装备后技能「抽一口」回 **20** HP；不消耗；仅阿飞 |
| 自行车 | `accessory.afei_bicycle`：行囊；小酒瓶离队事件可选遗弃 → 阿飞 **经验获取 ×1.2**（World 旗防刷）；未遗弃保留物品无倍率。**不是**移速 |

## v2.6 增量

| 项 | 说明 |
|----|------|
| 30 人立绘 | BB 风格半身肖像（无糕糕）；全尺寸 `gfx/ui/portraits/afei/`；背景 Icon 56×56；事件图 210×210 |
| 背景接入 | 全部 `afei_*_background` 的 `m.Icon` 指向 `ui/backgrounds/afei_cXX.png` |
| 事件接入 | 起源介绍 + R01–R20/R22–R28 首屏 `Image`；scenario 描述图用阿飞立绘 |
| 未接入 | **战术头像**仍走原版分层脸（Faces/Hairs）；无自定义 sprite sheet |

## 已知缺口（无 Windows 实机）

- 冰霜编制：优先 UnholdFrost spawnlist + 战术补编 `afei_frost_unhold`；无独立美术/技能表时回退普通巨兽
- 蓝旗友军为临时 `militia_guest` 衍生，战后不入名册
- 顶上去已接 `attackEntity` 改目标 + 仇恨吸引；无 Windows 实机校验
- 饰品图标复用原版 accessory 图；实机平衡与存档迁移未测
- 立绘仅背景栏/事件 UI；战场拼脸未替换

## 构建

`python3 tools/build_zip.py` → `dist/mod_afei_expedition.zip`

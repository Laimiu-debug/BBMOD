# 完整内容包进度（v2.3）

原「阶段1」文档升级为 **B1–B7 完整内容包** 对照。

## Legacy 对齐

新增 scenario / 事件 / 技能；**无**官方同路径覆盖；无 Modern/MSU。

## B 标准对照

| ID | 标准 | 状态 |
|----|------|------|
| B1 | 31 人可招、身份唯一 | **是**（C01–C31 / `afei_named_id` / hasNamed） |
| B2 | R01–R28、G01–G31、M01–M09 | **是**（门控按设定；G 按人物条件+奖励；M04/07/08 接契约/战斗钩） |
| B3 | 嘉豪≤16、觉醒、阿飞死亡停止 | **是**（recordJiahao / tryAwakenAfei / AfeiDead） |
| B4 | M09 驻营 39/20/19 | **是**（事件启用 + 驻营标记/日薪35%） |
| B5 | 号令/疲劳恢复上限 | **部分**（号令 2/3；疲劳恢复预算 20；叠加未全测） |
| B6 | 中文进 MOD | **是** |
| B7 | 文档化 | **是**（本文件 + README） |

## 已知缺口（无 Windows 实机）

- 冰霜编制：优先 UnholdFrost spawnlist + 战术补编 `afei_frost_unhold`；无独立美术/技能表时回退普通巨兽
- 蓝旗友军为临时 `militia_guest` 衍生，战后不入名册
- 顶上去已接 `attackEntity` 改目标 + 仇恨吸引；无 Windows 实机校验
- 实机平衡与存档迁移未测

## 构建

`python3 tools/build_zip.py` → `dist/mod_afei_expedition.zip`

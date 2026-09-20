# 阶段 1 垂直切片说明

## 参考对齐（2026-09-20）

以用户提供的 **Fate.zip**（`media/ref-fate-origin.zip`）为优先对照；沙匪包已自 BBMOD 历史找回作辅证。

| | Fate | 沙匪 | 本 MOD |
|--|------|------|--------|
| Hooks | Legacy `mods_hook*` | Legacy register+queue | **Legacy**（保持） |
| Modern/MSU | 无 | 无 | 不做 |
| scenario | 新增 `fate_cultists_scenario.nut` | 新增 `desert_bandits_scenario.nut` | 新增 `afei_expedition_scenario.nut` |
| 注册 | 无 `addScenario` | 无 `addScenario` | **已去掉** `scenario_manager` hook |
| 开场事件 | 复用官方 cultists intro | `events/events/scenario/` + `IsSpecial` + `fire` | 同沙匪路径：`afei_expedition_intro_event` |
| 官方同路径覆盖 | 无 | 无 | 无 |

## 已实现

- 起源可选、三队长固定数据、起步资源、中文文案
- 阿飞解雇防护占位；号令 2/场、1/轮
- M01 开场（接/拒送账）；R01 瓶队（日≥2 + 有报酬契约≥1）
- ZIP 构建：`python3 tools/build_zip.py` → `dist/mod_afei_expedition.zip`

## Stub / 未做

幕后队长双目标与真实疲劳减免、算盘命中钩、送账真契约、C04 完整页、嘉豪/磨合/带教、31 人其余、种子远征、实机验收。

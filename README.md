# 大飞午远征团 · 起源 MOD（`mod_afei_expedition`）

《战场兄弟》**1.5.2.3** 自定义战团起源。设定源稿：阿飞主题起源 v0.6.1（大飞午远征团 · 31 人精简版）。

## 与 BBMOD 的关系

| | |
|--|--|
| **本仓库** | 起源 MOD **源码**（独立 Git 仓） |
| **[Laimiu-debug/BBMOD](https://github.com/Laimiu-debug/BBMOD)** | 桌面安装器 / 独立汉化 / Hub；**不是**本 MOD 源码仓 |
| 安装 | 将构建出的 ZIP 放入游戏 `data/`，或用 BBMOD 军械库安装 |

## 依赖

- **Legacy Modding Script Hooks**（`mod_hooks`，与 BBMOD 独立汉化常见附带版本兼容，如 21.1）
- 首版**不**要求 Modern Hooks / MSU
- 首版**不**接入 BBMOD 种子远征 / `ORIGIN_LABELS`

## 阶段 1 范围（当前）

三队长开局 + 团队号令 + M01/安全送账 + R01（小酒瓶入口）。  
不做 31 人全量、不做种子远征。细节见 [STAGE1.md](./STAGE1.md)。

## 包内 ID

- 安装文件名：`mod_afei_expedition.zip`
- mod id：`mod_afei_expedition`
- scenario id：`scenario.afei_expedition`
- Legacy 版本号：`1.0`（纯数字）

## 构建

```bash
python3 tools/build_zip.py
# 或: make zip
```

**构建产物路径：** `dist/mod_afei_expedition.zip`

该 ZIP 根目录直接含 `scripts/`（无外层套娃），可通过 BBMOD `inspect_archive` 结构校验。在本环境若能 import BBMOD 的 `archive_safety`，构建脚本会自动跑一遍。

安装：复制到 `<Battle Brothers>/data/mod_afei_expedition.zip`。

## 目录结构

```
scripts/!mods_preload/mod_afei_expedition.nut
scripts/scenarios/world/afei_expedition_scenario.nut   # 新增，不覆盖官方
scripts/skills/backgrounds/...
scripts/skills/actives/...
scripts/skills/effects/...
scripts/skills/special/...
scripts/events/events/...
```

## 参考包与 Hooks 选型

| 参考 | 路径 / 来源 | Hooks | scenario 注册 |
|------|-------------|-------|---------------|
| **Fate（优先）** | Context `media/ref-fate-origin.zip` | Legacy（`::mods_hookNewObject`） | 仅新增 `*_scenario.nut`，**无** hook `scenario_manager` |
| 沙匪起源 | Context `media/ref-mod_desertBandits-沙匪起源.zip`（自 BBMOD git 历史抽出，SHA 与兼容性记录一致）；原作 [Nexus #588](https://www.nexusmods.com/battlebrothers/mods/588) | Legacy（`mods_registerMod` + `mods_queue`） | 同上；开场事件在 `events/events/scenario/` + `IsSpecial` |

**本 MOD 选型：** 保持 **Legacy `mod_hooks`**（Fate/沙匪一致，非 Modern/MSU）。结构对齐 Fate/沙匪：新增 scenario 文件自注册；开场用 special intro；preload 用沙匪式 `registerMod`+`queue` 挂玩法钩子。

## 状态说明

- Cloud Agent **无法**在 Linux 上实机启动 Windows 客户端验收。
- GitHub 仓已建：https://github.com/Laimiu-debug/afei-expedition-origin — 若 `cursor[bot]` 无 write，需维护者授权后才能由 Agent push。

## 许可

见 `LICENSE.txt`。

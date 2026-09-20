# 大飞午远征团 · 起源 MOD（`mod_afei_expedition`）

《战场兄弟》**1.5.2.3** 自定义战团起源。设定源稿：阿飞主题起源 v0.6.1（大飞午远征团 · 31 人精简版）。

## 与 BBMOD 的关系

| | |
|--|--|
| **源码真相（当前）** | [BBMOD `mirror/afei-expedition-origin`](https://github.com/Laimiu-debug/BBMOD/tree/mirror/afei-expedition-origin) |
| **独立仓** | https://github.com/Laimiu-debug/afei-expedition-origin（空仓；Cursor App 未授权，暂不推） |
| **[Laimiu-debug/BBMOD](https://github.com/Laimiu-debug/BBMOD)** | 桌面安装器 / 独立汉化 / Hub；**不是**本 MOD 日常开发树 |
| 安装 | 将构建出的 ZIP 放入游戏 `data/`，或用 BBMOD 军械库安装 |

## 依赖

- **Legacy Modding Script Hooks**（`mod_hooks`，与 BBMOD 独立汉化常见附带版本兼容，如 21.1）
- 首版**不**要求 Modern Hooks / MSU
- 首版**不**接入 BBMOD 种子远征 / `ORIGIN_LABELS`

## 阶段 1 范围（当前 · v1.3）

三队长开局 + 号令/嘉豪·磨合骨架 + M01/R01 + **黑队 R02–R07（C05–C10）**。  
不做 31 人全量、不做种子远征。黑队七人招募已接入。细节见 [STAGE1.md](./STAGE1.md)。

## 包内 ID

- 安装文件名：`mod_afei_expedition.zip`
- mod id：`mod_afei_expedition`
- scenario id：`scenario.afei_expedition`
- Legacy 版本号：`1.3`（纯数字）

## 构建

```bash
python3 tools/build_zip.py
# 或: make zip
```

**构建产物路径：** `dist/mod_afei_expedition.zip`

该 ZIP 根目录直接含 `scripts/`（无外层套娃），可通过 BBMOD `inspect_archive` 结构校验。

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
scripts/events/events/scenario/...
```

## 参考包与 Hooks 选型

| 参考 | Hooks | scenario 注册 |
|------|-------|---------------|
| **Fate（优先）** | Legacy | 仅新增 `*_scenario.nut`，**无** hook `scenario_manager` |
| 沙匪起源 | Legacy | 同上；开场 `IsSpecial` + `fire` |

**本 MOD：** Legacy；新增 scenario；special intro；preload `registerMod`+`queue`。禁止覆盖官方同路径。

## 状态说明

- Cloud Agent **无法**在 Linux 上实机启动 Windows 客户端验收。
- 独立仓推送需维护者把 Cursor GitHub App / 环境仓库列表加上 `afei-expedition-origin`。

## 许可

见 `LICENSE.txt`。

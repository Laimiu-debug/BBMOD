# 大飞午远征团 · 起源 MOD（`mod_afei_expedition`）

《战场兄弟》**1.5.2.3** 自定义战团起源。设定：阿飞主题起源 v0.6.1（31 人精简版）。

## 源码真相

[BBMOD `mirror/afei-expedition-origin`](https://github.com/Laimiu-debug/BBMOD/tree/mirror/afei-expedition-origin)  
独立仓 `afei-expedition-origin` 因 App 权限暂不推送。

## 依赖

- Legacy Modding Script Hooks（`mod_hooks`）
- **不**要求 Modern/MSU；**不**接种子远征

## 内容范围（v2.2 完整内容包）

| 模块 | 状态 |
|------|------|
| C01–C31 命名人物 | 可入队（三队长开局 + R01–R28） |
| R01–R28 招募 | 门控/签约/事件 |
| G01–G31 成长 | 营地结算事件（简化条件 + 嘉豪/磨合） |
| M01–M09 主线/并行 | 事件链（部分契约战斗为事件近似） |
| 号令/嘉豪/磨合/带教/代理/驻营 | 已落地骨架与规则 |
| 专属技能 | 条目齐；部分为可玩近似 + TODO |

细节见 [STAGE1.md](./STAGE1.md)（现为完整包进度说明）。

## 包内 ID

- ZIP：`mod_afei_expedition.zip` · mod id：`mod_afei_expedition` · scenario：`scenario.afei_expedition` · 版本：**2.2**

## 构建

```bash
python3 tools/build_zip.py
```

## 许可

见 `LICENSE.txt`。

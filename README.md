# 大飞午远征团 · 起源 MOD（`mod_afei_expedition`）

《战场兄弟》**1.5.2.3** 自定义战团起源。设定：阿飞主题起源 v0.6.1（**30 人**；已按用户要求移除「糕糕」/C24/R21/G24）。

## 源码真相

[BBMOD `mirror/afei-expedition-origin`](https://github.com/Laimiu-debug/BBMOD/tree/mirror/afei-expedition-origin)  
独立仓 `afei-expedition-origin` 因 App 权限暂不推送。

## 依赖

- Legacy Modding Script Hooks（`mod_hooks`）
- **不**要求 Modern/MSU；**不**接种子远征

## 内容范围（v2.8）

| 模块 | 状态 |
|------|------|
| 命名人物 | **30 人**可入队（三队长 + R01–R20/R22–R28；C24/R21 糕糕已删） |
| 五人大哥 | 小酒瓶/李李/余初九/大鹅/玩蛇 → **9 星**晚游向八维与日薪 |
| 阿飞饰品 | **电子烟**：战斗回血 20（无限次）；**自行车**：小酒瓶离队可选遗弃 → 阿飞经验获取 **×1.2**（仅一次，非移速） |
| 头像 / 立绘 | **已剥离**：改回原版 Faces / 默认背景 Icon；包内无自定义 portrait gfx |
| G 成长 | 对应在队人物；无 G24 |
| M01–M09 | 自定义契约开战等 |

细节见 STAGE1.md。

## 包内 ID

- ZIP：`mod_afei_expedition.zip` · mod id：`mod_afei_expedition` · scenario：`scenario.afei_expedition` · 版本：**2.8**

## 构建

```bash
python3 tools/build_zip.py
```

## 许可

见 `LICENSE.txt`。

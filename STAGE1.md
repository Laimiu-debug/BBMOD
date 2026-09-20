# 完整内容包进度（v2.8）

原「阶段1」文档升级为 **B1–B7 完整内容包** 对照。

## Legacy 对齐

新增 scenario / 事件 / 技能 / 饰品；**无**官方同路径覆盖；无 Modern/MSU。  
**自定义立绘已按用户要求从 MOD 剥离**（改回原版脸 / 默认背景 Icon）。

## B 标准对照

| ID | 标准 | 状态 |
|----|------|------|
| B1 | 30 人可招、身份唯一 | **是**（C01–C31 编号保留但跳过 C24；`afei_named_id` / hasNamed） |
| B2 | R01–R20/R22–R28、G（无 G24）、M01–M09 | **是** |
| B3 | 嘉豪≤16、觉醒、阿飞死亡停止 | **是** |
| B4 | M09 驻营 | **是** |
| B5 | 号令/疲劳恢复上限 | **部分** |
| B6 | 中文进 MOD | **是** |
| B7 | 文档化 | **是** |

## v2.8 增量

| 项 | 说明 |
|----|------|
| 拆立绘 | 删除 `gfx/ui/backgrounds/afei_c*.png`、`gfx/ui/events/afei_portrait_*.png` |
| 背景 Icon | 恢复原版 `background_15/20/06/19.png` |
| 事件图 | 招募首屏 `Image` 清空；起源介绍 / scenario 描述改回 `event_65.png` |
| 脸 | 继续用原版 `Faces` / Hair / Beard 分层（从未替换战术拼脸） |

## 已知缺口（无 Windows 实机）

- 冰霜编制 / 蓝旗友军 / 顶上去等无实机校验
- 实机平衡与存档迁移未测

## 构建

`python3 tools/build_zip.py` → `dist/mod_afei_expedition.zip`

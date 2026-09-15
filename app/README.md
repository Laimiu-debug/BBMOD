# BBMOD 管理器

专为《战场兄弟》(Battle Brothers) **1.5.2.3** 打造的 Windows 中文桌面工具，集成 **一键汉化 / MOD 管理 / 刷种子 / 健康诊断** 四大功能。

## 功能

### 仪表盘（健康诊断）
- 自动定位游戏（Steam 注册表 → libraryfolders.vdf → appmanifest）
- **对任意第三方 mod 生效**的静态分析：API 代际（旧 mod_hooks v21.1 / Modern Hooks）、依赖缺失、
  声明互斥、版本号格式预检（旧 hooks 拒绝非纯数字版本）、文件覆盖冲突、preload 清单冲突、
  内嵌 zip 检测
- **影响种子/地图生成的 mod 标记**（触碰世界生成/角色/物品脚本的一律点名）
- **运行时诊断**：解析上次游戏会话的 log.html，把 Script Error 归因到具体 mod（.cnut 编译 mod 也能确诊）
- **基座检测**：data_001.dat 被第三方重打包（如汉化整合版）时告警——刷种子前建议 Steam 校验还原原版

### MOD 管理
- 已装列表（启用/禁用/卸载，禁用=移出到 `bbmod_disabled/`，官方 .dat 永不触碰）
- 内置合集仓库（框架/基础功能/作弊/汉化 分类 + 中文说明 + 依赖标注）+ 外部文件夹导入
- 安装时自动解出内嵌 zip（如 EIMO 内的 zbigmap007）
- mod 集合方案（profile）保存/一键切换
- 全部文件操作写入审计日志（游戏目录旁 `BBMOD_operations.log`）

### 一键汉化（自研版本）
- 读取参考语料（狐狸汉化 zip 明文 .nut）建立 **11300+ 条翻译语料库**
- 翻译表编辑器：搜索/直接修改任意文本（覆盖表持久化在 `%APPDATA%/BBMOD`）
- 一键**构建自有品牌汉化包**（语料 + 覆盖 + 可替换字体 → `BBMOD汉化_*.zip`）并安装
- 支持**游戏档案读取**（data_001.dat 为无加密 ZIP，可提取 UI/字体等明文资源）

### 刷种子（全自动编排 + 实时结果）
- 五种推荐模式预设（仅地图/仅人物/人物+地图/人物+红装/全开）+ 起源级人物条件编辑
- 一键开始：**自动快照并移出全部 mod（RNG 纯净化）→ 注入种子生成器与配置 → 启动游戏**
  → 你在游戏里选起源难度点"开始新战役" → 软件实时解析 log.html 展示命中种子表格
- 一键停止：结束游戏进程 → 移除注入文件 → **逐字节恢复原 mod 配置**
- 结果可导出 CSV；进度（已刷种子数/命中数/最高队伍分）实时显示
- RNG 模拟核心以 .nut 原样分发（对游戏 RNG 的精确复刻只能在游戏引擎内运行，这是本工具与游戏机制的边界）

## 运行与开发

```
cd app
pip install -r requirements.txt
python main.py            # 图形界面
python main.py --selftest # 无界面自检
```

验收脚本（真机）：
```
python tools/diag_check.py      # 诊断引擎
python tools/manager_check.py   # MOD 管理往返
python tools/l10n_check.py      # 汉化管线
python tools/seedgen_check.py   # 刷种子核心
```

打包：`python -m PyInstaller --noconfirm --windowed --name BBMOD --add-data "data;data" --add-data "seedgen;seedgen" main.py`
（成品在 `dist/BBMOD/`；把含合集的仓库文件夹与 exe 放在同一目录即可被识别为内置仓库）

## 目录

```
app/
├── main.py               # 入口（--selftest 自检）
├── core/                 # 纯逻辑层（无 Qt 依赖）
│   ├── game.py           # Steam 检测链/版本/日志路径/进程
│   ├── modinfo.py        # 任意 zip 静态分析器
│   ├── diagnostics.py    # 诊断引擎
│   ├── modmanager.py     # data 目录管理/快照/profile
│   ├── modstore.py       # 仓库（内置索引 + 外部导入）
│   ├── l10n.py           # 汉化语料/覆盖/构建
│   ├── gamelog.py        # log.html 解析（增量）
│   └── seedgen/          # 刷种子：emitter / watcher / orchestrator
├── ui/                   # PySide6 界面（四页）
├── seedgen/payload/      # 种子生成器 .nut 原样分发
├── data/mod_index.json   # 内置合集元数据（51 条）
└── tools/*_check.py      # 真机验收脚本
```

# BBMOD 0.3.0-rc.15：南北港与竞技场港筛选

## 发布结果

- 官网已公开并推荐 `BBMOD-0.3.0-rc.15.exe`，大小 77,284,270 字节。
- SHA-256：`c9a315408421e8f476ef2639a9f815fceea0134d0694e8e966e0d5d8bd1a53cc`。
- 固定下载：https://bbmod.site/downloads/windows/1a9d5b9e-98bc-49a3-af2b-d1360c3d395c/
- 发布记录：`output/deployment/rc15-ports-20260918/published.json`。
- 应用版本、EXE 文件名、Windows 文件与产品版本、发布说明、官网推荐版本及更新接口一致。

## 本版变化

桌面端「种子远征 → 寻找新开局 → 地图与港口」增加南北港、竞技场港复选框，可同时勾选，与港口、城镇、甲店数量条件同时满足。南北港沿用生成器左上北港、左下南港各至少一座的定义；竞技场港要求同一城邦同时具备竞技场和港口。地图筛选设置持久保存。历史种子库与导入日志不重新过滤。

对比 rc14 的实际 EXE，Python 模块变化仅为 `core.version`、`ui.seedgen_page`，入口自检与 Windows 版本资源同步更新；无新增或删除模块与资源。标准库 ZIP 仅元数据变化，内部文件内容相同。证据为 `app/build/review/rc15-package-diff.json`。

## 验证

- 298 项 pytest 通过；另有 1 项直接操作真实游戏目录的往返检查未执行。包含 4 组勾选组合、32 个实际 Squirrel 判定样例，以及设置持久化和寻找模式隔离。
- 1080×720、1360×880 两种窗口尺寸的地图筛选控件可见，截图及结果位于 `app/build/review/seed-ports/`。
- EXE 资源与源码一致，隔离目录启动自检通过，`seed_ports=ready`，版本为 rc15；未包含退役注入组件。证据为 `app/build/review/rc15-exe-selftest.json`。
- Defender 对新 EXE 的自定义文件扫描退出码 0，未发现威胁，未执行修复。结果仅代表此次扫描，见 `app/build/review/rc15-defender-scan.json`。
- 隔离副本 rc14→rc15 的主动重启与正常退出时静默更新均通过；旧 EXE 备份哈希正确，配置文件字节不变，静默模式未重新启动软件。证据为 `rc15-update-install-check.json`、`rc15-update-silent-check.json`。
- 已发布的 rc14 EXE 通过公网官网接口检测到 `v0.3.0-rc.15`，见 `app/build/review/rc15-previous-updater-check.json`。
- 官网下载页、版本 API、默认下载和固定下载通过；HEAD 返回 200，Range 返回 206，文件名、大小、分段内容一致。文件检查请求使用 `Accept-Encoding: identity`，以校验原始文件大小。
- 使用真实 UpdateService 从官网完整下载 77,284,270 字节，SHA-256 与本地发布件相同。没有安装到用户日常程序。证据为 `app/build/review/rc15-public-update-check.json` 和 `output/deployment/rc15-ports-20260918/public-verification.json`。

## 数据与部署

- 发布前备份：`/home/ubuntu/bbmod-hub/backups/20260918-rc15-ports/bbmod-hub-20260918T154020864353Z.tar.gz`。
- 备份 SHA-256：`036dde747dbe1b775d16b9fffc8bead0f1b16c3e31b0bc7e4d57feb02fc5452f`；数据库完整性检查通过，13 个历史下载文件的大小及哈希全部通过。
- 通过既有 `import_desktop` 发布入口新增不可覆盖的版本。历史版本、独立汉化包、用户与种子数据保留；17 个容器及正在运行的网站源码版本均未变更。
- 独立汉化仍为 `0.3.0-rc.3`；此次不重新部署网站，不修改游戏目录或存档。

## 验证边界

本轮未启动游戏刷种。离线判定、自检和公网下载结果不代表游戏内生成与第三方 MOD 组合已验收。

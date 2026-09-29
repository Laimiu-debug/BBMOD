# 五款推荐 MOD 收录 · 2026-09-27

用户要求将推荐的五款全部收录到网站。本批已上线，官网共 **42 件作品：9 件本站文件、16 件作者文件直链、17 件作者页面入口**。五款均具有可搜索的详情、安装步骤和前置链接，未添加未经核实的站内归档。

| 作品 | 版本 | 官网入口 | 获取方式 |
| --- | --- | --- | --- |
| Extra Keybinds | 2.1.0 | [扩展快捷键](https://bbmod.site/mods/community/extra-keybinds/) | Nexus Files 页；作者明确禁止其他网站转载 |
| Detailed Status Effects | 1.9 | [详细状态效果](https://bbmod.site/mods/community/detailed-status-effects/) | Nexus Files 页；允许署名转载，但未取得原包 |
| Quicker | 1.4 | [轻量加速](https://bbmod.site/mods/community/quicker/) | 作者 GitHub ZIP 直链 |
| MaxiQE informative tooltips | 1.0.0 | [战斗信息增强](https://bbmod.site/mods/community/maxiqe-tooltips/) | 作者 GitHub ZIP 直链 |
| Legends | 核心 19.4.22 / 资源 19.4.3 | [传奇大修](https://bbmod.site/mods/community/legends/) | 开发团队 GitHub 两个原包直链 |

## 下载与说明核查

- Quicker、MaxiQE、Legends 核心以及 MaxiQE 的 Nested Tooltips 前置均已完整下载，验证归档 CRC、规范化路径、大小与 SHA-256，不执行 MOD 代码。
- Legends 资源包为 357,981,216 字节，按 19.4.22 发布说明解析出指定 19.4.3 资源链接，跟随跳转后的 HEAD 返回 200；未完整下载或声称已完成资源包 CRC 校验。
- 两个 Nexus Files 页可以经网页索引核对作品与文件记录；本机直接 HTTP 访问仍返回 403。未提交用户账号密码，未伪造下载直链或使用未确认的镜像。
- 原包来源、校验值和分发状态见 [author-downloads-2026-09-27-batch3.json](../content/author-downloads-2026-09-27-batch3.json)。
- Quicker 标注与 Swifter/Faster 二选一，冰洞 Boss（Ijirok）恢复正常战斗速度；汉化内置旧 Hooks，无需重复安装。
- MaxiQE 列出 Modern Hooks、MSU、Nested Tooltips、Tooltip Extension 四项前置；与 Detailed Status Effects 等同类战术提示互斥，伤害结果为预测。
- Legends 页面同时提供核心和资源包；按团队指南要求游戏 1.5.1+、常规官方 DLC、Modern Hooks、MSU，旧 Hooks 已内置。明确说明不能与 Reforged 混装、需要对应 Legends 的汉化适配；19.4.0+ 存档兼容范围仅针对 Legends 存档。
- 五款均未完成与汉化 rc.8 / 游戏 1.5.2.3 的实机组合验证。

## 网站改动与验证

- `community-mods.json` 添加五条记录；既有 32 条记录逐项保持一致。
- 详情模板支持明确的“前往作者下载页”按钮、安装步骤和前置指南链接；Nexus 页面入口不冒充文件直链，也不会被“作者文件下载”筛选选中。
- 隔离镜像通过 144 项网站测试，覆盖 Nexus 页面与 ZIP 链接的区别、Legends 两个必需文件、MaxiQE 前置链接和桌面 API 边界。
- 公网五个详情页均返回 200，搜索可找到；下载和依赖链接、安装步骤数量均匹配。目录总数 42，本站 9，作者文件 16，全部外部作品 33。
- 当前桌面 API 与发布前完整 JSON 一致，未改动既有九件本站下载。

## 部署与回退

- 活跃目录：`/home/ubuntu/bbmod-hub/releases/BBMOD-Hub-0.3.6-mods3-20260927`。
- 镜像：`bbmod-hub:mods3-20260927`，基于上一批线上镜像构建，仅覆盖目录数据、详情模板及对应测试三个文件。
- 没有数据库迁移、MOD 文件导入或桌面版本变更。只重建 BBMOD 应用容器，健康检查通过；其他容器 ID 与启动时间未变。
- 上一版 `BBMOD-Hub-0.3.6-mods2-20260927` 完整保留。回退时用上一版 `web/compose.gateway.yml` 重建 app 并恢复活跃目录记录，无需恢复数据库。
- 本地工作与验证证据：`app/build/mod-catalog-20260927/round-3/`；服务器暂存：`/home/ubuntu/bbmod-hub/mods3-20260927/`。第三方归档不进入 Git。

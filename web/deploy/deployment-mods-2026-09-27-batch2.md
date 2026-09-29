# MOD 下载扩充 · 第二批 · 2026-09-27

本批上线后共有 **37 件作品：9 件本站下载、13 件作者文件下载、15 件仅有作者说明页入口**。后续状态见[第三批记录](deployment-mods-2026-09-27-batch3.md)。桌面目录 API 仅提供本站作品，外部原包不混入自动安装目录。

## 本站新增两项下载

| 作品 | 版本 | 大小 | 发布 ID |
| --- | --- | ---: | --- |
| [旧版 Hooks](https://bbmod.site/mods/ce170bce-dd19-51c8-a637-d73dad0423c7/) | 21.1-bbmod.1 | 10,782 字节 | `9a4e358e-0b36-49bd-92cd-777a7c868473` |
| [更多血迹（兼容版）](https://bbmod.site/mods/019d53b5-b9b3-5516-8f00-27eaa79bccfb/) | 0.5-bbmod.1 | 3,342 字节 | `5cd290ed-5df5-4b28-854d-f72d7ea08f25` |

- Hooks 原作者为 Adam Milazzo，从 [JC Sato 镜像 v21.1](https://github.com/jcsato/modding_script_hooks/releases/tag/v21.1) 取得。原作者 [Nexus 页面](https://www.nexusmods.com/battlebrothers/mods/42) 明确允许署名转载。镜像文件名含 20.1，但发布说明和脚本注册版本均为 21.1。来源原包 SHA-256 为 `0461ea3f457a798e6af2082ecbe6e058f5917e70f4487a1298160161b0a8d38c`。
- 已完整下载当前线上汉化 rc.8，核对原先记录的 SHA-256，并确认含 Hooks 21.1 注册脚本、界面入口及 root_state。页面明确说明汉化用户不要重复安装独立 Hooks；独立包主要供未使用内置 Hooks 包的环境按需获取。
- 更多血迹使用 [Suor 固定源码](https://github.com/Suor/battle-brothers-mods/tree/9f6a37a5dd9170c8f6693a6e23389bd39ee9240a/more_blood)，作者代码采用 BSD-2-Clause，[兼容版 Nexus 页面](https://www.nexusmods.com/battlebrothers/mods/756) 同时允许署名转载。保留其原许可与说明，并注明原始概念来源 Poss；未分发 Nexus 28 的旧版文件。
- 两包保留所有来源游戏文件原字节，仅附加许可、署名与来源说明。大小、CRC、路径及哈希校验通过。未进行游戏实机测试。

发布元数据及逐文件哈希见 [curated-mods-2026-09-27-batch2.json](../content/curated-mods-2026-09-27-batch2.json)。

## 新补十项作者文件入口

已有 MSU 与 Modern Hooks 页面补充开发团队 GitHub 下载按钮，另新增八项 JC Sato 作品：

| 作品 | 固定版本 | 安装边界 |
| --- | --- | --- |
| MSU | 1.9.0 | 需要 Modern Hooks；新增菜单未自动汉化 |
| Modern Hooks | 0.6.0 | 与汉化界面入口重叠，加载顺序需验证 |
| 装备扩展 | 4.0 | 新物品写入存档，不建议中途卸载；旧版本升级存在物品外观变化 |
| 装备外观变体 | 1.6 | 卸载后新变体可能不可见；不建议与 Legends 混装 |
| 佣兵团详情面板 | 2.0 | K 键；作者要求游戏 1.5.1.x+ |
| 城镇状态说明（轻量版） | 1.0 | 英文机制说明，不显示精确数值；避免同类提示叠加 |
| 提示信息开关 | 0.1 | Y 键，与同键功能可能冲突 |
| 精简新手提醒 | 0.2 | 移除两类提醒，不删除霍加特起源 |
| 局部已探索地图 | 2.0 | 新建战役选项；作者要求游戏 1.5.1.x+ |
| 市场商品扩展 | 1.5 | 改变商店货物，与其他商店改动可能叠加 |

八项 Sato 作品均按作者说明要求旧 Hooks 20+。下载链接全部取自实际 GitHub release assets，原 ZIP 已完整下载并检查 CRC、长度和 SHA-256。两框架使用自定义资源根目录，八项 Sato 包采用反斜杠路径；这些原包没有通过 BBMOD 桌面安装规则，因此明确提示手动按作者方法安装，未改写归档或放宽安装校验。外部原包并未镜像到本站。

来源、原包大小和哈希见 [author-downloads-2026-09-27.json](../content/author-downloads-2026-09-27.json)。详细兼容性、依赖和存档说明保存在 [community-mods.json](../content/community-mods.json)。

## 网站与发布验证

- 列表新增“作者文件下载”筛选及卡片标识，仍保留“本站下载”和原有“作者原站”筛选。原有作者原站筛选包含全部 28 项外部作品，其中 13 项有文件直链。
- Hooks 转为本站作品后，依赖说明直接链接其本站详情；不再显示失效的内部前置入口。
- 隔离镜像通过 143 项网站测试，其中覆盖新筛选、搜索、分页、前置链接及外部链接不得进入桌面 API。
- 两个真实新包通过现有表单、发布服务、临时数据库和匿名完整下载演练。
- 发布前备份：`/srv/data/backups/bbmod-hub-20260927T023041488934Z.tar.gz`，1,585,904,993 字节；SQLite 完整性通过，25 个已有下载文件逐一匹配哈希。
- 新发布目录：`/home/ubuntu/bbmod-hub/releases/BBMOD-Hub-0.3.6-mods2-20260927`；镜像 `bbmod-hub:mods2-20260927`。
- 以当前线上镜像为基础，只覆盖目录数据、列表模板、前置链接函数、列表筛选和相应测试五个文件，无数据库迁移。未携带工作区的其他未发布改动。
- 两项新 MOD 在事务内发布；逐记录核对既有 Mod、Release、DesktopRelease 未变。其他服务容器的 ID 与启动时间未变。
- 公网验收：两项新包完整下载均返回 200，长度和 SHA-256 一致；13 个作者文件页全部返回 200 且具有预期按钮；筛选数分别为 37 / 9 / 13 / 28。原有 7 件 API 记录逐项保持一致。

工作脚本、发布前快照和公网证据保存在本地忽略目录 `app/build/mod-catalog-20260927/round-2/`。站内两包保存在 `batch-2/`，第三方原包不进入 Git。

回退网站时使用上一版 `BBMOD-Hub-0.3.6-mods-20260927/web` 的 Compose 配置重建 app，并恢复 `active-release.txt`。新增作品独立保存在持久卷；若需撤回，在后台撤回对应 Release，不恢复旧数据库覆盖新数据。

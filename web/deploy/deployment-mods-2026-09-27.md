# MOD 下载扩充 · 2026-09-27

第一批发布后共有 28 件作品，其中 7 件提供本站 ZIP 下载，3 件提供作者 GitHub 原包直链，18 件保留作者原站入口。后续状态见[第二批扩充记录](deployment-mods-2026-09-27-batch2.md)。

## 新增本站作品

原作者均为 Alexander Schepanovski（hackflow / Suor）。来源为作者 [Battle Brothers Mods 仓库](https://github.com/Suor/battle-brothers-mods)，固定提交 `9f6a37a5dd9170c8f6693a6e23389bd39ee9240a`。原仓库采用 BSD-2-Clause，作者 README 明确允许按其说明整理 ZIP 并署名分发。

| 作品 | 整理版 | 大小 | 发布版本 ID |
| --- | --- | ---: | --- |
| [招募费用减半 · Cheap Meat](https://bbmod.site/mods/5fb6de6f-36f9-5e2c-8710-ebe1804cfdcb/) | 0.2-bbmod.1 | 3082 字节 | `c387e62e-fa7f-4d54-9d3a-06146947e5d8` |
| [更多野兽战利品 · Better Beast Loot](https://bbmod.site/mods/5eb4d247-8b51-5ebd-88a0-958656309e96/) | 0.11-bbmod.1 | 2733 字节 | `967350d7-5250-43f8-b5cc-95e0415c82b9` |
| [背景编号称号 · Bro Renamer](https://bbmod.site/mods/edc8144f-82f6-578b-834d-403b2f447f31/) | 0.2-bbmod.1 | 3779 字节 | `90910122-7670-453d-baff-8a8e398293af` |

每包保留游戏脚本原字节，附完整原许可、原作者 README、变更记录和 `BBMOD_ATTRIBUTION.txt`。没有移植汉化、执行 MOD 脚本或宣称完成真实游戏验收。三包都需要旧版 Modding Script Hooks；野兽掉落要求 19+，背景编号要求 20+。经济与掉落平衡、称号写入存档等影响已在详情页说明。

来源 ZIP SHA-256 为 `da727be98e975cba947c9134a715c850f8d278ff9935fbd0b919a9bfbaad96ed`。逐文件哈希和发布元数据见 [`curated-mods-2026-09-27.json`](../content/curated-mods-2026-09-27.json)。产物与准备、导入、验证脚本保存在本地 `app/build/mod-catalog-20260927/`，第三方归档不进入 Git。

## 作者原包直链

- [宝藏地图](https://bbmod.site/mods/community/artifact-reliquary/)：0.5.2，90,895 字节。
- [血肉与信仰扩展](https://bbmod.site/mods/community/of-flesh-and-faith-plus/)：4.0.6，2,672,325 字节。补充作者说明：4.x 要求游戏 1.5.2.x+，与此前 MOD 版本不兼容。
- [Reforged](https://bbmod.site/mods/community/reforged/)：核心 0.9.3（1,299,599 字节）及资源 0.1.4（46,064,079 字节）。两个文件都需要，同时保留作者前置及安装指南入口。

四条直链来自各作者发布页的实际 release assets，跟随跳转后的 HEAD 均返回 200、二进制内容类型及相应大小。详情页直接链接作者 GitHub，没有将这些文件复制到本站或加入桌面自动安装 API。公开页面注明 GitHub 传输来源。

## 部署与验证

- 新目录：`/home/ubuntu/bbmod-hub/releases/BBMOD-Hub-0.3.6-mods-20260927`。
- 新镜像：`bbmod-hub:mods-20260927`；原镜像固定另标为 `bbmod-hub:mods-base-20260927`。
- 仅覆盖线上 `web/templates/community_detail.html` 和 `web/content/community-mods.json`，没有数据库迁移，也没有覆盖其他本地未发布修改。
- 仅重建 BBMOD 应用容器，其他容器 ID、启动时间逐一保持一致。健康检查通过后更新 `active-release.txt`。
- 发布前备份：`/srv/data/backups/bbmod-hub-20260927T020103595037Z.tar.gz`，1,585,891,328 字节。SQLite 完整性检查通过，22 个已有下载文件的大小和 SHA-256 全部匹配。
- 隔离的新镜像通过现有 142 项网站测试；真实三包经现有 `ModForm`、`ReleaseForm` 和 `create_release` 流程完成独立数据库演练，验证署名页、匿名完整下载及官方直链。
- 生产发布前再次无写入校验；三个新 Mod 在一个事务中发布，并逐记录确认已有 Mod、Release、DesktopRelease 数据未改变。
- 公网目录 API 返回 7 件作品，三个新增 ZIP 实际完整下载均为 200，长度与 SHA-256 一致；三个作者详情页显示预期的 1、1、2 个下载按钮。证据：本地 `app/build/mod-catalog-20260927/public-verification.json`。

回退网页时使用上一版 `BBMOD-Hub-0.3.6-rc26-20260925/web` 的 Compose 配置重建 app，并恢复活跃目录记录。新增 Mod 独立存于持久卷；若需撤回某包，在后台撤回其具体发布版本，不回灌旧数据库或删除历史文件。

## 仍待原包

第一批未取得 Hooks、Smart Recruiter、Better Obituary、Named Item Stat Viewer、More Weapon Skins、Well Trained Pets 的原包。第二批已从 JC Sato 的授权镜像取得并发布 Hooks，剩余五项仍受 Nexus 下载访问限制。未取得原包的项目继续保留原作者入口。

另外查阅了 Sato、Necro 等作者仓库。公开可读不等于已明确授权本站镜像；此轮只发布已确认许可且能完整打包校验的文件。含自定义顶层目录或复杂素材、前置的其他候选还需独立检查，不为增加数量而删掉其必需文件。

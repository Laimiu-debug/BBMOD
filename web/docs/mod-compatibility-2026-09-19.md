# 本地 MOD 兼容与转载核查（2026-09-19）

基准为 Battle Brothers 1.5.2.3、BBMOD 独立汉化 0.3.0-rc.7，汉化 ZIP SHA-256 为 `a7bdb5516df563faaf1d6ef831cb6339acbb1ba3d22710bf1555a9c57b2cf36d`。

盘点启用目录、停用目录、本地收藏及下载目录相关归档 71 份，内容去重后 66 份；排除自制 MOD 和旧汉化备份，得到 59 条第三方 / 整合包记录。检查范围不等于全盘扫描。逐条证据、原作链接与本地 SHA-256 保存在 `web/content/mod-compatibility-2026-09-19.json`。本节的“当前环境”只指本次检查的维护者电脑，不代表网站访客。

网站直接在“探索 MOD”及各作品详情页介绍功能、前置和适配情况，没有单独的兼容导航页。24 项社区作品由 `content/community-mods.json` 提供，其中三个许可明确的整理包通过正常发布流程提供本站下载。其余只链接作者原站；来源不明、整合游戏包及重复版本不作为公共目录项目。

## 主要发现

- 当前启用的 Swifter 1.1.3 缺少 MSU，且实际 Hooks 21.1 离线调用拒绝其非数字版本注册；职业属性范围 2.0.0 直接使用 Modern Hooks，但当前环境没有该框架。
- Modern Hooks 通过 `fps_module.js` 建立 MOD UI 连接，rc.7 也包含同名页面，不能让汉化页面覆盖框架连接逻辑。不能仅因“无脚本路径重叠”就认定运行兼容。
- 显星 / 评分的实际脚本注册、属性计算、星级、评分、招募按钮及中文背景通过专项离线验证。没有启动游戏，未覆盖真实存档 / 战斗验收。
- 详细阵亡名册、犬舍买狼、无限竞技场、军团战袍、旧完整汉化包有页面 / 脚本覆盖风险；双显星、双 Swifter、双 BBForge 及 Swifter + 旧 Autopilot 不能直接混装。
- 标作“营地显示人物11级上限”的包实际上仅有头像 / 脸型资源，不提供 11 级潜力计算。
- Armour Indicators 夹带同一 MOD 的旧版 ZIP。署名整理版只移除此嵌套包并增加说明，所有保留游戏文件逐字节不变。
- SHS RAR 包含完整游戏程序和官方 data 文件。只做目录盘点，不转载整包，内含 MOD 不能称为逐项已适配。音乐素材版权链和本地中文改版的作者授权不明时同样不转载。

## 免费署名整理版

| MOD | 原作者 | 检查版本 | 来源与转载依据 |
| --- | --- | --- | --- |
| Backgrounds and Attribute Ranges | Vazl | 2.0.0 | [原作许可](https://www.nexusmods.com/battlebrothers/mods/287)允许署名转载与修改 |
| Armour Indicators | AllanniaBB；原始 Armour Indicator 为 gwtwind | 1.4.2 | [原作许可](https://www.nexusmods.com/battlebrothers/mods/96)允许署名转载与修改，禁止用于收费 MOD / 文件 |
| Prepare Carefully | TaroEld | 0.9.2 | [原作许可](https://www.nexusmods.com/battlebrothers/mods/571)允许署名转载与修改，禁止用于收费 MOD / 文件 |

三个包仅增加 `BBMOD_ATTRIBUTION.txt`；装备图标包另移除嵌套旧版 ZIP。网站版本以 `-bbmod.1` 标识整理，游戏脚本自报版本不变。包内载明原作者、原作链接、许可核查日期、原归档哈希及整理范围。BBMOD 是整理发布者，不作为原作者。需要前置且未游戏验收的状态在下载页明确保留；没有把本体中文覆盖率扩展到 MOD 新增内容。

Swifter、MSU、Modern Hooks、EIMO 等原站禁止异站转载的作品只放原作链接。允许转载的原作也不自动授权未知来源的中文改版；这类本地包不上传。未经核实的作者不从文件名臆测成已确认署名。

## 源码仓库与历史

`其他mod/` 曾被纳入公开仓库，含 81 个第三方归档或相关文件。本次从当前 Git 索引移除并加入忽略规则，本地副本保留，不随网站源码包部署。停止跟踪不删除历史提交里的文件。历史清理需另行备份并明确授权改写 Git 历史，不能将本次移除称作彻底消除了既往公开内容。

网站发布增加可选原作者署名，发布快照分别记录原作者和上传账号；新版本保留历史快照的原署名。转载表单要求填写原作链接。只有公开、未撤回且未下架版本出现本站下载入口，也不会转成来源条目重新出现。

## 社区补充作品

本轮从 Steam MOD 讨论区、Nexus 作者发布页及作者 GitHub 仓库补充四项介绍，均为自主概述并链接原作，没有转载文件、截图、音乐或译文：

- [Stronghold，TaroEld](https://www.nexusmods.com/battlebrothers/mods/324)：自建据点。原站禁止异站上传，仅链接原站。
- [Plan Your Perks，TaroEld](https://www.nexusmods.com/battlebrothers/mods/452)：技能规划，未验收与本汉化界面的组合。
- [Of Flesh and Faith+，Sato](https://github.com/jcsato/of_flesh_and_faith_plus)：起源与事件扩展，新增内容未汉化；保留作者关于 2.0 起卸载后不能加载存档的说明。
- [Reforged 作者社区发布帖](https://steamcommunity.com/app/365360/discussions/3/4756452715167252567/)及[作者仓库](https://github.com/Battle-Modders/mod-reforged)：独立大修环境，尚未适配本体汉化。

游侠专区搜索结果主要为旧帖、转载及含游戏本体的整合资源，本次没有从这些帖子搬运文件或认定兼容。

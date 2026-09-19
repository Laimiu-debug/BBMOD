# BBMOD rc.24 与独立汉化 rc.7 发布记录

2026-09-19 15:41（UTC+8）通过既有 Hub 发布服务公开，官网推荐已切换为 rc.24。本次只新增版本文件及发布资料，运行中的 Hub 0.3.4、网关与其他容器未重启；原有账号、种子、建议和历史版本均保留。

| 发布物 | 文件大小 | SHA-256 |
| --- | ---: | --- |
| `BBMOD-0.3.0-rc.24.exe` | 85,364,393 字节 | `ec050b3b77b986298ba03312fdc5d531b6ccf2ff76dc1fc131ac96e99e814258` |
| 独立汉化 `0.3.0-rc.7` | 34,526,120 字节 | `a7bdb5516df563faaf1d6ef831cb6339acbb1ba3d22710bf1555a9c57b2cf36d` |

- [官网下载页](https://bbmod.site/downloads/)；[rc.24 固定下载](https://bbmod.site/downloads/windows/5e0364d6-3b33-4a88-9237-f1cc67be4e87/)。
- [独立汉化介绍](https://bbmod.site/mods/22c174ed-fc9d-4dbb-9642-44831ce694e8/)；[rc.7 固定下载](https://bbmod.site/files/39d9e847-9d13-4674-8785-eb72a2a40714/download/)。官网安装文件名保持 `mod_bbmod_zhcn.zip`。
- 本地发布文件位于 `app/dist/BBMOD-0.3.0-rc.24.exe` 和 `app/dist/mod_bbmod_zhcn-0.3.0-rc.7.zip`；文件名、应用版本、Windows 版本、官网元数据和哈希一致。

## 发布内容

汇总离线装备表格与图标、部分红装鉴定修复、启动状态与当前汉化引导、种子批量分享和快捷复制。汉化逐句通读 15,819 条中文文本及随机分支，修订 634 条；另优化四条装备场景译文。详情见 [rc.24 更新说明](../../app/releases/0.3.0-rc.24.md) 和 [审校记录](../../app/docs/localization-sentence-review-20260919.md)。

官网汉化介绍、版本说明、推荐下载、仓库 README 和安装引导同步更新。想使用新译文时导入并应用 rc.7；已经启用新版包时无需重复生成。仅更新桌面 EXE 不会自动替换当前汉化。

## 验证

- 桌面 337 项回归、最终打包修复的 22 项相关回归通过；实际包内 634 条修订、动态整句、称谓组合、结算与保护标记检查通过。
- Windows 独立 EXE 自检及资源一致性检查通过；Defender 自定义文件扫描返回 0，未发现威胁。此结果仅代表当次本机扫描。
- 从 rc.15 升级至 rc.24 的主动重启和退出静默更新均通过，旧 EXE 备份与用户设置保留。
- 官网 77 项 Django 测试和数据库迁移检查通过。首次 CI 发现容器漏打包 `app.core.seedgen.weapons`，已补齐 Dockerfile 与源码包清单，并扩大共享模块改动的 CI 触发范围；[修复后的 Ubuntu CI](https://github.com/Laimiu-debug/BBMOD/actions/runs/35429910652)通过测试、构建、迁移、健康检查和备份演练。
- 公开程序与 MOD API、下载页、汉化详情、首页版本和介绍均匹配发布资料。EXE 推荐与固定链接的 HEAD 200、Range 206、文件名和大小通过检查。MOD 下载接口沿用 GET，完整 ZIP 下载通过哈希校验。
- 真实 `UpdateService` 从官网完整下载 85,364,393 字节 EXE，SHA-256 一致；从原 rc.15 EXE 提取的实际更新解析器识别 rc.24 为可安装的新版本。
- Playwright 检查下载页与汉化页的 1360 px 和 390 px 布局，无页面横向溢出，浏览器未记录脚本错误；历史 rc.15 程序与 rc.3 汉化下载仍可访问。

**未启动游戏。** 本次发布检查不代表实际游戏排版、装备悬停、完整剧情或全部 MOD 组合验收。

## 备份与证据

发布前生成一致的数据库及下载文件备份，SQLite 完整性与 14 个历史下载文件的大小、哈希全部通过。备份为服务器 `backups/20260919-rc24/bbmod-hub-20260919T073440502389Z.tar.gz`，1,246,566,381 字节，SHA-256 `2ca06f7efe9aa970037e859d7208f9e1c854c06888e32019959d633dce970559`。发布没有撤回、覆盖或删除任何历史版本。

源码与发布资料提交 `7eeafebfb0846c38507874010f9df03afc1b5ece`，容器打包清单修复提交 `8ab3908069bf5eda919821c4173ae948f4449866`，均已推送 `origin/main`。发布记录作为后续文档提交保存。

本地证据位于 `output/deployment/rc24-20260919/`：`published.json`、`public-verification.json`、`public-update-check.json`、`backup.json`、`defender-scan.json`、两份更新安装报告及 CI 结果。浏览器截图位于 `output/playwright/rc24-release/`。包含生产快照的运行记录保持本地忽略，未提交账号、凭据或数据库。

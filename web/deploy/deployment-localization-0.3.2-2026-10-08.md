# 独立汉化 0.3.2 发布（2026-10-08）

用户要求将第三至五轮汉化审校合并推送并打包发布。本次通过官网现有 `ReleaseForm` 与 `create_release` 发布独立汉化新版本；网站代码、桌面版本（仍为 0.4.2）和生产容器均未改动或重启。

## 正式文件

| 项目 | 内容 |
| --- | --- |
| 版本 | 0.3.2 |
| 发布 ID | `72cc346c-a59c-4ef4-b42b-0bae1587d05f` |
| 本地文件 | `app/dist/localization-0.3.2/mod_bbmod_zhcn-0.3.2.zip` |
| 公开下载文件名 | `mod_bbmod_zhcn.zip` |
| 大小 | 34,530,549 字节 |
| SHA-256 | `e4bb60fcfa08a07509909c58e3e1caef6232087594bda4ab27dd5adf0d0fb97b` |

[汉化固定下载](https://bbmod.com/files/72cc346c-a59c-4ef4-b42b-0bae1587d05f/download/) · [汉化作品页](https://bbmod.com/mods/22c174ed-fc9d-4dbb-9642-44831ce694e8/)

相对 0.3.1 再修订 360 条：第三轮排版与引用一致性 327 条，第四轮委托长文 14 条，第五轮事件与人物背景长文 19 条。第二轮遗留的全部 1,583 条长文已逐句对照英文读完。

## 验证

- 16 个本地化测试模块 187 项通过；版本号改为 0.3.2 后相关 5 个模块复跑通过。
- 官方档案对照：2,279 个脚本、19,329 个函数指令不变，205,339 个受保护常量通过，17,748 处文本补丁与词库一致，2,559 处原始地名保留；原生 bbsq 读取 2,281 份 CNUT 通过，45 个 JavaScript 文件语法通过。
- 15,630 条显示扫描：格式问题 0，显示 15,629 条，1 条署名保留；三轮修订均已确认进入包内词库。
- 公开下载 HEAD 200、Content-Length 与文件名正确，Range 206，完整下载 SHA-256 一致；作品页 200 并显示 0.3.2。

没有启动游戏核对实机排版，也没有修改本机游戏安装或存档。

## 备份与清理

遵守[备份约定](../../app/docs/publishing-backups.md)，只创建 SQLite 在线一致快照，未执行 `backup_hub`：

- `/srv/data/deployments/localization-0.3.2/before.sqlite3`，1,777,664 字节，`integrity_check=ok`，SHA-256 `ff7c0c1d61f60a4c30507c4eeb61bf0f75bea90b8d0726708c843c005c7c3834`。

两条旧汉化记录保持一致。正式原件位于 `/srv/data/private/archives/d31b13d599a64f4f9d235fffac437ae8.zip`。验收后删除了宿主机上传 ZIP 和容器 `/tmp/bbmod-l10n-0.3.2`，保留正式原件、快照与小体积记录（`/opt/bbmod-hub/releases/localization-0.3.2/`）。本机证据：`app/build/deploy-l10n-0.3.2/`、`app/build/review/release-20261008/localization/`。

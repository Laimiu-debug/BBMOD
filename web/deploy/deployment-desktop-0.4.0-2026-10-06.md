# BBMOD 0.4.0 官网发布记录

2026-10-06（UTC+8）已将桌面 **0.4.0** 发布至 https://bbmod.com ，设为推荐稳定版。
0.3.1 等 27 条既有桌面发布记录的状态、文件与校验信息保持一致。
网站继续运行 **0.3.7**；本次通过现有 `import_desktop --publish` 发布 EXE 和版本说明。

## 功能与版本

- 根据游戏报错和调用栈定位可疑 MOD，并提示脚本覆盖关系。
- 自动记录从 BBMOD 启动且正常退出的 MOD 组合，可恢复「上次正常退出」。
- 分轮排查问题 MOD，保留前置、进度及原组合恢复能力。
- 修复后台任务结束时收尾步骤被跳过、MOD 管理停留在忙碌状态的问题。

详情见[0.4.0 版本说明](../../app/releases/0.4.0.md)。独立汉化包仍为 **0.3.0-rc.9**。

## 安装包与公开验收

| 项目 | 结果 |
| --- | --- |
| 文件 | `BBMOD-0.4.0.exe` |
| 发布 ID | `578d0dbb-d1e2-408d-bbd1-7b3e17acf4ca` |
| 状态／通道 | `published`／稳定版 |
| 大小 | 85,806,978 字节 |
| SHA-256 | `d1c91e086c28147943c5fcd6f466b10c1f2edaad342f64690581bc919eb0aea1` |
| 更新 API 推荐版本 | `0.4.0` |
| 固定版本与默认下载 HEAD | HTTP 200，大小及文件名正确 |
| Range 下载 | HTTP 206，1024 字节内容及范围正确 |
| 官网完整下载 | 85,806,978 字节，SHA-256 与本地成品一致 |
| 本机公网验收 | 更新 API、两个下载地址 HEAD 和 Range 内容检查通过 |
| 0.3.1 成品检查更新 | 从官网发现 `v0.4.0`，无备用源错误 |
| 0.4.0 成品检查更新 | 官网返回当前已是最新，无备用源错误 |
| 网站入口 | 首页、下载页、百科、军械库 API 均 HTTP 200，健康状态 `ok` |

[固定版本下载](https://bbmod.com/downloads/windows/578d0dbb-d1e2-408d-bbd1-7b3e17acf4ca/)
 · [官网下载页](https://bbmod.com/downloads/)

复用已验证的本地成品，EXE 和构建清单 SHA-256、大小及 922 个来源文件校验一致。
为缩短传输，将新文件中不相同的字节与服务器上已核验的 0.3.1 组合，
生成安装包后再次验证完整大小和 SHA-256。公开下载提供完整 EXE。

## 验证与备份

发布前桌面完整回归：61 个模块，**648 项通过、17 项按环境条件跳过、0 个失败模块**。
新增闪退排查的 7 项回归通过；EXE 隔离自检通过，并确认包含归因、分轮排查及相应界面模块。
网站本地回归为 182 项，1 项跳过，无失败；迁移和系统检查通过。
本次没有启动实际游戏，游戏内兼容性仍待实机验收。

发布前完整一致备份：

- 文件：`/srv/data/backups/bbmod-hub-20261006T144334797533Z.tar.gz`
- 大小：2,667,898,773 字节。
- SHA-256：`3a98280cd7ef531e11775227a35abd6e7f4aa0a939a8529492b4fcbee4b4492a`。
- SQLite 与 Wiki 数据库完整性均为 `ok`。
- 130 个下载文件、1 张封面、3 个 Wiki 文件、5,101 个 Wiki 素材校验通过。

备份校验通过后导入并公开 0.4.0。生产应用镜像保持
`bbmod-hub:0.3.7`，镜像 ID 为
`sha256:acefede192986430b01c6442692fd80d497f240f067ca07646dbe736b64ee8b5`。

## 证据位置

用户同日明确要求后续不做默认完整备份、不重复备份历史桌面 EXE。
上述备份记录保留本次执行事实；后续发布按[新的备份与存储约定](../../app/docs/publishing-backups.md)执行。

服务器发布资料：`/opt/bbmod-hub/releases/desktop-0.4.0/`，
包含安装包、版本说明、构建清单、发布前记录、备份验收、发布回执和公网下载验收。

本机发布资料：`app/build/deploy-0.4.0/`，包含：

- `manifest.json`、`desktop-tests.json`、`package-check.json`、`embedded-code-check.json`。
- `before.json`、`backup-verified.json`、`published.json`、`public-verification.json`。
- `external-public-verification.json`。
- `frozen-0.3.1-update-check.json`、`frozen-0.4.0-update-check.json`。

成品及原始构建清单：`app/dist/BBMOD-0.4.0.exe` 与
`app/dist/BBMOD-0.4.0.manifest.json`。

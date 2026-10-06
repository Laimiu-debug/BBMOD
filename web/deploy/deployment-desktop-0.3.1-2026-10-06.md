# BBMOD 0.3.1 与网站 0.3.7 发布记录

2026-10-06（UTC+8）已将桌面 **0.3.1** 发布至 https://bbmod.com ，网站应用更新至
**0.3.7**。官网下载和更新 API 推荐稳定版 0.3.1，历史 rc.38 文件及发布记录保留。

## 四个桌面缺陷

- 设置文件读取暂时失败时，保存先重读并合并；仍无法读取则拒绝覆盖原文件。
- 配置含非法 UTF-8 时按损坏配置处理并备份。备份失败时禁止覆盖，避免启动崩溃或丢失原件。
- 本地 MOD 操作排队等待扫描完成后，在实际写入前再次检查游戏是否启动。
- 在线安装、更新和回滚与本地扫描、分析共用文件锁，等待 ZIP 句柄释放后才修改文件，
  获得锁后也检查游戏运行状态；下载期间不占用文件锁。

## 固定编号

从此版起使用 `主版本.功能版本.修复版本`，修复发布递增末位，增加功能递增中间位，
不兼容改版递增主位。重复打包、测试和文档修改不改号，不再按日期或构建次数改编号。
版本唯一来源为 `app/core/version.py`，成品名固定为 `BBMOD-<版本>.exe`。
构建入口复用同版本同源码的已验证成品，拒绝覆盖同版本不同内容。
网站与独立汉化分别维护版本；独立汉化仍为 rc.9。详细规则见
[版本约定](../../app/docs/versioning.md)，长期约束写入 `app/AGENTS.md`。

## 安装包与公开验收

| 项目 | 结果 |
| --- | --- |
| 文件 | `BBMOD-0.3.1.exe` |
| 发布 ID | `aa1a9a1f-1c96-405b-a350-6c9b619f9ee4` |
| 状态／通道 | `published`／稳定版 |
| 大小 | 85,548,283 字节 |
| SHA-256 | `f90d41bd7ca3da1d55bc76ad1abd450b660f4c04823940510c3d6622134461a4` |
| 公网 HEAD／Range | HTTP 200／206，1024 字节区间正确 |
| 公网完整下载 | 大小与 SHA-256 一致 |
| 新版打包客户端联网 | 官网返回正常，显示当前已是最新 |
| 旧 rc.38 打包客户端联网 | 从官网发现 `v0.3.1`，无备用源错误 |
| 网站入口 | 首页、下载页、百科、军械库 API 均 HTTP 200 |

[官网下载](https://bbmod.com/downloads/windows/aa1a9a1f-1c96-405b-a350-6c9b619f9ee4/)

## 网站部署

以生产原镜像 `bbmod-hub:cloudcone-20261002` 为基础，只同步 `catalog/wiki_store.py`
与 `hub/version.py`，生成固定镜像 `bbmod-hub:0.3.7`，镜像 ID 为
`sha256:acefede192986430b01c6442692fd80d497f240f067ca07646dbe736b64ee8b5`。
百科翻译计数独立缓存，修复缓存并发清理时的取值竞态并避免重复聚合。
无新增数据库迁移；没有将本地其他网站代码差异一并同步到生产。

部署前在不挂载生产数据、禁用网络的候选容器中完成 68 项百科测试。
保留生产 Compose 配置和原镜像，只更换 app 镜像并等待健康检查；网关容器保持原 ID。
运行中的源码 SHA-256 与候选文件一致，`/health/` 返回 `status=ok`。
部署脚本在切换失败时恢复原 Compose 和镜像。

## 测试与备份

桌面回归逐模块独立进程运行：60 个模块，641 项通过、17 项按环境条件跳过，
0 个失败模块。四个按用户要求删除的历史测试文件没有恢复；新增聚焦的文件操作回归。
网站完整回归共 182 项，1 项跳过，无失败；模型迁移检查无变化。

成品自检验证内置资源、词库、字体和更新组件，并核对 EXE 内六个修复相关模块
与当前源码一致。真实 rc.38 内置更新器在隔离副本升级到 0.3.1：立即重启与静默替换
两种模式均通过，安装后版本、文件名、旧 EXE 备份校验正确，设置字节不变。
未启动实际游戏或修改实际游戏目录。

发布前完整备份为 `/srv/data/backups/bbmod-hub-20261006T074237637826Z.tar.gz`，
2,582,717,140 字节，SHA-256 为
`d3a932438ca3b69b42eba43b67c8b3422a857ffd91eaaa4102ae760f311eecba`。
SQLite 与 Wiki 数据库完整性均为 `ok`；129 个下载文件、1 张封面、3 个 Wiki 文件、
5,101 个 Wiki 素材校验通过。

本地证据在 `app/build/deploy-0.3.1/`：`desktop-tests-final.json`、
`embedded-code-check.json`、`old-helper-upgrade-check.json`、`old-helper-silent-check.json`、
`staged.json`、`backup-verified.json`、`activated.json`、`published.json`、
`public-verification.json` 与两个打包客户端联网报告。
构建清单为 `app/dist/BBMOD-0.3.1.manifest.json`，成品自检报告位于
`app/build/desktop/0.3.1/package-check.json`。

服务器保留网站部署资料 `/opt/bbmod-hub/releases/hub-0.3.7/`，以及桌面发布资料
`/opt/bbmod-hub/releases/desktop-0.3.1/`。本次直接打包当前工作区并发布官网，
未创建 Git 提交或 GitHub 版本。

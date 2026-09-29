# rc.26 桌面与配套网站发布

2026-09-25 19:58（UTC+8）发布至 https://bbmod.site/。推荐下载和自动更新接口均为 **0.3.0-rc.26**；独立汉化仍为 **0.3.0-rc.8**。

- 固定下载：`/downloads/windows/4f550f50-9ec4-4ebb-9b7a-60c914c3d9c2/`。
- 文件：`BBMOD-0.3.0-rc.26.exe`，86,039,411 字节。
- SHA-256：`b2829cb39322aa7ec62acf4631a28b535b3f0c25782a0922bbf2f31abdfaf774`。
- 按现有 `import_desktop` 流程校验后公开，未覆盖历史版本。

## 部署范围

基于线上 Hub 0.3.6 的现有源码及镜像，只覆盖本轮 13 个网站文件（模板、CSS、截图、种子读取接口及对应测试、SQLite 校验连接释放）。未覆盖其他本地业务数据或汉化包。依赖版本不变，没有新增数据库迁移。

新源码目录：`/home/ubuntu/bbmod-hub/releases/BBMOD-Hub-0.3.6-rc26-20260925`；镜像 `bbmod-hub:rc26-20260925`，以原镜像 `sha256:2682f8804e5034c9a1fe28377f5f50f859d5c160a89d5e83bd24eb8686764ff2` 为基础构建。旧镜像另标记为 `bbmod-hub:rc26-base` 以保留重建依据。

仅重建 BBMOD 应用容器；检查确认其他容器 ID 和启动时间均未变化。原有网关、Vercel、私有配置和持久卷沿用。应用健康检查通过后更新 `active-release.txt`。

## 备份与验证

- 发布前备份：`/srv/data/backups/bbmod-hub-20260925T115447875964Z.tar.gz`，1,500,207,121 字节。备份数据库 `integrity_check` 通过，全部 21 个原有下载文件的大小和 SHA-256 通过检查。
- 服务器隔离的新镜像通过 142 项网站测试；`makemigrations --check --dry-run` 无变更。
- 桌面本地 352 项通过、15 项跳过；rc.26 EXE 隔离配置自检返回 0。
- 公网下载及接口验收结果见本地 `app/build/deploy-rc26/public-verification.json`。
- 公网主页、下载、兼容提示、两张截图、种子档案及读取接口、百科、反馈、目录 API 均通过检查；推荐版本与固定下载 HEAD 200、Range 206，旧 rc.25 下载 HEAD 200。实际完整下载 rc.26 的 86,039,411 字节并计算 SHA-256，与本地产物一致。

如需回退网站，使用上一版目录 `BBMOD-Hub-0.3.6-1413d0a37df7/web` 的 Compose 配置，执行 `up -d --no-deps --no-build app` 并恢复活跃目录记录。本次没有数据库迁移，不回灌旧数据库。若客户端有问题，应在管理器版本后台撤回 rc.26，保留历史 rc.25；不覆盖已发布文件。

本轮未启动真实游戏，MOD 组合兼容性仍待实机验证。用户需在新版设置中启用网页联动。

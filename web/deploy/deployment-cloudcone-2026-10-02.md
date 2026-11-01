# BBMOD 迁移至 CloudCone · 2026-10-02 UTC / 2026-10-03 本地时间

**状态：迁移、rc.36 发布及公开网络验收完成。** 正式官网为 [bbmod.com](https://bbmod.com)。本文记录本次迁移与维护方法；UTC 执行日期为 2026-10-02，Asia/Hong_Kong 最终验收日期为 2026-10-03。

用户已购买 `bbmod.com`，域名使用 Cloudflare 名称服务器；DNS 记录由用户添加。新官网以 `https://bbmod.com` 为规范地址，`www.bbmod.com` 配置为跳转到主域名。旧官网不再列入本次对外维护范围。源服务器暂时保留，用于一致性迁移和受控回退。

## 已核实的架构与目录

| 项目 | 已核实内容 |
| --- | --- |
| 源服务器 | 腾讯服务器，SSH 别名 `my-server`；与 `cloudcone` 的 SSH 信任分别管理 |
| 源生产目录 | `/home/ubuntu/bbmod-hub/releases/BBMOD-Hub-0.3.6-guide-0274-20260929` |
| 源 app 容器 | `bbmod-hub-app-1`，Compose 项目 `bbmod-hub`，服务 `app` |
| 源生产镜像 | `bbmod-hub:guide-0274-20260929`；迁移读取实际运行镜像和容器身份 |
| 源持久卷 | `bbmod-hub_bbmod_data` → `/srv/data`；`bbmod-hub_bbmod_desktop` → `/srv/desktop` |
| 应用与存储 | Django；SQLite；MOD、共享方案、封面、桌面安装包和 Wiki 资源存于持久卷 |
| 现生产部署目录 | `/opt/bbmod-hub/candidate`；保留迁移时的目录名，`data/`、`desktop/` 为独立 bind mount |
| 维护入口 | `/opt/bbmod-hub/current` → `/opt/bbmod-hub/candidate`；实际目录和 Compose 项目不改名，以保留回退工具的身份保护 |
| 现生产 Compose | 保留项目名 `bbmod-candidate`；镜像标签 `bbmod-hub:cloudcone-20261002` |
| 现生产镜像 ID | `sha256:cb913cdac7363049f1dc342a9fbf4201a5c08d2b468c89ba5c6ef99a72249a72` |
| 现生产网关 | nginx，仅向宿主机 `127.0.0.1:18080` 发布端口；应用无公开端口 |
| 私有网络 | `backend` 为 Docker 内部网络；app 使用数据目录，gateway 只读挂载资源目录 |
| 旧源状态 | `bbmod-hub-app-1` 和 `bbmod-hub-gateway-1` 已停止；原卷与一致备份保留 |

源站 `/srv/web` 和 `/srv/app` 已检查，未发现容器层的源码热更新。迁移以生产实际源码为基线，额外覆盖使用本次迁移专用 `app/build/cloudcone-migration-20261002/overlay/` 文件集合，最终镜像 ID 见上表。没有将整个未提交工作区自动发布。

源网关配置曾单独更新，不能只使用 app 镜像中的历史网关文件。源实际配置摘要为 SHA-256 `591f917ceb8958ea26a02769e1552e6f4e5515f62b664df72b7a2ffa116e91ef`；本次迁移保留下载权限检查、内部资源 location 和 Range 行为，最终通过公开下载、续传及内部目录保护检查。

源初查时 SQLite `integrity_check` 为 `ok`；数据量约为：桌面安装包 1.95 GB、私有资源 159.6 MB、Wiki 482.5 MB。这些是初查时的体量，最终文件集合与数据库校验以最终一致快照为准。

## 仓库中的部署配置

- [`cloudcone/compose.yml`](cloudcone/compose.yml)：从当前迁移目录中的 Compose 文件原样复制，保留候选项目名及容器身份约束。
- [`cloudcone/nginx.conf`](cloudcone/nginx.conf)：宿主 nginx 的 HTTP/TLS 与 SNI 分流候选配置。
- [`cloudcone/nginx-quota.conf`](cloudcone/nginx-quota.conf)：nginx 与既有 `cloudcone-quota.service` 的依赖约束。
- [`cloudcone/prepare_xray.py`](cloudcone/prepare_xray.py)：生成、校验尚未应用的 Xray 候选配置；不打印客户端凭据。
- [`cloudcone/renew-nginx.sh`](cloudcone/renew-nginx.sh)：已安装的证书续期 deploy hook，先检查 nginx 配置，再在服务运行时 reload。

运行 Compose 时，配置文件需放在 `/opt/bbmod-hub/candidate`，同目录包含私有 `.env`、已恢复的 `data/` 和 `desktop/`、已核实的 `nginx-gateway.conf`。本配置使用相对路径，不能直接在仓库配置目录运行而意外创建空的数据目录。`.env` 不入库。

候选资源限制为 app 512 MiB、1 CPU，gateway 128 MiB；健康检查使用 **GET** `/health/` 并携带 HTTPS 转发头。`HEAD /health/` 返回 405 是现有接口行为，不用它判断服务故障。

最终验收时磁盘可用约 28 GB；app RSS 约 72 MiB、gateway RSS 约 4.3 MiB。这是本次检查时的观测值，不是持续运行或负载测试结果。

已应用的宿主入口路径为：

```text
bbmod.com / www.bbmod.com 的 TLS SNI
  → 宿主 nginx :443
  → 127.0.0.1:8443（证书终止）
  → 127.0.0.1:18080（候选 gateway）
  → app:8000

其他 TLS SNI
  → 宿主 nginx :443
  → 127.0.0.1:10443（原有 REALITY 服务）
```

入口使用有效的 `bbmod.com` / `www.bbmod.com` 证书、nginx stream 模块，以及接收 PROXY protocol 的内网 Xray 配置。`prepare_xray.py` 本身只写入 `/opt/bbmod-hub/pending/xray-config.json` 并执行配置测试；应用与切换由独立受控流程执行。本次宿主 nginx 与 Xray 切换状态已确认为 `confirmed`，状态文件位于 `/opt/bbmod-hub/network-cutover/bf8108083f7a/state.json`。切换后原有 REALITY 客户端实际认证通过，quota、meter、nginx、xray 服务均为 active。

证书到期日期为 **2026-12-31**，`certbot.timer` 已启用；`certbot renew --dry-run --run-deploy-hooks` 成功。续期 hook 已安装，执行脚本与仓库中的 `renew-nginx.sh` 对应。

## 一致性备份与最终切换

迁移工具位于工作区 `app/build/cloudcone-migration-20261002/`，部署时保留 `prepare_final_delta.py` 与 `apply_final_delta.py` 在同一工具目录。工具默认进行检查；只有显式 `--execute` 才改变服务或目录。执行参数和最终生成路径需保存在私有运行记录中。

初始完整备份位于源服务器：

```text
/home/ubuntu/bbmod-hub/migration-cloudcone-20261002/candidate-backup.tar.gz
```

本次迁移已执行源 `prepare_final_delta.py --execute`，最终快照与 delta 已生成，目标最终一致恢复和公网验收均成功。旧源 app 与 gateway 均保持停止，文件摘要、恢复事务和验收结果见下文。

最终切换遵循以下顺序：

1. 核对源 app 的容器 ID、镜像、项目、服务与两份实际持久卷，排除同时写入这些卷的其他容器；保存其运行状态。
2. 只停止源 BBMOD app，等待已有请求退出。使用原生产镜像创建一次性、无网络、只读根文件系统的备份进程，挂载同一组持久卷执行 `manage.py backup_hub`；不启动第二个 gunicorn，不执行数据库迁移。
3. 保留源卷中的最终完整快照。按初始与最终归档内的文件字节 SHA-256 生成仅新增、变化的 `delta.tar.gz`；SQLite 完整快照始终加入 delta，不能复制运行中的 `db.sqlite3` 代替。
4. 通过受信任 SSH 传输 `delta.tar.gz`、`metadata.json`、`checksums.txt`，校验包摘要。备份与 metadata 按私有数据保护；不展示其中的记录或文件名清单。
5. 目标停止候选 gateway 和 app，检查候选基线，构造完整最终文件树，核对数据库、文件引用、下载文件与 Wiki 资产。
6. 将目标原 `data/`、`desktop/` 移入独立回退目录，再安装校验通过的新树；保留源完整快照和目标原数据目录。成功后服务仍停止，由主执行者决定何时启用公网入口。

工具会设置目标所有者 `10001:10001`，验证最终 SQLite 完整性、全部表的聚合计数和摘要、MOD/共享文件/桌面包的长度与 SHA-256、封面引用、Wiki manifest 及资产哈希。账号和反馈只作一致性验证，报告不输出记录内容。

以下命令为维护示例，**应在工具所在目录执行，先检查实际路径；不是已完成的执行记录**：

```sh
# 源：检查实际生产容器和初始备份，不停服务
python3 prepare_final_delta.py

# 源：开始最终一致备份，成功后仍保持源 app 停止
sudo -n python3 prepare_final_delta.py --execute

# 目标：检查上传的最终 bundle 和候选容器
sudo -n python3 apply_final_delta.py \
  --bundle-dir /opt/bbmod-hub/incoming/final-delta

# 目标：恢复一致最终快照，成功后仍保持目标服务停止
sudo -n python3 apply_final_delta.py \
  --bundle-dir /opt/bbmod-hub/incoming/final-delta --execute
```

默认拒绝基线数据库发生变化或残留非空 WAL/journal。只有确认变动全部来自可丢弃的候选演练时，才可显式使用 `--allow-candidate-db-changes`；原目录仍需保留。不得用这个参数掩盖真实用户写入。

最终恢复的聚合报告位于 `/opt/bbmod-hub/candidate/final-staging-<UTC>/aggregate-report.json`，回退日志为同目录的 `transaction.json`。发布者核对报告和停写状态后，在候选目录执行：

```sh
cd /opt/bbmod-hub/candidate
docker compose config --quiet
docker compose up -d --force-recreate
```

恢复过程中目录通过 rename 替换；重建容器可以重新绑定新目录。仅 `docker start` 旧容器可能仍挂载旧目录，不用于此处的恢复上线。启动后检查容器健康、网关连通和公网验收，再宣布公开发布。

## 已完成的最终恢复与候选站发布

最终恢复已通过 SQLite 完整性检查；全部业务表的记录计数和内容聚合摘要与源最终快照一致。恢复阶段验证 121 个下载文件：93 个 MOD 发布文件、5 个共享文件、23 个桌面版本文件；文件长度与 SHA-256 均匹配。Wiki 验证 5,101 个素材，完整快照共验证 5,229 个文件。

候选演练产生的会话数据库变动经确认后使用显式 `--allow-candidate-db-changes` 替换为源最终一致快照；原候选数据目录仍保留。该操作没有放弃源站真实用户数据。

| 产物 | 路径 / 校验结果 |
| --- | --- |
| 源最终完整备份 | `/var/lib/docker/volumes/bbmod-hub_bbmod_data/_data/backups/bbmod-hub-20261002T155308086480Z.tar.gz` |
| 最终备份 SHA-256 | `9d1d7d6b7f8943fb96097e88eb51da1fde9015a4193c00239193f90c35fe3205` |
| 最终 delta | 272,957 字节；仅数据库变化，包含完整 SQLite 快照 |
| delta SHA-256 | `190664429e7f7264ab0297000159accc48265454306b33c284805df0555ff4ed` |
| 成功恢复事务 | `/opt/bbmod-hub/candidate/final-staging-20261002T155933293039Z/transaction.json` |
| 聚合恢复报告 | `/opt/bbmod-hub/candidate/final-staging-20261002T155933293039Z/aggregate-report.json` |
| SQLite 与业务数据 | 完整性通过；全部业务表与源最终快照一致 |
| 资源文件 | 121 个下载文件、5,101 个 Wiki 素材、5,229 个快照文件校验通过 |

最终恢复后，已通过 `import_desktop --publish` 在候选站发布 BBMOD `0.3.0-rc.36`：

| 项目 | 已核实结果 |
| --- | --- |
| 发布 ID | `966a4dfa-80c5-4b10-af26-ce4aefaac531` |
| 安装包长度 | 86,192,865 字节 |
| 安装包 SHA-256 | `e8dd7d46e92d0f3456488d269d68a2955aead1701510af57b041ef00e96f42b8` |
| 历史桌面版本 | 原有 23 个版本的数据保持原样，rc.36 为新增版本 |
| 下载地址生成 | 生产 `BBMOD_PUBLIC_DOWNLOAD_BASE` 留空，返回站内相对路径，由新域名提供下载 |
| 公网下载与更新 | 公开完整安装包长度、SHA-256、HEAD、Range 与 rc.36 更新检查均已通过，详见公开验收记录 |

## 失败与回退

工具失败时不自动启动服务。先保留维护停写状态，检查安全错误码与私有日志；不要反复重跑恢复，也不要删除回退目录。源 app 和目标 app 不得同时接受用户写入。

**目标数据恢复失败，或候选验收失败且尚未开放用户写入：** 使用对应的事务日志恢复完整原目录；当前失败的新目录会另外保留。工具返回后服务仍停止。

```sh
sudo -n python3 apply_final_delta.py --execute \
  --rollback-state /opt/bbmod-hub/candidate/final-staging-<UTC>/transaction.json
```

如决定放弃此次迁移、恢复源服务，先确认目标入口关闭且目标保持停写，再使用生成 bundle 中的实际源状态文件：

```sh
sudo -n python3 prepare_final_delta.py --execute \
  --resume-from-state /home/ubuntu/bbmod-hub/migration-cloudcone-20261002/final-delta-<UTC>/source-running-state.json
```

恢复命令核对原容器身份和此前运行状态，只恢复指定源 app，不重启无关服务。当前源 gateway 也已停止；如果确需恢复旧源入口，须另行核对其原容器身份、挂载与网关配置再恢复，不能只启动 app 后就认为入口已恢复。源完整快照、卷和目标回退目录都继续保留，不执行递归删除。

**目标公开上线并产生用户写入以后：** 原源站已不再包含最新数据，不能直接恢复旧库或启动源站。必须先关闭目标写入口，对目标新数据制作一致完整备份，确认新增数据的恢复方案，再进行服务回退。任何代码、入口、数据回退都应分别记录，避免丢弃上线后的账号、反馈或上传内容。

**宿主 nginx / Xray / 配额配置回退：** 应使用应用配置前保存的原文件及服务状态，切换日志为 `/opt/bbmod-hub/network-cutover/bf8108083f7a/state.json`。先通过 `nginx -t` 与 Xray 配置测试，再由执行者恢复端口和入口；既有配额统计及锁定文件保留。本次切换已 confirmed，原有客户端配置和私有状态文件不入库。

## 日常维护与保密

日常备份使用 `backup_hub`，保留数据库一致快照和它引用的资源；进行迁移或目录替换时仍使用上述停写流程。备份保留周期、异地副本和磁盘告警阈值由发布后补充，不能只保留唯一服务器上的一个副本。

`.env`、Django 密钥、账户密码散列、SSH 私钥、TLS 私钥、Xray 客户端凭据、反馈记录及完整迁移归档都不入库、不打印到公开报告。私有目录权限使用 `0700`，迁移包和状态记录使用 `0600`，只授予受信任执行账户读取权限。对外仅报告状态、聚合校验结果、公开资源摘要及必要路径。

本次迁移使用的临时受限 SSH 授权和源服务器传输私钥已删除。

源 `my-server` 与目标 `cloudcone` 的 SSH 身份和 known_hosts 保持分离；主机密钥变化必须先在对应供应商控制台核实，不通过清空信任记录解决。服务配置测试失败时不启用入口。

## 已完成的公开验收

DNS 恢复后的最终检查使用普通公开域名 `bbmod.com`，分别在 Windows 客户端环境与服务器环境运行。完整 EXE 下载先在本机 DNS negative cache 期间按下表方式指向公开 IP；没有修改 hosts，也没有使用内部入口代替最终公网检查。

| 项目 | 状态 / 结果 |
| --- | --- |
| 公开网站检查 | Windows 与服务器的普通域名 12 路径 checker 均通过 |
| DNS | 三家 DoH 与本机默认 DNS 解析正常 |
| 主域名与规范跳转 | HTTPS 访问通过；HTTP 和 `www.bbmod.com` 跳转到规范 HTTPS 主域名通过 |
| Qt 客户端请求 | `/api/v1/suggestions/`、`/api/v1/desktop/releases/`、`/downloads/` 均返回 200 |
| 桌面更新服务 | `UpdateService` 返回 `source=site`、最新版本 `v0.3.0-rc.36`，`attempts_errors=[]` |
| 附件下载与续传 | HEAD 200、Range 206；长度与公开摘要匹配 |
| 完整 EXE 下载 | 86,192,865 字节，29.145643 秒；SHA-256 与发布包一致；下载时 curl 指定公开 IP，仍校验 `bbmod.com` TLS 证书 |
| 教程、种子、方案、反馈接口 | `/guide/`、`/seeds/`、`/profiles/`、`/api/v1/suggestions/` 均返回 200 |
| 最新教程 PDF | 1,908,843 字节；SHA-256 `ac8e0ab027379e0b9ee1981aeaa4c1df584db4ef57ae04e61f5bf92ee95a8a8d` |
| 内部目录保护 | `/_desktop/`、`/_mods/`、`/db.sqlite3` 均返回 404 |
| 登录与 CSRF | HTTPS 登录页、同源 CSRF 和 Secure cookie 检查通过；无效用户 POST 返回 200，未创建账号 |
| TLS 与续期 | 证书到期 2026-12-31；续期 dry-run 含 deploy hook 成功，timer enabled |
| 既有服务 | REALITY 实际认证通过；quota、meter、nginx、xray 均 active |
| 旧源与临时授权 | 源 app、gateway 停止；临时受限 SSH 授权及源传输私钥已删除 |

DNS 初期曾受本地路由器 negative cache 影响。完整 EXE 下载在这段时间使用 `curl --noproxy '*' --resolve bbmod.com:443:113.20.0.234` 指向服务器的公开 IP，仍使用并校验 `bbmod.com` 的 TLS 证书；86,192,865 字节、29.145643 秒及 SHA-256 匹配的结果属于这次下载，不表示当时普通 DNS 已恢复。缓存随后自行刷新，三家 DoH 与本机默认 DNS 正常，之后普通域名 12 路径 checker、Qt 三接口、UpdateService、HEAD 与 Range 均通过。额外检查中曾出现一次临时 urllib 代理 SSL EOF，改用直接连接重试后检查通过；该瞬态失败保留在执行记录中，不计为持续故障。

本地验证证据位于 `app/build/cloudcone-migration-20261002/`，包括 `final-restoration-report.json`、`published-rc36.json`、`public-verification.json`、`public-update-service.json`、`site-extra-verification.json`、公开下载的 rc.36 安装包和 package check 记录。服务器数据一致性证据位于上文成功恢复事务目录，网络切换证据位于私有 cutover 状态目录。只引用检查结果与摘要，不公开凭据或反馈内容。

## 本地检查与验收边界

- 桌面完整测试：**561 passed，1 skipped**。
- 后续 hardening 相关集中测试：**122 passed**。
- 服务器种子测试：**12 passed**。
- EXE package check：**通过**。

这些结果确认本次代码、包、数据恢复和公开网络流程。没有新增实际游戏运行验收；本次网络检查也不能给出长期中国大陆线路稳定性的结论。后续应继续按日常备份流程维护并观察真实使用情况。

# 裸连下载修复与桌面 0.9.3

2026-11-03（Asia/Hong_Kong）已发布并完成裸连验收。官网继续使用 `https://bbmod.com`，网站镜像保持 `bbmod-hub:0.4.2`，独立汉化保持 0.3.3。

## 故障与处理

本机禁用代理的请求复现 `113.20.0.234:443` TCP 超时；Cloudflare 的部分 IPv4 入口超时，其他入口及 IPv6 存在读取超时。原站应用健康，服务器本机下载返回 200。生产网页当时配置 `BBMOD_PUBLIC_DOWNLOAD_BASE=https://dl.bbmod.com`，其 DNS 仍指向无法裸连的 `113.20.0.234`。这不是文件丢失，也没有证据表明新加了下载限速；未证明具体运营商或网络中断原因。

现有 `182.255.88.49` 本机直连可用，服务器到 BBMOD 源站 HTTPS 连通。复用已经指向该服务器的 `dl.gongpro.app` DNS，新建独立 HTTPS 下载入口：

- [无需代理的下载页](https://dl.gongpro.app/bbmod/)
- [最新稳定版直连下载](https://dl.gongpro.app/bbmod/downloads/windows/)
- 官网网页下载按钮改用 `https://dl.gongpro.app/bbmod`，无需更改 DNS 或用户系统代理。

入口为只读转发：TLS 校验源站证书，只允许明确的公开 GET/HEAD 路由；拒绝账号、后台、上传和带查询参数的请求，清除 Cookie 和 Authorization。每次文件请求和续传均由原站执行公开状态与文件检查。不新增文件缓存、文件副本或数据库副本，不绕过下架状态。下载支持 HEAD 和 Range 206。

## 部署位置

- 独立节点配置：`/etc/nginx/sites-available/bbmod-download-relay`，受版本管理的模板为 [direct-download-relay.conf](direct-download-relay.conf)。下载页为 `/srv/bbmod-download-relay/index.html`。
- `/etc/nginx/gongpro-stream.conf` 只新增 `dl.gongpro.app → 127.0.0.1:19443` 的 SNI 分流，其他网站与默认代理分流不变。只校验并 reload 宿主 Nginx，全部原容器 ID、启动时间不变。
- 复用现有 certbot 账号为 `dl.gongpro.app` 签发独立证书，有效期至 2027-02-01；现有 certbot 每 12 小时检查续期，定向续期 dry-run 通过。新增 `bbmod-download-tls-reload.timer` 每小时检查该证书 SHA，仅证书变化时校验并 reload 宿主 Nginx。
- 原站只修改 `/opt/bbmod-hub/candidate/compose.yml` 的 `BBMOD_PUBLIC_DOWNLOAD_BASE` 并重建 app；镜像和持久挂载不变，gateway 容器未重建。发布前备份仅包含修改的 Compose、Nginx 配置。首次验收因 Docker 挂载数组顺序变化而自动回退；改为按挂载目标比较后重新切换并验收成功，挂载源、目标及权限没有改变。
- 原站连接变更记录：`/opt/bbmod-hub/releases/download-connectivity-20261103/`；独立节点记录：`/var/lib/bbmod-downloads/direct-20261103/`。

## 桌面修复

0.9.3 的版本检查、军械库目录及公开文件下载优先使用直连入口，失败后尝试官网。保存的官网身份、第三方站点、账号与上传地址不变。桌面更新新增有界重试、Range 续传和跨线路续传；服务器忽略 Range 时重置文件重新下载。错误范围、错误大小、损坏哈希、非 EXE 及用户取消均不得安装。

7 个相关测试模块共 **184 项通过，0 跳过**，包含真实 HTTP 中途断线、跨线路续传、忽略或错误 Range、损坏内容、404 下架、重试期间取消和版本源回退。成品隔离自检通过，117 个模块和入口字节码与源码一致，3,964 项资源与构建清单一致。0.9.2 内置更新器完成隔离升级与重启，全部原测试设置保持；初始化仅增加既有 `seed_engine=auto` 默认值。未运行用户游戏、未更改真实存档或正在使用的程序。

0.9.3 文件为 `BBMOD-0.9.3.exe`，96,299,250 字节，SHA-256：

```text
39174791186c4d6f84d851466a5085f7eb46f3e3c3f512134b2b55770adf8267
```

本地记录：`app/build/download-connectivity-20261103/`、`app/build/deploy-0.9.3/`。首次直连完整下载原 0.9.2 的 96,294,608 字节用时 41.538 秒，2.318 MB/s，完整 SHA 一致；同时验证真实 MOD、HEAD、Range 和访问限制。这是本机当时链路观测，不保证其他地区速度，也不表示原源站 IP 的裸连已恢复。

发布 ID 为 `6b736e23-a92d-47db-99d4-1d50bc2af619`。[0.9.3 固定直连下载](https://dl.gongpro.app/bbmod/downloads/windows/6b736e23-a92d-47db-99d4-1d50bc2af619/)由真实 Qt 更新器设置 `NoProxy` 后完整下载，96,299,250 字节，71.568 秒，平均 1.346 MB/s，0 次重试，SHA 与成品及线上发布记录一致。官网公开 API 推荐、下载页、默认及固定 HEAD 200、Range 206、服务器经公开域名的完整流式 SHA 也通过。版本发布仅新增一条记录，原有 41 条桌面发布及 115 条 MOD 发布均保持不变。

发布使用 3,932,218 字节差分传输并复用原站正式 0.9.2 文件；仅新增 4,939,776 字节 SQLite 在线快照，完整性 `ok`。桌面发布期间没有重建应用或网关容器。本次没有提交或推送 Git。

## 回退与存储

直连入口故障时，0.9.3 自动尝试官网备用线路。网页可将 `BBMOD_PUBLIC_DOWNLOAD_BASE` 改为空字符串并仅重建 app，恢复站内下载。撤回 0.9.3 推荐时保留发布文件及当前数据库，不能回灌发布前快照覆盖新增用户数据。

如需撤销独立入口，先将网页恢复到官网并验证，再比对本次配置 SHA，只移除本次新增 SNI 项和 `bbmod-download-relay` 站点链接，停用本次证书 reload timer，并执行 `nginx -t` 后 reload；不要整体覆盖共享配置或停用其他网站的 certbot。

遵守 [备份约定](../../app/docs/publishing-backups.md)：仅保留修改配置、桌面发布所需 SQLite 在线快照与小体积记录，未做全站备份。验收后按 SHA 清理本次传输与测试副本，正式服务器文件及本地成品保留。容量阈值只作预警，本次没有写盘失败；本机容量报告为 `H:/codex/storage-guard/latest.json`。

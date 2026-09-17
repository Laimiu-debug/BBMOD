# BBMOD 社区军械库 · 0.3.1

可自行部署的 MOD 分发网站，配套桌面端 `0.3.0-rc.5` 的在线军械库。访客无需登录即可浏览和下载；管理员创建作者账号，作者首次登录改密后可直接公开作品；管理员可以下架作品、停用账号和重置密码。

## 当前功能

- 所有公开页面显示「欢迎你，第 xxx 位好兄弟」及累计访客数。编号按浏览器分配，签名 Cookie 保留一年且访问时续期；记录存于数据库，刷新、跨页面访问和服务器重启不重复增加访客。
- 管理后台显示累计访客、今日访客、今日新访客和累计浏览次数。统计从上线开始，按站点时区计算“今日”；不推算历史流量，不保存 IP、User-Agent 或逐页访问轨迹。
- 同一浏览器刷新只增加浏览次数。清除 Cookie、换浏览器/设备、跨域名访问或 Cookie 过期会成为新访客；禁用 JavaScript 时不统计，因此数字是浏览器访客估算值。仅公开页面执行一次 CSRF 保护的统计请求，常见爬虫、健康检查、文件下载、错误页与管理后台不参与计数。统计故障不影响浏览和下载。

- 种子广场 `/seeds/`：匿名浏览、按起源/难度/港口/红装/同一名兄弟的属性与特质筛选、人数门槛、排序、档案与复制。
- 桌面 rc.7 的「分享给兄弟」通过 `POST /api/v1/seeds/` 发布所选完整档案，无需登录。只接收最多 64 KB 的版本化 JSON，要求 `X-BBMOD-Seed-Share: 1`；拒绝浏览器跨站提交。每个代理确认地址每小时最多 200 次新分享，全站每小时最多 2000 次；代理出口共用地址时也共用额度。
- 同种子码（区分大小写）/起源/游戏版本/难度重复上传返回原链接，不覆盖原介绍。管理员从「种子分享管理」下架或恢复；被下架种子不能通过重传绕过。

- 分类、搜索、作品详情、展示图片、版本记录及各版本下载。
- 桌面管理器在 `/downloads/` 一键下载，无需 GitHub 或作者账号；文件名包含实际版本号。
- 作者拖入 ZIP，确认名称、版本和介绍，一页完成发布；安装文件名自动生成，原有英文加载顺序前缀保留，前置、封面等选项可以展开填写。已上传文件与当时的作品资料不覆盖，修改资料会在下一次上传时生效。
- 同一作品沿用固定安装文件名，避免升级后同时加载两份 MOD。保留文件名中的加载顺序前缀。
- 管理员查看所有版本和审计记录、下架/恢复作品、创建/停用作者账号。被下架作品不能由作者自行恢复。
- 下架或停用作者后，公开目录及下载入口立即隐藏；作者本人和管理员仍能检查文件。已经被他人下载的副本不被远程删除。
- 原作链接、分发许可、游戏/DLC 要求、前置和冲突 MOD ID、存档与种子影响说明。
- ZIP 结构、CRC、大小、哈希和路径检查，图片解码后重新保存。检查不执行游戏脚本，也不是病毒扫描或游戏兼容性认证。
- `GET /api/v1/catalog/` 同时为桌面端提供公开目录；下载地址始终在本站。

不预装第三方合集、不包含狐狸汉化资源。正式数据库初始为空，测试账号和测试 ZIP 不进入部署包。

## Ubuntu 部署（无域名）

需要 Docker Engine 与 Compose 插件，安装方法见 [Docker 官方 Ubuntu 指南](https://docs.docker.com/engine/install/ubuntu/)。以下命令从项目根目录运行，或解压 `BBMOD-Hub-0.3.1.tar.gz` 后进入 `BBMOD-Hub-0.3.1/`。

```bash
cd web
python3 tools/init_env.py --host 你的服务器公网IP
docker compose up -d --build
docker compose exec app python manage.py createsuperuser
docker compose ps
curl -f http://127.0.0.1:8080/health/
```

1. `init_env.py` 生成不公开的随机密钥和 `.env`，不会覆盖已有文件。
2. `createsuperuser` 交互设置管理员账号和密码；不要使用预览账号。邮箱可留空。
3. 云服务器安全组及 Ubuntu 防火墙按需开放 **8080/TCP**，浏览 `http://公网IP:8080`。
4. 进入「作者登录 → 管理后台 → 作者账号管理」，创建账号、设置初始密码并私下交给作者。
5. 在 BBMOD「MOD 军械库 → 在线军械库」填写相同的 `http://公网IP:8080`，连接后即可使用。

容器不会映射数据库或上传目录为公开静态文件，也不会改动其他服务。账号与 MOD 使用 `bbmod-hub_bbmod_data`，管理器 EXE 使用 `bbmod-hub_bbmod_desktop` 持久卷；一个应用进程、四个线程和 SQLite，适用于先给群友使用的单机站点。服务器 IP 改变时修改 `.env` 的 `BBMOD_ALLOWED_HOSTS` 再运行 `docker compose up -d`。不要把 `.env`、账号数据库或证书私钥上传到 GitHub。

### 正式账号使用 HTTPS

IP 的 HTTP 地址可用于初次检查与公开下载；**在公网交付真实作者账号前，应配置 HTTPS，避免密码和会话通过明文传输**。不强制购买域名，可使用覆盖服务器 IP 的有效证书；已有域名证书也可用。证书申请、续期和服务器 DNS 取决于实际部署环境，未在本地代办。

把证书链与私钥保存到 `web/certs/fullchain.pem`、`web/certs/privkey.pem`，然后：

```bash
docker compose -f compose.yml -f compose.https.yml up -d --build
```

开放 443/TCP，使用 `https://服务器IP` 或证书对应的域名。HTTPS 覆盖配置开启安全 Cookie、HTTPS 跳转和 HSTS；桌面端也应改为该 HTTPS 地址。此时 8080 会跳转到 443。应用端口仅在 Docker 内网，代理会覆盖转发来源头；不要另外将应用的 8000 端口映射到公网。

### 上传和容量

默认 ZIP 最大 100 MB，图片最大 5 MB，每作者存储 2 GB，每 24 小时最多上传 30 个版本。ZIP 必须直接含 `scripts/`、`ui/`、`gfx/` 等游戏目录；不支持 RAR、套娃整合包或 EXE/DLL 安装器。ZIP 解压总量最高 512 MB，单个资源最高 64 MB。

调整 `.env` 中 `BBMOD_MAX_UPLOAD_MB` 时，同时调整 nginx 的 `client_max_body_size`；当前桌面端最多接收 100 MB。设置 `BBMOD_AUTHOR_QUOTA_MB` 调整作者额度。此版采用保留历史版本的方式，没有自助永久删文件入口；增加磁盘前请检查剩余空间。

## 现有 Vercel 入口（可选，后续可切换自有域名）

部署入口为 [`web/vercel`](vercel/README.md)。Vercel 通过外部重写转发到 Ubuntu 的 HTTPS 服务；Django、账号数据库和上传文件仍在 Ubuntu。不要把整个 `web/` 部署为 Vercel Python Function：本项目使用持久化 SQLite 和最大 100 MB 的上传。

`compose.gateway.yml` 为已有 HTTPS 代理的服务器提供独立部署配置，不占用宿主机的 80/443/8080 端口。它使用 BBMOD 专用数据卷；只有网关容器连接已有代理网络。`deploy/bbmod-origin-location.conf` 是需要加入现有 HTTPS 站点的单独路由片段。具体配置、更新及验证见上述说明。

源码打包：`python tools/package_hub.py`，默认输出到 `app/build/hub/0.3.1/BBMOD-Hub-0.3.1.tar.gz`。包内不含 `.env`、Vercel 登录信息、账号数据库、上传文件或预览账号初始化命令。升级前使用 `backup_hub` 备份，在备份副本演练迁移 `0003_seed_sharing`；只增加种子相关表，不改已有作者、MOD 和管理器版本记录。Vercel 继续转发到当前源站。

## 管理员发布软件版本

1. 登录管理员账号，进入「管理后台 → 管理器版本」。
2. 拖入打包完成的 EXE。带版本号的文件会自动填写版本号；旧名 `BBMOD.exe` 需手动填写。写好更新说明，上传即可。
3. 勾选「上传成功后立即公开」时直接出现在下载页；不勾选则保存为草稿，管理员检查后再公开。
4. 玩家可以选择稳定版、测试版以及历史版本，直接下载 `BBMOD-实际版本号.exe`。默认推荐最高稳定版本，没有稳定版时推荐最高测试版本。
5. 可以撤回有问题的版本，公开列表和下载链接立即失效。历史文件不可覆盖，修复后使用新版本号发布。

只有管理员可以上传 EXE，最大 300 MB；普通作者仍只可上传最大 100 MB 的 MOD ZIP。两类文件使用不同存储目录，网页不会运行上传程序。上传显示真实传输进度；校验失败时保留已选文件，方便修改字段后重试。

### 下载与更新接口

- `/downloads/`：管理器下载页，附历史版本与更新说明。
- `/downloads/windows/`：当前推荐版本的附件下载，支持 HEAD。
- `/downloads/windows/<版本ID>/`：固定版本的附件地址，不跳转 GitHub。Compose 使用 Nginx 传输并支持断点续传；本地 Django 直接流式传输。
- `/api/v1/desktop/releases/`：返回公开版本、推荐版本、版本说明、文件大小、SHA-256 及本站相对下载地址。草稿、撤回或文件不完整的版本不会返回。

**现有 rc.5 EXE 的自动更新仍连接 GitHub**，尚未使用本站更新接口。本次只更新网站，未改动或重新打包桌面程序。玩家可直接下载网站上的新 EXE 替换旧程序；以后适配桌面更新源后，才能自动发现仅在网站发布的新版本。上传新版本文件和更新网站源代码是两回事，日常发布 EXE 无需重新部署网站。

### 从服务器已有文件导入

无需经过浏览器再次传输已有文件。管理员也可以通过命令导入，经过同样的格式、版本及完整性检查：

```bash
python manage.py import_desktop /路径/BBMOD.exe --release-version 0.3.0-rc.5 --admin 你的管理员账号 --notes /路径/更新说明.txt --sha256 完整的SHA256值 --publish
```

Compose 使用独立持久卷 `bbmod-hub_bbmod_desktop`，应用可写入，Nginx 只读挂载。内部下载目录不允许外部直接访问。本地默认程序存放于 `web/var/desktop/`，可用 `BBMOD_DESKTOP_DOWNLOAD_ROOT` 指定目录。

### 独立汉化的首个作品

`content/independent-l10n.json` 保存现有 `mod_bbmod_zhcn.zip` 的发布资料、版本及 SHA-256。当前文件为 `0.3.0-rc.2`、25,831,547 字节；对应仓库现有 `app/dist/mod_bbmod_zhcn.zip`。可以用简化上传页填写这些资料后发布。程序历史版本使用已发布的 rc.2–rc.5 原始 EXE，网站下载时提供带版本号的文件名。生产源码包不包含预览账号或上传数据，实际部署结果另记于 `deploy/`。

中文地名启动组件的 Defender 兼容问题仍未完成复核，rc.6 继续暂停打包；下载说明保留此限制。

## 数据备份与升级

```bash
docker compose exec app python manage.py backup_hub
```

命令使用 SQLite 在线备份接口生成一致的数据库快照，并按快照中的文件清单备份 MOD、图片和桌面 EXE 到 `/srv/data/backups/`。用 `docker compose cp app:/srv/data/backups ./backups` 拷到服务器外，再另行安全保管 `.env`。仅同盘备份不能防止磁盘故障。

升级前备份，替换源代码后执行 `docker compose up -d --build`；数据库迁移自动运行，持久卷保留。不要使用 `docker compose down -v`。若要回到旧程序，先恢复旧源码，并核对其迁移是否兼容当前数据库。

恢复时停止 app，将备份中的 `db.sqlite3` 与 `private/` 恢复到 `bbmod_data`，将 `desktop/` 的内容恢复到 `bbmod_desktop`（先保留现有卷的副本），所有者为 UID/GID `10001`，再启动原匹配版本。程序代码、数据库、文件三者应成套恢复。备份不包含 `.env`。

## Windows 本地开发与验证

```powershell
cd web
py -3.12 -m venv .venv
./.venv/Scripts/python.exe -m pip install -r requirements.lock
$env:BBMOD_DEBUG='1'
./.venv/Scripts/python.exe manage.py migrate
./.venv/Scripts/python.exe manage.py createsuperuser
./.venv/Scripts/python.exe manage.py runserver 127.0.0.1:8765
```

默认数据在 `web/var/`。`runserver` 仅用于本地开发，Ubuntu 使用上面的容器配置。测试：

```powershell
./.venv/Scripts/python.exe manage.py test catalog --noinput
./.venv/Scripts/python.exe manage.py makemigrations --check --dry-run
```

浏览器预览账号仅能在 `BBMOD_DEBUG=1`、`BBMOD_DATA_DIR` 路径含 `preview` 且数据库为空时通过 `seed_preview` 命令创建；不能用它初始化正式服务器。

后端采用 [Django 5.2 的认证与会话机制](https://docs.djangoproject.com/en/5.2/topics/auth/default/)，文件处理依据 [Django 文件上传接口](https://docs.djangoproject.com/en/5.2/topics/http/file-uploads/)。依赖锁定在 `requirements.lock`。美术复用项目原有自制营地与盾徽，Cinzel 字体许可随静态文件保留。

## 桌面端安装边界

首次安装拒绝覆盖已有同名 ZIP；后续更新须匹配本站作品 ID、固定文件名和上次安装哈希。更新会备份旧 ZIP，保持原启用/禁用状态，支持恢复上一版。文件被手工修改时停止自动覆盖。所有下载在临时目录校验后才写入游戏目录。

检查前置和冲突的 MOD ID，版本范围、DLC、存档影响仍需阅读作者说明。不会自动装一串前置，也不会把静态检查标为游戏兼容性验收。HTTP 连接的哈希校验只能发现文件不一致，不能证明服务器身份。未连接网站或断网时，本地 MOD、汉化和种子功能继续可用。

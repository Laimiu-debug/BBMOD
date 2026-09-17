# BBMOD 社区军械库 · 0.1.0

可自行部署的 MOD 分发网站，配套桌面端 `0.3.0-rc.5` 的在线军械库。访客无需登录即可浏览和下载；管理员创建作者账号，作者首次登录改密后可直接公开作品；管理员可以下架作品、停用账号和重置密码。

## 当前功能

- 分类、搜索、作品详情、展示图片、版本记录及各版本下载。
- 作者创建作品、上传 ZIP、发布或撤回版本。已上传文件与当时的作品资料不覆盖，修改资料会在下一次上传时生效。
- 同一作品沿用固定安装文件名，避免升级后同时加载两份 MOD。保留文件名中的加载顺序前缀。
- 管理员查看所有版本和审计记录、下架/恢复作品、创建/停用作者账号。被下架作品不能由作者自行恢复。
- 下架或停用作者后，公开目录及下载入口立即隐藏；作者本人和管理员仍能检查文件。已经被他人下载的副本不被远程删除。
- 原作链接、分发许可、游戏/DLC 要求、前置和冲突 MOD ID、存档与种子影响说明。
- ZIP 结构、CRC、大小、哈希和路径检查，图片解码后重新保存。检查不执行游戏脚本，也不是病毒扫描或游戏兼容性认证。
- `GET /api/v1/catalog/` 同时为桌面端提供公开目录；下载地址始终在本站。

不预装第三方合集、不包含狐狸汉化资源。正式数据库初始为空，测试账号和测试 ZIP 不进入部署包。

## Ubuntu 部署（无域名）

需要 Docker Engine 与 Compose 插件，安装方法见 [Docker 官方 Ubuntu 指南](https://docs.docker.com/engine/install/ubuntu/)。以下命令从项目根目录运行，或解压发布附件 `BBMOD-Hub-0.1.0.tar.gz` 后进入 `BBMOD-Hub-0.1.0/`。

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

容器不会映射数据库或上传目录为公开静态文件，也不会改动其他服务。默认使用名为 `bbmod-hub_bbmod_data` 的持久卷；一个应用进程、四个线程和 SQLite，适用于先给群友使用的单机站点。服务器 IP 改变时修改 `.env` 的 `BBMOD_ALLOWED_HOSTS` 再运行 `docker compose up -d`。不要把 `.env`、账号数据库或证书私钥上传到 GitHub。

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

## 数据备份与升级

```bash
docker compose exec app python manage.py backup_hub
```

命令使用 SQLite 在线备份接口生成一致的数据库快照，并按快照中的文件清单备份 ZIP 和图片到 `/srv/data/backups/`。用 `docker compose cp app:/srv/data/backups ./backups` 拷到服务器外，再另行安全保管 `.env`。仅同盘备份不能防止磁盘故障。

升级前备份，替换源代码后执行 `docker compose up -d --build`；数据库迁移自动运行，持久卷保留。不要使用 `docker compose down -v`。若要回到旧程序，先恢复旧源码，并核对其迁移是否兼容当前数据库。

恢复时停止 app，将备份中的 `db.sqlite3` 与 `private/` 恢复到原持久卷（先保留现有卷的副本），所有者为 UID/GID `10001`，再启动原匹配版本。程序代码、数据库、文件三者应成套恢复。备份不包含 `.env`。

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

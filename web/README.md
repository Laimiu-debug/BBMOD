# BBMOD 社区军械库 · 0.3.7

官网已迁移至 **https://bbmod.com**，网站、API 和下载由海外服务器直接提供，保留原账号、作品和历史数据。当前桌面版本为 **0.3.1**；rc.36 及更新版本可在软件内检查更新，更早的旧官网版本请从新官网下载最新版。

桌面管理器 **0.3.1** 修复设置保存、损坏配置启动及 MOD 并发修改问题，固定使用三段版本号。安装包仍通过 `import_desktop --publish` 发布；独立汉化包保持 rc.9。网站 **0.3.7** 修复百科翻译计数缓存并发清理的问题，无新增数据库迁移。详见[版本说明](../app/releases/0.3.1.md)、[版本约定](../app/docs/versioning.md)与[部署记录](deploy/deployment-desktop-0.3.1-2026-10-06.md)。

新手使用说明（2026-10-03 官网迁移修订）：[`/guide/`](https://bbmod.com/guide/) 提供 BBMOD 下载与升级指引、汉化 rc.9 和阿飞 v0.27.4 的完整安装图文及 PDF；操作截图沿用已检查的 rc.33 界面。首页、顶部导航、下载页均有入口；阿飞升级后须新建战役。网页模板与版本化静态资源由 `python web/tools/build_beginner_guide.py` 在仓库根目录生成，需要 `markdown-it-py`，输入为根目录 Markdown、`docs/images/` 截图和已检查的 `output/pdf/BBMOD新手使用说明.pdf`；页面上的桌面版本标签读取自 `app/core/version.py`，Markdown 未提及该版本时脚本会报错。首次教程发布步骤与验证见[部署记录](deploy/deployment-beginner-guide-2026-09-29.md)。

错误报告收集（rc.32）：`POST /api/v1/suggestions/` 接受可选 `diagnostic_report` 文本，最多 60,000 字；GET 返回支持的长度。原有反馈客户端保持兼容，提交继续使用会话、CSRF、回执去重和限流。升级需执行迁移 `0008`。管理员在 `/manage/suggestions/?reports=1` 按日志内容、版本和 MOD ID 搜索报告，详情页支持私密 TXT 下载及处理状态、内部备注；报告随数据库备份。

可自行部署的 MOD 分发网站，配套桌面端的在线军械库；软件及独立汉化的当前版本以官网公开下载目录为准。访客无需登录即可浏览和下载；管理员创建作者账号，作者首次登录改密后可直接公开作品；管理员可以下架作品、停用账号和重置密码。

## 当前功能

- rc.30 配套更新（2026-09-28 已上线）：`GET /api/v1/profiles/?q=<关键词>&page=<页码>` 为桌面「方案管理」提供公开方案列表。每页 12 项，按分享时间倒序；搜索名称和介绍，下架方案不返回。响应包含 `schema_version`、`items`、`page`、`pages`、`total`；条目包含编号、名称、介绍、游戏版本、MOD 数量、总大小、分享时间和本站详情路径。列表与网页广场共用筛选规则，应用仍通过详情接口检查全部文件可用性。无需登录、无新增数据库迁移，现有 POST 发布接口保持兼容。管理器 rc.30 同时公开，详见[部署记录](deploy/deployment-profiles-rc30-2026-09-28.md)。

- 共享 MOD 方案（2026-09-27 已上线，客户端 rc.29）：`/profiles/` 展示玩家的多 MOD 搭配，方案详情通过 `bbmod://profiles/<编号>` 打开客户端，或复制网页链接到管理器。方案固定文件内容，更新作品不会自动替换方案版本。
- 桌面先调用 `/api/v1/profiles/plan/`，按 SHA-256 和大小查找历史公开版本及玩家补传文件，仅向 `/api/v1/profiles/files/<sha256>/` 上传缺失 ZIP；全部文件可用后才通过 `/api/v1/profiles/` 发布。中断重试复用已上传文件，不重复存储同一内容。只有介绍和原作链接、没有实际文件的目录条目不能代替下载文件。
- 接收者通过 `/api/v1/profiles/<编号>/` 读取清单，用该方案内的 `/files/<sha256>/` 下载精确版本。未公开、撤回、作者停用和文件下架均禁止被方案引用或重新上传；方案文件不可用时停止应用，不自动替换版本。共享文件与作者作品分开存储，不修改原作者的作品或署名。
- `/manage/profiles/` 管理方案及补传文件。下架文件影响引用它的全部方案，下架方案仅影响该方案。匿名桌面上传需要原生请求头和短期签名凭据，不接受浏览器跨站请求；全部 ZIP 沿用网站结构与 CRC 检查。方案至多 200 个 MOD / 2 GB，单文件 100 MB。每日每来源最多补传 500 个文件 / 2 GB，全站最多 5000 个文件 / 20 GB；共享文件存储默认 20 GB，可用 `BBMOD_PROFILE_STORAGE_MB` 调整。未发布完成的已上传文件保留供重试复用，并占用额度。
- 官网已完成迁移 `0007` 并发布 rc.29；自托管升级时也需迁移并更新客户端。备份命令已纳入共享 MOD 文件。官网共享文件存储初始额度为 4 GB，部署与验证见[发布记录](deploy/deployment-profiles-rc29-2026-09-27.md)。

- 游戏百科 `/wiki/`：提供游戏资料的中文全文、中英对照与英文原文，支持中文全文检索、分类、重定向、原文下载和来源版本。118 篇官方历史日志按明确范围保留英文。原文的过时提示、DLC 条件与公式保留；目录与长表适配手机阅读。
- 百科通过公开 MediaWiki API 离线构建，访问时不调用 Fandom。HTML 经白名单清洗，原站脚本不运行；图片使用本站内容哈希地址。当前资料、原始来源版本和完整性报告与社区数据库分开存储，管理员通过 `/manage/wiki/` 查阅报告。
- 图片保留独立来源信息；原站未提供许可声明时如实记录为 `source_unstated`，不将正文的 CC 许可自动套用到媒体文件。大图可生成最大 1600 像素的网页阅读副本，原始来源元数据和实际返回文件哈希分别保存。
- 百科维护、快照发布、备份和验收见 [`docs/wiki-migration.md`](docs/wiki-migration.md)。

- 「反馈与建议」`/suggestions/`：无需登录即可提交功能建议、问题反馈或其他想法，称呼、联系方式和相关版本均为选填。内容仅管理员可见，提交成功显示建议编号；刷新或重复提交同一表单不会重复保存。
- 管理后台新增「玩家建议」入口和待查看数量，支持按状态、类型、关键词筛选与分页，查看原文、联系方式并保存处理状态和内部备注。状态包括待查看、处理中、已完成、暂不采纳；内部备注不会自动发送给提交者。过期编辑页面不能覆盖其他管理员刚保存的处理记录。
- 建议提交使用 CSRF 防护与每小时额度（每浏览器 5 条、代理确认地址 30 条、全站 300 条）。只保存用于限流的短期 HMAC 摘要，不保存原始地址；两天前的额度记录在后续有效提交时清理。反向代理出口可能共享地址。提交失败保留表单内容；关闭浏览器后不保留未提交草稿。

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

需要 Docker Engine 与 Compose 插件，安装方法见 [Docker 官方 Ubuntu 指南](https://docs.docker.com/engine/install/ubuntu/)。以下命令从项目根目录运行，或解压 `BBMOD-Hub-0.3.7.tar.gz` 后进入 `BBMOD-Hub-0.3.7/`。

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

## 海外服务器与自有域名部署

正式入口为 `https://bbmod.com`，应用、账号数据库、百科和上传文件已迁移至同一台海外服务器的独立 Docker 服务中。域名、HTTPS 和来源限制使用新官网地址，下载继续执行大小、SHA-256 及公开权限检查。

`compose.gateway.yml` 为已有 HTTPS 代理的服务器提供独立部署配置，不占用宿主机的 80/443/8080 端口。它使用 BBMOD 专用数据卷；只有网关容器连接已有代理网络。现有服务端数据和生产源码须从一致备份迁入，再在候选环境核对账号数量、作品、历史版本、方案、种子、反馈和百科。

源码打包：`python tools/package_hub.py`，默认输出到 `app/build/hub/0.3.7/BBMOD-Hub-0.3.7.tar.gz`。包内不含 `.env`、账号数据库、上传文件或预览账号初始化命令。升级前使用 `backup_hub` 备份，并在备份副本演练迁移。百科快照单独存放于持久卷的 `wiki/`。迁移现有网站时优先保留正在运行的生产代码及匹配的数据备份。

## 管理员发布软件版本

1. 登录管理员账号，进入「管理后台 → 管理器版本」。
2. 拖入打包完成的 EXE。带版本号的文件会自动填写版本号；旧名 `BBMOD.exe` 需手动填写。写好更新说明，上传即可。
3. 勾选「上传成功后立即公开」时直接出现在下载页；不勾选则保存为草稿，管理员检查后再公开。
4. 玩家可以选择稳定版、测试版以及历史版本，直接下载 `BBMOD-实际版本号.exe`。默认推荐最高稳定版本，没有稳定版时推荐最高测试版本。
5. 可以撤回有问题的版本，公开列表和下载链接立即失效。历史文件不可覆盖，修复后使用新版本号发布。

只有管理员可以上传 EXE，最大 300 MB；普通作者仍只可上传最大 100 MB 的 MOD ZIP。两类文件使用不同存储目录，网页不会运行上传程序。上传显示真实传输进度；校验失败时保留已选文件，方便修改字段后重试。

### 下载与更新接口

网关部署对 MOD、汉化包及共享方案文件启用 `BBMOD_MOD_DOWNLOAD_ACCEL=1`，通过私有 `/_mods/` 交给 Nginx 传输，并支持 HEAD 和 Range 续传。每次下载及续传仍先经过 Django 的公开、下架与文件校验。网关以只读方式挂载数据卷；`/_mods/` 禁止外部直接访问。直接运行 Django 时保留普通文件响应。

当前生产环境将 `BBMOD_PUBLIC_DOWNLOAD_BASE` 留空，网页下载按钮和桌面 API 返回站内相对路径，由 `https://bbmod.com` 提供文件下载。自部署时如需显式生成绝对地址，可设置为自己的 HTTPS 官网域名。下载及续传仍必须通过相同的发布权限检查。

- `/downloads/`：管理器下载页，附历史版本与更新说明。
- `/downloads/windows/`：当前推荐版本的附件下载，支持 HEAD。
- `/downloads/windows/<版本ID>/`：固定版本的附件地址，不跳转 GitHub。Compose 使用 Nginx 传输并支持断点续传；本地 Django 直接流式传输。
- `/api/v1/desktop/releases/`：返回公开版本、推荐版本、版本说明、文件大小、SHA-256 及本站相对下载地址。草稿、撤回或文件不完整的版本不会返回。

**当前推荐桌面版本为 0.3.1**。rc.36 及更新版本可直接检查更新；更早的旧官网版本先从 `https://bbmod.com` 手动下载最新版，此后自动更新优先连接新官网，失败时回退到 GitHub。上传新版本文件和更新网站源代码是两回事，日常发布 EXE 无需重新部署网站。

### 从服务器已有文件导入

无需经过浏览器再次传输已有文件。管理员也可以通过命令导入，经过同样的格式、版本及完整性检查：

```bash
python manage.py import_desktop /路径/BBMOD.exe --release-version 0.3.0-rc.5 --admin 你的管理员账号 --notes /路径/更新说明.txt --sha256 完整的SHA256值 --publish
```

Compose 使用独立持久卷 `bbmod-hub_bbmod_desktop`，应用可写入，Nginx 只读挂载。内部下载目录不允许外部直接访问。本地默认程序存放于 `web/var/desktop/`，可用 `BBMOD_DESKTOP_DOWNLOAD_ROOT` 指定目录。

### 独立汉化的首个作品

`content/independent-l10n.json` 保存独立汉化的发布资料、版本及 SHA-256。当前为 `0.3.0-rc.9`，归档路径以该文件的 `archive` 字段为准，下载时保持安装名 `mod_bbmod_zhcn.zip`。普通 MOD 版历史下载保留，已撤回的旧注入版继续保持撤回。生产源码包不包含预览账号或上传数据，实际发布结果另记于 `deploy/`（rc.9 见[发布记录](deploy/deployment-localization-rc9-2026-09-27.md)）。

新版汉化使用普通 MOD，启用后从 Steam、游戏 EXE 或 BBMOD 启动均通过游戏界面显示中文地名。汉化 rc.7 起逐句复核 15,819 条文本及随机分支并修订 634 条，完成词库、实际包、字节码和动态显示离线检查；本轮没有启动游戏，当前版实机显示及所有 MOD 组合尚未验收。已启用的包无需重复生成，要使用新译文时导入并应用官网新版包。

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

桌面建议接口：`GET /api/v1/suggestions/` 获取会话绑定凭据和 CSRF token，`POST` 使用相同 Cookie、`X-CSRFToken` 和 JSON 字段提交。与官网共用管理员收件箱、校验、限流和幂等回执；本版没有新增数据库迁移。


## MOD 介绍与来源

“探索 MOD”统一展示本站作品与原作者作品，支持分类、搜索、分页和来源筛选。`content/community-mods.json` 收录 24 项简短介绍；每项说明功能、前置和汉化适配情况，不把维护者的电脑环境当作访客环境。只有许可明确的三个署名整理包提供本站下载，其余在 MOD 详情页链接原作者页面。没有额外兼容导航页。桌面安装 API 继续只返回可由本站下载的公开版本。

公开快照分别记录 `original_author` / `uploader`，兼容原有 `author` 字段。未经许可的本地收藏不进入部署源码包；59 项本地核查证据见 `docs/mod-compatibility-2026-09-19.md` 与对应 JSON，不作为公共导航内容。

## rc.26 客户端配套网站更新

新增下载入门指南、软件截图、首页入口、可见的存档兼容提示，以及 `bbmod://mods/<UUID>` 和 `bbmod://seeds/<UUID>` 链接。公开种子读取接口为 `GET /api/v1/seeds/<UUID>/`，下架条目返回 404；没有新增数据库迁移。部署时同步模板、Python 文件与 static 文件并按既有流程执行 collectstatic、重启服务。2026-09-25 已部署到生产环境，并公开 rc.26 EXE。详见 `deploy/deployment-rc26-2026-09-25.md`。

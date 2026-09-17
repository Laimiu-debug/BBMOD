# BBMOD Hub 0.1.1 部署记录

## 入口与存储

- 网站：<https://bbmod.vercel.app>
- Vercel 项目：`laimiu-debugs-projects/bbmod`
- 当前部署 ID：`dpl_CCZc3D2xFLrKL32XPzZJ4DsfBpPr`，平台状态 `READY`，域名已绑定；公开地址已实测。
- Vercel 项目允许公开访问；BBMOD 自己的作者与管理员功能仍要求账号登录。
- Ubuntu：使用已有服务器；独立 Compose 项目 `bbmod-hub`。
- 源码目录：`/home/ubuntu/bbmod-hub/releases/BBMOD-Hub-0.1.1-f006c6e35b0a`。
- 活跃版本记录：`/home/ubuntu/bbmod-hub/active-release.txt`。
- 数据卷：`bbmod-hub_bbmod_data`，账号和 MOD 文件不会写入 Vercel。
- 私有配置：`/home/ubuntu/bbmod-hub/shared/.env`，不纳入 Git 或部署附件。

## 构建证据

- 版本化源码包：`BBMOD-Hub-0.1.1.tar.gz`，59 个文件，逐个校验 manifest。
- 源码包 SHA256：`f006c6e35b0ac75b3275978bcb2e5be051e1a146ee55a419133c6f14e0640468`。
- 镜像：`bbmod-hub:0.1.1`。
- 镜像 manifest：`sha256:b32aea35f93490160d9599870cd82c11ed83206b524bffd80214cd45d664c71d`。
- 依赖版本沿用 `requirements.lock`。Ubuntu 下载较慢，使用从 PyPI 下载、传输后再次校验 SHA256 的相同 Linux wheels 离线安装；构建配方保存在服务器 `shared/Dockerfile.offline`。
- Vercel 只上传入口配置，不包含 Python 程序、服务器密钥、数据库或 MOD。

## 验证结果及范围

- Windows 本地 17 项 Django 测试通过；Linux 发布镜像内 17 项测试通过。
- 数据库迁移检查无遗漏；应用容器健康检查通过。
- Ubuntu HTTPS 源站：首页、四个静态资源、目录 API、登录、强制首次改密页面及退出检查通过。
- 未登录的管理入口跳转登录；`.env`、私有目录不能公开读取。
- 页面与下载禁用共享缓存；登录会话使用 Secure Cookie。
- 现有网站首页部署前后响应哈希一致；原有服务容器未重启。
- Vercel 正式网址：首页、登录页、CSS、健康检查和目录 API 全部返回 200；实际浏览器中确认首页、分类页和登录后的作者工坊正常显示。100 MB 上传仍未经过 Vercel 实网压力验证。
- `check --deploy` 仅提示未启用 HSTS 子域继承和浏览器 preload；HTTPS、安全 Cookie 与一年 HSTS 已启用。未擅自扩展到其他子域。
- 无测试账号或测试 MOD 留在正式库。管理员账号 `bbmod-admin` 已创建，首次登录要求改密，初始密码单独保存在本机私有交付文件。

## 备份与维护

- 代理变更备份：`/home/ubuntu/bbmod-hub/backups/nginx-20260917T065445Z`，含原模板、原生效配置、校验结果。
- 初始数据备份：数据卷内 `/srv/data/backups/bbmod-hub-20260917T065715268679Z.tar.gz`。
- 源站路由同时写入现有 Nginx 模板与生效配置。后续部署其他站点时，保留 HTTPS `server` 中的 `bbmod-origin-location.conf` 引用及对应文件。
- Vercel 未绑定 Git 自动部署；入口配置变化需重新部署 `web/vercel`。作者上传、发布和下架 MOD 不需要重新部署网站。
- 备份、升级和地址变更步骤见 [`../vercel/README.md`](../vercel/README.md)。

## 404 修复

首次部署 `dpl_Ar84TE7wJz2GdhMMgE6WCdJwLQyA` 使用空的静态输出目录，平台显示 READY，但公开请求没有转发到 Ubuntu，返回 Vercel `NOT_FOUND`。源站仍返回 200。

修复后由 `web/vercel/build.mjs` 明确生成 Build Output API 路由产物，用 `--prebuilt` 部署。预览地址检查通过后发布正式版本，并再次访问正式域名验收。`web/tools/check_gateway.py` 可复用来检查公开地址、页面内容和缓存设置，发布流程不再仅依赖平台状态。

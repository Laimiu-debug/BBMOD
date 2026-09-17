# BBMOD 的 Vercel 入口

公开地址目标：`https://bbmod.vercel.app`。Vercel 项目只部署本目录。`vercel.json` 把所有路径转发到 `https://sdhaohan.cn/bbmod-origin/`；地址栏仍显示 BBMOD。不要上传整个仓库或 `.env`。

## Ubuntu 配置

1. 解压带版本号的 Hub 源码包，进入 `web/`。
2. 运行 `python3 tools/init_env.py --host bbmod.vercel.app`，保留生成的随机密钥。
3. 修改私有 `.env`：

   ```dotenv
   BBMOD_ALLOWED_HOSTS=localhost,127.0.0.1,bbmod.vercel.app
   BBMOD_HTTPS=1
   BBMOD_CSRF_ORIGINS=https://bbmod.vercel.app
   BBMOD_EDGE_NETWORK=weld-system_weld_network
   ```

4. 执行 `docker compose -f compose.gateway.yml up -d --build`。只有 BBMOD 的容器及数据卷参与这个 Compose 项目。
5. 备份已有 HTTPS 代理配置，在 `sdhaohan.cn` 的 HTTPS `server` 内引入 `deploy/bbmod-origin-location.conf`。现有代理必须能解析 Docker 网络中的 `bbmod_hub_gateway`，并使用 `resolver 127.0.0.11 valid=10s ipv6=off`。先运行 `nginx -t`，通过后 reload；保留原有其他路由。若代理配置由模板生成，同步模板与当前生效配置。
6. 检查源站 `/bbmod-origin/health/`、静态文件、目录 API、CSRF 登录和上传下载。内部网关信任上一级代理覆盖的 Host、X-Real-IP；不要给它映射公网端口。
7. 使用 `docker compose -f compose.gateway.yml exec app python manage.py createsuperuser` 创建自己的管理员。正式数据库初始为空。

源站路径供 Vercel 连接，不是用户入口。站内链接从根目录开始。另换源站时，同时修改 Vercel 重写地址和 HTTPS 路由；另换公开域名时，同步固定 Host、ALLOWED_HOSTS 和 CSRF_TRUSTED_ORIGINS。

## Vercel 配置

在本目录执行以下步骤：

```bash
vercel link --project bbmod --yes
node build.mjs
vercel deploy --prebuilt --yes
python ../tools/check_gateway.py https://上一步返回的预览地址
vercel promote 上一步返回的部署ID --yes
```

等待正式部署达到 `READY` 且域名分配完成，再执行 `python ../tools/check_gateway.py https://bbmod.vercel.app`，并用浏览器检查首页和作者登录页。平台显示 `READY` 不代表页面可用。

本项目没有本地 HTML 页面，必须使用 `build.mjs` 生成 Build Output API 的 `.vercel/output/config.json`，并使用 `--prebuilt` 上传路由产物。空的 `public/` 静态部署曾出现构建成功但所有请求返回 404 的情况。发布时确认外部路由、禁止共享缓存设置均写入产物。

面向群友的地址应允许访客访问，作者登录仍由 BBMOD 管理。

不要为 Python Function 创建中转上传接口。这里使用 [外部重写](https://vercel.com/docs/routing/rewrites)，避免 [Function 的 4.5 MB 请求限制](https://vercel.com/docs/functions/limitations)。外部源站首次响应仍受 Vercel 代理超时限制；慢速网络的最大上传应在实际使用网络下确认。

Vercel 侧明确关闭外部重写缓存；应用页面、API、文件下载返回 `private, no-store`，避免登录状态泄漏和下架后继续命中旧文件。静态资源由 WhiteNoise 提供。当前上游按代理连接地址进行登录限流，不信任公网客户端自行填写的转发 IP 头。

## 备份与升级

```bash
docker compose -f compose.gateway.yml exec app python manage.py backup_hub
docker compose -f compose.gateway.yml cp app:/srv/data/backups ./backups
```

另存私有 `.env`。升级保留 `bbmod-hub` 项目名与 `bbmod_data` 卷，先备份再重新构建、迁移。不要运行 `down -v`。Vercel 入口无需访问数据库或任何服务器凭据。

# BBMOD 自有域名部署记录

部署日期：2026-09-17。网站版本：0.2.0。本文记录已完成的生产部署，替代早期 Vercel 入口记录中的当前状态。

## 访问与日常发布

- 网站：https://bbmod.site/
- 管理器下载：https://bbmod.site/downloads/
- 管理员发布软件：https://bbmod.site/manage/software/
- 作者发布 MOD：https://bbmod.site/workshop/new/
- 独立汉化：https://bbmod.site/mods/22c174ed-fc9d-4dbb-9642-44831ce694e8/

原管理员账号、密码和作者数据保留。在新域名重新登录即可使用。管理员上传 EXE，填写版本号、更新说明后公开；作者拖入 ZIP，填写介绍等基本信息后公开，其他安装资料可选填写。作者不能进入管理员页面或上传 EXE。

软件发布不需要再次部署网站，也可以使用 `import_desktop --release-version` 从服务器已有文件导入。同一版本不允许覆盖；旧版本可以下载，管理员可以撤回版本。

## 已公开的文件

| 文件 | 大小（字节） | SHA-256 |
| --- | ---: | --- |
| BBMOD-0.3.0-rc.2.exe | 75525475 | ff4e070cef314c2a3bf2c2eea78f29a78e958cb87d15525cdb6fb60eaf1c10d5 |
| BBMOD-0.3.0-rc.3.exe | 75541923 | 5e296b2b4811192dd86c444a87464a7c10c3cd64fd926f6d17a90710926d4a5e |
| BBMOD-0.3.0-rc.4.exe | 75574483 | 091744be5ef3659013612cc7158f3cb65851cb2ed7092443c522bf2231d5a286 |
| BBMOD-0.3.0-rc.5.exe | 76135918 | 8c688cb597d7b9834849a88d4c01e6a4d17f9a916d34d6fa392ec67491b41302 |
| mod_bbmod_zhcn.zip（0.3.0-rc.2） | 25831547 | 467d524c4a75240ecfd2154b094dd6cde9dcb67094aa8053a834ca0cf3c01210 |

EXE 均为已经发布的原文件，哈希与 GitHub 发布资产相符，只在下载时提供带版本号的文件名。未重新打包桌面程序。沿用管理员之前创建的汉化作品 ID，补齐发布资料并上传现有 ZIP。

## 服务器与源代码

- Ubuntu：43.142.188.252；网站直接由此服务器提供，不经 Vercel 转发。
- DNS 已存在：`bbmod.site A 43.142.188.252`，DNSPod 管理；未修改注册人信息。
- 应用发布目录：`/home/ubuntu/bbmod-hub/releases/BBMOD-Hub-0.2.0-cb53d8abce7c`。
- 应用源码包：`app/build/hub/0.2.0/candidate-3/BBMOD-Hub-0.2.0.tar.gz`。
- 源码包 SHA-256：`cb53d8abce7c4b971bf952ebf9867a3c99ea60ba4922edb29fa78dc1fb6dc055`，78 个源文件。
- 镜像：`bbmod-hub:0.2.0`；镜像索引摘要 `sha256:6c8a3074d189ca2a6ece8b8e40ce8d08c0195c975cbfd153fb652329c6f2495d`。
- Compose 项目 `bbmod-hub`，文件 `web/compose.gateway.yml`。
- 数据卷 `bbmod-hub_bbmod_data`；管理器文件卷 `bbmod-hub_bbmod_desktop`，网关只读挂载。
- 私有设置 `/home/ubuntu/bbmod-hub/shared/.env`，不在源码包或本文中。
- `active-release.txt` 已更新为上述发布目录。

### 外层 HTTPS 配置

外层配置独立于应用镜像。生产使用本目录的 `bbmod-site.conf`，其最终 SHA-256 为 `d6712b5fbb1965ea7bae342e51d2e7c9a637819f32006519e505a04f72ba7645`。此配置在应用源码包制作后完成了上传链路调整；后续更新外层代理应使用该文件的当前版本。

配置安装于 `/home/ubuntu/GongPro/apps/cloud/nginx/conf.d/bbmod-site.conf`。主模板与运行中的 Nginx 配置均已加入独立 include，容器重建后仍会加载。原 Vercel 回源路由保留，上传上限更新为 308 MB。

实际浏览器的大文件上传在 HTTP/2 下出现 `ERR_HTTP2_PING_FAILED`，请求在到达应用前中断。BBMOD 域名改用 HTTPS 上的 HTTP/1.1，真实 76 MB 上传随后完成。为使设置按站点生效，将其他四个站点的旧 `listen ... http2` 写法转换为等价的 `http2 on`；逐一验证这些站点仍协商 HTTP/2。未重启其他业务容器。

## 证书与续期

- Let's Encrypt 证书覆盖 `bbmod.site`，有效期至 **2026-12-16 07:22:36 UTC**。
- HTTP 自动跳转 HTTPS，ACME 验证目录仍可访问。
- 现有 `weld_certbot` 每 12 小时执行续期检查，已经包含新证书。
- `bbmod-cert-reload.timer` 每小时检查新证书指纹；仅在证书变化后检查 Nginx 配置并平滑重载。
- `certbot renew --cert-name bbmod.site --dry-run --no-random-sleep-on-renew` 成功。

## 验证结果

- Windows 与 Ubuntu 容器均通过 31 项 Django 测试；迁移检查无遗漏。
- 用生产备份演练数据库升级，账号密码和原作品记录保留；生产迁移 `0002_desktoprelease` 成功。
- 新域名首页、登录、健康检查、CSS、下载页、MOD API、管理器 API 均返回 200，动态响应禁止共享缓存。
- 四个 EXE 的 HEAD、文件名、长度、SHA-256 响应头、Range 206 均通过；内部文件目录无法直接访问。
- 匿名完整下载 rc.5 EXE（76135918 字节）和汉化 ZIP（25831547 字节），SHA-256 与源文件一致，无外站跳转。
- 实际浏览器通过管理员页面上传完整 rc.5 EXE；后台拒绝覆盖重复版本，表单保留所选文件，公开列表仍为四个版本。
- 简化 MOD 页的拖拽、自动填写、错误后保留文件与完整发布已在本地浏览器验证。生产汉化经相同验证逻辑导入。
- 桌面与 390 px 手机页面已截图检查。临时验证会话已撤销，未重设管理员密码。
- 旧 `bbmod.vercel.app` 的七个基本页面/API 仍可访问。
- 除 BBMOD 两个容器外，原有容器 ID、启动时间全部保持不变。

公开检查结果与浏览器证据位于本地 `output/deployment/bbmod-site-public-verification.json` 和 `output/playwright/`，不包含于公开网站。

## 备份

升级前的数据库、上传文件、私有配置与 Nginx 配置已备份至服务器 `/home/ubuntu/bbmod-hub/backups/20260917-bbmod-site-020/`，并保留旧发布目录。调整上传连接前另存了一份当时的代理配置。

最终完整备份：`/srv/data/backups/bbmod-hub-20260917T085749379566Z.tar.gz`（位于持久数据卷）。SHA-256：`cc404648b650bbc9186198422e18fc98b470e96a21cfd89ea830d94e5b6be1cf`。

已从备份内读取数据库做完整性检查，并逐个校验四个 EXE、一个 ZIP 及封面；备份前后账号凭据相同。这份完整备份仍在原服务器，尚未建立异机定期备份。

## 保留的边界

- 现有 rc.5 EXE 的自动更新源仍是 GitHub；仅在网站上传新 EXE 后，旧程序不会自动发现它。玩家可以手动从网站下载替换。桌面军械库可填 `https://bbmod.site` 使用本站 MOD。
- 中文地名启动组件的 Defender 复核未完成，rc.6 继续暂停打包，发布说明保留这一事实。
- 未启动游戏，未声称所有游戏流程或第三方 MOD 组合已经验收。
- 本次未提交或推送 Git，网站已按当前本地源码部署。

# Hub 0.3.4 与 BBMOD rc14

## 官网

- 已部署：`/home/ubuntu/bbmod-hub/releases/BBMOD-Hub-0.3.4-583f78f0a7ca`。
- 源码包：`output/deployment/desktop-api-20260918/BBMOD-Hub-0.3.4.tar.gz`，SHA-256 `583f78f0a7ca192505ea9cedf0a2d4563a9562f94441c5c5114b5b251cffdd38`。
- 功能：桌面匿名反馈 API、反馈名称统一、种子分页及每页数量；按用户最终要求保留原种子页面样式。
- 验证：77 项 Django 测试；迁移演练保留全部原有行；实际部署事务检查 CSRF、提交、重复重试、管理员查看和处理，检查后全部回滚，未留下测试反馈。
- 线上浏览器：第一页 6 条、第二页 4 条，无重复；选择每页 12 条后显示 10 条且回到第一页；390 px 手机宽度无横向溢出。
- 只重建 BBMOD app；原网关和其余容器均未重启，独立 Wiki 快照保留。
- 证据：`output/deployment/desktop-api-20260918/verified.json`、`output/playwright/seeds-v034-live-desktop.png`、`output/playwright/seeds-v034-live-mobile.png`。

## 桌面

- 构建：`BBMOD-0.3.0-rc.14.exe`，77,282,477 字节。
- SHA-256：`4712445db283cb66bdb4d8f040fe9db810365178f4af37a7bf98c6ab6c25ff48`。
- 自定义快捷键；原游戏属性框保持完整，独立对比小框按原框实际边界自动避让；悬停显示、移开隐藏、背景透明度可调。MOD v2 需退出游戏后安装，再重启游戏。
- 种子管理与回收站；设置固定在侧栏底部；装备百科、反馈与建议名称统一；设置页手动检查与默认退出时静默更新；桌面免登录反馈。
- 验证：291 项 pytest；原版 TooltipModule JavaScript 回调与离线 Squirrel；受控前台身份的 Qt 日志联调、显隐、快捷键、原框不同位置避让；28 组字体布局。
- EXE：资源哈希和隔离启动通过；Windows 文件版本、产品版本、原文件名一致；未打包退役注入组件；Defender 自定义扫描未发现威胁，扫描不执行修复。
- 隔离 rc13 → rc14 更新：主动重启与退出时静默替换均通过，旧 EXE 备份哈希正确、设置字节不变，静默模式未重新启动。
- 发布前备份：`/home/ubuntu/bbmod-hub/backups/20260918-rc14-tools/bbmod-hub-20260918T150125363006Z.tar.gz`，数据库完整，12 个历史下载文件哈希全量通过。
- 发布状态：已公开。版本 ID `7e417333-40fd-4fbd-a4f7-dc26a3cb4916`，下载 `/downloads/windows/7e417333-40fd-4fbd-a4f7-dc26a3cb4916/`。历史版本、汉化包与容器状态保持不变；记录见 `output/deployment/rc14-tools-20260918/published.json`。

## 公网交付核验

官网下载页推荐 rc14，并保留 rc13、rc12。正式更新 API 的版本、下载路径、大小与哈希一致。使用桌面真实 UpdateService 从公网完整下载 77,282,477 字节并校验成功，SHA-256 与本地发布件一致；未安装到用户日常软件或启动游戏。证据：`app/build/review/rc14-public-update-check.json`、`output/deployment/rc14-tools-20260918/public-api.json`。第一次检查因测试脚本 120 秒总时限取消；扩展为 360 秒后通过，产品传输超时逻辑未修改。

## 验证边界

Qt 前台游戏身份使用受控 fixture。隔离 Steam 游戏之前在进入脚本前退出，本轮未将离线结果冒充真实游戏验收。实际游戏里的背包、商店、战利品悬停、DPI 与第三方 MOD 组合仍需玩家验收；建议无边框或窗口化。此前使用 GitHub 更新源的 rc13 及更早版需从官网下载 rc14 一次，此后由官网更新。汉化包维持独立版本，不因 EXE 更新而覆盖。

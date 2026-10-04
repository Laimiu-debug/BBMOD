# BBMOD rc.38：已安装 MOD 更新识别与状态显示

2026-10-04（UTC+8）已将 `0.3.0-rc.38` 发布到 https://bbmod.com 。本次仅通过现有 `import_desktop --publish` 导入桌面安装包，没有重建网站或重启生产容器。官网更新 API 推荐 rc.38，已公开的历史桌面版本保持原样。

## 发布内容

- 已核实文件或可信安装记录对应的旧 `preview` 版本可以识别新版，例如 `0.29.0-preview.12` → `0.29.0-preview.13`；数字序号按数值比较，支持后续 rc 和正式版。
- 已安装列表的更新列直接显示「已是最新」「版本待确认」「未匹配官网」或「本地版本较新」，确认有更新时显示行内「更新」按钮。
- 更新继续保留原文件名、启停状态和旧版备份；无法确认的脚本内部编号不直接当作官网发布版本。

## 安装包与公开验收

| 项目 | 结果 |
| --- | --- |
| 文件 | `BBMOD-0.3.0-rc.38.exe` |
| 发布 ID | `10243345-f5dd-4676-8cc8-c8fdb717855c` |
| 状态 | `published` |
| 大小 | 86,229,795 字节 |
| SHA-256 | `6db5913362f71828ede1413c5ae1d14a9b87baaf37b65f65e6e8aed99a2db85f` |
| 官网推荐 | `0.3.0-rc.38` |
| 公网完整下载 | 长度、SHA-256、EXE 校验全部通过；来自官网，无备用源错误 |
| 公网 HEAD / Range | HTTP 200 / 206，1024 字节区间长度正确 |
| 直连生产网关 | HEAD 200、Range 206；长度、校验值和文件前 1024 字节匹配 |
| 打包客户端联网 | rc.38 通过；旧 rc.37 从官网识别到 rc.38 |
| 网站健康 | `/health/` HTTP 200，`status=ok` |

[官网下载](https://bbmod.com/downloads/windows/10243345-f5dd-4676-8cc8-c8fdb717855c/)

## 测试与备份

完整桌面回归逐模块运行：61 个模块，727 项通过，1 项可选原始游戏 UI 用例因本地夹具未提取而跳过，0 个失败模块。此前本次改动的 104 项相关测试已通过。

打包自检使用临时配置和项目外的独立 EXE 副本，验证词库、字体、图标、种子和更新组件。额外检查 EXE 内 `core.installed_mod_catalog`、`ui.mods_page`、`core.version` 的代码与当前源码一致，并直接执行包内 preview 比较逻辑。

隔离的 rc.37 → rc.38 更新验证通过：正常等待旧进程退出，替换程序后内部版本正确，官方版本文件名同步更新，旧 EXE 备份校验正确，设置字节保持原样；没有启动游戏或更新实际游戏目录里的 MOD。

发布前新备份为 `/srv/data/backups/bbmod-hub-20261004T042644038729Z.tar.gz`，2,496,816,132 字节，SHA-256 为 `bb5000bacc1134f3a4d2337c7f6e07e09260ff02e0d9df0a182ef35af6516b9e`。SQLite 与 Wiki 数据库完整性均为 `ok`，128 个下载文件、1 张封面、3 个 Wiki 文件、5,101 个 Wiki 素材全部校验通过。

## 来源与证据

本次源码基于提交 `b5ad5414de55aad953b5830da034c459859d6384`。构建清单记录本次 10 个源码／版本／说明文件的逐文件 SHA-256，EXE 的嵌入代码检查对应同一份源码。rc.38 的 GitHub 源码与安装包使用版本标签 [v0.3.0-rc.38](https://github.com/Laimiu-debug/BBMOD/releases/tag/v0.3.0-rc.38)；安装包沿用官网已核验的相同文件和 SHA-256。

证据保存在 `app/build/deploy-rc38/`：`tests.json`、`tests.log`、`build-manifest.json`、`package-check.json`、`embedded-fix-check.json`、`update-install-check.json`、`backup-verified.json`、`published.json`、`public-verification.json`、`public-update-check.json`、`origin-verification.json`、`frozen-rc37-update-check.json`、`frozen-rc38-update-check.json`。

rc.36 及更新客户端可在「设置 → 检查更新」升级；更早的旧官网客户端从新官网手动下载并更换。本次公开文件和桌面更新链路已验证，实际游戏运行验收仍由玩家完成。

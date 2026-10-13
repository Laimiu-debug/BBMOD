# 本机离线测试环境补齐（2026-10-07）

用户授权补齐此前六项测试缺失的环境后，已安装项目专用的便携工具，并从本机 Steam 原版 1.5.2.3 只读提取测试输入。没有改动游戏安装、MOD、存档或系统 PATH。

| 缺项 | 原跳过测试数 | 已准备路径 |
| --- | --- | --- |
| Squirrel 离线解释器 | 3 | `app/build/full-l10n/tools/bin/sq.exe` |
| 原版脚本反编译输入 | 2 | `app/build/full-l10n/decompiled/` |
| 原版提示框 JavaScript 夹具 | 1 | `output/art-review/tooltip_module.js` |

工具为作者 [Adam Milazzo 的 Battle Brothers mod kit v9](https://www.adammil.net/blog/v133_Battle_Brothers_mod_kit.html)，包含 Squirrel 3.0.7 stable（32 位）、bbsq 和 Nutcracker。本机已有缓存与作者官网下载 ZIP 逐字节核对后复用；官方 ZIP 的 SHA-256 为 `fd442abb2d2e40a32d142e2edc8371e2babb1c19c55912af005279c6d203485d`。Python 3.13.16、Node v22.23.3 和 PySide6 6.11.2 已存在。

这六项补测后，相关六个模块为 **103 通过、0 跳过、0 失败**。随后完整回归发现另有两项测试使用旧的解释器路径 `app/build/fox-audit/tools/sq.exe`，复制同一核验过的二进制后，该模块重跑 10 项全部通过。

完整回归与必要补测合计 **61 模块、718 通过、0 跳过、0 失败**。这是完整初跑加单模块补测的汇总，没有重复声称运行了两轮完整回归。报告位于 `app/build/deploy-0.4.1/desktop-tests-final.json`，来源记录为同目录 `desktop-tests-final-provenance.json`。

## 输入核对与工具限制

- 原版 2,319 份汉化来源、94 份装备来源均匹配既有记录，无缺失或哈希差异。
- 提取 3,340 个文件，完整解密 3,109 份 CNUT；装备目录重建所需的 98／506 份反编译输入均与既有来源哈希匹配。
- Nutcracker 成功反编译 3,108 份脚本。原版 `cultist_origin_vs_old_gods_event.cnut` 含非 UTF-8 字节 `0x92`，该工具严格转换时失败；原始与解密副本均完整保留，未伪造或修改夹具。该文件的字节码结构解析通过，不影响上述测试和汉化包结构核验。
- 提示框夹具来自官方归档中的 `ui/screens/tooltip/modules/tooltip_module.js`，SHA-256 为 `12ca759d189bac3b1f5265d1100e2ffdaeec499f00faca2a58012da0036204da`。

逐项工具版本、来源 URL、文件哈希、输入一致性及限制证据位于 `app/build/review/release-20261007/environment-manifest.json` 与 `environment-nutcracker-limit.json`。工具及原版输入是本机开发依赖，不分发到桌面 EXE 或汉化 ZIP 中。

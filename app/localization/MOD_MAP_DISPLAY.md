# 普通 MOD 中文地图候选

2026-09-17：按用户确认，启用独立汉化后，Steam、游戏 EXE 和 BBMOD 均显示中文地名，不再按启动入口切换地名语言。

旧 `bbmod_launch.exe` 的 Defender 行为检测已有本机记录。本候选不运行或分发该启动器、`bbmod_han.dll`，不写入其他进程内存，不修改防护设置。旧组件的微软复核状态与本候选的验收分开记录。

## 实现

- 复用 2,196 条校对条目展开的 7,723 个地名，地图和正文使用同一份词典。
- `map_labels.nut` 经公开 Script Hooks 接入世界界面的绘制回调，读取游戏公开的标签、坐标、颜色和发现状态；`map_labels.js` 使用游戏既有 HTML 界面的 Canvas 和内置 Noto 字体绘制。
- 标签只在原生绘制调用期间临时隐藏，调用结束或抛出异常都会恢复。实体名称、标签文字、区域名称、存档字段和 RNG 均不改写。
- 原版区域文字不提供可枚举的脚本标签。本包以透明 PNG 覆盖 `cinzel_bold_100.png` 的图像资源，保留字体度量、区域对象和英文保存值，再根据区域信息显示中文。移除 ZIP 恢复原版资源。
- 第一个地图绘制回调请求 UI 初始化，避开原生 UI 在创建时缓存连接回调的时序。图层位于普通页面之下，事件遮挡时仍保留地图地名；退出世界地图清空，断开连接时移除，鼠标穿透。地图不变时复用上一帧；城市和队伍名称位于区域文字上方。
- 旧汉化包须重新生成并应用。管理器遇到依赖旧原生组件的包会明确要求更新，不调用旧启动器。
- 游戏按 Windows 桌面方式启动。Steam 可能重新启动注册目录的游戏，所以先核对 `appmanifest_365360.acf` 指向的目录，拒绝从隔离副本跳到常用安装目录。旧隔离测试入口不再用于实机启动。

## 检查与边界

215 项 Python 基础回归通过；追加启动目录保护后，相关 35 项专项检查通过。普通 MOD 检查覆盖全部 7,723 个译名、无启动标记时的中文显示、画布大小变化、连接释放、原始名称保留、未发现地点和隐藏队伍过滤，以及绘制异常后的标签恢复。Squirrel 检查使用离线原生解释器，UI 检查使用模拟桥接。

最终 ZIP 的 SHA-256 为 `1b3b0e9a6b874a097500960a2cd1cf97be9eb3d03e1645aaa47754175c633bdf`。2,281 个字节码脚本、19,329 个原函数的指令保持不变；205,339 项程序常量检查通过，其中两处原有姓名池引用转向相同顺序的原版英文池。新增地图显示逻辑由独立 MOD 脚本提供。

实机在 `E:/SteamLibrary/steamapps/common/Battle Brothers` 进行，用户授权临时切换。保存函数和自动保存函数均由专用测试包禁用。正常 EXE/BBMOD 后端和 Steam 入口均已进入游戏；新战役能生成，旧存档能读取。修正连接后抽查了中文城镇、区域名、缩放、人物界面及返回地图。所有数据文件和存档在每轮恢复后哈希一致，原汉化包也已恢复。最终 Steam 启动在着色器清单检查阶段等待约 90 秒后正常完成，没有更改 Steam 设置。

Defender 实时防护保持开启，当前签名版本 `1.459.250.0`；EXE 和最终 ZIP 的定向扫描均未发现威胁，行为记录仍只有此前旧组件的 4 条检测。该结果仅适用于这台机器和当前签名库。未恢复隔离文件、添加排除项或重新编译旧组件。

证据：`build/review/rc8-tests.xml`、`build/review/rc8-launch-directory-tests.xml`、`build/review/rc8-exe-selftest.json`、`build/mod-map-check/validation.json`、`build/mod-map-candidate/validation.json`；实机截图、日志和逐文件恢复凭据位于 `build/mod-map-candidate/live/`，最终汇总见 `build/mod-map-candidate/live/acceptance.json`。

候选包：`app/build/mod-map-candidate/mod_bbmod_zhcn.zip`，独立汉化版本 `0.3.0-rc.3`。验证命令：

```powershell
python tools/build_l10n.py --game 'E:/SteamLibrary/steamapps/common/Battle Brothers' --output build/mod-map-candidate/mod_bbmod_zhcn.zip
python tools/check_mod_map.py --package build/mod-map-candidate/mod_bbmod_zhcn.zip
python tools/verify_l10n_preview.py --package build/mod-map-candidate/mod_bbmod_zhcn.zip --output build/mod-map-candidate/structure
```

城镇和区域的全部地图布局、迷雾边缘、战斗全流程和任意第三方 MOD 组合仍需更广泛验收。本机日志另有职业属性范围、Swifter 的依赖报错，本次保留其原文件。区域显示依赖 UI 桥接，失败时区域文字可能不可见；作为测试版交付，尚不声明所有游戏路径稳定。

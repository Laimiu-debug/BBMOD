# 发布约定

桌面版本与成品命名必须遵守 `docs/versioning.md`。版本唯一来源为
`core/version.py`；使用 `tools/build_desktop.py` 打包，不根据日期或构建次数自动改号，
不覆盖同版本的不同发布文件。桌面、独立汉化与网站分别维护版本。

官网发布前必须读取 `docs/publishing-backups.md`：默认不做完整备份，
不重复备份历史桌面 EXE，不默认调用 `backup_hub`。常规发布仅保存必要的
数据库一致快照、发布记录和校验信息，验收后清理本次临时传输大文件。

已按用户要求删除的四个历史测试文件不恢复。缺陷修复使用现有测试或聚焦的新回归，
Qt 测试通过 `tools/run_desktop_tests.py` 逐模块独立进程运行。

# Wiki 中文译文

本目录保存 BBMOD 独立编写、逐句审校的 Wiki 译文，以及在核对完整原句和上下文后复用的 BBMOD 自有游戏汉化。未使用其他第三方汉化包的译文或脚本。

原文来自 [Battle Brothers Wiki](https://battlebrothers.fandom.com/wiki/Battle_Brothers_Wiki)。中文改编与原文正文遵循 [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/)；网站每篇文章保留来源、修订版本和贡献历史入口。图片及其他媒体的权利信息另行记录，正文许可不自动适用于媒体。

## 格式与维护

- `titles.json`：条目名称与分类名称。
- `translation-scope.json`：按原站分类及确切页面版本，列出保留英文的官方历史日志。游戏攻略、玩家战报不在此例外中。
- 其他 JSON：完整文本块的译文、审校状态、原句哈希及适用页面修订号。不同页面可拥有不同译法，但重叠页面范围不得冲突。
- `{#n}…{/#n}` 和 `{#n/}` 保留原文内联节点，包括链接、强调、图片、公式及换行。不可手工改变节点目标或数量。
- 图片代码异常仅限经过核对的重复转义图片，并保留实际图片节点；不能借此跳过英文段落。

修改后运行 `wiki_translation_units.py validate`、网站测试及完整 Wiki 构建。抽查中文、中英对照、英文原文的电脑与手机排版，并检查长表格、公式、事件目录、图片和跨页锚点。详见 [`../../docs/wiki-migration.md`](../../docs/wiki-migration.md)。

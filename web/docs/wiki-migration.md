# 战场兄弟百科迁移

## 范围与来源

入口 `/wiki/`，覆盖 Battle Brothers Wiki 主命名空间的全部游戏正文及重定向，配套分类、模板、文件说明和可获取的 Wiki 图片。保留原站 Wikitext、页面 ID、修订 ID、抓取时间、来源链接及历史入口。分类没有自建页面时，按原站分类成员关系生成目录。视频保留来源链接；源站自身无法提供的文件明确标记，不伪造文件副本。

论坛、聊天、账户及用户页不在百科正文许可和迁移范围内。外部参考资料保持引用链接；原站不存在的词条不会编造内容。原站的过时提示、缺失引用提示和 DLC 条件保留。

正文与排版、名称对照改编按 CC BY-SA 3.0 提供；每页保留源词条、原文版本和贡献历史链接。来源：

- https://battlebrothers.fandom.com/api.php?action=query&meta=siteinfo&siprop=statistics%7Crightsinfo&format=json
- https://www.fandom.com/licensing
- https://support.fandom.com/hc/en-us/articles/360026387674-Where-can-I-find-database-dumps

图片元数据与正文许可分开记录。`source_unstated` 表示原站没有明确的媒体许可声明，不能表述为已获得 CC 授权。保留原文件链接、上传者、原图 SHA-1、CDN 返回文件 SHA-256 和发布副本 SHA-256。Fandom CDN 可能将 PNG/JPEG 转成相同尺寸的 WebP；这种情况下核对图像类型和尺寸并明确记录 `cdn_representation`，不声称取得了哈希相同的原始二进制。SVG 剔除活动内容、外链和外部 DTD；位图进行解码校验。

## 名称与语言

原文与中文名称分开保存。`app/localization/full_catalog.json` 的 `reviewed` 游戏名称参与精确对照；保留词库哈希和适用游戏版本。百科栏目名称是界面导航用语，不宣称是游戏内名称。没有可靠对照的名称保留英文。`双语名称` 与 `英文原文` 是阅读模式，当前没有把整篇英文正文标为中文译文。

后续全文翻译应以页面 ID 和原文修订号另存，不覆盖 `source_text`。同步只更新原文快照和审核过的名称，不覆盖外部维护的译文成果。

## 获取与构建

在项目根目录，用独立的本地输出目录保存原始素材，不提交生成数据到 Git：

```powershell
web/.venv/Scripts/python.exe -m pip install -r web/requirements-wiki.txt
web/.venv/Scripts/python.exe web/tools/fetch_wiki.py --output output/wiki-source/YYYYMMDD
web/.venv/Scripts/python.exe web/tools/fetch_wiki_media.py --source output/wiki-source/YYYYMMDD
web/.venv/Scripts/python.exe web/tools/build_wiki.py --source output/wiki-source/YYYYMMDD --destination web/var/wiki
```

抓取采用明确的 User-Agent、请求节流、`maxlag`、有界响应、重试及断点续传。失败状态存于 `fetch-status.json`、`media-index.json`；重跑仅补齐相应修订或媒体。更新清单可加 `--refresh-inventory`。图片下载限于 Wiki 自己的 HTTPS 媒体仓库，拒绝跳转至其他主机。

源快照与网站发布数据分开：原始响应包含展开后的 HTML、Wikitext 和页面引用；网站数据保留 HTML 白名单清洗结果和检索索引，绝不执行源站 JavaScript。表格的合并单元格、MathML、脚注和锚点保留；只对独立行表格启用排序。

`build_wiki.py --allow-incomplete` 仅用于检查尚未抓取完整的数据，不允许同时激活。发布命令拒绝存在缺失正文、缺失正文配图或下载错误的快照；报告单独列出外链视频、原站无法提供的文件和未明确的媒体使用条件。

## 发布与回退

由应用的 `BBMOD_WIKI_ROOT` 指定持久化目录，默认是 `BBMOD_DATA_DIR/wiki`。结构：

```text
wiki/
  current.json
  previous.json
  assets/<sha256>.<extension>
  releases/<snapshot>/
    wiki.sqlite3
    styles.css
    report.json
    manifest.json
```

将新的快照和它引用的图片上传到这些目录，执行：

```text
python manage.py publish_wiki <snapshot> --check-only
python manage.py publish_wiki <snapshot>
```

命令验证快照哈希、数据库完整性、来源版本完整性和全部图片哈希，然后原子切换 `current.json`。上一版快照及图片保留；回退时将上一版本传给同一命令。读请求使用只读不可变数据库连接。网站原有账号、MOD、种子、建议和访客数据库不因百科导入发生结构变化。

`backup_hub` 现在同时保存当前百科快照、指针和其引用的图片。恢复时将归档里的 `wiki/` 放回配置的百科持久目录，再运行 `publish_wiki --check-only`；不要用旧社区数据库覆盖上线后产生的建议或访客数据。原始抓取缓存需另行归档，网站备份保留每页 Wikitext 和来源信息。

## 验收

- 比对来源清单与保存的修订数量，主命名空间正文与重定向分别计数。
- 全文和中英文名称搜索、分页、分类成员、重定向目标及锚点、英文阅读模式。
- 中文名称遵循已校对词库；未校对名称不伪装为完整汉化。
- 检查缺图、源站缺失词条、原站解析警告及独立图片许可信息；报告保留真实状态。
- HTML/CSS/URL 清洗、只读快照路径、匿名权限、私有管理报告、旧站回归检查。
- 实际浏览器查看装备长表、背景、事件和手机宽度；断开原站访问后，已迁移正文和配图仍从 BBMOD 读取。

公开只读接口：`/api/v1/wiki/search/?q=...`、`/api/v1/wiki/pages/<page_id>/`，为后续桌面百科提供版本化数据。红装悬停鉴定、桌面反馈及更新器不是这次网站迁移的实现范围。

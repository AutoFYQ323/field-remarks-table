# Field Remarks Table

A complementary attribute table for QGIS 3.28 through 4.99 (Qt 5 and Qt 6).

This plugin does **not** replace the built-in QGIS Attribute Table (F6).
It adds field-remark packs, batch editing, field mapping, a multi-start line-direction check, and a settings dialog.

## Install from plugins.qgis.org

1. In QGIS, open **Plugins → Manage and Install Plugins…**
2. Search for **Field Remarks Table**
3. Install and enable the plugin

## How to open

Select a vector layer, then:

- click the toolbar button, or
- **Vector → Field Remarks Table**, or
- right-click the layer in the Layers panel

If no vector layer is selected, the plugin asks you to pick one.

## What it adds

- **Field-remark packs** — alias names, hover notes, and insert meanings, stored per named pack and shared across projects
- **Pack variables** — `{{title}}` placeholders resolved when inserting values
- **Batch fill** — constant, sequence around text, add text, expression, and replace (one box: Standard, Around the match, or Whole field, then a constant or an expression)
- **Paste by feature id** — copy a filtered column, edit it outside, paste back by `#fid`
- **CSV export**, field manager, and unique-value statistics
- **Settings** — toolbar order, per-tool shortcuts, and parameters
- **Field mapping copy** — a project layer, a file, or the Copy Features clipboard (WKT/WKB, GeoJSON)
- **Line direction check** — every filtered point on the start layer is a start at once; the nearest start sets each line's direction. This is direction, not topology. Branches at a junction are not errors. An end cuts a loop only when it sits on a junction. Lines whose direction still cannot be decided are drawn on a visible temporary layer.
- **Saved expressions** — a list icon next to ε adds, edits, notes, reorders, and deletes them. The settings button stays the gear. After a short pause, typing matches saved expressions; the arrow on the right lists them all. Double-click selects all the text, and dragging selects part of it. An item shows as «note» expression; only the part after » runs, so an edit in the box does not change the saved item.

## Interface language and theme

- **Language:** 中文, English, Español, Français, العربية, Deutsch, 日本語, 한국어. The language menu and the About text use each language's own spelling. The first launch follows the QGIS locale, then the system locale. A matching language is used as-is. Any other non-empty locale uses English. If both locales are empty, Chinese is used. The choice is remembered. Arabic lays out plugin buttons and titles from right to left. Values in the attribute table stay left to right. Layer names, field values, and text the user wrote are not translated.
- **Theme:** Default (native QGIS), Sakura pink, or Mint fresh. The main attribute table, field remarks, field mapping, and line direction windows follow the same theme when you change it from the toolbar.

## Toolbar

Default order matches common editing workflows. You can reorder or hide buttons in **Settings**. **Field mapping** and **Line direction** sit on the toolbar.

Edits go through the layer edit buffer. Use the plugin Save / Rollback buttons, or QGIS layer save.

## Requirements

- QGIS 3.28 through 4.99 (Qt 5 and Qt 6)
- No extra Python packages
- Windows, Linux, and macOS

Metadata and this README are English. The plugin UI follows the language chosen above.

## Differences from the built-in attribute table

| Built-in table | This plugin |
| --- | --- |
| Default F6 / layer “Open Attribute Table” | Separate toolbar, Vector menu, and layer context menu |
| Field aliases live on the layer | Remark packs are reusable configurations across projects |
| Standard editors | Batch fill, paste-by-fid, field mapping, line direction |

## License

GNU GPL v2 or later. See `LICENSE`.

## Source, releases, and QGIS plugin upload

- Homepage: https://yuyouhui.online/tools/qgis/field-remarks-table/
- Chinese page: https://yuyouhui.online/tools/qgis/字段备注表/
- **Source (GitHub):** https://github.com/AutoFYQ323/field-remarks-table
- Issues: https://github.com/AutoFYQ323/field-remarks-table/issues

**GitHub** holds the source code. Pushing a new commit updates that repository; the URL does not change.

**plugins.qgis.org** does not pull automatically from GitHub. For each release you still:

1. From the plugin folder, run `python _make_release_zip.py`. It checks Chinese, English, Spanish, French, Arabic, German, Japanese, and Korean, including the five help pages, then writes `../TEST/attribute_table-<version>.zip`. The archive root is `attribute_table/` with `metadata.txt` inside. Do not zip the folder by hand in Explorer: that skips the language check.
2. Upload that zip on the plugin page at plugins.qgis.org (or update the version there as required). New `tr()` strings must be filled in every language before this script will write the zip.

## Version 1.18.11 (high level)

- About lists each UI language in its own spelling
- Line direction detects direction, not topology. Branches at a junction are not errors. An end cuts a loop only when exactly one end sits on a junction. If there is no end layer, a loop has no end, a loop has several ends, or an end sits in the middle of a line, those lines are written to a visible temporary layer and are not treated as correct
- Settings → Parameters: column-header mode and default fill method (including Remember last). Those two lists open wide enough to show the full text and every row
- Saved expressions: a list icon next to ε. Typing pauses, then matches saved items; the arrow lists them all; double-click selects all; dragging selects part of the text. The display form is «note» expression, and an edit in the box does not change the saved item
- Field manager: Field remarks button removed

## Version 1.18.10 (high level)

- Same product text as 1.18.9. The release package no longer ships `.flake8`, so the QGIS plugin repository does not mark the scan as developer-configured.
- Qt 6 enum names are fully qualified. QGIS 3.28 through 4.99.

## Version 1.18.7 (high level)

- Spanish, French, and Arabic, in addition to Simplified Chinese and English
- First launch follows the QGIS locale, then the system locale; the choice is remembered
- The language menu and worded toolbar icons use the current language only
- Arabic lays out plugin buttons and titles from right to left; attribute values stay left to right
- Help has the same five pages in all five languages
- Scheme option text, the sample preview grid, and per-issue line-direction messages stay in Chinese

## Version 1.18.6 (high level)

- Field remarks help expanded: display versus write, packs, enable and matching, variables, value map, quick insert
- Help is split into five pages
- Fill modes are constant, sequence around text, add text, expression, and replace
- Plugin windows that are already open follow the Chinese / English switch

## Version 1.18.5 (high level)

- Flake8: remove duplicate `localize_button_box` in `i18n/runtime.py` (marketplace quality scan)

## Version 1.18.4 (high level)

- plugins.qgis.org Bandit scan: `# nosec` on intentional except pass/continue and line-direction jitter (`random.random()`)

## Version 1.18.3 (high level)

- Security scan: removed shipped `.bandit`; intentional guards use `# nosec` where needed
- CN/EN UI with remembered language; dialog buttons follow plugin language
- Filter value list: click to open, value counts
- Toolbar order, hide buttons, language placement, new tools with icons
- Field remarks: merged pack / import-export actions; copy pack with orphan drop
- Full field mapping and free-start line direction tools, themed like other plugin windows

---

# 字段备注表（原名：属性表 Plus）

面向矢量图层的增强属性表，**不替换** QGIS 自带属性表（F6）。

入口：主工具栏、**矢量 → Field Remarks Table**、图层右键。

主要功能：字段备注项目包、项目变量、批量赋值与替换、设置与快捷键、字段映射（含剪贴板）、多起点线方向检查、CSV 导出。界面可选简体中文、英文、西班牙文、法文、阿拉伯文、德文、日文、韩文。首次安装先看 QGIS 语言，再看系统语言；对不上且语言不是空的就用英文。阿拉伯文的按钮和标题从右向左，表格里的属性值仍从左向右。

源码：https://github.com/AutoFYQ323/field-remarks-table  

**本地开发交付**（中文细则见仓库根目录 `README.md`）：每轮改完须自检（脚本在 `../TEST/`）→ 在 `../临时/` 留序号备份 → 覆盖到本机  
`%AppData%\Roaming\QGIS\QGIS3\profiles\default\python\plugins\attribute_table` → **重启 QGIS** 试用。  
上架：在插件目录运行 `python _make_release_zip.py`，写出 **`../TEST/attribute_table-<version>.zip`**。仓库根目录勿散落 zip/py。

## 1.18.11

- 关于里的界面语言改成各自的写法。
- 线方向判的是方向，不是拓扑。分叉不算错误。终点只在成环、并且正好一个终点落在接头上时把环断开。没配终点、环上没有终点、环上多个终点，或终点落在线中间，这些线会画到临时图层上，不会被当成方向正确。
- 设置 → 参数：列标题显示、编辑模式赋值方式默认（含记住上次）。这两个下拉一次展开全部选项。
- 常用表达式在 ε 右边用列表图标管理，设置按钮仍是齿轮。打字停一下会匹配，右边箭头列出全部，双击全选，按住拖动可选中一段。显示为「«备注» 表达式」，框里改字不改已保存的那条。
- 字段管理里去掉「字段备注」按钮。

## 1.18.7

- 界面增加西班牙文、法文、阿拉伯文。首次按 QGIS 语言，没有再看系统语言，之后记住选择。
- 语言菜单和带字的工具栏图标只用当前这一种语言。阿拉伯文的按钮和标题从右向左，属性值仍从左向右。
- 帮助五页五种语言都有。
- 线方向的方案说明、模拟预览格子、逐条检测原文和结果图层名仍是中文。

## 1.18.6

- 帮助分成五页：属性表、字段备注、快速命名、字段映射、线方向。字段备注一页写了显示和写入、启用与匹配、变量、值映射、快速插入。
- 赋值保留：常量、前后序号、前后加字、表达式、替换。
- 已经打开的插件窗口，切换中文或英文后立刻更换界面文字。

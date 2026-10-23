# Field Remarks Table

A complementary attribute table for QGIS 3.34 or later.

This plugin does **not** replace the built-in QGIS Attribute Table (F6).
It adds field-remark packs, batch editing, quick naming from symbology, KMZ export, and several editing tools.

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
- **Quick naming** — write values back from categorized / rule-based symbology
- **Batch fill** — constant, sequence around text, add text, expression, find/replace
- **Paste by feature id** — copy a filtered column, edit it outside, paste back by `#fid`
- **KMZ / CSV export** — KMZ can follow single / categorized / graduated colors
- **Field manager** and unique-value statistics
- **Field mapping copy** — full layer-to-layer transfer with saved mapping, file load, fuzzy match, and type coercion (settings under `AttributeTablePlus/field_map.json`)
- **Line direction check** — pick one start point and one or more line layers, filter by category, walk the network, flip reversed lines (tolerance stored under `AttributeTablePlus/line_dir_tolerance`)

## Interface language and theme

- **Language:** Simplified Chinese, English, Spanish, French, or Arabic. The language menu and the worded toolbar icons use that language only. The first launch follows the QGIS locale, then the system locale. `zh`, `es`, `fr`, `ar`, and `en` select that language. Any other locale, such as German, selects English. If both locales are empty, Chinese is used. The choice is remembered. Arabic lays out plugin buttons and titles from right to left. Values in the attribute table stay left to right. Layer names, field values, and text the user wrote are not translated.
- **Theme:** Default (native QGIS), Sakura pink, or Mint fresh. The main attribute table, field remarks, field mapping, and line direction windows follow the same theme when you change it from the toolbar.

## Toolbar

Default order matches common editing workflows. You can reorder or hide buttons (except the customize control). The language button sits immediately left of **Toolbar order**. **Field mapping** and **Line direction** sit after KMZ export.

Edits go through the layer edit buffer. Use the plugin Save / Rollback buttons, or QGIS layer save.

## Requirements

- QGIS 3.34 or later
- No extra Python packages
- Windows, Linux, and macOS

Metadata and this README are English. The plugin UI follows the language chosen above.

## Differences from the built-in attribute table

| Built-in table | This plugin |
| --- | --- |
| Default F6 / layer “Open Attribute Table” | Separate toolbar, Vector menu, and layer context menu |
| Field aliases live on the layer | Remark packs are reusable configurations across projects |
| Standard editors | Batch fill, paste-by-fid, quick naming, KMZ export, field mapping, line direction |

## License

GNU GPL v2 or later. See `LICENSE`.

## Source, releases, and QGIS plugin upload

- Homepage: https://yuyouhui.online/tools/qgis/field-remarks-table/
- Chinese page: https://yuyouhui.online/tools/qgis/字段备注表/
- **Source (GitHub):** https://github.com/AutoFYQ323/field-remarks-table
- Issues: https://github.com/AutoFYQ323/field-remarks-table/issues

**GitHub** holds the source code. Pushing a new commit updates that repository; the URL does not change.

**plugins.qgis.org** does not pull automatically from GitHub. For each release you still:

1. From the plugin folder, run `python _make_release_zip.py`. It checks Chinese, English, Spanish, French, and Arabic, including the five help pages, then writes `attribute_table-<version>.zip` beside the plugin folder. The archive root is `attribute_table/` with `metadata.txt` inside. Do not zip the folder by hand in Explorer: that skips the language check.
2. Upload that zip on the plugin page at plugins.qgis.org (or update the version there as required). New `tr()` strings must be filled in every language before this script will write the zip.

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

主要功能：字段备注项目包、项目变量、从符号化快速命名、批量赋值、按要素编号回贴、KMZ/CSV 导出、字段映射复制、线方向检查。界面可选简体中文、英文、西班牙文、法文或阿拉伯文。语言菜单和带字的工具栏图标都只用当前这一种语言。阿拉伯文的按钮和标题从右向左，表格里的属性值仍从左向右。樱花粉/薄荷清新主题对主窗口、字段备注、映射与线方向窗口生效。

源码：https://github.com/AutoFYQ323/field-remarks-table  
上架 QGIS 插件库不会随 GitHub 自动更新。在插件目录运行 `python _make_release_zip.py`：先检查五种语言有没有漏句，通过后才写出 zip。不要在资源管理器里把文件夹直接压成 zip。

## 1.18.7

- 界面增加西班牙文、法文、阿拉伯文。首次按 QGIS 语言，没有再看系统语言，之后记住选择。
- 语言菜单和带字的工具栏图标只用当前这一种语言。阿拉伯文的按钮和标题从右向左，属性值仍从左向右。
- 帮助五页五种语言都有。
- 线方向的方案说明、模拟预览格子、逐条检测原文和结果图层名仍是中文。

## 1.18.6

- 帮助分成五页：属性表、字段备注、快速命名、字段映射、线方向。字段备注一页写了显示和写入、启用与匹配、变量、值映射、快速插入。
- 赋值保留：常量、前后序号、前后加字、表达式、替换。
- 已经打开的插件窗口，切换中文或英文后立刻更换界面文字。

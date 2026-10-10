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
- **Batch fill** — constants, padded sequences, expressions, find/replace
- **Paste by feature id** — copy a filtered column, edit it outside, paste back by `#fid`
- **KMZ / CSV export** — KMZ can follow single / categorized / graduated colors
- **Field manager** and unique-value statistics
- **Field mapping copy** — full layer-to-layer transfer with saved mapping, file load, fuzzy match, and type coercion (settings under `AttributeTablePlus/field_map.json`)
- **Line direction check** — pick one start point and one or more line layers, filter by category, walk the network, flip reversed lines (tolerance stored under `AttributeTablePlus/line_dir_tolerance`)

## Interface language and theme

- **Language:** Simplified Chinese or English. The first launch follows the QGIS locale, then the system locale; the choice is remembered. Toolbar language control shows **CN** / **EN**.
- **Theme:** Default (native QGIS), Sakura pink, or Mint fresh. The main attribute table, field remarks, field mapping, and line direction windows follow the same theme when you change it from the toolbar.

## Toolbar

Default order matches common editing workflows. You can reorder or hide buttons (except the customize control). The language button sits immediately left of **Toolbar order**. **Field mapping** and **Line direction** sit after KMZ export.

Edits go through the layer edit buffer. Use the plugin Save / Rollback buttons, or QGIS layer save.

## Requirements

- QGIS 3.34 or later
- No extra Python packages
- Windows, Linux, and macOS

Metadata and this README are English; the plugin UI is Chinese or English as chosen above.

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

1. Zip the plugin folder so the archive root is `attribute_table/` with `metadata.txt` inside (no `__pycache__`, no `.git`).
2. Upload the zip on the plugin page at plugins.qgis.org (or update the version there as required).

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

主要功能：字段备注项目包、项目变量、从符号化快速命名、批量赋值、按要素编号回贴、KMZ/CSV 导出、字段映射复制、线方向检查。界面可选简体中文或英文；樱花粉/薄荷清新主题对主窗口、字段备注、映射与线方向窗口生效。

源码：https://github.com/AutoFYQ323/field-remarks-table  
上架 QGIS 插件库仍需本地打 zip 后在 plugins.qgis.org 上传，不会随 GitHub 自动更新。

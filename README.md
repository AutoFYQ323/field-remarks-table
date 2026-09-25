# Field Remarks Table

A complementary attribute table for QGIS 3.34 or later.

This plugin does **not** replace the built-in QGIS Attribute Table (F6).
It adds field-remark packs, batch editing, quick naming from symbology, and KMZ export.

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

Edits go through the layer edit buffer. Use the plugin Save / Rollback buttons, or QGIS layer save.

## Requirements

- QGIS 3.34 or later
- No extra Python packages
- Windows, Linux, and macOS

The current user interface is Simplified Chinese. Metadata and this README are English.

## Differences from the built-in attribute table

| Built-in table | This plugin |
| --- | --- |
| Default F6 / layer “Open Attribute Table” | Separate toolbar, Vector menu, and layer context menu |
| Field aliases live on the layer | Remark packs are reusable configurations across projects |
| Standard editors | Batch fill, paste-by-fid, quick naming, KMZ export |

## License

GNU GPL v2 or later. See `LICENSE`.

## Source and issues

- Homepage: https://yuyouhui.online/tools/qgis/field-remarks-table/
- Chinese page: https://yuyouhui.online/tools/qgis/字段备注表/
- Source: https://github.com/AutoFYQ323/field-remarks-table
- Issues: https://github.com/AutoFYQ323/field-remarks-table/issues

---

# 字段备注表（原名：属性表 Plus）

面向矢量图层的增强属性表，**不替换** QGIS 自带属性表（F6）。

入口：主工具栏、**矢量 → Field Remarks Table**、图层右键。

主要功能：字段备注项目包、项目变量、从符号化快速命名、批量赋值、按要素编号回贴、KMZ/CSV 导出。

当前界面为简体中文。上架说明与插件管理器摘要为英文。

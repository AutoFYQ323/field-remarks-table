# -*- coding: utf-8 -*-
"""Chinese msgid -> English translations. tr() falls back to msgid."""

LANG_ZH = "zh"
LANG_EN = "en"

_EN = {
    # language / common
    "语言": "Language",
    "中文": "Chinese",
    "英文": "English",
    "确定": "OK",
    "取消": "Cancel",
    "是": "Yes",
    "否": "No",
    "关闭": "Close",
    "全部": "All",
    "保存": "Save",
    "回滚": "Rollback",
    "刷新": "Refresh",
    "帮助": "Help",
    "启用": "Enable",
    "关闭备注": "Disable",
    "添加": "Add",
    "删除": "Delete",
    "导入": "Import",
    "导出": "Export",
    "预览": "Preview",
    "变量": "Variables",
    # toolbar
    "切换编辑": "Toggle editing",
    "复制选中要素": "Copy selected features",
    "剪切选中要素": "Cut selected features",
    "粘贴要素": "Paste features",
    "删除选中要素": "Delete selected features",
    "字段管理": "Field manager",
    "字段备注": "Field remarks",
    "值/注显示": "Value / note display",
    "快速命名": "Quick naming",
    "缩放到选中": "Zoom to selected",
    "全选（当前筛选）": "Select all (filtered)",
    "反选（当前筛选）": "Invert selection (filtered)",
    "取消选择": "Clear selection",
    "列宽模式": "Column width mode",
    "导出 CSV": "Export CSV",
    "导出 KMZ": "Export KMZ",
    "界面风格": "UI theme",
    "工具栏顺序": "Toolbar order",
    "语言切换": "Language",
    "字段映射复制": "Field mapping copy",
    "线方向检查": "Line direction check",
    "工具栏显示快速命名": "Show Quick naming on toolbar",
    "拖拽调整顺序（分隔线也可拖动）。确定后本地保存：":
        "Drag to reorder (separators too). Saved locally on OK:",
    "插入分隔线": "Insert separator",
    "恢复默认": "Reset default",
    "—— 分隔线 ——": "— Separator —",
    "隐藏": "Hide",
    "显示": "Show",
    "勾选隐藏的按钮将不出现在工具栏（顺序仍保留）。":
        "Checked buttons stay hidden from the toolbar (order is kept).",
    # themes
    "默认（QGIS 原生）": "Default (native QGIS)",
    "樱花粉": "Sakura pink",
    "薄荷清新": "Mint fresh",
    "界面风格：%s": "UI theme: %s",
    # filter / scope
    "钉": "Pin",
    "范围": "Scope",
    "搜索": "Search",
    "筛选": "Filter",
    "冻结": "Freeze",
    "全部要素": "All features",
    "已选中": "Selected",
    "地图可见要素": "Visible on map",
    "编辑修改": "Edited",
    "输入即过滤…": "Type to filter…",
    "分类筛选": "Category filter",
    "（无字段）": "(no fields)",
    "（空）": "(blank)",
    "仅列出前 %d 个值": "Showing first %d values only",
    "已选 %d 项": "%d selected",
    "全部（不额外筛选）": "All (no extra filter)",
    "按分类筛选，或选一个字段按取值筛选":
        "Filter by category, or pick a field and filter by values",
    "把指定字段固定到左侧不随滚动移出":
        "Pin the chosen field to the left while scrolling",
    # remarks hub
    "当前项目：": "Current pack:",
    "新建项目": "New pack",
    "删除项目": "Delete pack",
    "修改名称": "Rename",
    "预览配置": "Preview config",
    "项目管理": "Pack manager",
    "导入导出": "Import / Export",
    "变量配置": "Variables",
    "图层管理": "Layer settings",
    "字段（末项为图层名，仅悬停用）：":
        "Fields (last item is the layer name, hover only):",
    "中文名：": "Display name:",
    "表头第一行显示，如 Type → 类型":
        "Header label, e.g. Type → Type label",
    "悬停说明（多行，只显示，不赋值）：":
        "Hover notes (multi-line, display only, not written):",
    "悬停时显示在中文名下面，不写入字段、不进插入下拉":
        "Shown under the display name on hover; not written to the field",
    "含义说明（双击一行改说明；值映射项后面的「原」不变，不能删除）：":
        "Meanings (double-click to edit; value-map「原」rows stay, cannot delete):",
    "中文，如 盒子": "Label, e.g. Box",
    "常量": "Const",
    "写入值，如 FAT；可插入变量": "Value to write, e.g. FAT; variables allowed",
    "插入变量": "Insert variable",
    "常量写入固定值；QGIS 则右边粘贴表达式，赋值时按要素计算":
        "Const writes a fixed value; QGIS uses an expression evaluated per feature",
    "把当前项目的变量插进写入值，如 {{城市}}123":
        "Insert a pack variable into the write value, e.g. {{city}}123",
    "恢复默认": "Restore default",
    "删除选中": "Delete selected",
    "把选中的值映射项说明恢复成 QGIS 当前描述":
        "Restore the selected value-map note to the current QGIS description",
    "项目名称：": "Pack name:",
    "未命名": "Untitled",
    "开始匹配": "Start matching",
    "返回重新选择": "Back to reselect",
    "复制为新项目": "Copy as new pack",
    "匹配图层和字段": "Match layers and fields",
    "图层对不上": "Layers do not match",
    "字段对不上": "Fields do not match",
    "名字相同的已自动对应。下面只列出对不上的项。选「删除」才会丢掉这一份配置。":
        "Same names are matched automatically. Only mismatches are listed. Choose Delete to drop that config.",
    "对不上的图层": "Unmatched layers",
    "请选择…": "Choose…",
    "删除该图层配置": "Delete this layer config",
    "请先选择一个矢量图层。": "Please select a vector layer first.",
    "无图层": "No layer",
    "导出范围：": "Export scope:",
    "图层全部要素（默认）": "All layer features (default)",
    "仅当前表格显示的要素": "Only features shown in the table",
    "按 QGIS 属性表格式（首列 wkt_geom / 经纬度 + 图层原始字段顺序）":
        "QGIS attribute-table format (wkt_geom / lat-lon + original field order)",
    "文本型纯数字（含小数）按数字导出":
        "Export numeric-looking text fields as numbers",
    "只决定属性表工具栏要不要多一个「快速命名」图标。快速命名是独立功能，与字段备注启用无关。":
        "Only controls whether Quick naming appears on the toolbar. It is independent of field remarks.",
    "重新读取配置文件。另一边 QGIS 改完后，点这里，或点一下本窗口，即可看到，不用重启。":
        "Reload the shared config file. After edits in another QGIS, click here or this window.",
    "启用/关闭备注显示。默认关闭。":
        "Toggle remark display. Off by default.",
    "给当前项目配置变量（标题给人看，内容才是写入值）。跟项目包走，导入导出一起带走。":
        "Configure pack variables (title for people, value is what gets written). Travels with import/export.",
    "导入备注项目（一份 JSON 可含多个项目）。同名时选择覆盖或换名。":
        "Import remark packs (one JSON may hold many). On name clash choose overwrite or rename.",
    "勾选要导出的项目。单项目文件名：属性表Plus(项目名).json":
        "Pick packs to export. Single-pack file: FieldRemarks(name).json",
    "只读查看当前项目已配置的图层、字段和含义。":
        "Read-only view of layers, fields and meanings in the current pack.",
    "选择：新建 / 删除 / 重命名当前备注项目":
        "Choose: new / delete / rename the current remark pack",
    "选择：导入或导出备注项目":
        "Choose: import or export remark packs",
    "将复制当前项目为新项目。对不上的图层/字段配置会被丢弃：":
        "This copies the current pack to a new pack. Unmatched layer/field config will be discarded:",
    "新项目名称：": "New pack name:",
    "复制后进入匹配": "Copy then match",
    "不复制，直接匹配": "Match without copying",
}

# Longer / parameterized messages kept as templates with % formatting.
_EN.update(
    {
        "项目「%s」有 %s 个图层对不上：%s\n若选错了项目可返回重选。":
            "Pack \"%s\" has %s unmatched layer(s): %s\n"
            "If you picked the wrong pack, go back and reselect.",
        "「%s」是占位名称，请换一个名字。":
            "\"%s\" is a placeholder name. Please choose another.",
        "「%s」是占位项目，不能删除。":
            "\"%s\" is a placeholder pack and cannot be deleted.",
        "确定删除项目「%s」？": "Delete pack \"%s\"?",
        "图层「%s」→": "Layer \"%s\" →",
    }
)


def available_languages():
    return (
        (LANG_ZH, "中文"),
        (LANG_EN, "English"),
    )


def detect_initial_language(qgis_locale=None, system_locale=None):
    """Prefer QGIS locale, then system. Default zh for zh*; else en."""
    for raw in (qgis_locale, system_locale):
        text = str(raw or "").strip().lower().replace("_", "-")
        if not text:
            continue
        if text.startswith("zh"):
            return LANG_ZH
        return LANG_EN
    return LANG_ZH


def tr(msgid, *args, **kwargs):
    from .runtime import translate

    return translate(msgid, *args, **kwargs)

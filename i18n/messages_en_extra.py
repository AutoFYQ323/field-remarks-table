# -*- coding: utf-8 -*-
"""English strings added after the main catalog. Keys are Simplified Chinese."""

EXTRA = {
    "地图范围无法换算到图层坐标系，「地图可见」没有结果":
        "The map extent cannot be transformed into the layer CRS, so Visible on map is empty.",
    "无数据": "No data",
    "无重名": "No duplicates",
    "有重名(%d组/%d条)": "Duplicates (%d groups / %d rows)",
    "未点中字段列，请对准列标题右键": "That was not a field header. Right-click a column title.",
    "该列已隐藏，请在可见列标题上右键": "This column is hidden. Right-click a visible header.",
    "复制本列（可回贴）": "Copy column (round-trip)",
    "粘贴回本列": "Paste back into this column",
    "表格里没有行": "The table has no rows",
    "「%s」在当前表格行里没有重复值": "\"%s\" has no duplicate values in the current rows",
    "「%s」在当前表格行里没有空值": "\"%s\" has no blank values in the current rows",
    "该字段不在「筛选」的字段列表里": "This field is not in the Filter field list",
    "「筛选」下拉只列出前 %d 个值，有 %d 个勾选值没能加入":
        "The Filter list only shows the first %d values, so %d checked values were left out",
    "已按 %d 个值筛选": "Filtered by %d values",
    "行号范围（当前共 %d 行，按表格显示顺序）：\n例如 10-50、1-20,35,80-  （80- 表示到末行）":
        "Row range (%d rows, table order):\nExamples: 10-50, 1-20,35,80-  (80- means through the last row)",
    "已复制列「%s」共 %s 行（两列：编号和值，可改值后粘贴回本列）":
        "Copied column \"%s\", %s rows (two columns: id and value; edit values, then paste back)",
    "已按编号写回 %s 行 → %s": "Wrote %s rows back by id → %s",
    "编号已对齐，字段「%s」的值没有变化": "Ids matched, but \"%s\" values did not change",
    "已保存": "Saved",
    "帮助 — 字段备注表 %s": "Help — Field Remarks Table %s",
    "已选插入值：选弹出项立即写入，或点取消后用赋值条按钮写入":
        "Insert value: pick a popup item to write now, or Cancel and use the fill bar",
    "快速插入：表达式未能写入任何行": "Quick insert: the expression wrote no rows",
    "\n\n没有可写入的值。": "\n\nThere is no value to write.",
    "赋值完成：已更新 %s 行 → %s ← %s": "Fill done: updated %s rows → %s ← %s",
    "已填空白 %s 行，跳过已有内容 %s 行 → %s":
        "Filled %s blank rows, skipped %s rows that already had a value → %s",
    "赋值完成：已更新 0 行 → %s": "Fill done: updated 0 rows → %s",
    "空白单元格的值没有变化 → %s": "Blank cells did not change → %s",
    "前后序号完成：已在原文字%s加上序号，更新 %s 行 → %s":
        "Sequence done: numbered %s the existing text, updated %s rows → %s",
    "前后加字完成：已更新 %s 行，空白未改 %s 行 → %s":
        "Text added: updated %s rows, left %s blank rows unchanged → %s",
    "已有文字没有变化 → %s": "Existing text did not change → %s",
    "编辑·未保存（已改 %s 条）": "Editing, unsaved (%s changed)",
    "编辑·未保存": "Editing, unsaved",
    "编辑中": "Editing",
    "只读": "Read-only",
    "点": "Point",
    "线": "Line",
    "面": "Polygon",
    "排序": "Sort",
    "%s  |  共 %s  |  显示 %s  |  选中 %s  |  %s":
        "%s  |  Total %s  |  Shown %s  |  Selected %s  |  %s",
    "范围是「仅选中」": "Scope is Selected only",
    "范围是「地图可见」": "Scope is Visible on map",
    "范围是「仅已修改」": "Scope is Edited only",
    "过滤「%s」": "Filter \"%s\"",
    "没有匹配的行": "No matching rows",
    "没有匹配的行：%s，可清除或把范围切回「全部要素」":
        "No matching rows: %s. Clear it, or set the scope back to All features",
    "选中合计 %s个 / 总和 %s": "Selection count %s / sum %s",
    "选中重名 %s": "Selection duplicates %s",
    "%s合计 筛选 %s / 全部 %s": "%s sum  filtered %s / all %s",
    "%s重名 筛选 %s / 全部 %s": "%s duplicates  filtered %s / all %s",
    "请先选择单元格": "Select a cell first",
    "已复制 %s 个单元格到剪贴板": "Copied %s cells to the clipboard",
    "请先选中要素（选择单元格会同步选中对应行）":
        "Select features first (selecting a cell also selects its row)",
    "请先选中要剪切的要素": "Select the features to cut first",
    "剪贴板是「编号 + 值」两列 → 按编号粘贴回列":
        "Clipboard is id + value → pasted back into the column by id",
    "剪贴板不是可回贴格式 → 已按 QGIS 要素粘贴（新增要素）":
        "Clipboard is not round-trip format → pasted as QGIS features (new features)",
    "字段管理 — ": "Field manager — ",
    "重命名字段": "Rename field",
    "（未启用，只读）": " (disabled, read-only)",
    "项目名称：": "Pack name:",
    "无法读取该文件。": "Cannot read this file.",
    "默认（不可修改）": "Default (locked)",
    "（%s）": " (%s)",
    "源图层或目标图层未选择。": "Source or target layer is not selected.",
    "几何类型不兼容：源={}，目标={}。": "Geometry types are incompatible: source={}, target={}.",
    "源图层没有选中的要素。": "The source layer has no selected features.",
    "源图层没有可复制的要素。": "The source layer has no features to copy.",
    "无法开启目标图层编辑模式，请检查图层是否只读。":
        "Cannot start editing on the target layer. Check whether it is read-only.",
    "没有有效几何的要素可复制（可能全部被跳过）。":
        "No features with valid geometry to copy (they may all have been skipped).",
    "写入目标图层失败，已回滚。": "Writing to the target layer failed. Changes were rolled back.",
    "复制完成：{} 条写入「{}」，跳过 {} 条。":
        "Copy finished: {} features written to \"{}\", {} skipped.",
    "矢量文件 (*.kml *.kmz *.shp *.gpkg *.geojson *.json *.gpx *.dxf *.tab);;KML/KMZ (*.kml *.kmz);;GeoPackage (*.gpkg);;Shapefile (*.shp);;GeoJSON (*.geojson *.json);;所有文件 (*.*)":
        "Vector files (*.kml *.kmz *.shp *.gpkg *.geojson *.json *.gpx *.dxf *.tab);;KML/KMZ (*.kml *.kmz);;GeoPackage (*.gpkg);;Shapefile (*.shp);;GeoJSON (*.geojson *.json);;All files (*.*)",
    "图层 {}": "Layer {}",
    "文件不存在：{}": "File not found: {}",
    "无法读取图层「{}」。已尝试 KMZ/KML 直接打开、/vsizip 和解压。最后尝试：{}":
        "Cannot read layer \"{}\". Tried opening KMZ/KML directly, /vsizip, and unzipping. Last attempt: {}",
    "（不映射）": "(do not map)",
    "选择子图层": "Choose a sublayer",
    "文件包含多个图层，请选择要加载的图层：": "This file has several layers. Choose one to load:",
    "请选择一个子图层。": "Choose a sublayer.",
    "图层选择": "Layers",
    "从文件加载…": "Load from file…",
    "未匹配源字段：": "Unmatched source fields:",
    "模糊匹配": "Fuzzy match",
    "用于「按名称自动匹配」：去掉空格/下划线后仍唯一，或一方名称包含另一方且只能唯一配对时才自动填入。":
        "Used by Match by name: a pair is filled only when it is still unique after removing spaces/underscores, or when one name contains the other and the pair is unique.",
    "隐藏已匹配源字段": "Hide matched source fields",
    "开启时：已经配给某一目标字段的源字段，不再出现在其它行的下拉里。关闭后可把同一源字段配给多个目标字段，重复项会标红。":
        "On: a source field already used by one target is hidden from the other rows. Off: the same source can map to several targets, and repeats are shown in red.",
    "按名称自动匹配": "Match by name",
    "清空映射": "Clear mapping",
    "刷新图层列表": "Refresh layer list",
    "目标类型": "Target type",
    "目标别名": "Target alias",
    "复制选项": "Copy options",
    "仅复制源图层中选中的要素": "Copy only selected features from the source",
    "坐标系不同时自动重投影到目标图层": "Reproject to the target CRS when they differ",
    "源字段「{}」已被 {} 个目标字段使用": "Source field \"{}\" is used by {} target fields",
    "未匹配源字段：请先选择源图层": "Unmatched source fields: choose a source layer first",
    "未匹配源字段：无": "Unmatched source fields: none",
    "未匹配源字段（{}）：{}": "Unmatched source fields ({}): {}",
    "重复使用源字段（{}）：{}": "Source fields used more than once ({}): {}",
    "已保存当前图层选择和字段映射。": "Saved the current layer choice and field mapping.",
    "保存失败：{}": "Save failed: {}",
    "选择矢量文件": "Choose a vector file",
    "无法读取该文件或未包含矢量图层。\nKMZ 已尝试直接打开、读取压缩包内 KML，以及解压后再读。\n请确认文件能被 QGIS「数据源管理器」打开。":
        "Cannot read this file, or it has no vector layer.\nFor KMZ, opening it directly, reading the KML inside, and unzipping were all tried.\nCheck that QGIS Data Source Manager can open it.",
    "已加载图层：{}": "Loaded layer: {}",
    "请先选择源图层和目标图层。": "Choose a source layer and a target layer first.",
    "源图层与目标图层不能相同。": "Source and target must not be the same layer.",
    "源与目标几何类型不同，仍要继续吗？": "Source and target geometry types differ. Continue anyway?",
    "未配置字段映射，将只复制几何。是否继续？": "No field mapping is set, so only geometry will be copied. Continue?",
    "成功复制 {} 条要素到「{}」。": "Copied {} features to \"{}\".",
    "\n跳过 {} 条。": "\nSkipped {}.",
    "\n\n请记得在目标图层上保存编辑。": "\n\nRemember to save edits on the target layer.",
    "复制失败：\n": "Copy failed:\n",
    "找不到图层：{}": "Layer not found: {}",
    "有多个同名图层「{}」，请在图层配置里重新选一次再保存。":
        "There are several layers named \"{}\". Pick the layer again in the layer setup and save.",
    "图层 {} 的分类筛选有 {} 类对不上当前符号（已按分类名称兜底匹配），建议重新筛选。":
        "Layer {} has {} categories that no longer match the current symbols (matched by name as a fallback). Filter again.",
    "找不到字段：{}（图层 {}）": "Field not found: {} (layer {})",
    "筛选分类 — {}": "Filter categories — {}",
    "只勾选要使用的分类。未勾选的要素不参与。分类来自图层符号化（分类/规则），括号内是要素数量。":
        "Check only the categories to use. Unchecked features are skipped. Categories come from the layer symbology (categorized/rule-based). Counts are in parentheses.",
    "字段": "Field",
    "(可选)": "(optional)",
    "增加": "Add",
    "图层": "Layer",
    "分类": "Category",
    "图层不存在: %s": "Layer not found: %s",
    "无": "None",
    "空": "Blank",
    "{}类": "{} classes",
    "按分类筛选，未勾选的要素不参与": "Filter by category. Unchecked features are skipped.",
    "图层配置": "Layer setup",
    "光交": "Cabinet",
    "字段(不用)": "Field (unused)",
    "只选光交图层。当前功能不读、不写这个字段。":
        "Choose the cabinet point layer only. This tool does not read or write this field.",
    "接头": "Splice",
    "CODE读写字段": "CODE read/write field",
    "读写。接头命名：写入 CODE。分纤盒命名、光缆命名：读取 CODE。":
        "Read/write. Splice naming writes CODE. FAT naming and cable naming read CODE.",
    "分纤盒": "FAT",
    "户数读写字段": "Household read/write field",
    "读写。分纤盒赋值：写入户数。光缆赋值、接头/分纤盒命名：读取户数。":
        "Read/write. FAT fill writes households. Cable fill and splice/FAT naming read households.",
    "读写。分纤盒命名：写入 CODE。光缆命名：读取 CODE。":
        "Read/write. FAT naming writes CODE. Cable naming reads CODE.",
    "用户点": "User point",
    "户数读取字段": "Household read field",
    "读取。皮线赋值从这里读用户户数。分纤盒赋值用它核对总户数，不按用户点累加。":
        "Read. Drop-cable fill reads user households here. FAT fill uses it to check the total, not by summing user points.",
    "光缆": "Cable",
    "户数写入字段": "Household write field",
    "CODE写入字段": "CODE write field",
    "写入。光缆赋值把分纤盒户数写到这里。主干/配线按两端点判定。":
        "Write. Cable fill writes FAT households here. Feeder/distribution is decided from the two ends.",
    "写入。光缆命名把生成的 CODE 写到这里。": "Write. Cable naming writes the generated CODE here.",
    "主干和配线用同一图层。光交–接头、接头–接头是主干；接头–分纤盒、分纤盒–分纤盒是配线。":
        "Feeder and distribution share one layer. Cabinet–splice and splice–splice are feeder; splice–FAT and FAT–FAT are distribution.",
    "皮线": "Drop cable",
    "读写。皮线赋值：写入户数。分纤盒赋值：读取户数。":
        "Read/write. Drop-cable fill writes households. FAT fill reads households.",
    "皮线赋值把用户点户数写到这里。分纤盒赋值再把这里的户数加到所出的分纤盒。":
        "Drop-cable fill writes user households here. FAT fill then adds those households onto the FAT they leave.",
    "参数配置": "Parameters",
    "吸附按米计算。图层会先转到局部米制，工程默认 4326 或其它坐标系都可以。":
        "Snap is in meters. Layers are transformed to a local meter CRS first. Project CRS 4326 or any other CRS is fine.",
    " 米": " m",
    "吸附容差": "Snap tolerance",
    "顺时针": "Clockwise",
    "逆时针": "Counterclockwise",
    "方向排序": "Direction order",
    "起始角度": "Start angle",
    "吸附与排序": "Snap and order",
    "方案": "Scheme",
    "接头 CODE 前缀": "Splice CODE prefix",
    "分纤盒 CODE 前缀": "FAT CODE prefix",
    "光缆 CODE 前缀": "Cable CODE prefix",
    "接头前缀用于接头 CODE。分纤盒前缀用于分纤盒 CODE。光缆前缀用于主干/配线 CODE。":
        "The splice prefix is for splice CODE. The FAT prefix is for FAT CODE. The cable prefix is for feeder/distribution CODE.",
    "导出…": "Export…",
    "导入…": "Import…",
    "{} 无法进入编辑": "{} cannot start editing",
    "NTAL 线方向修复": "Line direction repair",
    "{} #{} 找不到要素": "{} #{} feature not found",
    "{} #{} 无法翻转": "{} #{} cannot be reversed",
    "{} #{} 改几何失败": "{} #{} geometry change failed",
    "{} 修复异常：{}": "{} repair error: {}",
    "正在检查…": "Checking…",
    "NTAL 全面检测": "Full network check",
    "请在图层配置里选择光交。方向从光交往外走。":
        "Choose a cabinet layer in the layer setup. Direction is traced outward from the cabinet.",
    "请至少配置光缆或皮线其中一类。": "Configure at least cable or drop cable.",
    "吸附容差必须大于 0。": "Snap tolerance must be greater than 0.",
    "正在读取点": "Reading points",
    "正在读取线": "Reading lines",
    "正在检查线端": "Checking line ends",
    "起点同时靠近多个点：{}": "The start is within tolerance of several points: {}",
    "终点同时靠近多个点：{}": "The end is within tolerance of several points: {}",
    "线两端接到同一点：{}": "Both ends snap to the same point: {}",
    "一端空：{}": "One end is empty: {}",
    "从光交往外走，数字化起点应在上游。":
        "Tracing outward from the cabinet, the digitized start should be upstream.",
    "容差 {} 米。": "Tolerance {} m.",
    "  正向  {}  {} → {}": "  forward  {}  {} → {}",
    "数字化方向反了（终点在上游）：{}  上游 {}  下游 {}":
        "Digitized direction is reversed (end is upstream): {}  upstream {}  downstream {}",
    "。多段线会整条一起倒转。": " Multipart lines are reversed as a whole.",
    "  反了  {}": "  reversed  {}",
    "两端都空，无法判断方向：{}": "Both ends are empty, so direction cannot be judged: {}",
    "未从光交通到，不判断方向：{}": "Not reached from a cabinet, so direction is not judged: {}",
    "一端空，无法判断方向：{}": "One end is empty, so direction cannot be judged: {}",
    "光交没有出线：{}": "Cabinet has no outgoing cable: {}",
    "正在检查网络结构": "Checking network structure",
    "方向反了 {} 条：数字化终点在上游。可用「全部翻转」，或在表里勾选后「翻转勾选」。":
        "{} lines are reversed: the digitized end is upstream. Use Reverse all, or check rows and use Reverse checked.",
    "修复只改线的顶点顺序，不改属性；写入编辑缓冲，需要你自己保存图层。":
        "Repair only reverses vertex order. Attributes stay. It writes the edit buffer; save the layer yourself.",
    "一端空/两端空 {} 处：建议先用「线显示」看端点，或把吸附容差改大一点。":
        "{} places have one or both ends empty. Show the line ends, or increase the snap tolerance.",
    "未从光交通到 {} 条：可能断在接头/分纤盒，或图层没配齐。通不到的线程序不会翻。":
        "{} lines were not reached from a cabinet. The break may be at a splice/FAT, or a layer is missing. Unreached lines are not reversed.",
    "端点歧义 {} 处：容差内有多个点，先错开点或改小容差，否则方向不可靠。":
        "{} ambiguous ends: several points are inside the tolerance. Separate them or lower the tolerance, or the direction is unreliable.",
    "自环 {} 处：线两端接到同一点，不会自动翻。":
        "{} self-loops: both ends snap to the same point and are not reversed.",
    "结构硬错误 {} 处：成环、分叉、多进线或光交被当成下游。只报告，不翻转。":
        "{} hard structure errors: loops, branches, extra incoming lines, or a cabinet treated as downstream. Reported only, not reversed.",
    "修完再用「线显示」看：圆点（起点）应更靠近光交一侧。":
        "After repair, the start dot should sit closer to the cabinet side.",
    "从光交通到的线方向都正确。": "Every line reached from a cabinet already points the right way.",
    "检查了线 {} 条（光缆 {}，其中主干 {}、配线 {}，皮线 {}）。":
        "Checked {} lines (cable {}, of which feeder {}, distribution {}, drop {}).",
    "从光交通到 {} 条，方向正确 {} 条，方向反了 {} 条。":
        "Reached {} from a cabinet: {} correct, {} reversed.",
    "  {}：正向 {}，反了 {}。": "  {}: forward {}, reversed {}.",
    "风险：硬错误 {}，软错误 {}，警告 {}（含方向反了）。":
        "Risk: hard {}, soft {}, warnings {} (including reversed direction).",
    "结构硬错误 {} 处（成环、分叉、多进线、光交被当成下游），不参与翻转。":
        "{} hard structure errors (loops, branches, extra incoming lines, cabinet treated as downstream) are not reversed.",
    "建议：": "Suggestion:",
    "不挡地图，窗口置顶。打勾的翻转，不打勾的不动。方向反了默认打勾，伪成环默认不勾。":
        "This window stays on top and does not block the map. Checked lines are reversed; unchecked lines stay. Reversed lines start checked. False loops start unchecked.",
    "不挡地图，窗口置顶。检查页是这次的硬错误、软错误和警告；可修复页是方向反了的线。全部翻转=这些线一次翻；翻转勾选=只翻表里打勾的。":
        "This window stays on top and does not block the map. The Check page lists hard errors, soft errors, and warnings. The Repairable page lists reversed lines. Reverse all flips those lines at once. Reverse checked flips only the checked rows.",
    "不挡地图，窗口置顶。全部翻转=所有方向反了的线；翻转勾选=只翻表里打勾的。":
        "This window stays on top and does not block the map. Reverse all flips every reversed line. Reverse checked flips only the checked rows.",
    "类型": "Type",
    "名称": "Name",
    "说明": "Note",
    "检查": "Check",
    "明细": "Detail",
    "可修复": "Repairable",
    "全部翻转": "Reverse all",
    "不管表格勾选，把检查到的全部「方向反了」的线一次翻转。":
        "Reverse every line found reversed, whether or not its row is checked.",
    "翻转勾选": "Reverse checked",
    "只翻转打勾的线。方向反了默认打勾，伪成环默认不勾。":
        "Reverse only checked lines. Reversed lines start checked. False loops start unchecked.",
    "只翻转「可修复」表里打勾的线，可先对照地图去掉不确定的。":
        "Reverse only the checked rows on the Repairable page. Uncheck anything you are not sure about on the map first.",
    "<b>全面检测</b>　含线方向　容差 {} 米<br>":
        "<b>Full check</b>  including line direction  tolerance {} m<br>",
    '<span style="color:#c62828; font-weight:700;">配置</span>':
        '<span style="color:#c62828; font-weight:700;">Setup</span>',
    '<br><span style="color:#c62828; font-weight:700;">硬错误：{}</span>':
        '<br><span style="color:#c62828; font-weight:700;">Hard errors: {}</span>',
    "<div>（无）</div>": "<div>(none)</div>",
    '<span style="color:#ef6c00; font-weight:700;">软错误：{}</span>':
        '<span style="color:#ef6c00; font-weight:700;">Soft errors: {}</span>',
    "<div>… 还有 {} 条</div>": "<div>… {} more</div>",
    '<span style="color:#f9a825; font-weight:700;">警告：{}</span>':
        '<span style="color:#f9a825; font-weight:700;">Warnings: {}</span>',
    "<b>图层参与</b>（走到 / 筛出）": "<b>Layers used</b> (reached / filtered)",
    "问题点在图层组「全面检测」里，下面分「硬错误」「软错误」「警告」。关掉本窗后图层还在，双击「可修复」表可缩放到对应点。":
        "Issue points are in the Full check layer group, split into hard errors, soft errors, and warnings. They stay after this window closes. Double-click a Repairable row to zoom to it.",
    "问题点已写入图层组「拓扑检查结果」。默认只显示「线方向反了」，其余图层在该组里，需要时再勾选。":
        "Issue points were written to the Topology check group. Only reversed lines are visible at first. The other layers are in that group if you need them.",
    "已生成临时图层：": "Temporary layers created:",
    "\n已翻转 {} 条线到编辑缓冲。请保存图层。":
        "\nReversed {} lines into the edit buffer. Save the layer.",
    "将翻转全部 {} 条「方向反了」的线，不看勾选。\n只改顶点顺序，写入编辑缓冲，不保存。\n一端空、未挂上、歧义的线不会动。\n继续？":
        "Reverse all {} lines marked reversed, ignoring the checkboxes.\nOnly vertex order changes, into the edit buffer, without saving.\nLines with an empty end, unattached, or ambiguous ends stay.\nContinue?",
    "没有打勾的线。": "No lines are checked.",
    "将翻转勾选的 {} 条线。\n只改顶点顺序，写入编辑缓冲，不保存。\n继续？":
        "Reverse the {} checked lines.\nOnly vertex order changes, into the edit buffer, without saving.\nContinue?",
    "NTAL 线方向": "Line direction",
    "配置不完整": "Setup is incomplete",
    "正在生成临时图层": "Creating temporary layers",
    "{} 段{}": "{} parts{}",
    "请选择点图层。": "Choose a point layer.",
    "请至少增加一个线图层。": "Add at least one line layer.",
    "请在列表里点一个起点。": "Click one start point in the list.",
    "吸附容差必须大于 0。请先在参数配置里设置。":
        "Snap tolerance must be greater than 0. Set it above before starting.",
    "正在读取起点": "Reading the start point",
    "筛选后的点里没有这个起点。": "That start point is not in the filtered points.",
    "线图层筛选后没有可用的线。": "The line layers have no usable lines after filtering.",
    "正在连接端点": "Connecting endpoints",
    "起点容差 {} 米内没有线的端点。缝更大的地方不会跨过去。":
        "No line endpoint is within {} m of the start. Wider gaps are not crossed.",
    "正在沿起点往外走": "Walking outward from the start",
    "从所选起点往外走。线的两端在容差内才算接到同一个点，缝更大就停下。":
        "Walk outward from the chosen start. Two ends count as the same point only when they are within the tolerance. A wider gap stops the walk.",
    "容差 {} 米。起点 {}。": "Tolerance {} m. Start {}.",
    "两端接到同一点：{}": "Both ends meet at the same point: {}",
    "  自环  {}": "  self-loop  {}",
    "伪成环：这条线两边的接头，不靠它也能从起点走到，方向定不下来，不翻转：{}":
        "False loop: both sides can still be reached from the start without this line, so its direction is not reversed: {}",
    "  伪成环  {}": "  false loop  {}",
    "未从起点走到（中间断开，不跨缝）：{}":
        "Not reached from the start (the chain is broken; gaps are not crossed): {}",
    "  未走到  {}": "  not reached  {}",
    "  正向  {}": "  forward  {}",
    "数字化方向反了（终点在上游）：{}":
        "Digitized direction is reversed (the end is upstream): {}",
    "。多段线要各段都反了才整条翻转。":
        " A multipart line is reversed only when every part is reversed.",
    "多段线没有全部走到或各段方向不一致，不整条翻转：{}":
        "Not every part was reached, or the parts disagree, so the whole line is not reversed: {}",
    "数字化方向反了：{}": "Digitized direction is reversed: {}",
    "方向反了 {} 条：可修复里默认打勾，用「翻转勾选」。伪成环也在表里，默认不勾。":
        "{} lines are reversed and start checked on Repairable. Use Reverse checked. False loops are listed too, and start unchecked.",
    "端点距离大于容差就停下，不会把断开的下一段接上。":
        "The walk stops when the gap is larger than the tolerance. It does not jump to the next piece.",
    "自环 {} 处：线两端落在同一个点上，不翻转。":
        "{} self-loops: both ends land on the same point and are not reversed.",
    "伪成环 {} 段：可修复里默认不勾。要翻就打勾。":
        "{} false-loop parts start unchecked on Repairable. Check them if you want them reversed.",
    "未走到 {} 段：和起点这条链中间断开了，这些段不翻。":
        "{} parts were not reached: the chain from the start is broken, so those parts are not reversed.",
    "从起点走到的线方向都正确。": "Every line reached from the start already points the right way.",
    "起点 {}。线 {} 段（要素按段走，多段线各段分开接）。":
        "Start {}. {} line parts (each part is walked on its own; multipart lines are split).",
    "走到 {} 段，方向正确 {} 段，方向反了 {} 条要素，伪成环 {} 段。":
        "Reached {} parts: {} correct, {} features reversed, {} false-loop parts.",
    "风险：硬错误 {}，软错误 {}（含方向反了）。":
        "Risk: hard {}, soft {} (including reversed direction).",
    "分叉会每条都走。断口大于容差 {} 米就停。":
        "Every branch is walked. A gap larger than {} m stops the walk.",
    "起点{}": "Start {}",
    " 段": " parts",
    "起点只用一个点。线在左，终点在右，都可以加多条并各自筛选分类。终点可以不选。走到终点就停。不选终点时，拿掉某条线后若有一头从起点走不到，就不叫伪成环。":
        "Use one start point. Lines are on the left and ends are on the right. You can add several of each and filter each one. Ends are optional. The walk stops at an end. With no ends, a line is not a false loop if removing it leaves one side unreachable from the start.",
    "端点按容差链式合并：A 靠近 B、B 靠近 C 时，三个端点算同一个点，即使 A 和 C 相距超过容差。端点很密的地方要留意。":
        "Endpoints are chained by tolerance: if A is near B and B is near C, all three are one point, even when A and C are farther apart than the tolerance. Be careful where endpoints are dense.",
    "吸附容差（米）": "Snap tolerance (m)",
    "起点图层": "Start layer",
    "按分类筛选。图例未勾选的分类也会列出来，勾上即可参与。":
        "Filter by category. Categories that are off in the legend are still listed. Check them to include them.",
    "可增加多个线图层。每条线各自按分类筛选。":
        "You can add several line layers. Each one has its own category filter.",
    "终点": "End",
    "可选。可增加多个终点图层，每条各自筛选分类。走到终点就停。":
        "Optional. You can add several end layers, each with its own category filter. The walk stops at an end.",
    "起点（筛选后的点，点一个）": "Start (filtered points, pick one)",
    "搜索名称或 FID": "Search name or FID",
    "开始": "Start",
    "通用线方向": "Line direction",
    "请先选择图层。": "Choose a layer first.",
    "请选择点图层，并至少增加一个线图层。": "Choose a point layer and add at least one line layer.",
    "起点{} {}": "Start {} {}",
    "终点{} {}": "End {} {}",
    "通用线方向_起点终点": "Line direction start and end",
    "无法开始": "Cannot start",
    "未知": "Unknown",
    "全部": "All",
    "仅点": "Points only",
    "仅线": "Lines only",
    "仅面": "Polygons only",
    "目标字段": "Target field",
    "源字段": "Source field",
    "源图层": "Source layer",
    "目标图层": "Target layer",
    "字段映射复制": "Field mapping copy",
    "线方向检查": "Line direction check",
    "剪贴板是空的。": "The clipboard is empty.",
    "无法读取剪贴板：%s": "Cannot read the clipboard: %s",
    "剪贴板不是可回贴格式。请用列标题「复制本列（可回贴）」，第一列必须是编号（表头以 #fid 开头），第二列才是要改的值。":
        "The clipboard is not in paste-back format. Use Copy column (round-trip) on the column header. Column 1 must be the id (header starts with #fid), and column 2 is the value to change.",
    "没有可写回的数据行。": "There are no data rows to write back.",
    "值列是空的，没有写入，表格里的原数据不会被清掉。请同时复制编号列和有内容的值列，不要只复制空列。":
        "The value column is empty, so nothing was written and existing values were kept. Copy the id column together with a value column that has content.",
    "除了编号和值之外还有别的内容，没有写入，避免贴错列。":
        "There is more than the id and value columns, so nothing was written.",
    "字段「%s」这一列是空的，没有写入，避免把原数据清掉。请复制编号列和这一列。":
        "The column for \"%s\" is empty, so nothing was written. Copy the id column and this column.",
    "表头缺少字段名。第一列是编号，第二列的表头应是字段名。":
        "The header has no field name. Column 1 is the id. Column 2's header should be the field name.",
    "第 %s 行编号无效：%s": "Row %s has an invalid id: %s",
    "编号 %s 重复（第 %s 行）": "Id %s is repeated (row %s)",
    "\n…共 %s 处问题": "\n… %s problems in total",
    "没有写入。请改好后再贴：\n%s%s": "Nothing was written. Fix these and paste again:\n%s%s",
    "请输入行号，例如 10-50 或 1-20,35": "Enter row numbers, for example 10-50 or 1-20,35",
    "看不懂「%s」，请写成 10-50 这样的形式": "Cannot read \"%s\". Use a form like 10-50",
    "行号超出范围（当前共 %d 行）": "Row numbers are out of range (%d rows now)",
    "值": "Value",
    "含义": "Meaning",
    "条数": "Count",
    "占比": "Share",
    "当前项目还没有图层配置。": "This pack has no layer setup yet.",
    "当前项目还没有图层配置和变量。": "This pack has no layer setup or variables yet.",
    "悬停说明：%s": "Hover note: %s",
    "（无字段配置）": "(no field setup)",
    "（无含义）": "(no meanings)",
    "确定删除项目「%s」？": "Delete pack \"%s\"?",
    "0°正北，90°正东，180°正南，270°正西。按出线第一段，不是线末端。方向和起始角只给光交 ODF：第一段主干一样长时才用来打破平局。接头分叉比该方向全部户数和到下一接头的主干长度，不用角度。分纤盒链路比户数和到首盒的线长，也不用角度。赋值和命名方案在「方案」页，六个功能各自一份。":
        "0° is north, 90° east, 180° south, 270° west. The angle uses the first segment, not the far end. Direction and start angle apply only to cabinet ODF ties. Splice branches compare households and feeder length, not angle. FAT chains compare households and length to the first FAT, not angle. Fill and naming schemes are on the Scheme page, one per tool.",
    "导出当前全部图层配置和参数（含分类筛选、字段、容差、各功能方案、前缀、城市/PM）。导入是全覆盖：立刻替换现有配置并保存，点取消也不会还原。":
        "Exports every layer setup and parameter (category filters, fields, tolerance, schemes, prefixes, city/PM). Import replaces everything immediately and saves it. Cancel does not restore the previous setup.",
    "组网骨架不变：光交 → 主干 → 接头 → 配线 → 分纤盒 → 入户。这里只改每个功能怎么写编号。六个功能各自独立，互不影响。以后加方案：在 ntal_scheme.py 的 ACTION_SCHEMES 对应功能下追加一行即可。":
        "The network shape stays cabinet → feeder → splice → distribution → FAT → user. This page only changes how each tool writes codes. The six tools are independent. To add a scheme, append a row under that tool in ACTION_SCHEMES in ntal_scheme.py.",
    "按下面每一类单独勾选。默认全部检查。反选会把当前勾选反过来。检测完会留下结果窗：硬错误、软错误、警告写在「检查」页，方向反了的线在「可修复」页，可以翻转。地图图层在「全面检测」组里，硬错误、软错误、警告分开。":
        "Check each class on its own. Everything is checked by default. Invert flips the current checks. The result window keeps hard errors, soft errors, and warnings on Check, and reversed lines on Repairable so you can flip them. Map layers go in the Full check group, split the same way.",
    "第四段：光交出线按第一段主干短的号小，一样长再比角度。第一个接头 01-01。没分叉第五段一直 01，第六段按走过的顺序。分叉时户数多的接着当前第五段，少的新开第五段，第六段接最大号后面。":
        "Part 4: cabinet exits get a smaller number when the first feeder segment is shorter; equal length then uses angle. The first splice is 01-01. Without a branch, part 5 stays 01 and part 6 follows the walk order. At a branch, the side with more households keeps the current part 5, the smaller side opens a new part 5, and part 6 continues after the highest number.",
    "同一 ODF 的配线放在一起排。第五段从该 ODF 接头第五段最大值 +1 起，户数多的号小，相同则到首盒线长更长的号小。每条链第六段从 01 起，离接头近的是 01。不跟接头共用第五段。":
        "Distribution cables of the same ODF are numbered together. Part 5 starts at that ODF splice's highest part 5 plus 1. More households get the smaller number; if equal, the longer line to the first FAT gets the smaller number. Each chain's part 6 starts at 01, and the piece nearer the splice is 01. It does not share part 5 with the splice.",
    "没有图层": "No layer",
    "图层没有符号化": "The layer has no symbology",
    "无法复制符号化": "Cannot copy the symbology",
    "无法调用 QGIS 保存": "Cannot call QGIS save",
    "找不到 QGIS 自带的保存编辑": "Cannot find QGIS Save Layer Edits",
    "请选择一个矢量图层": "Select a vector layer",
    "该分类没有可反推的字段值": "This class has no field value to write",
    "请先在地图或属性表中选中要素": "Select features on the map or in the attribute table first",
    "规则里的字段在当前图层上不存在": "A field in the rule does not exist on this layer",
    "没有分类图层": "No categorized layer",
    "请先选中要复制的图层要素": "Select features to copy first",
    "几何类型不同，无法复制进分类图层（点/线/面须同类）":
        "Geometry types differ, so features cannot be copied into the categorized layer. Points, lines, and polygons must match.",
    "请先在来源图层选中要素": "Select features on the source layer first",
    "规则里的字段在分类图层上不存在": "A field in the rule does not exist on the categorized layer",
    "图层无法保存": "The layer cannot be saved",
    "无法切到要保存的图层": "Cannot switch to the layer that should be saved",
    "当前图层没有符号化": "The current layer has no symbology",
    "当前是渐变符号化，无法反推成确定字段值":
        "This is a graduated renderer, so it cannot be turned into fixed field values",
    "当前符号化不是分类/规则（%s），没有可点选的分类":
        "The renderer is not categorized or rule-based (%s), so there is no class to click",
    "无法开始编辑该图层": "Cannot start editing this layer",
    "无法开始编辑分类图层": "Cannot start editing the categorized layer",
    "没有可复制的几何": "There is no geometry to copy",
    "无法复制符号化：%s": "Cannot copy the symbology: %s",
    "其它值 / 空类，无法反推赋值": "Other values / empty class. Nothing to write.",
    "表达式分类无法反推字段值": "An expression class cannot be turned into a field value",
    "ELSE（其余）规则，无法反推赋值": "The ELSE rule cannot be turned into a field value",
    "字段「%s」存不下值「%s」（%s）": "Field \"%s\" cannot store \"%s\" (%s)",
    "读取分类失败：%s": "Cannot read classes: %s",
    "来源图层和分类图层的坐标系无法转换，没有复制":
        "The source and categorized layers cannot be transformed. Nothing was copied.",
    "坐标系转换失败，没有复制：%s": "Coordinate transform failed. Nothing was copied: %s",
    "写入失败": "Write failed",
    "ELSE（其余）": "ELSE (other)",
    "要素 %s 的几何无法转成分类图层的几何类型":
        "Feature %s geometry cannot be converted to the categorized layer geometry type",
    "复制要素失败": "Copying the feature failed",
    "要素 %s 坐标转换失败，没有复制": "Feature %s could not be transformed. Nothing was copied.",
    "常量：直接填 1 或文字；也可输入字段名引用其内容\n前后序号：在已有文字前面或后面加上序号（只选一边），原文字保留，序号用位数补零\n前后加字：在已有文字前或后追加，空白不动\n表达式：QGIS 表达式\n替换：对目标字段做部分文字替换（一格多处全部替换）":
        "Constant: type 1 or text, or a field name to copy that field\nSequence around text: add the number before or after existing text (one side). The original text stays, and the number can be padded\nAdd text: append before or after existing text. Blanks stay blank\nExpression: a QGIS expression\nReplace: replace part of the text (every match in a cell)",
    "赋值：": "Fill:",
    "位数": "Width",
    "加在": "Place",
    "替换前": "Find",
    "替换后": "Replace",
    "选中": "selected",
    "（空白）→ %s": "(blank) → %s",
    "将用字段「%s」的内容写入「%s」共 %s 条（%s）记录，继续？":
        "Write field \"%s\" into \"%s\" for %s %s rows. Continue?",
    "将向字段「%s」写入 %s 条（%s）记录，继续？":
        "Into field \"%s\", write %s %s rows. Continue?",
    "赋值完成：已更新 %s 行 → %s": "Fill done: updated %s rows → %s",
    "请先切换到编辑模式": "Switch to edit mode first",
    "当前数据源不支持字段重命名": "This data source cannot rename fields",
    "当前数据源不支持添加字段": "This data source cannot add fields",
    "字段管理 — %s": "Fields — %s",
    "%s　　原 %s": "%s    was %s",
    "无法核对当前配置。": "Cannot check the current setup.",
    "已选中 %s 个要素。\n将归属到分类「%s」。\n写入：%s\n继续？":
        "%s features are selected.\nThey will be assigned to class \"%s\".\nWrite: %s\nContinue?",
    "将把 %s 个要素从「%s」复制到「%s」，并归属分类「%s」。\n来源图层不改。写入：%s\n继续？":
        "Copy %s features from \"%s\" to \"%s\" and assign class \"%s\".\nThe source layer stays unchanged. Write: %s\nContinue?",
    "变量": "Variables",
    "「默认（不可修改）」为占位项目，请新建或选择一套配置。":
        "Default (locked) is a placeholder pack. Create or choose a pack.",
    "当前工程没有矢量图层，无法核对配置。":
        "This project has no vector layers, so the setup cannot be checked.",
    "配置的图层、字段全部有效。": "Every configured layer and field matches.",
    " 等%s项": " and %s more",
    "图层对不上：%s": "Layers do not match: %s",
    "字段对不上：%s": "Fields do not match: %s",
    "值：%s": "Value: %s",
    "未选": "None",
    "修": "Fix",
    "、": ", ",
    "；": "; ",
    "未知": "Unknown",
    "方向反了": "Reversed",
    "线": "Line",
    "起点": "Start",
    "光交": "Cabinet",
    "接头": "Splice",
    "分纤盒": "FAT",
    "主干": "Feeder",
    "配线": "Distribution",
    "光缆": "Cable",
    "皮线": "Drop cable",
    "用户": "User",
}

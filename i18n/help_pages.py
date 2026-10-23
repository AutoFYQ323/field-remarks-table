# -*- coding: utf-8 -*-
"""Help pages. Chinese source and English pages stay in the same order."""

PAGES_ZH = (
    (
        "属性表",
        """
<h3>功能介绍</h3>
<p>这是 QGIS 自带属性表旁边的一张表，不替换 F6，也不占用 F6 的快捷键。
用来看和改矢量图层的属性：排序、筛选、冻结列、批量赋值、按要素编号粘贴、导出。
字段备注、快速命名、字段映射、线方向各自有一页。</p>
<h3>使用说明</h3>
<ul>
<li><b>打开</b>：工具栏按钮、菜单「矢量 → Field Remarks Table」，或图层右键。先在图例里选中矢量图层。</li>
<li><b>语言</b>：工具栏上的语言按钮。第一次打开跟着 QGIS 语言，其次是系统语言，之后记住你的选择。可选中文、英文、西班牙文、法文、阿拉伯文。切换后，已经打开的本插件窗口立刻换成对应语言。阿拉伯语下，本插件窗口的按钮和标题从右向左，表格里的属性值仍从左向右。</li>
<li><b>双击左侧序号</b>：选中该要素并缩放到地图。</li>
<li><b>单击列标题</b>：按该列排序。看起来像数字的文字按数值排。</li>
<li><b>排序后状态栏右侧</b>：纯数字列显示筛选合计和全部合计。其它列查重名（忽略大小写），有重名红色，没有则绿色。</li>
<li><b>框选单元格</b>：大约半秒后，在原地统计。纯数字给出数量和总和，否则查重名。</li>
<li><b>列标题右键</b>：复制本列、带表头复制、可回贴复制、粘贴回本列、唯一值统计、选中重复值、选中空值、编辑备注。可回贴带要素编号，改的是第二列，按编号写回，不按行号对位。日期复制成 2024-09-01 这种文字。</li>
<li><b>左侧序号右键</b>：按表格显示顺序选行，例如 10-50、1-20,35、80-（到末行）。</li>
<li><b>拖列</b>：只改本窗口的显示顺序，不改图层字段顺序。关掉窗口后不记住。</li>
<li><b>顶栏从左到右</b>：钉、范围、冻结、筛选、过滤。钉是蓝字时表跟着图例当前层走，红字时钉住当前层。范围有全部要素、仅选中、地图可见、仅已修改。冻结把一列固定在左边，左右表的行对齐。筛选是两个下拉：左边选分类或字段，右边多选，满足任一即留下；右边第一项「全部」表示这次不额外筛选。过滤是输入即搜，大约半秒生效。筛选和过滤同时起作用。</li>
<li><b>未保存的修改</b>：单元格淡黄底，悬停写着还没保存。关掉窗口不额外弹窗，保存和回滚仍由 QGIS 管。</li>
<li><b>写入校验</b>：手改、赋值、快速插入、粘贴回本列都会按字段类型检查。类型不符的跳过。小数写入整数会四舍五入，超长文字会先列出例子让你确认。表达式字段和不能编辑的连接字段只读。</li>
<li><b>赋值</b>（只在编辑模式出现）：常量、前后序号、前后加字、表达式、替换。可更新筛选行或更新选中。常量可输入另一个字段名，把那一列抄过来；要写入和字段名一模一样的文字，用单引号包起来。前后序号在已有文字前面或后面加序号，原文字保留，位数可选不补零、自动或指定位数，补零只留在文本字段，空白格子只写序号。前后加字只改已有文字，空白不动。表达式用 QGIS 表达式。替换是字面量，一格里多处全部替换。</li>
<li><b>全选 / 反选 / 取消选择</b>：全选和反选针对当前表格里的行。取消选择清空图层上的全部选中。</li>
<li><b>列宽</b>：「适」按内容比例铺满窗口；「全」按内容撑开，可以超出窗口。仍可手动拖。</li>
<li><b>复制 / 剪切 / 粘贴</b>：Ctrl+C 复制选中单元格的值。工具栏「复制」复制整条要素。要改完贴回：列标题用「复制本列（可回贴）」，第一列表头以 #fid 开头，不要改；只改第二列，再粘贴回本列。编号对不上、重复，或值列整列是空的，则一条都不写。</li>
<li><b>导出</b>：CSV 可按数值写入纯数字文本。KMZ 可只导出当前表格里的行，也可用单一、分类、分级符号的颜色。规则符号不上色。坐标转不过去会报错。</li>
<li><b>字段管理</b>：增删改字段。若该字段在当前备注项目里还有中文名或含义，删除时会问要不要一起删掉备注。</li>
<li><b>工具栏顺序</b>：最右侧「顺序」。可隐藏按钮、拖拽排序，本机记住。快速命名默认不放在工具栏上，在这里勾选后才出现。</li>
<li><b>界面风格</b>：默认、樱花粉、薄荷清新。本插件各个窗口一起换，本机记住。</li>
<li><b>窗口大小</b>：这一次 QGIS 开着时记住，退出后不保留。</li>
</ul>
""",
    ),
    (
        "字段备注",
        """
<h3>功能介绍</h3>
<p>字段备注是这套插件的主功能。它给矢量图层准备一套可复用的字段说明：显示名、悬停说明、可点选写入的含义，以及项目变量。
配置按「项目」存在本机，多份工程共用，不写进某一个 .qgz。图层和字段按名称对应，不按 QGIS 内部编号。</p>
<p>启用之后，本表表头上面是显示名、下面是原字段名。鼠标放在列标题上，能看到显示名、悬停说明和含义；有这些内容时，悬停不再只显示原字段名。
没启用时，属性表照常编辑，不套这套说明。QGIS 自带属性表（F6）也不受影响。</p>
<p><b>显示和写入是两件事。</b>显示名、悬停说明只给人看，不会写进要素。含义里的常量或表达式才会写入字段。
值映射字段写入的仍是原来的代码，你改的是旁边给人看的说明。</p>
<h3>使用说明</h3>
<ul>
<li><b>第一次使用</b>：打开属性表，点工具栏上的字段备注。先在「项目管理」里新建一个项目并选中它。占位项目不能改。再到图例选中要配置的图层，左边点一个字段，填显示名和含义，最后点「启用」。</li>
<li><b>图标颜色</b>：备注按钮只负责打开窗口，不是启用开关。彩色表示已经选了真正的项目，而且窗口里已启用。灰色表示停在占位项目，或还没启用。</li>
<li><b>占位项目</b>：每次重新打开 QGIS，都从「默认（不可修改）」开始。它不能改、不能启用、不能配变量。这一次 QGIS 开着时，你选过的项目会记住；退出 QGIS 后再打开，又回到占位项目。项目里的配置本身还在，只要再选中并启用即可。</li>
<li><b>项目管理</b>：新建、删除、重命名。名称不能和别的项目重复，也不能用占位名称。删项目会删掉这份配置，不改图层里的要素。</li>
<li><b>启用</b>：只有点启用，才会把配置套到图层字段上，并检查图层名、字段名是否对得上当前工程。对不上时再进入匹配，可以把对不上的图层或字段指到现有的名字上。打开窗口、换项目、预览都不会弹出匹配。换项目会先关掉启用，需要再点一次。</li>
<li><b>对不上时</b>：可以先复制成一个新项目，再匹配。复制时，当前工程里对不上的图层和字段会被丢掉，原来的项目不动。也可以不复制，直接在当前项目里匹配。</li>
<li><b>编辑字段</b>：左边列出当前图例图层的字段，最后一项是图层名。未启用时这一列只读；启用后才能改。字段可填显示名、悬停说明、含义。图层名只填显示名和悬停说明，给图例悬停用，没有含义列表，也不写入属性。</li>
<li><b>含义</b>：一行是一个可插入的选项。双击可改说明。写入值可选常量，或粘贴 QGIS 表达式。常量可以再插入当前项目的变量，例如 {{城市}}123。表达式按每个要素计算，算失败的要素跳过，其它要素照常写。下拉里只出现这个字段已经配好的含义，不会把项目变量直接灌进每一列。</li>
<li><b>值映射</b>：QGIS 里已经做了值映射的字段，名称标绿。这些项是从 QGIS 带过来的，不能删除。后面的「原」是 QGIS 里原来的描述，恢复默认会把说明改回那个描述。你改的是显示说明，格子里存的仍是原来的字段值。本表编辑这种字段时也可以下拉选说明，写入仍是代码。</li>
<li><b>值/注显示</b>：属性表工具栏上的切换。值：格子里看字段原值。注：有备注含义时，格子里看说明。过滤在「注」模式下也会按说明来找。切换只改变看的方式，不改已经存进去的值。</li>
<li><b>变量</b>：在启用旁边，跟当前项目走，不是整个 QGIS 共用。标题给人看，内容才是真正替换进去的文字。占位项目不能配。给某一列加含义时，点「插入变量」把 {{标题}} 拼进写入值，旁边还可以再加固定文字。点插入的那一刻才替换成变量当前内容；以后改变量，已经写进字段的旧值不会自动改，含义本身也不用改。标题被删或改掉之后，再插入会提示找不到，不会写成空。</li>
<li><b>快速插入</b>：备注已启用，并且图层处于编辑模式时，表格上方出现一行与各列对齐的下拉。选一个含义后，可选更新全部、更新筛选项、更新选中，或取消。取消则保留刚才选的内容，再用赋值条上的按钮写入。常量写的是等号右边的结果；表达式逐要素计算。</li>
<li><b>和赋值条的关系</b>：快速插入用的是这个字段已经配好的含义。赋值条仍可写常量、前后序号、前后加字、表达式和替换，不要求先配备注。两边都要先进入编辑模式，写完后用本插件或 QGIS 的保存，才会落到数据源。</li>
<li><b>预览</b>：只读查看这个项目里已配置的图层、字段和含义，也能看到变量。红色是当前工程对不上的图层或字段。默认只列出对不上的项。</li>
<li><b>导入 / 导出</b>：可勾选多个项目。一份 JSON 里可以有多个项目，变量一起带走。同名时再选择覆盖或换名。导入不会自动启用，选中项目后仍要点启用。</li>
<li><b>刷新</b>：另一边 QGIS 改过同一份配置时，点刷新，或点一下本窗口，即可看到，不用重启。</li>
<li><b>删除字段时</b>：在字段管理里删除字段，如果当前项目里这个字段还有显示名、说明或含义，会问要不要把这条备注一起删掉。选保留时，备注留在项目里；以后这个图层再出现同名字段，仍会套用。</li>
</ul>
<h3>建议这样配</h3>
<ul>
<li>一个项目对应一套业务，例如一条线路或一个区县。不要把互不相关的图层堆在同一个项目里，匹配时不容易看。</li>
<li>显示名写短，悬停说明写规则。需要反复填写的固定说法放进含义，需要随项目变化的地名、编号放进变量。</li>
<li>值映射字段先在 QGIS 里设好代码和描述，再在这里只改给人看的说明。</li>
<li>换工程后如果底栏提示图层或字段对不上，先看是不是选错了项目；确认要用这份配置，再点启用去做匹配。</li>
</ul>
""",
    ),
    (
        "快速命名",
        """
<h3>功能介绍</h3>
<p>按图层符号化里的分类或规则，给选中要素写入对应的字段值。它不依赖字段备注有没有启用。
读的是全部分类，不管图例里勾没勾。点线面必须是同一类几何。</p>
<h3>使用说明</h3>
<ul>
<li><b>入口</b>：属性表工具栏「顺序」里勾上「工具栏显示快速命名」，才会出现青绿的「快」图标。本机记住，默认不放。</li>
<li><b>列表</b>：每一行是一个分类。括号里是本窗口自己维护的要素数量：打开或换图层时数一次，命名之后按刚写的条数加减。标题里图层名后面的总数等于下面分类之和，用来对照 QGIS 图例。</li>
<li><b>点分类</b>：默认会先确认。勾上「点分类不再确认」之后直接写。</li>
<li><b>钉住图层</b>：默认不勾。钉住分类图层 A 之后，在 A 上选中再点分类，只改属性、不复制几何。在别的图层上选中再点分类，把几何复制进 A，再按这个分类的规则赋值。来源图层不改，A 也不会多出来源字段。</li>
<li><b>自动保存</b>：默认「不自动保存」，还能回滚，图例要等你在 QGIS 里保存才变。选「N 秒后保存」则先写入，大约 N 秒后点一次 QGIS 自带的保存图层编辑。连续命名按当前秒数重新计时，只存一次。关掉窗口会立刻补存。这一次会把该层还没保存的修改都写进去，不能再撤销。</li>
<li><b>刷新图例计数</b>：只在你点的时候，把当前层的符号化原样设回去，让 QGIS 重算左侧分类后面的数量。不改要素，也不会自动刷。</li>
<li><b>写不进去时</b>：渐变符号、无法反推字段的规则，点了会说明原因，不写。</li>
</ul>
""",
    ),
    (
        "字段映射",
        """
<h3>功能介绍</h3>
<p>把一个矢量图层的要素复制到另一个图层，并按你排好的字段对应关系写入属性。
几何类型必须一致。源图层和目标图层不能是同一个。坐标系不同时可以自动重投影。</p>
<h3>使用说明</h3>
<ul>
<li><b>入口</b>：属性表工具栏上的字段映射。窗口可以一直开着，切换语言会立刻换成本插件的英文或中文。</li>
<li><b>选图层</b>：上面选源，下面选目标。可以用点、线、面过滤列表。源图层也可以从文件加载，包括 QGIS 能打开的矢量文件。</li>
<li><b>对字段</b>：每一行是目标图层的一个字段，右边选源字段。可以按名称自动匹配。模糊匹配会忽略空格和下划线，只有能唯一对上时才填上。「隐藏已匹配源字段」打开时，已经用过的源字段不再出现在其它行里。关掉之后，同一个源字段可以配给多个目标字段，重复的会标红。</li>
<li><b>复制选项</b>：可以只复制源图层里选中的要素。坐标系不同时，默认重投影到目标图层。</li>
<li><b>开始复制</b>：写入目标图层的编辑缓冲。复制完要在目标图层上保存编辑，才会落到文件里。</li>
<li><b>保存</b>：字段对应关系保存在本机，下次打开还能用。换了一对图层之后，按那一对图层各自记住。</li>
</ul>
""",
    ),
    (
        "线方向",
        """
<h3>功能介绍</h3>
<p>从你点的一个起点出发，沿相接的线往外走，找出数字化方向反了的线，并可以翻转顶点顺序。
端点靠得够近才算接上。中间断开就停下，不会把下一段硬接上。不改属性，只改线的顶点顺序，写入编辑缓冲，需要你自己保存图层。</p>
<h3>使用说明</h3>
<ul>
<li><b>入口</b>：属性表工具栏上的线方向。</li>
<li><b>吸附容差</b>：单位是米。A 靠近 B、B 靠近 C 时，三个端点会算成同一个点，即使 A 和 C 比容差更远。端点很密的地方要看清楚再设。</li>
<li><b>起点图层</b>：选一个点图层。右边的「全部」是分类筛选：图例里没勾的分类也会列出来，勾上才参与。不筛选就是这个图层的全部点。</li>
<li><b>线</b>：至少加一个线图层。可以加多条，每条各自筛选分类。线在走向上被当成从左到右：起点一侧是线的起点，另一侧是线的终点。</li>
<li><b>终点</b>：可以不选。选了之后，走到终点就停。不选终点时，拿掉某条线后如果有一头从起点走不到，就不把这种情况叫伪成环。</li>
<li><b>点一个起点</b>：下面的列表是筛选之后的点，可以按名称或 FID 搜。必须点中一个再开始。</li>
<li><b>开始之后</b>：结果窗口置顶，不挡地图。方向反了的线默认打勾，伪成环默认不勾。「翻转勾选」只翻打了勾的线。一端空着、没挂上、方向互相矛盾的线不会动。</li>
<li><b>临时图层</b>：会放出起点、终点或方向问题的临时点，方便在地图上对照。关掉结果窗口后，这些临时图层还在，不需要可以自己移除。</li>
</ul>
""",
    ),
)

PAGES_EN = (
    (
        "Attribute table",
        """
<h3>What it does</h3>
<p>This is a table beside the built-in QGIS attribute table. It does not replace F6 and does not take the F6 shortcut.
Use it to view and edit a vector layer: sort, filter, freeze a column, fill values, paste by feature id, and export.
Field remarks, quick naming, field mapping, and line direction each have their own page.</p>
<h3>How to use</h3>
<ul>
<li><b>Open</b> from the toolbar, <b>Vector → Field Remarks Table</b>, or the layer context menu. Select a vector layer in the Layers panel first.</li>
<li><b>Language</b> is the toolbar language button. The first launch follows the QGIS locale, then the system locale, and the choice is remembered. Choices are Chinese, English, Spanish, French, and Arabic. Switching updates plugin windows that are already open. In Arabic, buttons and titles in this plugin's windows run right to left. Values in the table stay left to right.</li>
<li><b>Double-click the row number</b> to select the feature and zoom to it.</li>
<li><b>Click a column header</b> to sort. Numeric text is sorted as a number.</li>
<li><b>After a sort</b>, the status bar shows a filtered total and a full total for numeric columns. Other columns report duplicates, ignoring case.</li>
<li><b>Drag-select cells</b>. After about half a second the same spot shows a count and sum for numbers, or a duplicate check otherwise.</li>
<li><b>Right-click a column header</b> to copy the column, copy with the header, copy for paste-back, paste back, show unique values, select duplicates, select blanks, or edit remarks. Paste-back keeps the feature id in column 1 (the header starts with #fid). Edit column 2 only. Values are written by id, not by row position. Dates are copied as 2024-09-01.</li>
<li><b>Right-click a row number</b> to select displayed rows, for example 10-50, 1-20,35, or 80- through the last row.</li>
<li><b>Drag a column</b> to change the order in this window only. The layer field order stays the same. The order is not kept after you close the window.</li>
<li><b>Top bar, left to right</b>: pin, scope, freeze, category/field filter, text filter. Blue pin text follows the current legend layer. Red pin text keeps this layer. Scope is all features, selected, visible on the map, or modified in this edit session. Freeze locks one column on the left and keeps rows aligned. The filter has two boxes: a category or a field on the left, and values on the right (any checked value keeps the row). The first right-hand item, All, adds no extra filter. The text box filters as you type, after about half a second. Both filters apply together.</li>
<li><b>Unsaved edits</b> use a pale yellow cell. Closing the window does not add another prompt. Save and rollback stay with QGIS.</li>
<li><b>Value checks</b> apply to hand edits, fill, quick insert, and paste-back. Values that do not fit the field type are skipped. Decimals written into an integer field are rounded. Text that is longer than the field is listed before you confirm. Expression fields and non-editable joins are read-only.</li>
<li><b>Fill</b> (edit mode only): constant, sequence around text, add text, expression, replace. Update filtered rows or update selected rows. A constant can be another field name, which copies that column. To write text that is exactly a field name, wrap it in single quotes. Sequence around text adds a number before or after existing text and keeps the original text. Width can be no padding, automatic, or a fixed width. Padding is kept only on text fields. A blank cell receives the number only. Add text changes existing text and leaves blanks alone. Expression uses a QGIS expression. Replace is literal and replaces every match in the cell.</li>
<li><b>Select all / invert / clear</b>: select all and invert use the current table rows. Clear drops the layer selection.</li>
<li><b>Column width</b>: Fit spreads columns across the window. Full sizes them to their content and may extend past the window. You can still drag a width.</li>
<li><b>Copy, cut, paste</b>: Ctrl+C copies the selected cell values. The toolbar Copy copies whole features. To edit and paste back, use Copy column (round-trip). Do not change the #fid column. If ids do not match, repeat, or the value column is entirely empty, nothing is written.</li>
<li><b>Export</b>: CSV can write numeric text as numbers. KMZ can export only the current table rows and can use single, categorized, or graduated symbol colors. Rule-based symbols are not colored. A failed coordinate transform is reported.</li>
<li><b>Field manager</b> adds, deletes, and renames fields. If the current remark pack still has a label or meanings for that field, delete asks whether to drop the remark too.</li>
<li><b>Toolbar order</b> is the rightmost button. Hide buttons and drag to reorder. The choice is remembered on this computer. Quick naming is off the toolbar until you check it here.</li>
<li><b>Theme</b>: Default, Sakura pink, or Mint. Every window of this plugin follows it. The choice is remembered on this computer.</li>
<li><b>Window size</b> is remembered while this QGIS session is open.</li>
</ul>
""",
    ),
    (
        "Field remarks",
        """
<h3>What it does</h3>
<p>Field remarks are the main feature of this plugin. A pack stores reusable field text for vector layers: a display name, a hover note, meanings you can insert, and pack variables.
Packs are saved on this computer and shared by every project. They are not stored inside one .qgz file. Layers and fields are matched by name, not by QGIS internal id.</p>
<p>When a pack is enabled, this table's header shows the display name above the field name. Hovering a column title shows the display name, the hover note, and the meanings. While those exist, the hover does not fall back to the raw field name alone.
While the pack is off, the attribute table edits as usual and does not apply the pack. The built-in QGIS attribute table (F6) is left alone.</p>
<p><b>Display and writing are separate.</b> Display names and hover notes are only for people to read. They are not written into features. A meaning's constant or expression is what gets written.
On a value-map field, the stored value stays the original code. You edit the description shown beside it.</p>
<h3>How to use</h3>
<ul>
<li><b>First time</b>: open the attribute table and click Field remarks. In Packs, create a pack and select it. The placeholder pack cannot be edited. Select the layer in the legend, click a field on the left, fill in a display name and meanings, then click Enable.</li>
<li><b>Icon color</b>: the remarks button only opens the window. It is not the enable switch. Color means a real pack is selected and enabled. Gray means the placeholder pack, or that enable is off.</li>
<li><b>Placeholder pack</b>: every new QGIS launch starts on Default (locked). It cannot be edited, enabled, or given variables. The pack you pick is remembered until you quit QGIS. The next launch starts on the placeholder again. The pack you built is still there. Select it and enable it again.</li>
<li><b>Packs</b>: new, delete, and rename. The name must be unique and must not be the placeholder name. Deleting a pack deletes that setup. It does not change features on the layer.</li>
<li><b>Enable</b> applies the pack to layer fields and checks that layer and field names match this project. A mismatch opens matching, where you can point an old name at a layer or field that exists now. Opening the window, changing packs, and preview do not open matching. Changing packs turns enable off, so you enable again.</li>
<li><b>When names do not match</b>: you can copy the pack to a new name and then match. The copy drops layers and fields that do not exist in this project. The original pack stays as it was. You can also match in place without copying.</li>
<li><b>Edit fields</b>: the list is the current legend layer. The last item is the layer name. The list is read-only until the pack is enabled. A field has a display name, a hover note, and meanings. The layer name has a display name and a hover note for the legend only. It has no meanings and is not written into attributes.</li>
<li><b>Meanings</b>: one row is one insert choice. Double-click to edit the description. The value can be a constant or a pasted QGIS expression. A constant can include a pack variable, such as {{city}}123. An expression is evaluated per feature. A feature that fails is skipped. The other features are still written. The insert list shows only meanings configured for that field. Pack variables are not poured into every column by themselves.</li>
<li><b>Value map</b>: a field that already uses a QGIS value map is marked in green. Those rows come from QGIS and cannot be deleted. The text after "was" is the original QGIS description. Restore default puts that description back. You edit the description people see. The cell still stores the original code. In this table you can also pick the description from a drop-down. The written value is still the code.</li>
<li><b>Value / note display</b> is the toolbar toggle. Value shows the stored field value. Note shows the remark description when one exists. In note mode, the text filter also searches descriptions. The toggle changes what you see. It does not change values already stored.</li>
<li><b>Variables</b> sit next to Enable and belong to the current pack, not to all of QGIS. The title is what you read. The value is the text that gets substituted. The placeholder pack has none. When you add a meaning, Insert variable places {{title}} into the value. You can add fixed text beside it. Substitution happens at insert time. Changing a variable later does not rewrite values already stored, and you do not have to edit the meaning. If the title is missing, insert tells you and does not write a blank.</li>
<li><b>Quick insert</b> appears above the table when remarks are enabled and the layer is editable. The drop-downs line up with the columns. After you pick a meaning, choose update all, update filtered rows, update selected rows, or cancel. Cancel keeps the choice so the fill-bar buttons can write it. A constant writes the resolved text. An expression is evaluated per feature.</li>
<li><b>Fill bar</b>: quick insert uses meanings you already configured. The fill bar can still write a constant, a sequence around text, added text, an expression, or a replacement without a remark pack. Both need edit mode. Save from this plugin or from QGIS before the data source stores the edit.</li>
<li><b>Preview</b> is a read-only view of the layers, fields, meanings, and variables in this pack. Red means a layer or field does not match this project. By default only mismatches are listed.</li>
<li><b>Import / Export</b> can include several packs. One JSON file can hold more than one pack, including variables. On a name clash, choose overwrite or rename. Import does not enable a pack. Select it and click Enable.</li>
<li><b>Refresh</b>: if another QGIS window changed the same packs, click Refresh, or click this window, to see them. You do not need to restart.</li>
<li><b>Deleting a field</b>: if Field manager deletes a field that still has a display name, note, or meanings in the current pack, it asks whether to delete that remark too. If you keep it, the remark stays in the pack. A later field with the same name on that layer still receives it.</li>
</ul>
<h3>A practical setup</h3>
<ul>
<li>Use one pack for one job, such as one route or one district. Unrelated layers in the same pack make matching harder to read.</li>
<li>Keep the display name short and put the rule in the hover note. Put repeated fixed text in meanings. Put names and numbers that change per job in variables.</li>
<li>Set a value map's codes and descriptions in QGIS first. Use this window only to adjust the description people see.</li>
<li>After you open another project, if the status line says layers or fields do not match, check that you picked the right pack. When you do want this pack, click Enable and match the names.</li>
</ul>
""",
    ),
    (
        "Quick naming",
        """
<h3>What it does</h3>
<p>Write field values from categorized or rule-based symbology onto the selected features. It does not depend on field remarks being enabled.
Every class is listed, whether or not the legend checkbox is on. Points, lines, and polygons must be the same geometry type.</p>
<h3>How to use</h3>
<ul>
<li><b>Open</b>: in the attribute table, open toolbar order and check Show quick naming on the toolbar. A green Quick button appears. The choice is remembered on this computer and is off by default.</li>
<li><b>List</b>: each row is one class. The number in parentheses is kept by this window. It is counted when you open or change layers, then adjusted by how many features you just wrote. The total after the layer name equals the sum of the classes, so you can compare it with the QGIS legend.</li>
<li><b>Click a class</b>: a confirmation appears unless you check the box to write immediately.</li>
<li><b>Pin the layer</b> is off by default. After you pin categorized layer A, selecting features on A and clicking a class only updates attributes. Selecting features on another layer and clicking a class copies the geometry into A, then applies that class. The source layer is unchanged, and A does not gain the source fields.</li>
<li><b>Auto-save</b> defaults to off, so you can still roll back. The legend counts change after you save in QGIS. Choose "save after N seconds" to write first, then trigger QGIS Save Layer Edits once after about N seconds. Further clicks restart that timer and save once. Closing the window saves immediately. That save writes every unsaved change on the layer and cannot be undone.</li>
<li><b>Refresh legend counts</b> runs only when you click it. It sets the current renderer back onto the layer so QGIS recalculates the legend counts. It does not change features and does not run by itself.</li>
<li><b>When a class cannot be written</b>, for example a graduated renderer or a rule with no field value, the click explains why and writes nothing.</li>
</ul>
""",
    ),
    (
        "Field mapping",
        """
<h3>What it does</h3>
<p>Copy features from one vector layer to another and write attributes with the field map you set.
Geometry types must match. The source and target cannot be the same layer. Different coordinate systems can be reprojected.</p>
<h3>How to use</h3>
<ul>
<li><b>Open</b> from Field mapping on the attribute-table toolbar. The window can stay open. Switching language updates its labels immediately.</li>
<li><b>Layers</b>: source on the first row, target on the second. Filter the lists by point, line, or polygon. The source can also be loaded from a vector file QGIS can open.</li>
<li><b>Fields</b>: each row is a target field. Choose the source field on the right. Match same names fills unique pairs. Fuzzy match ignores spaces and underscores and fills a pair only when it is unique. Hide matched source fields removes a source field from the other lists after it is used. Turn that off to map one source field to several targets. Repeats are marked in red.</li>
<li><b>Options</b>: copy only features selected on the source. When coordinate systems differ, reprojection to the target is on by default.</li>
<li><b>Copy now</b> writes into the target edit buffer. Save the target layer edits to store them in the file.</li>
<li><b>Save</b> keeps the field map on this computer for the next time you open this pair of layers.</li>
</ul>
""",
    ),
    (
        "Line direction",
        """
<h3>What it does</h3>
<p>Start from one point you pick, walk connected lines, find lines whose digitizing direction faces the wrong way, and flip vertex order.
Endpoints count as the same point only when they are close enough. A gap stops the walk. Attributes are not changed. Only vertex order is written into the edit buffer, and you save the layer yourself.</p>
<h3>How to use</h3>
<ul>
<li><b>Open</b> from Line direction on the attribute-table toolbar.</li>
<li><b>Snap tolerance</b> is in meters. If A is near B and B is near C, all three endpoints are one point, even when A and C are farther apart than the tolerance. Be careful where endpoints are dense.</li>
<li><b>Start layer</b> is a point layer. The button on the right filters by category. Categories that are unchecked in the legend are still listed. Check them to include them. All means every point on that layer.</li>
<li><b>Lines</b>: add at least one line layer. You can add several and filter each one. Along a line, the start side is the line start and the other side is the line end.</li>
<li><b>Ends</b> are optional. The walk stops at an end. With no ends, a line is not treated as a false loop just because removing it leaves one side unreachable from the start.</li>
<li><b>Pick one start</b> in the list. Search by name or feature id. Start stays disabled until one point is chosen.</li>
<li><b>After Start</b>: the result window stays on top and does not block the map. Reversed lines are checked by default. False loops are not. Flip checked reverses only the checked lines. A line with an open end, a line that never connected, or a line whose parts disagree is left alone.</li>
<li><b>Temporary layers</b> mark starts, ends, or direction problems so you can see them on the map. They remain after you close the result window. Remove them yourself if you do not need them.</li>
</ul>
""",
    ),
)


def pages_for(language):
    from .catalog import LANG_AR, LANG_EN, LANG_ES, LANG_FR

    if language == LANG_EN:
        return PAGES_EN
    if language == LANG_ES:
        from .help_es import PAGES as pages

        return pages
    if language == LANG_FR:
        from .help_fr import PAGES as pages

        return pages
    if language == LANG_AR:
        from .help_ar import PAGES as pages

        return pages
    return PAGES_ZH

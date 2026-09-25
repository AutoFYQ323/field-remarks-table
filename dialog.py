# -*- coding: utf-8 -*-
"""Main attribute table dialog."""

import csv
import io
import os
from collections import Counter

try:
    from qgis.PyQt.QtCore import QStringListModel
except Exception:
    from qgis.PyQt.QtGui import QStringListModel
from qgis.PyQt.QtCore import Qt, QTimer, QItemSelectionModel, QItemSelection, QObject, QEvent, QSize, pyqtSignal
from qgis.PyQt.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QToolBar,
    QAction,
    QTableView,
    QLineEdit,
    QLabel,
    QComboBox,
    QCheckBox,
    QMessageBox,
    QFileDialog,
    QAbstractItemView,
    QStatusBar,
    QDialogButtonBox,
    QSplitter,
    QRadioButton,
    QMenu,
    QWidgetAction,
    QApplication,
    QWidget,
    QPushButton,
    QTextBrowser,
    QToolButton,
    QSizePolicy,
    QLayout,
    QAbstractScrollArea,
    QCompleter,
    QInputDialog,
)
try:
    from qgis.PyQt.QtWidgets import QWIDGETSIZE_MAX
except ImportError:
    QWIDGETSIZE_MAX = 16777215
from qgis.PyQt.QtGui import QIcon, QKeySequence, QStandardItem, QStandardItemModel

from qgis.core import (
    QgsApplication,
    QgsProject,
    QgsMapLayer,
    QgsVectorDataProvider,
    QgsFeatureRequest,
    QgsExpression,
    QgsExpressionContext,
    QgsExpressionContextUtils,
    QgsCoordinateTransform,
    NULL,
)
from qgis.gui import QgsExpressionBuilderDialog

from . import theme
from .model import FeatureTableModel, try_parse_number
from .column_tools import BLANK_KEY, UniqueValuesDialog, group_column, parse_row_ranges
from .value_utils import coerce_for_field, temporal_text, value_text
from .kmz_dialog import ExportKmzDialog
from .kmz_export import export_layer_to_kmz
from .fields_manager import FieldsManagerDialog
from .settings_store import SettingsStore
from .toolbar_order_dialog import ToolbarOrderDialog
from .remarks_store import (
    RemarksSession,
    meaning_display,
    meaning_payload,
    resolve_var_template,
)
from .remarks_dialog import (
    QuickFillBar,
    RemarksHubDialog,
)
from .value_map import ValueMapDelegate, qgis_description_for_value, value_key
from .classify_assign import layer_categories, attr_values_equal, field_eq_expression


def plugin_version():
    path = os.path.join(os.path.dirname(__file__), "metadata.txt")
    try:
        with open(path, "r", encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("version="):
                    return (line.split("=", 1)[1] or "").strip() or "—"
    except Exception:
        pass
    return "—"


HELP_HTML = """
<h3>Field Remarks Table — 功能说明（版本 __VERSION__）</h3>
<p><b>English:</b> Complementary attribute table for vector layers. It does not replace
QGIS built-in Attribute Table (F6). Open from the toolbar, <b>Vector &gt; Field Remarks Table</b>,
or the layer context menu. Field-remark packs, pack variables, quick naming from symbology,
batch fill, paste-by-feature-id, KMZ/CSV export. Interface language: Simplified Chinese.</p>
<ul>
<li><b>双击左侧序号</b>：选中该要素并缩放到地图。</li>
<li><b>左键单击列标题</b>：按该列智能排序（文本型数字按数值排）。</li>
<li><b>排序后状态栏右侧</b>：纯数字列显示「筛选/全部合计」；非数字列显示「重名」检测（忽略大小写），有重名红色、无重名绿色。</li>
<li><b>框选/点选单元格</b>：约 500 毫秒后在同一位置统计所选值——纯数字显示数量与总和；否则查重名（点表头整列统计仍保留）。</li>
<li><b>列标题右键</b>：复制本列 / 复制本列（含表头）/ 复制本列（可回贴）/ 粘贴回本列 / 唯一值统计 / 选中重复值 / 选中空值 / 编辑备注。普通复制只有单元格文字。可回贴会带上要素编号，改完后按编号写回，不按行号对位。日期统一复制成 2024-09-01 这种文字。</li>
<li><b>唯一值统计</b>：列出本列每个值出现几次、占比，含义列显示值映射/备注描述。统计范围是当前表格里的行（受范围、过滤、筛选影响）。勾选后可「按勾选筛选」（填进顶栏筛选）或「选中勾选要素」，也能复制列表。</li>
<li><b>选中重复值 / 选中空值</b>：在当前表格行里找出本列重复的值（空值不算）或空值（NULL 或空白），直接在图层上选中，状态栏报条数。</li>
<li><b>左侧序号右键</b>：「选中第 a–b 行…」按表格显示顺序选行，可写 10-50、1-20,35、80-（到末行）；或「从第 N 行选到末行」。</li>
<li><b>拖动列标题</b>：仅改变本窗口显示顺序，不改图层字段顺序；关闭窗口后不记忆。</li>
<li><b>顶栏</b>：第一行从左到右为「钉」→ 范围 → 冻结 → 筛选 → 过滤（含文本框），按窗口宽度分担。第二行是赋值条，只在编辑模式出现。</li>
<li><b>钉</b>：小按钮。蓝字=未钉住（表随图例当前层切换）；红字=钉住当前图层。</li>
<li><b>范围</b>：全部要素 / 仅选中 / 地图可见要素（画布范围内，平移缩放后约 500 毫秒刷新）/ 仅已修改（编辑模式下还没保存的新增或改过的要素）。无单独标题。表格为空时状态栏会说明是哪个范围、过滤或筛选挡住了。</li>
<li><b>未保存修改</b>：编辑模式下改过还没保存的单元格显示淡黄底色，悬停提示「已修改，未保存」；状态栏显示「编辑·未保存（已改 N 条）」。关闭窗口或切图层不弹提示，保存/回滚仍由 QGIS 管。</li>
<li><b>写入校验</b>：手改单元格、赋值条、快速插入、粘贴回本列都会按字段类型检查。存不下的值（如往整数字段写「abc」、日期写错）跳过不写；小数写进整数字段会四舍五入、文字超出字段长度，写入前弹窗列出例子让你确认。没有问题就不多弹窗。整数/小数/日期列双击是文本框编辑，不会把小数截成两位、也不丢秒。表达式字段和不可编辑的连接字段只读。数字列靠右对齐。</li>
<li><b>过滤 / 文本框 / 筛选</b>：过滤选字段或所有字段；文本框输入即过滤（固定约 500 毫秒，无延迟选项）。筛选始终显示，是两个下拉：左边选「分类筛选」或某个字段；右边勾选具体项（可多选，满足任一即留下）。选「分类筛选」时右边是图层分类/规则；选字段时右边是该字段的不重复值（空值显示为「(空)」，值映射显示描述）。右边第一项「全部」表示这次不额外筛选。与文本过滤同时生效。</li>
<li><b>冻结</b>：将指定字段固定到左侧。右侧表出现横向滚动条时，左侧也显示一条同高的（能拖或只占位），两边的行始终对齐。</li>
<li><b>界面风格</b>（工具栏「色」图标）：默认（QGIS 原生）/ 樱花粉 / 薄荷清新。作用于本插件所有窗口（主表、字段备注、快速命名、字段管理、导出、弹窗等），本机记住。文字一律深色、背景浅色，选中行白字深底，保证看得清。</li>
<li><b>赋值条</b>（仅编辑模式，单独一行）：常量 / 只填空白 / 序号 / 前缀+序号 / 前后序号 / 前后加字 / 表达式 / 替换，可更新筛选行或选中行。序号、前缀+序号、前后序号可选位数：不补零、自动（按本次最大序号补零，写到 100 则 001），或指定位数（4 位为 0001，超出不截断）。补零只留在文本字段。前后序号是在已有文字前面或后面加上序号（二选一），原文字保留；位数同样可选。例如原文字 JT1、加在后面、自动位数得到 JT11。空白格子只写序号。只填空白只写当前为空的格子，已有内容不动。前后加字只改已有文字，空白不动。常量框可输入字段名（打字弹出下拉，按包含匹配列出全部候选，如 AM 会列出 NAME、NAMF、2NAMG）：整名匹配则把该字段内容写入目标字段；要写入恰好等于字段名的文字，用单引号包起来。替换为字面量部分替换（一格多处全部替换）。</li>
<li><b>全选 / 反选 / 取消选择</b>：全选、反选针对当前表格筛选结果；取消选择清空图层全部选中。</li>
<li><b>列宽</b>：点击图标切换。「适」=适配窗口（按去掉换行/超长后的最大内容宽度比例铺满窗口，拉窗口会重算）；「全」=完整显示（按同样规则撑开，可超出窗口）。仍可手动拖列宽。</li>
<li><b>图层右键 Field Remarks Table</b>：从图例打开本窗口。</li>
<li><b>字段备注</b>：工具栏图标只负责打开窗口，不是启用开关。彩色=已选真正项目且窗口里已启用（表头会套配置）；灰色=停在「默认（不可修改）」或未启用。管理项目并编辑当前图例图层的字段。「修改名称」右边可树形预览已配置图层/字段：红色为当前工程对不上的图层/字段，默认只显示不匹配项。未启用时图层管理只读，启用后才能改。每次打开 QGIS 都从占位「默认（不可修改）」开始（不能改数据、不能启用）；本次会话里选过的项目一直记住，关掉 QGIS 就回到占位。导入/导出可勾选多个项目。打开窗口、换项目、预览都不会弹匹配；点「启用」才预检图层/字段，对不上再匹配。换项目会先关闭启用，需再点启用。启用开关只决定要不要把配置套到图层字段上（默认关闭）。启用后表头两行：中文名在上、原字段名在下。列标题悬停显示中文名、悬停说明、含义，有这些时不显示原字段名。含义写入值可选常量或粘贴 QGIS 表达式；常量写入值可插入当前项目的变量。列表末项是图层名：只填中文名和悬停说明（图例悬停，不赋值），没有含义列表。值映射字段名称标绿；值映射项不能删除，后面「原」描述不变，可恢复默认。</li>
<li><b>变量配置</b>：字段备注窗口里、启用旁边。跟当前备注项目走，不是全 QGIS 共用。选了真正项目就能配（不依赖启用开关）；占位「默认（不可修改）」不能配。标题给人看，内容才是写入值。图1 给某一列加含义时点「插入变量」把 {{标题}} 拼进写入值（可再加常量）。插入下拉只出现这条含义。点插入当下才替换成变量当前内容；变量改了含义不用改。删了或改了标题，插入会提示找不到，不写空。导入/导出一并带走。预览点「显示全部」能看到变量列表。QGIS 表达式和值映射项不掺变量。</li>
<li><b>快速插入行</b>（启用备注且编辑模式）：表格上方与各列对齐。选含义后弹出「更新全部 / 更新筛选项 / 更新选中 / 取消」；取消则保留所选，再用赋值条按钮写入。常量写入等号右侧；含义里的变量按当前项目内容替换后再写，找不到变量则不写并提示。QGIS 含义按表达式逐要素计算，算失败的要素跳过。插入下拉只列本字段已配含义，不会把项目变量直接灌进每一列。</li>
<li><b>快速命名</b>：独立功能，与字段备注启用无关。入口在属性表工具栏：到「顺序」里勾 <b>工具栏显示快速命名</b> 才出现青绿「快」图标（本地记住，默认不放）。读取分类/规则的全部类别（不管图例勾没勾）。列表括号内是本窗口维护的要素数量：打开/换图层数一次，命名后按刚写的条数加减。标题图层名后的总数=下列分类之和，用来对照 QGIS 图例。钉住图层右边是自动保存下拉（默认「不自动保存」）：不保存还能回滚，图例要等你在 QGIS 里保存才变。选「N秒后保存」则命名后先只写入，约 N 秒再点一次 QGIS 自带的「保存图层编辑」（连续命名按当前秒数重新计时，只存一次），图例由 QGIS 自己刷。关掉窗口会立刻补存。该层未保存修改都会写入，这次不能再撤销。另两个勾选默认都不勾：钉住图层、勾选后点分类不再确认。底部「刷新图例计数」只在你点的时候把当前层符号化原样设回去，逼 QGIS 重算左侧分类 [n]；不改要素、不自动刷。钉住分类图层 A 后：在 A 上选中再点分类=只改属性、不复制；在其他层选中再点分类=把几何复制进 A，再按该类规则给新要素赋值。来源层不改；A 不增加来源字段。点线面须同类。</li>
<li><b>值映射下拉</b>：QGIS 设了值映射的字段，本表也可下拉选描述，写入仍是字段值。</li>
<li><b>工具栏最右侧「顺序」</b>：自定义按钮顺序，本地保存。</li>
<li><b>复制 / 剪切 / 粘贴</b>：Ctrl+C 复制当前选中单元格的值（Tab/换行，不带几何）；工具栏「复制」仍复制整条要素。剪切、粘贴要素需编辑模式。要改完贴回筛选行：列标题用「复制本列（可回贴）」（当前筛选的全部行，含未滚到的）。剪贴板只有两列：编号、字段值。第一列表头以 <b>#fid</b> 开头，不要改、不要删；在外面只改第二列。再点「粘贴回本列」或 Ctrl+V。按编号写回，与当前筛选顺序无关。编号对不上、重复、来自别的图层，或值列整列都是空的，则一条都不写，避免把原数据清掉。Ctrl+V 会在状态栏说明这次是「按编号粘贴回列」还是「按 QGIS 要素粘贴（新增要素）」。</li>
<li><b>导出 KMZ</b>：可勾「只导出当前表格里的行」（默认导出全部）、「使用图层颜色」（单一/分类/分级符号上色，规则符号不上色）。多点要素导出为多个点；日期按 2024-09-01 写入描述。坐标转换失败会报错而不是悄悄导出错位置。</li>
<li><b>删除字段</b>（字段管理）：如果该字段在当前备注项目里有中文名/说明/含义，会问是否一并删掉这条备注。</li>
<li><b>窗口大小</b>：本次 QGIS 会话内记住；退出 QGIS 后不保留。</li>
</ul>
"""

FILTER_DELAY_MS = 500

# Not a legal field name, so it cannot collide with a real column called category.
QUICK_MODE_CATEGORY = "\x1fquick-category"
QUICK_VALUE_LIMIT = 400


def _blank_field_expr(field_name):
    name = (field_name or "").replace('"', '""')
    quoted = '"%s"' % name
    return "(%s IS NULL OR trim(to_string(%s)) = '')" % (quoted, quoted)


def _temporal_text(value):
    """QDate / QDateTime / QTime as a QGIS expression literal, or None."""
    return temporal_text(value) or None


class _CoerceIssue:
    """A value that needed rounding, is too long, or cannot be stored in the field."""

    __slots__ = ("status", "raw", "value", "note")

    def __init__(self, status, raw, value, note):
        self.status = status
        self.raw = raw
        self.value = value
        self.note = note


def _plain_attr(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    temporal = _temporal_text(value)
    if temporal:
        return temporal
    if isinstance(value, float) and value == int(value):
        return str(int(value))
    return str(value)


def _expr_attr(value):
    temporal = _temporal_text(value)
    if temporal:
        return temporal
    if isinstance(value, float) and not isinstance(value, bool) and value == int(value):
        return int(value)
    return value


class MultiCheckCombo(QComboBox):
    """Dropdown whose items stay open and can be checked. Row 0 is 「全部」."""

    selectionChanged = pyqtSignal()

    def __init__(self, parent=None):
        super(MultiCheckCombo, self).__init__(parent)
        self.setModel(QStandardItemModel(self))
        self.setEditable(True)
        edit = self.lineEdit()
        edit.setReadOnly(True)
        edit.setFrame(False)
        self.setInsertPolicy(QComboBox.NoInsert)
        self.view().viewport().installEventFilter(self)
        self.add_check_item("全部", None, True)

    def wheelEvent(self, event):
        event.ignore()

    def hidePopup(self):
        QComboBox.hidePopup(self)
        # Closing the list selects the clicked row and would replace the summary.
        self._sync_text()

    def showPopup(self):
        QComboBox.showPopup(self)
        self._sync_text()

    def eventFilter(self, obj, event):
        if obj is self.view().viewport():
            etype = event.type()
            if etype == QEvent.MouseButtonPress:
                return True
            if etype == QEvent.MouseButtonRelease:
                index = self.view().indexAt(event.pos())
                if index.isValid():
                    self._toggle_row(index.row())
                return True
        return QComboBox.eventFilter(self, obj, event)

    def clear_items(self):
        self.model().clear()

    def add_check_item(self, text, payload, checked=False):
        item = QStandardItem(text)
        item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
        item.setData(payload, Qt.UserRole)
        item.setCheckState(Qt.Checked if checked else Qt.Unchecked)
        self.model().appendRow(item)

    def add_note(self, text):
        item = QStandardItem(text)
        item.setFlags(Qt.ItemIsEnabled)
        self.model().appendRow(item)

    def checked_payloads(self):
        out = []
        model = self.model()
        for row in range(1, model.rowCount()):
            item = model.item(row)
            if item is None or not (item.flags() & Qt.ItemIsUserCheckable):
                continue
            if item.checkState() == Qt.Checked:
                payload = item.data(Qt.UserRole)
                if payload:
                    out.append(payload)
        return out

    def expression(self):
        parts = self.checked_payloads()
        if not parts:
            return ""
        if len(parts) == 1:
            return parts[0]
        return " OR ".join("(%s)" % part for part in parts)

    def _toggle_row(self, row):
        model = self.model()
        item = model.item(row)
        if item is None or not (item.flags() & Qt.ItemIsUserCheckable):
            return
        if row == 0:
            self._check_all_only()
        else:
            item.setCheckState(
                Qt.Unchecked if item.checkState() == Qt.Checked else Qt.Checked
            )
            if self.checked_payloads():
                all_item = model.item(0)
                if all_item is not None:
                    all_item.setCheckState(Qt.Unchecked)
            else:
                self._check_all_only()
        self._sync_text()
        self.selectionChanged.emit()

    def _check_all_only(self):
        model = self.model()
        for row in range(model.rowCount()):
            item = model.item(row)
            if item is None or not (item.flags() & Qt.ItemIsUserCheckable):
                continue
            item.setCheckState(Qt.Checked if row == 0 else Qt.Unchecked)

    def ensure_some_check(self):
        if not self.checked_payloads():
            self._check_all_only()
        self._sync_text()

    def _sync_text(self):
        labels = []
        model = self.model()
        for row in range(1, model.rowCount()):
            item = model.item(row)
            if item is None or not (item.flags() & Qt.ItemIsUserCheckable):
                continue
            if item.checkState() == Qt.Checked:
                labels.append(item.text())
        if not labels:
            text = "全部"
            tip = "全部（不额外筛选）"
        elif len(labels) == 1:
            text = labels[0]
            tip = labels[0]
        else:
            joined = "、".join(labels)
            text = joined if len(joined) <= 18 else ("已选 %d 项" % len(labels))
            tip = joined
        edit = self.lineEdit()
        if edit is not None:
            edit.setText(text)
        self.setToolTip(tip)

# First column of a round-trip column copy. Paste refuses text that lacks this header.
ROUNDTRIP_FID_HEADER = "#fid"


def sequence_pad_width(choice, start, count):
    """0 = no padding. choice 'auto' uses the widest number in this batch."""
    if choice in (None, "none", 0, "0") or count <= 0:
        return 0
    if choice == "auto":
        first = abs(int(start))
        last = abs(int(start) + int(count) - 1)
        return max(len(str(first)), len(str(last)), 1)
    try:
        width = int(choice)
    except (TypeError, ValueError):
        return 0
    return width if width > 0 else 0


def format_padded_int(number, width):
    number = int(number)
    if width <= 0:
        return str(number)
    if number < 0:
        return "-" + str(abs(number)).zfill(width)
    return str(number).zfill(width)


def _parse_fid_token(text):
    raw = (text or "").strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        pass
    try:
        num = float(raw)
    except ValueError:
        return None
    if num != int(num):
        return None
    return int(num)


def _split_fid_header(cell):
    """Return (layer_id, ok). Header is '#fid' or '#fid@layer'."""
    text = (cell or "").strip().strip('"')
    if text == ROUNDTRIP_FID_HEADER:
        return "", True
    prefix = ROUNDTRIP_FID_HEADER + "@"
    if text.startswith(prefix) and text[len(prefix) :].strip():
        return text[len(prefix) :].strip(), True
    return "", False


def _roundtrip_cell(row, index):
    if row is None or index >= len(row) or row[index] is None:
        return ""
    return row[index]


def parse_roundtrip_text(text):
    """
    Return (payload, error).
    payload is {field, layer_id, rows: [(fid, value_text), ...]}.
    Any problem returns an error and no rows to apply.
    Clipboard is two columns: feature id, value. A leftover empty third
    column (older copies put the layer id there) is ignored. An all-empty
    value column is refused so it cannot wipe existing data.
    """
    if text is None:
        return None, "剪贴板是空的。"
    raw = str(text).lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
    if not raw.strip():
        return None, "剪贴板是空的。"
    try:
        rows = list(csv.reader(io.StringIO(raw), delimiter="\t"))
    except Exception as exc:
        return None, "无法读取剪贴板：%s" % exc
    while rows and (not rows[-1] or all(not (cell or "").strip() for cell in rows[-1])):
        rows.pop()
    if not rows:
        return None, "剪贴板是空的。"
    header = rows[0]
    layer_id, ok = _split_fid_header(header[0] if header else "")
    if not ok:
        return None, (
            "剪贴板不是可回贴格式。请用列标题「复制本列（可回贴）」，"
            "第一列必须是编号（表头以 #fid 开头），第二列才是要改的值。"
        )
    data_rows = []
    for row in rows[1:]:
        if not row or all(not (cell or "").strip() for cell in row):
            continue
        data_rows.append(row)
    if not data_rows:
        return None, "没有可写回的数据行。"

    width = max([len(header)] + [len(row) for row in data_rows])
    nonempty = []
    for index in range(1, width):
        if any((_roundtrip_cell(row, index) or "").strip() for row in data_rows):
            nonempty.append(index)
    if not layer_id and len(header) > 2 and (header[2] or "").strip() and 2 not in nonempty:
        layer_id = header[2].strip()
    header_field = header[1].strip() if len(header) > 1 and header[1] else ""
    if layer_id and header_field == layer_id:
        header_field = ""
    if not nonempty:
        return None, (
            "值列是空的，没有写入，表格里的原数据不会被清掉。"
            "请同时复制编号列和有内容的值列，不要只复制空列。"
        )
    if 1 in nonempty:
        if len(nonempty) > 1:
            return None, "除了编号和值之外还有别的内容，没有写入，避免贴错列。"
        value_idx = 1
    elif header_field:
        return None, (
            "字段「%s」这一列是空的，没有写入，避免把原数据清掉。"
            "请复制编号列和这一列。" % header_field
        )
    elif len(nonempty) == 1:
        value_idx = nonempty[0]
    else:
        return None, "除了编号和值之外还有别的内容，没有写入，避免贴错列。"
    field_name = ""
    if value_idx < len(header) and (header[value_idx] or "").strip():
        field_name = header[value_idx].strip()
    if not field_name or (layer_id and field_name == layer_id):
        return None, "表头缺少字段名。第一列是编号，第二列的表头应是字段名。"

    parsed = []
    seen = set()
    errors = []
    for lineno, row in enumerate(rows[1:], start=2):
        if not row or all(not (cell or "").strip() for cell in row):
            continue
        fid = _parse_fid_token(_roundtrip_cell(row, 0))
        if fid is None:
            errors.append("第 %s 行编号无效：%s" % (lineno, (_roundtrip_cell(row, 0) or "").strip()))
            continue
        if fid in seen:
            errors.append("编号 %s 重复（第 %s 行）" % (fid, lineno))
            continue
        seen.add(fid)
        parsed.append((fid, _roundtrip_cell(row, value_idx)))
    if errors:
        shown = "\n".join(errors[:8])
        more = "" if len(errors) <= 8 else "\n…共 %s 处问题" % len(errors)
        return None, "没有写入。请改好后再贴：\n%s%s" % (shown, more)
    if not parsed:
        return None, "没有可写回的数据行。"
    return {"field": field_name, "layer_id": layer_id, "rows": parsed}, None


def clipboard_is_roundtrip(text):
    if not text:
        return False
    raw = str(text).lstrip("\ufeff").lstrip()
    if not raw:
        return False
    first = raw.splitlines()[0]
    cell = first.split("\t", 1)[0].strip().strip('"')
    _layer_id, ok = _split_fid_header(cell)
    return ok

# Default toolbar order (ids). Separators: sep1 / sep2 / …; customize always last.
DEFAULT_TOOLBAR_ORDER = [
    "save",
    "revert",
    "reload",
    "edit",
    "sep1",
    "delete",
    "fields",
    "remarks",
    "display_mode",
    "sep2",
    "zoom",
    "select_all",
    "invert",
    "deselect",
    "col_width",
    "copy",
    "cut",
    "paste",
    "sep3",
    "export_csv",
    "export_kmz",
    "theme",
    "help",
    "customize",
]

# Session-only window geometry / column-width mode (cleared when QGIS exits / plugin unload).
_SESSION_GEOMETRY = None
_SESSION_COL_WIDTH_MODE = "fit"  # "fit" | "full"


class OverflowToolBar(QToolBar):
    """
    QToolBar in a QDialog reports all buttons as minimum width, so the window
    cannot shrink. Native attribute table is QMainWindow-style: overflow to >>.
    """

    def minimumSizeHint(self):
        hint = super().sizeHint()
        icon = self.iconSize()
        min_w = max(icon.width() + 36, 64)
        return QSize(min_w, hint.height())


def field_display_label(name, alias, remark_label=""):
    alias = (alias or "").strip()
    display = (remark_label or "").strip() or alias
    if display and display != name:
        return f"{name} ({display})"
    return name


class _HeaderRightClickFilter(QObject):
    """Catch right-click on QHeaderView — more reliable than customContextMenuRequested in QGIS."""

    def __init__(self, dialog, header, handler=None):
        super().__init__(header)
        self._dialog = dialog
        self._header = header
        self._handler = handler or dialog._show_header_column_menu

    def eventFilter(self, obj, event):
        if obj is not self._header:
            return super().eventFilter(obj, event)
        et = event.type()
        if et == QEvent.ContextMenu:
            self._handler(self._header, event.pos())
            return True
        if et == QEvent.MouseButtonPress and event.button() == Qt.RightButton:
            self._handler(self._header, event.pos())
            return True
        return super().eventFilter(obj, event)


class _CopyShortcutFilter(QObject):
    """Ctrl+C copies selected cells; toolbar 复制 still copies features."""

    def __init__(self, dialog, view):
        super().__init__(view)
        self._dialog = dialog
        self._view = view

    def eventFilter(self, obj, event):
        if obj is not self._view:
            return super().eventFilter(obj, event)
        if event.type() == QEvent.KeyPress and event.matches(QKeySequence.Copy):
            self._dialog._copy_by_shortcut()
            return True
        return super().eventFilter(obj, event)


class ExportCsvDialog(QDialog):
    """Choose export scope and column format."""

    SCOPE_ALL = "all"
    SCOPE_VISIBLE = "visible"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("导出 CSV")
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("导出范围："))
        self.radio_all = QRadioButton("图层全部要素（默认）")
        self.radio_visible = QRadioButton("仅当前表格显示的要素")
        self.radio_all.setChecked(True)
        layout.addWidget(self.radio_all)
        layout.addWidget(self.radio_visible)

        self.chk_qgis_format = QCheckBox(
            "按 QGIS 属性表格式（首列 wkt_geom / 经纬度 + 图层原始字段顺序）"
        )
        self.chk_qgis_format.setChecked(True)
        self.chk_qgis_format.setToolTip(
            "勾选：与自带属性表复制粘贴一致（wkt_geom + 图层字段顺序）；\n"
            "不勾选：按本插件当前表格的列顺序导出（不含几何列）。"
        )
        layout.addWidget(self.chk_qgis_format)

        self.chk_numeric_text = QCheckBox(
            "文本型纯数字（含小数）按数字导出"
        )
        self.chk_numeric_text.setChecked(True)
        self.chk_numeric_text.setToolTip(
            "勾选：字段虽为文本，但内容是纯数字时按数值写入 CSV，便于 Excel 计算；\n"
            "不勾选：一律按文本写出。"
        )
        layout.addWidget(self.chk_numeric_text)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def scope(self):
        return self.SCOPE_ALL if self.radio_all.isChecked() else self.SCOPE_VISIBLE

    def use_qgis_format(self):
        return self.chk_qgis_format.isChecked()

    def coerce_numeric_text(self):
        return self.chk_numeric_text.isChecked()


class AttributeTableDialog(QDialog):
    """Enhanced attribute table window."""

    def __init__(self, iface_ref, parent=None):
        # Parent should be iface.mainWindow() so the dialog stays with QGIS
        # (above QGIS when switching layers; no independent taskbar minimize).
        super().__init__(parent)
        # A closed window must not stay alive listening to layer switches.
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.iface = iface_ref
        self._settings = SettingsStore()
        self._remarks = RemarksSession()
        self._remarks_hub = None
        self._pin_layer = False
        self._layer = None
        self._syncing_selection = False
        self._freeze_field = ""  # field name to freeze, empty = off
        self._all_field_names = []
        self._field_labels = {}
        self._visible_fields = []
        self._stats_field_name = None
        self._sum_filtered = None  # float or None when numeric column
        self._sum_all = None
        self._dup_filtered = None  # str summary when text column
        self._dup_all = None
        # 'column' = header-sort stats; 'selection' = selected-cells stats
        self._stats_mode = None
        self._sel_count = None
        self._sel_sum = None
        self._sel_dup = None
        self._tool_actions = {}
        self._col_width_mode = _SESSION_COL_WIDTH_MODE if _SESSION_COL_WIDTH_MODE in ("fit", "full") else "fit"
        self.btn_col_width = None
        self._applying_col_widths = False

        self._filter_timer = QTimer(self)
        self._filter_timer.setSingleShot(True)
        self._filter_timer.timeout.connect(self._apply_text_filter_now)

        self._quick_value_timer = QTimer(self)
        self._quick_value_timer.setSingleShot(True)
        self._quick_value_timer.timeout.connect(self._refresh_quick_values_keep)

        self._selection_stats_timer = QTimer(self)
        self._selection_stats_timer.setSingleShot(True)
        self._selection_stats_timer.timeout.connect(self._refresh_selection_stats)

        self._canvas_scope_timer = QTimer(self)
        self._canvas_scope_timer.setSingleShot(True)
        self._canvas_scope_timer.timeout.connect(self._refresh_after_canvas_scope)
        self._watching_canvas = False

        self._col_width_timer = QTimer(self)
        self._col_width_timer.setSingleShot(True)
        self._col_width_timer.timeout.connect(self._apply_column_widths)

        self._reload_timer = QTimer(self)
        self._reload_timer.setSingleShot(True)
        self._reload_timer.timeout.connect(self.reload_table)

        self._selected_scope_timer = QTimer(self)
        self._selected_scope_timer.setSingleShot(True)
        self._selected_scope_timer.timeout.connect(self._refresh_selected_scope)

        self._status_timer = QTimer(self)
        self._status_timer.setSingleShot(True)
        self._status_timer.timeout.connect(self._update_status)

        # field name -> values of the whole layer (sort statistics); cleared on edits
        self._layer_value_cache = {}

        self.setWindowTitle("无图层")
        self.setWindowFlags(
            Qt.Window
            | Qt.WindowMinimizeButtonHint
            | Qt.WindowMaximizeButtonHint
            | Qt.WindowCloseButtonHint
        )
        self.resize(1100, 620)
        self.setMinimumSize(420, 300)
        self.setMaximumSize(QWIDGETSIZE_MAX, QWIDGETSIZE_MAX)
        self._restore_session_geometry()

        self.model = FeatureTableModel(self)
        self.model.editRejected.connect(lambda msg: self.status.showMessage(msg, 6000))
        self._build_ui()
        theme.register(self)
        self._connect_project()
        self._load_active_layer()
        self._reuse_open_remarks_hub()
        self._shared_reload_ready = True

    def on_theme_changed(self):
        quick = getattr(self, "quick_fill", None)
        if quick is not None:
            quick.apply_theme()
        act = getattr(self, "_tool_actions", {}).get("theme")
        if act is not None:
            ref = theme.THEME_ICONS.get(theme.current_theme(), theme.THEME_ICONS["default"])
            act.setIcon(self._tool_icon(ref))
            act.setToolTip("界面风格：%s" % theme.THEME_LABELS[theme.current_theme()])
        self._sync_frozen_geometry()

    def _show_theme_menu(self):
        current = theme.current_theme()
        menu = QMenu(self)
        for key in theme.THEME_ORDER:
            act = menu.addAction(
                self._tool_icon(theme.THEME_ICONS[key]), theme.THEME_LABELS[key]
            )
            act.setCheckable(True)
            act.setChecked(key == current)
            act.triggered.connect(lambda _=False, k=key: theme.set_theme(k))
        anchor = None
        tool_act = self._tool_actions.get("theme")
        if tool_act is not None:
            anchor = self.toolbar.widgetForAction(tool_act)
        if anchor is not None and anchor.isVisible():
            menu.exec_(anchor.mapToGlobal(anchor.rect().bottomLeft()))
        else:
            from qgis.PyQt.QtGui import QCursor

            menu.exec_(QCursor.pos())

    def _restore_session_geometry(self):
        global _SESSION_GEOMETRY
        if _SESSION_GEOMETRY is not None:
            try:
                self.restoreGeometry(_SESSION_GEOMETRY)
            except Exception:
                pass

    def _save_session_geometry(self):
        global _SESSION_GEOMETRY
        try:
            _SESSION_GEOMETRY = self.saveGeometry()
        except Exception:
            pass

    def _theme_icon(self, name):
        """QGIS theme icon; name like mActionToggleEditing.svg."""
        try:
            icon = QgsApplication.getThemeIcon(name)
            if icon is not None and not icon.isNull():
                return icon
        except Exception:
            pass
        try:
            icon = QgsApplication.getThemeIcon("/" + name.lstrip("/"))
            if icon is not None and not icon.isNull():
                return icon
        except Exception:
            pass
        return QIcon()

    def _tool_icon(self, icon_ref):
        """Theme svg name, or plugin:filename under attribute_table/icons/."""
        if icon_ref.startswith("plugin:"):
            from qgis.PyQt.QtCore import QSize

            name = icon_ref[len("plugin:") :]
            icons_dir = os.path.join(os.path.dirname(__file__), "icons")
            path = os.path.join(icons_dir, name)
            if os.path.exists(path) and name.lower().endswith(".svg"):
                return QIcon(path)
            icon = QIcon()
            if os.path.exists(path):
                icon.addFile(path)
            # Prefer companion 32px for HiDPI if present (csv_24 -> csv_32)
            if name.endswith("_24.png"):
                path32 = os.path.join(icons_dir, name.replace("_24.png", "_32.png"))
                if os.path.exists(path32):
                    icon.addFile(path32, QSize(32, 32))
            return icon if not icon.isNull() else QIcon()
        return self._theme_icon(icon_ref)

    def _tool_specs(self):
        """id -> (label, callable, icon_ref, checkable)."""
        return {
            "save": ("保存", self._save_edits, "mActionFileSave.svg", False),
            "revert": ("回滚", self._revert_edits, "mActionRollbackEdits.svg", False),
            "reload": ("刷新", self.reload_table, "mActionRefresh.svg", False),
            "edit": ("切换编辑", self._toggle_editing, "mActionToggleEditing.svg", True),
            "copy": ("复制选中要素", self._copy_features, "mActionEditCopy.svg", False),
            "cut": ("剪切选中要素", self._cut_features, "mActionEditCut.svg", False),
            "paste": ("粘贴要素", self._paste_features, "mActionEditPaste.svg", False),
            "delete": ("删除选中要素", self._delete_selected, "mActionDeleteSelected.svg", False),
            "fields": ("字段管理", self._manage_fields, "mActionNewAttribute.svg", False),
            "remarks": (
                "字段备注",
                self._open_remarks_hub,
                "plugin:remarks_24.png",
                False,
            ),
            "display_mode": (
                "值/注显示",
                self._toggle_display_mode,
                "plugin:display_note_24.png",
                False,
            ),
            "quick_name": (
                "快速命名",
                self._open_quick_name,
                "plugin:quick_name_24.png",
                False,
            ),
            "zoom": ("缩放到选中", self._zoom_selected, "mActionZoomToSelected.svg", False),
            "select_all": (
                "全选（当前筛选）",
                self._select_all_filtered,
                "mActionSelectAll.svg",
                False,
            ),
            "invert": (
                "反选（当前筛选）",
                self._invert_selection,
                "mActionInvertSelection.svg",
                False,
            ),
            "deselect": (
                "取消选择",
                self._deselect_all,
                "mActionDeselectAll.svg",
                False,
            ),
            "col_width": (
                "列宽模式",
                self._apply_column_widths,
                "plugin:colwidth_fit_24.png",
                False,
            ),
            "export_csv": ("导出 CSV", self._export_csv, "plugin:csv_24.png", False),
            "export_kmz": (
                "导出 KMZ",
                self._export_kmz,
                "plugin:kmz_24.png",
                False,
            ),
            "theme": (
                "界面风格",
                self._show_theme_menu,
                theme.THEME_ICONS.get(theme.current_theme(), theme.THEME_ICONS["default"]),
                False,
            ),
            "help": ("帮助", self._show_help, "mActionHelpContents.svg", False),
            "customize": (
                "工具栏顺序",
                self._customize_toolbar,
                "mActionOptions.svg",
                False,
            ),
        }

    def _resolved_toolbar_order(self):
        saved = self._settings.load_toolbar_order()
        specs = self._tool_specs()
        known = set(specs.keys())
        if not saved:
            return list(DEFAULT_TOOLBAR_ORDER)
        order = []
        seen = set()
        for tid in saved:
            if tid.startswith("sep"):
                if tid not in seen:
                    order.append(tid)
                    seen.add(tid)
            elif tid in known and tid not in seen:
                order.append(tid)
                seen.add(tid)
        if "fields" in order:
            insert_at = order.index("fields") + 1
            if "remarks" not in seen and "remarks" in known:
                order.insert(insert_at, "remarks")
                seen.add("remarks")
                insert_at += 1
            if "display_mode" not in seen and "display_mode" in known:
                order.insert(insert_at, "display_mode")
                seen.add("display_mode")
        if "remarks" in order and "display_mode" not in seen and "display_mode" in known:
            order.insert(order.index("remarks") + 1, "display_mode")
            seen.add("display_mode")
        if self._settings.load_quick_name_toolbar() and "quick_name" not in seen:
            anchor = "display_mode" if "display_mode" in order else "remarks"
            if anchor in order:
                order.insert(order.index(anchor) + 1, "quick_name")
                seen.add("quick_name")
        if "invert" in order:
            insert_at = order.index("invert") + 1
            for extra in ("deselect", "col_width"):
                if extra not in seen and extra in known:
                    order.insert(insert_at, extra)
                    seen.add(extra)
                    insert_at += 1
        for tid in DEFAULT_TOOLBAR_ORDER:
            if tid.startswith("sep"):
                continue
            if tid not in seen:
                order.append(tid)
                seen.add(tid)
        if "customize" in order:
            order = [t for t in order if t != "customize"] + ["customize"]
        elif "customize" not in order:
            order.append("customize")
        return order

    def _make_tool_action(self, tool_id):
        specs = self._tool_specs()
        if tool_id not in specs or tool_id == "col_width":
            return None
        text, slot, icon_name, checkable = specs[tool_id]
        act = QAction(self._tool_icon(icon_name), text, self)
        act.setToolTip(text)
        act.setStatusTip(text)
        if checkable:
            act.setCheckable(True)
            act.triggered.connect(slot)
        else:
            act.triggered.connect(lambda _checked=False, s=slot: s())
        shortcuts = {
            "cut": QKeySequence.Cut,
            "paste": QKeySequence.Paste,
        }
        if tool_id in shortcuts:
            act.setShortcut(shortcuts[tool_id])
            act.setShortcutContext(Qt.WidgetWithChildrenShortcut)
        return act

    def _rebuild_toolbar(self):
        self.toolbar.clear()
        self._tool_actions = {}
        order = self._resolved_toolbar_order()
        if not self._settings.load_quick_name_toolbar():
            order = [tid for tid in order if tid != "quick_name"]
        for tid in order:
            if tid.startswith("sep"):
                self.toolbar.addSeparator()
                continue
            if tid == "col_width":
                self.toolbar.addWidget(self._ensure_col_width_button())
                continue
            act = self._make_tool_action(tid)
            if act is None:
                continue
            self.toolbar.addAction(act)
            self._tool_actions[tid] = act

        # Convenience aliases used elsewhere
        self.act_save = self._tool_actions.get("save")
        self.act_revert = self._tool_actions.get("revert")
        self.act_reload = self._tool_actions.get("reload")
        self.act_toggle_edit = self._tool_actions.get("edit")
        self.act_delete = self._tool_actions.get("delete")
        self.act_fields = self._tool_actions.get("fields")
        self.act_remarks = self._tool_actions.get("remarks")
        self._sync_remarks_action()
        self.act_display_mode = self._tool_actions.get("display_mode")
        self._sync_display_mode_action()
        self.act_zoom = self._tool_actions.get("zoom")
        self.act_select_all = self._tool_actions.get("select_all")
        self.act_invert = self._tool_actions.get("invert")
        self.act_deselect = self._tool_actions.get("deselect")
        self.act_export = self._tool_actions.get("export_csv")
        self.act_kmz = self._tool_actions.get("export_kmz")
        self.act_help = self._tool_actions.get("help")
        self.act_copy = self._tool_actions.get("copy")
        self.act_cut = self._tool_actions.get("cut")
        self.act_paste = self._tool_actions.get("paste")
        # restore edit checked state after rebuild
        if self.act_toggle_edit is not None and self._layer is not None:
            self.act_toggle_edit.setChecked(self._layer.isEditable())
        if hasattr(self, "fill_bar"):
            self._update_edit_actions()

    def _ensure_col_width_button(self):
        # toolbar.clear() 会销毁旧 widget，每次重建
        btn = QToolButton(self)
        btn.setAutoRaise(True)
        btn.setToolButtonStyle(Qt.ToolButtonIconOnly)
        btn.setIconSize(QSize(24, 24))
        btn.clicked.connect(self._toggle_col_width_mode)
        self.btn_col_width = btn
        self._sync_col_width_button()
        return btn

    def _toggle_col_width_mode(self):
        self._set_col_width_mode("full" if self._col_width_mode != "full" else "fit")

    def _sync_col_width_button(self):
        global _SESSION_COL_WIDTH_MODE
        mode = self._col_width_mode
        _SESSION_COL_WIDTH_MODE = mode
        if self.btn_col_width is None:
            return
        if mode == "full":
            self.btn_col_width.setIcon(self._tool_icon("plugin:colwidth_full_24.png"))
            self.btn_col_width.setToolTip("列宽：完整显示（再点切换为适配窗口）")
        else:
            self.btn_col_width.setIcon(self._tool_icon("plugin:colwidth_fit_24.png"))
            self.btn_col_width.setToolTip("列宽：适配窗口（再点切换为完整显示）")

    def _set_col_width_mode(self, mode):
        self._col_width_mode = "full" if mode == "full" else "fit"
        self._sync_col_width_button()
        self._apply_column_widths()

    def _remarks_active(self):
        session = getattr(self, "_remarks", None)
        if session is None:
            return False
        getter = getattr(session, "is_active", None)
        if callable(getter):
            return bool(getter())
        return bool(getattr(session, "enabled", False))

    def _sync_remarks_action(self):
        act = getattr(self, "act_remarks", None)
        if act is None:
            return
        on = self._remarks_active()
        if on:
            act.setIcon(self._tool_icon("plugin:remarks_24.png"))
            act.setToolTip("字段备注（已套用配置）")
        else:
            act.setIcon(self._tool_icon("plugin:remarks_off_24.png"))
            act.setToolTip("字段备注")

    def _toggle_display_mode(self, *_args):
        if not hasattr(self, "model") or self.model is None:
            return
        self.model.set_show_note(not self.model.show_note())
        self._sync_display_mode_action()
        if self.model.text_filter():
            # 值 mode matches raw values only, 注 mode also matches descriptions.
            self._apply_text_filter_now()

    def _sync_display_mode_action(self):
        act = getattr(self, "act_display_mode", None)
        if act is None or not hasattr(self, "model"):
            return
        note = bool(self.model.show_note())
        if note:
            act.setIcon(self._tool_icon("plugin:display_note_24.png"))
            act.setToolTip("显示：注（再点切换为原值）")
            act.setText("显示注")
        else:
            act.setIcon(self._tool_icon("plugin:display_value_24.png"))
            act.setToolTip("显示：值（再点切换为备注）")
            act.setText("显示值")

    def _apply_column_widths(self):
        if self._applying_col_widths or not hasattr(self, "table"):
            return
        names = self.model.field_names()
        if not names:
            return
        self._applying_col_widths = True
        try:
            for header in (self.table.horizontalHeader(), self.frozen.horizontalHeader()):
                try:
                    header.setMaximumSectionSize(QWIDGETSIZE_MAX)
                    header.setMinimumSectionSize(36)
                    header.setStretchLastSection(False)
                except Exception:
                    pass

            naturals = self._measure_column_natural_widths()
            if len(naturals) != len(names):
                return

            if self._col_width_mode == "full":
                widths = list(naturals)
            else:
                split_w = self.splitter.width()
                if split_w < 50:
                    split_w = self.table.viewport().width()
                if split_w < 50:
                    return
                vh = self.table.verticalHeader().width()
                n_vh = 2 if self.frozen.isVisible() else 1
                sb = 0
                vsb = self.table.verticalScrollBar()
                if vsb is not None and vsb.isVisible():
                    sb = vsb.sizeHint().width()
                available = split_w - vh * n_vh - sb - 4
                if available < 40:
                    return
                total = sum(naturals) or 1
                scale = available / float(total)
                widths = []
                used = 0
                last = len(naturals) - 1
                for i, nat in enumerate(naturals):
                    if i < last:
                        w = max(36, int(round(nat * scale)))
                        widths.append(w)
                        used += w
                    else:
                        widths.append(max(36, available - used))

            for i, w in enumerate(widths):
                self.table.setColumnWidth(i, int(w))
                if i == 0:
                    self.frozen.setColumnWidth(0, int(w))
            self._update_frozen_pane_width()
            if hasattr(self, "quick_fill"):
                self.quick_fill.schedule_sync(0)
        finally:
            self._applying_col_widths = False

    def _measure_column_natural_widths(self):
        names = self.model.field_names()
        texts = self.model.widest_plain_texts(max_chars=48, sample_limit=2500)
        fm = self.table.fontMetrics()
        hfm = self.table.horizontalHeader().fontMetrics()

        def text_w(metrics, s):
            try:
                return metrics.horizontalAdvance(s)
            except AttributeError:
                return metrics.width(s)

        pad = 22
        header_pad = 20
        out = []
        sort_field = self.model.sort_field()
        for name in names:
            header = self.model.header_label(name)
            hw = 0
            for line in str(header).split("\n"):
                hw = max(hw, text_w(hfm, line))
            if sort_field == name:
                hw += text_w(hfm, " ▲")
            cw = 0
            sample = texts.get(name) or ""
            if sample:
                cw = text_w(fm, sample)
            out.append(max(hw + header_pad, cw + pad, 48))
        return out

    def _schedule_column_widths(self, delay=50):
        if not hasattr(self, "_col_width_timer") or not hasattr(self, "table"):
            return
        self._col_width_timer.start(max(0, int(delay)))

    def _update_frozen_pane_width(self):
        if not self.frozen.isVisible():
            return
        total = self.frozen.columnWidth(0) + self.frozen.verticalHeader().width() + 4
        self.frozen.setFixedWidth(total)
        self.splitter.setSizes([total, max(200, self.width() - total)])

    def _customize_toolbar(self):
        specs = self._tool_specs()
        items = [
            (tid, specs[tid][0])
            for tid in DEFAULT_TOOLBAR_ORDER
            if tid in specs and tid != "customize"
        ]
        # also include any extra tool ids not in default list
        for tid, (lab, *_rest) in specs.items():
            if tid != "customize" and tid not in {i[0] for i in items}:
                items.append((tid, lab))
        current = self._resolved_toolbar_order()
        dlg = ToolbarOrderDialog(items, current, self)
        dlg.set_default_order(DEFAULT_TOOLBAR_ORDER)
        dlg.set_show_quick_name(self._settings.load_quick_name_toolbar())
        if dlg.exec_() != QDialog.Accepted:
            return
        order = dlg.result_order()
        self._settings.save_toolbar_order(order)
        self._settings.save_quick_name_toolbar(dlg.show_quick_name())
        self._rebuild_toolbar()

    def _make_combo_shrinkable(self, combo, min_chars=6, min_px=72):
        """Don't let longest item lock the whole dialog width."""
        combo.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        combo.setMinimumContentsLength(min_chars)
        combo.setMinimumWidth(min_px)
        combo.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

    def _theme_host(self, object_name):
        """Group widgets without a filled background. Sizes stay as they are."""
        host = QWidget()
        host.setObjectName(object_name)
        host.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        lay = QHBoxLayout(host)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        return host

    def _theme_label(self, text, color):
        lbl = QLabel(text)
        lbl.setStyleSheet("color: %s; background: transparent;" % color)
        return lbl

    def _theme_combo(self, combo, border):
        combo.setStyleSheet(
            "QComboBox { background-color: palette(base); color: #1a1a1a; border: 1px solid %s; }"
            "QComboBox QLineEdit { background: transparent; color: #1a1a1a; border: none; }"
            "QComboBox QAbstractItemView { background-color: palette(base); color: #111111; }"
            % border
        )

    def _theme_line(self, edit, border):
        edit.setStyleSheet(
            "QLineEdit { background-color: palette(base); color: #1a1a1a; border: 1px solid %s; }"
            % border
        )

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSizeConstraint(QLayout.SetNoConstraint)

        self.toolbar = OverflowToolBar()
        self.toolbar.setMovable(False)
        self.toolbar.setFloatable(False)
        self.toolbar.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self.toolbar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        try:
            from qgis.PyQt.QtCore import QSize

            self.toolbar.setIconSize(QSize(24, 24))
        except Exception:
            pass
        self._rebuild_toolbar()

        root.addWidget(self.toolbar)

        filt_host = QWidget()
        filt_host.setMinimumWidth(0)
        filt_host.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        filt = QHBoxLayout(filt_host)
        filt.setContentsMargins(0, 0, 0, 0)
        filt.setSpacing(4)

        pin_group = self._theme_host("pinGroup")
        pin_group.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        pin_lay = pin_group.layout()
        self.btn_pin = QToolButton()
        self.btn_pin.setObjectName("pinBtn")
        self.btn_pin.setText("钉")
        self.btn_pin.setCheckable(True)
        self.btn_pin.setFixedSize(24, 24)
        self.btn_pin.toggled.connect(self._on_pin_toggled)
        self.chk_pin = self.btn_pin
        pin_lay.addWidget(self.btn_pin)
        self._sync_pin_button(False)

        self.cmb_scope = QComboBox()
        self.cmb_scope.addItem("全部要素", "all")
        self.cmb_scope.addItem("仅选中", "selected")
        self.cmb_scope.addItem("地图可见要素", "canvas")
        self.cmb_scope.addItem("仅已修改", "modified")
        self.cmb_scope.setToolTip(
            "范围：全部要素 / 仅选中 / 地图可见要素（画布范围内，平移缩放后约 500 毫秒刷新）"
            " / 仅已修改（本次编辑里改过、新增、还没保存的要素）"
        )
        self._make_combo_shrinkable(self.cmb_scope, min_chars=6, min_px=108)
        self.cmb_scope.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self._theme_combo(self.cmb_scope, "#3d7ec4")
        self.cmb_scope.currentIndexChanged.connect(self._on_scope_changed)
        pin_lay.addWidget(self.cmb_scope)
        filt.addWidget(pin_group)

        filter_group = self._theme_host("filterGroup")
        filter_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        filter_lay = filter_group.layout()
        filter_lay.addWidget(self._theme_label("过滤", "#2a5a32"))
        self.cmb_filter_field = QComboBox()
        self._make_combo_shrinkable(self.cmb_filter_field, min_chars=5, min_px=72)
        self.cmb_filter_field.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self._theme_combo(self.cmb_filter_field, "#3e8f4e")
        self.cmb_filter_field.currentIndexChanged.connect(self._on_filter_field_changed)
        filter_lay.addWidget(self.cmb_filter_field, 1)

        self.ed_text = QLineEdit()
        self.ed_text.setPlaceholderText("输入即过滤…")
        self.ed_text.setClearButtonEnabled(True)
        self.ed_text.setMinimumWidth(140)
        self.ed_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._theme_line(self.ed_text, "#3e8f4e")
        self.ed_text.textChanged.connect(self._on_filter_text_changed)
        filter_lay.addWidget(self.ed_text, 3)

        screen_group = self._theme_host("screenGroup")
        screen_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        screen_lay = screen_group.layout()
        self.lbl_quick_filter = self._theme_label("筛选", "#8a3a3a")
        screen_lay.addWidget(self.lbl_quick_filter)
        self.cmb_quick_mode = QComboBox()
        self._make_combo_shrinkable(self.cmb_quick_mode, min_chars=4, min_px=72)
        self.cmb_quick_mode.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._theme_combo(self.cmb_quick_mode, "#a34b5a")
        self.cmb_quick_mode.setToolTip("分类筛选，或选择一个字段按其取值筛选")
        self.cmb_quick_mode.currentIndexChanged.connect(self._on_quick_mode_changed)
        screen_lay.addWidget(self.cmb_quick_mode, 1)
        self.cmb_quick_filter = MultiCheckCombo()
        self._make_combo_shrinkable(self.cmb_quick_filter, min_chars=4, min_px=84)
        self.cmb_quick_filter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._theme_combo(self.cmb_quick_filter, "#a34b5a")
        self.cmb_quick_filter.selectionChanged.connect(self._on_quick_filter_changed)
        screen_lay.addWidget(self.cmb_quick_filter, 2)

        freeze_group = self._theme_host("freezeGroup")
        freeze_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        freeze_lay = freeze_group.layout()
        freeze_lay.addWidget(self._theme_label("冻结", "#6a5420"))
        self.cmb_freeze = QComboBox()
        self._make_combo_shrinkable(self.cmb_freeze, min_chars=8, min_px=96)
        self.cmb_freeze.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._theme_combo(self.cmb_freeze, "#c4962a")
        self.cmb_freeze.setToolTip("将指定字段固定到首列并冻结显示")
        self.cmb_freeze.currentIndexChanged.connect(self._on_freeze_field_changed)
        freeze_lay.addWidget(self.cmb_freeze, 1)

        # 钉 + 范围 → 冻结 → 筛选 → 过滤
        filt.addWidget(freeze_group, 2)
        filt.addWidget(screen_group, 3)
        filt.addWidget(filter_group, 4)

        self.fill_bar = QWidget()
        self.fill_bar.setObjectName("fillBar")
        self.fill_bar.setMinimumWidth(0)
        self.fill_bar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        fill = QHBoxLayout(self.fill_bar)
        fill.setContentsMargins(0, 2, 0, 0)
        fill.setSpacing(4)
        fill.addWidget(self._theme_label("赋值：", "#4a3d66"))
        self.cmb_fill_field = QComboBox()
        self._make_combo_shrinkable(self.cmb_fill_field, min_chars=8, min_px=100)
        self.cmb_fill_field.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self._theme_combo(self.cmb_fill_field, "#7b5ea8")
        self.cmb_fill_field.setToolTip("要写入的目标字段")
        self.cmb_fill_field.currentIndexChanged.connect(self._on_fill_field_changed)
        fill.addWidget(self.cmb_fill_field)
        fill.addWidget(self._theme_label("=", "#4a3d66"))
        self.cmb_fill_mode = QComboBox()
        self.cmb_fill_mode.addItem("常量", "const")
        self.cmb_fill_mode.addItem("只填空白", "blank")
        self.cmb_fill_mode.addItem("序号", "seq")
        self.cmb_fill_mode.addItem("前缀+序号", "prefix_seq")
        self.cmb_fill_mode.addItem("前后序号", "around_seq")
        self.cmb_fill_mode.addItem("前后加字", "affix")
        self.cmb_fill_mode.addItem("表达式", "expr")
        self.cmb_fill_mode.addItem("替换", "replace")
        self.cmb_fill_mode.setToolTip(
            "常量：直接填 1 或文字；也可输入字段名引用其内容\n"
            "只填空白：同上，但已有内容的格子不动\n"
            "序号：按当前表筛选顺序递增。位数可选不补零、自动或指定位数\n"
            "前缀+序号：如填 A，不补零为 A1、A2；4 位为 A0001\n"
            "前后序号：在已有文字前面或后面加上序号（只选一边），原文字保留，序号用位数补零\n"
            "前后加字：在已有文字前或后追加，空白不动\n"
            "表达式：QGIS 表达式\n"
            "替换：对目标字段做部分文字替换（一格多处全部替换）"
        )
        self._make_combo_shrinkable(self.cmb_fill_mode, min_chars=5, min_px=96)
        self._theme_combo(self.cmb_fill_mode, "#7b5ea8")
        self.cmb_fill_mode.currentIndexChanged.connect(self._on_fill_mode_changed)
        fill.addWidget(self.cmb_fill_mode)
        self._fill_width_group = self._theme_host("fillWidthGroup")
        self._fill_width_group.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        width_lay = self._fill_width_group.layout()
        self.lbl_fill_width = self._theme_label("位数", "#2a4568")
        self.cmb_fill_width = QComboBox()
        self.cmb_fill_width.addItem("不补零", "none")
        self.cmb_fill_width.addItem("自动", "auto")
        for _width in (2, 3, 4, 5, 6, 8, 10):
            self.cmb_fill_width.addItem("%d位" % _width, _width)
        self.cmb_fill_width.setToolTip(
            "不补零：1、2、3\n"
            "自动：按本次最大序号的位数补零。从 1 写到 100 为 001，写到 1000 为 0001\n"
            "指定位数：4 位为 0001。超出位数不截断（10000 仍是 10000）\n"
            "前导零只留在文本字段"
        )
        self._make_combo_shrinkable(self.cmb_fill_width, min_chars=4, min_px=72)
        self._theme_combo(self.cmb_fill_width, "#3d7ab5")
        width_lay.addWidget(self.lbl_fill_width)
        width_lay.addWidget(self.cmb_fill_width)
        fill.addWidget(self._fill_width_group)
        self._fill_side_group = self._theme_host("fillSideGroup")
        self._fill_side_group.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        side_lay = self._fill_side_group.layout()
        self.lbl_fill_seq_side = self._theme_label("加在", "#6a4530")
        self.cmb_fill_seq_side = QComboBox()
        self.cmb_fill_seq_side.addItem("后面", "after")
        self.cmb_fill_seq_side.addItem("前面", "before")
        self.cmb_fill_seq_side.setToolTip("序号加在已有文字的前面或后面，只选一边。原文字保留。")
        self._make_combo_shrinkable(self.cmb_fill_seq_side, min_chars=2, min_px=64)
        self._theme_combo(self.cmb_fill_seq_side, "#c47a45")
        side_lay.addWidget(self.lbl_fill_seq_side)
        side_lay.addWidget(self.cmb_fill_seq_side)
        fill.addWidget(self._fill_side_group)
        self.lbl_fill_prefix = self._theme_label("前面", "#4a3d66")
        self.ed_fill_prefix = QLineEdit()
        self.ed_fill_prefix.setClearButtonEnabled(True)
        self.ed_fill_prefix.setPlaceholderText("加在现有文字前，可空")
        self.ed_fill_prefix.setMinimumWidth(48)
        self._theme_line(self.ed_fill_prefix, "#7b5ea8")
        self.ed_fill_prefix.setToolTip("加在已有文字前面。空白单元格不会被改成只有这段字。")
        fill.addWidget(self.lbl_fill_prefix)
        fill.addWidget(self.ed_fill_prefix, 1)
        self.lbl_fill_suffix = self._theme_label("后面", "#4a3d66")
        self.ed_fill_suffix = QLineEdit()
        self.ed_fill_suffix.setClearButtonEnabled(True)
        self.ed_fill_suffix.setPlaceholderText("加在现有文字后，可空")
        self.ed_fill_suffix.setMinimumWidth(48)
        self._theme_line(self.ed_fill_suffix, "#7b5ea8")
        self.ed_fill_suffix.setToolTip("加在已有文字后面。空白单元格不动。")
        fill.addWidget(self.lbl_fill_suffix)
        fill.addWidget(self.ed_fill_suffix, 1)
        self.cmb_fill_preset = QComboBox()
        self._make_combo_shrinkable(self.cmb_fill_preset, min_chars=4, min_px=72)
        self._theme_combo(self.cmb_fill_preset, "#7b5ea8")
        self.cmb_fill_preset.setToolTip("常用值：点选填入常量")
        try:
            self.cmb_fill_preset.activated[int].connect(self._on_fill_preset_chosen)
        except Exception:
            self.cmb_fill_preset.activated.connect(self._on_fill_preset_chosen)
        fill.addWidget(self.cmb_fill_preset)
        self.btn_fill_expr = QPushButton("ε")
        self.btn_fill_expr.setFixedWidth(28)
        self.btn_fill_expr.setToolTip("打开表达式构建器")
        self.btn_fill_expr.clicked.connect(self._open_fill_expression_builder)
        fill.addWidget(self.btn_fill_expr)
        self.ed_fill = QLineEdit()
        self.ed_fill.setClearButtonEnabled(True)
        self.ed_fill.setMinimumWidth(60)
        self.ed_fill.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._theme_line(self.ed_fill, "#7b5ea8")
        self._fill_field_model = QStringListModel(self)
        self._fill_field_completer = QCompleter(self._fill_field_model, self)
        self._fill_field_completer.setCaseSensitivity(Qt.CaseInsensitive)
        self._fill_field_completer.setCompletionMode(QCompleter.PopupCompletion)
        try:
            self._fill_field_completer.setFilterMode(Qt.MatchContains)
        except Exception:
            pass
        self._fill_field_completer.setMaxVisibleItems(12)
        self.ed_fill.setCompleter(self._fill_field_completer)
        fill.addWidget(self.ed_fill, 1)
        self.lbl_fill_find = self._theme_label("替换前", "#4a3d66")
        fill.addWidget(self.lbl_fill_find)
        self.ed_fill_find = QLineEdit()
        self.ed_fill_find.setClearButtonEnabled(True)
        self.ed_fill_find.setPlaceholderText("要替换的文字（部分匹配）")
        self.ed_fill_find.setMinimumWidth(48)
        self._theme_line(self.ed_fill_find, "#7b5ea8")
        fill.addWidget(self.ed_fill_find, 1)
        self.lbl_fill_replace = self._theme_label("替换后", "#4a3d66")
        fill.addWidget(self.lbl_fill_replace)
        self.ed_fill_replace = QLineEdit()
        self.ed_fill_replace.setClearButtonEnabled(True)
        self.ed_fill_replace.setPlaceholderText("替换成…（可空=删除该段）")
        self.ed_fill_replace.setMinimumWidth(48)
        self._theme_line(self.ed_fill_replace, "#7b5ea8")
        fill.addWidget(self.ed_fill_replace, 1)
        self._fill_stretch_index = fill.count()
        fill.addStretch(1)
        self.btn_fill_filtered = QPushButton("更新筛选行")
        self.btn_fill_filtered.setToolTip("更新当前表格筛选后的全部行（含未滚到的）")
        self.btn_fill_filtered.clicked.connect(lambda: self._run_fill(selected_only=False))
        fill.addWidget(self.btn_fill_filtered)
        self.btn_fill_selected = QPushButton("更新选中")
        self.btn_fill_selected.setToolTip("仅更新地图/表中已选中的要素")
        self.btn_fill_selected.clicked.connect(lambda: self._run_fill(selected_only=True))
        fill.addWidget(self.btn_fill_selected)
        self.fill_bar.setVisible(False)
        root.addWidget(filt_host)
        root.addWidget(self.fill_bar)
        self._on_fill_mode_changed()

        self.quick_fill = QuickFillBar(self)
        self.quick_fill.setVisible(False)
        root.addWidget(self.quick_fill)

        self.splitter = QSplitter(Qt.Horizontal)
        self.frozen = QTableView()
        self.table = QTableView()
        for view in (self.frozen, self.table):
            view.setModel(self.model)
            view.setSelectionBehavior(QAbstractItemView.SelectItems)
            view.setSelectionMode(QAbstractItemView.ExtendedSelection)
            view.setAlternatingRowColors(True)
            view.setSortingEnabled(False)
            view.verticalHeader().setDefaultSectionSize(22)
            view.setWordWrap(False)
            view.setMinimumWidth(0)
            view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            try:
                view.setSizeAdjustPolicy(QAbstractScrollArea.AdjustIgnored)
            except Exception:
                pass
            view.horizontalHeader().setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            view.horizontalHeader().setMinimumHeight(40)
            try:
                view.horizontalHeader().setMaximumSectionSize(QWIDGETSIZE_MAX)
                view.horizontalHeader().setMinimumSectionSize(36)
                view.horizontalHeader().setStretchLastSection(False)
            except Exception:
                pass
        self._vm_delegate = ValueMapDelegate(self.model)
        self.table.setItemDelegate(self._vm_delegate)
        self.frozen.setItemDelegate(self._vm_delegate)
        self.frozen.setFocusPolicy(Qt.NoFocus)
        self.frozen.horizontalHeader().setStretchLastSection(False)
        self.frozen.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.frozen.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.table.horizontalHeader().setSectionsMovable(True)
        self.table.horizontalHeader().sectionClicked.connect(self._on_header_clicked)
        self.table.horizontalHeader().sectionMoved.connect(self._on_section_moved)
        self.frozen.horizontalHeader().sectionClicked.connect(self._on_header_clicked)
        self._header_filters = []
        for header in (self.table.horizontalHeader(), self.frozen.horizontalHeader()):
            header.setSectionsClickable(True)
            # Prevent Qt default context handling; we use event filter
            header.setContextMenuPolicy(Qt.NoContextMenu)
            filt = _HeaderRightClickFilter(self, header)
            header.installEventFilter(filt)
            self._header_filters.append(filt)
        for header in (self.table.verticalHeader(), self.frozen.verticalHeader()):
            header.setContextMenuPolicy(Qt.NoContextMenu)
            filt = _HeaderRightClickFilter(self, header, self._show_row_header_menu)
            header.installEventFilter(filt)
            self._header_filters.append(filt)
        self.table.verticalHeader().sectionClicked.connect(self._on_row_header_clicked)
        self.frozen.verticalHeader().sectionClicked.connect(self._on_row_header_clicked)
        self.table.verticalHeader().sectionDoubleClicked.connect(
            self._on_row_header_double_clicked
        )
        self.frozen.verticalHeader().sectionDoubleClicked.connect(
            self._on_row_header_double_clicked
        )
        self._copy_filters = []
        for view in (self.table, self.frozen):
            filt = _CopyShortcutFilter(self, view)
            view.installEventFilter(filt)
            self._copy_filters.append(filt)
        self.table.selectionModel().selectionChanged.connect(self._on_table_selection)
        self.frozen.selectionModel().selectionChanged.connect(self._on_frozen_selection)
        self.table.selectionModel().currentChanged.connect(self._on_table_current_changed)
        self.frozen.selectionModel().currentChanged.connect(self._on_frozen_current_changed)

        self.table.verticalScrollBar().valueChanged.connect(
            self.frozen.verticalScrollBar().setValue
        )
        self.frozen.verticalScrollBar().valueChanged.connect(
            self.table.verticalScrollBar().setValue
        )
        # Both viewports must be equally tall or the synced scroll values drift apart
        # near the bottom: mirror the main table's horizontal bar on the frozen side.
        self.table.horizontalScrollBar().rangeChanged.connect(
            lambda *_a: self._sync_frozen_geometry()
        )
        self.model.headerDataChanged.connect(lambda *_a: self._sync_frozen_geometry())
        self.model.modelReset.connect(self._sync_frozen_geometry)
        self.model.layoutChanged.connect(self._sync_frozen_geometry)
        self.table.horizontalScrollBar().valueChanged.connect(
            lambda _v: self.quick_fill.schedule_sync(0)
        )
        self.table.horizontalHeader().sectionResized.connect(
            lambda *_a: self.quick_fill.schedule_sync(0)
        )
        self.table.horizontalHeader().sectionMoved.connect(
            lambda *_a: self.quick_fill.schedule_sync(0)
        )
        self.frozen.horizontalHeader().sectionResized.connect(
            lambda *_a: self.quick_fill.schedule_sync(0)
        )

        self.splitter.addWidget(self.frozen)
        self.splitter.addWidget(self.table)
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setMinimumWidth(0)
        self.splitter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.splitter.splitterMoved.connect(lambda *_a: self.quick_fill.schedule_sync(0))
        root.addWidget(self.splitter, 1)

        self.status = QStatusBar()
        self.status.setSizeGripEnabled(False)
        self.lbl_stats = QLabel()
        self.lbl_stats.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.status.addPermanentWidget(self.lbl_stats)
        root.addWidget(self.status)

        self._update_frozen_visibility()
        self._update_edit_actions()

    def _connect_project(self):
        QgsProject.instance().layersWillBeRemoved.connect(self._on_layers_removed)
        try:
            QgsProject.instance().readProject.connect(self._on_project_read)
        except Exception:
            pass
        try:
            QgsProject.instance().cleared.connect(self._on_project_cleared)
        except Exception:
            pass
        try:
            self.iface.currentLayerChanged.connect(self._on_current_layer_changed)
        except Exception:
            pass

    def _on_project_read(self, *_args):
        self._remarks.load()
        self._apply_remarks_to_ui()
        self._update_edit_actions()
        hub = getattr(self, "_remarks_hub", None)
        if hub is not None:
            hub._reload_combo()
            hub._sync_enable_buttons()
            hub.reload_from_session()

    def _on_project_cleared(self):
        self._remarks.load()
        self._apply_remarks_to_ui()
        self._update_edit_actions()

    def _update_window_title(self):
        if self._layer is None:
            self.setWindowTitle("无图层")
            return
        mode = "编辑中" if self._layer.isEditable() else "只读"
        self.setWindowTitle(f"{self._layer.name()} — {mode}")

    def _on_pin_toggled(self, checked):
        self._pin_layer = checked
        self._sync_pin_button(checked)

    def _sync_pin_button(self, checked=None):
        btn = getattr(self, "btn_pin", None)
        if btn is None:
            return
        if checked is None:
            checked = bool(btn.isChecked())
        if checked:
            btn.setStyleSheet(
                "QToolButton#pinBtn { color: #c62828; font-weight: 700; font-size: 13px; "
                "border: 1px solid #c62828; border-radius: 3px; background: palette(button); "
                "padding: 0; min-width: 22px; }"
            )
            btn.setToolTip("已钉住当前图层（再点取消）")
        else:
            btn.setStyleSheet(
                "QToolButton#pinBtn { color: #3d7ec4; font-weight: 400; font-size: 13px; "
                "border: 1px solid #3d7ec4; border-radius: 3px; background: palette(button); "
                "padding: 0; min-width: 22px; }"
            )
            btn.setToolTip("钉住图层：不随图例切换当前表")

    def _on_current_layer_changed(self, layer):
        if self._pin_layer:
            return
        self.set_layer(layer)

    def _on_layers_removed(self, layer_ids):
        if self._layer is not None and self._layer.id() in layer_ids:
            self.set_layer(None)

    def _load_active_layer(self):
        self.set_layer(self.iface.activeLayer())

    def set_layer(self, layer):
        self._disconnect_layer_signals()
        self._reload_timer.stop()
        self._selected_scope_timer.stop()
        self._invalidate_layer_value_cache()

        if layer is not None and (
            not hasattr(layer, "type") or layer.type() != QgsMapLayer.VectorLayer
        ):
            layer = None

        self._layer = layer
        self._update_window_title()

        if layer is None:
            self.model.set_layer(None)
            self._all_field_names = []
            self._field_labels = {}
            self._visible_fields = []
            self._freeze_field = ""
            self._rebuild_filter_field_combo()
            self._rebuild_quick_filter()
            self._rebuild_freeze_combo()
            self._rebuild_fill_field_combo()
            self._apply_remarks_to_ui()
            self._update_canvas_extent_watch()
            self._update_edit_actions()
            self._update_status()
            return

        self._all_field_names = [f.name() for f in layer.fields()]
        # Always start fresh: layer native field order, no freeze
        self._visible_fields = list(self._all_field_names)
        self._freeze_field = ""
        self._clear_column_stats()

        # Rows are built once, by _apply_text_filter_now at the end.
        self.model.set_layer(layer, rebuild=False)
        self.model.set_display_fields(self._visible_fields)
        self._apply_remarks_to_ui()
        self._update_frozen_visibility()
        self._connect_layer_signals()
        self.act_toggle_edit.setChecked(layer.isEditable())
        self._update_edit_actions()
        self._update_window_title()
        self._update_canvas_extent_watch()
        self._rebuild_quick_filter()
        self._apply_scope_now(reload_now=False)
        self._apply_text_filter_now()
        self._update_row_header_width()
        self._update_status()
        self._sync_selection_from_layer()
        self._schedule_column_widths()

    def _rebuild_filter_field_combo(self):
        current = self.cmb_filter_field.currentData()
        self.cmb_filter_field.blockSignals(True)
        self.cmb_filter_field.clear()
        self.cmb_filter_field.addItem("所有字段", None)
        for name in self._all_field_names:
            self.cmb_filter_field.addItem(self._field_labels.get(name, name), name)
        idx = self.cmb_filter_field.findData(current) if current else 0
        self.cmb_filter_field.setCurrentIndex(idx if idx >= 0 else 0)
        self.cmb_filter_field.blockSignals(False)

    def _usable_categories(self):
        if self._layer is None:
            return []
        try:
            items, _err = layer_categories(self._layer)
        except Exception:
            return []
        return [it for it in items if (it.get("filter_expr") or "").strip()]

    def _rebuild_quick_filter(self):
        mode_combo = getattr(self, "cmb_quick_mode", None)
        value_combo = getattr(self, "cmb_quick_filter", None)
        if mode_combo is None or value_combo is None:
            return
        prev_mode = mode_combo.currentData() if mode_combo.count() else None
        prev_exprs = set(value_combo.checked_payloads())
        categories = self._usable_categories()
        mode_combo.blockSignals(True)
        mode_combo.clear()
        if categories:
            mode_combo.addItem("分类筛选", QUICK_MODE_CATEGORY)
        for name in self._all_field_names:
            mode_combo.addItem(self._field_labels.get(name, name), name)
        if mode_combo.count() == 0:
            mode_combo.addItem("（无字段）", "")
        restore = mode_combo.findData(prev_mode) if prev_mode else -1
        same_mode = restore >= 0
        mode_combo.setCurrentIndex(restore if same_mode else 0)
        mode_combo.blockSignals(False)
        self._fill_quick_values(prev_exprs if same_mode else set())

    def _fill_quick_values(self, checked_exprs):
        combo = self.cmb_quick_filter
        mode = self.cmb_quick_mode.currentData()
        combo.blockSignals(True)
        combo.clear_items()
        items = []
        truncated = False
        if mode == QUICK_MODE_CATEGORY:
            for it in self._usable_categories():
                items.append((it.get("label") or "(未命名)", it.get("filter_expr") or ""))
        elif mode:
            items, truncated = self._field_value_choices(mode)
        wanted = set(checked_exprs or ())
        matched = False
        combo.add_check_item("全部", None, True)
        for label, expr in items:
            checked = expr in wanted
            if checked:
                matched = True
            combo.add_check_item(label, expr, checked)
        if truncated:
            combo.add_note("仅列出前 %d 个值" % QUICK_VALUE_LIMIT)
        if matched:
            all_item = combo.model().item(0)
            if all_item is not None:
                all_item.setCheckState(Qt.Unchecked)
        else:
            combo.ensure_some_check()
        combo._sync_text()
        combo.blockSignals(False)

    def _field_value_choices(self, field_name):
        layer = self._layer
        if layer is None:
            return [], False
        field_idx = layer.fields().indexFromName(field_name)
        if field_idx < 0:
            return [], False
        seen = {}
        blank = False
        truncated = False
        req = (
            QgsFeatureRequest()
            .setFlags(QgsFeatureRequest.NoGeometry)
            .setSubsetOfAttributes([field_idx])
        )
        try:
            features = layer.getFeatures(req)
        except Exception:
            return [], False
        try:
            feature_iter = iter(features)
        except Exception:
            return [], False
        while True:
            try:
                feat = next(feature_iter)
            except StopIteration:
                break
            except Exception:
                break
            raw = feat.attribute(field_idx)
            if raw is None or raw == NULL or str(raw).strip() == "":
                blank = True
                continue
            key = value_key(raw)
            if key in seen:
                continue
            if len(seen) >= QUICK_VALUE_LIMIT:
                truncated = True
                break
            seen[key] = raw
        rows = []
        if blank:
            rows.append((0, 0.0, "", "(空)", "(空)", _blank_field_expr(field_name)))
        for raw in seen.values():
            num = try_parse_number(raw)
            plain = _plain_attr(raw)
            desc = ""
            try:
                desc = qgis_description_for_value(layer, field_name, raw) or ""
            except Exception:
                desc = ""
            label = desc if desc and desc != plain else plain
            expr = field_eq_expression(field_name, _expr_attr(raw))
            if num is not None:
                rows.append((1, float(num), "", label, plain, expr))
            else:
                rows.append((2, 0.0, plain.casefold(), label, plain, expr))
        rows.sort(key=lambda row: (row[0], row[1], row[2], row[3]))
        counts = Counter(row[3] for row in rows)
        items = []
        for _kind, _num, _text, label, plain, expr in rows:
            if counts[label] > 1 and label != plain:
                items.append(("%s（%s）" % (label, plain), expr))
            else:
                items.append((label, expr))
        return items, truncated

    def _on_quick_mode_changed(self, _index):
        self._fill_quick_values(set())
        self._on_quick_filter_changed(0)

    def _on_quick_filter_changed(self, _index=None):
        expr = ""
        if hasattr(self, "cmb_quick_filter"):
            expr = self.cmb_quick_filter.expression()
        self.model.set_category_filter(expr)
        self._update_row_header_width()
        if self.model.sort_field():
            self._refresh_column_stats(self.model.sort_field())
        else:
            self._clear_column_stats()
        self._update_status()
        self._schedule_column_widths()

    def _sync_quick_mode_labels(self):
        combo = getattr(self, "cmb_quick_mode", None)
        if combo is None:
            return
        for i in range(combo.count()):
            data = combo.itemData(i)
            if data and data != QUICK_MODE_CATEGORY:
                combo.setItemText(i, self._field_labels.get(data, data))

    def _schedule_quick_value_refresh(self, field_index=None):
        mode = self.cmb_quick_mode.currentData() if hasattr(self, "cmb_quick_mode") else None
        if not mode or mode == QUICK_MODE_CATEGORY:
            return
        if field_index is not None and self._layer is not None:
            idx = self._layer.fields().indexFromName(str(mode))
            try:
                if idx >= 0 and int(field_index) != idx:
                    return
            except (TypeError, ValueError):
                return
        self._quick_value_timer.start(FILTER_DELAY_MS)

    def _refresh_quick_values_keep(self):
        if not hasattr(self, "cmb_quick_filter") or self.model is None:
            return
        before = self.model.category_filter()
        self._fill_quick_values(set(self.cmb_quick_filter.checked_payloads()))
        if self.cmb_quick_filter.expression() != before:
            self._on_quick_filter_changed(0)

    def _rebuild_freeze_combo(self):
        self.cmb_freeze.blockSignals(True)
        self.cmb_freeze.clear()
        self.cmb_freeze.addItem("不冻结", "")
        for name in self._all_field_names:
            self.cmb_freeze.addItem(self._field_labels.get(name, name), name)
        idx = self.cmb_freeze.findData(self._freeze_field)
        self.cmb_freeze.setCurrentIndex(idx if idx >= 0 else 0)
        self.cmb_freeze.blockSignals(False)

    def _rebuild_fill_field_combo(self):
        self.cmb_fill_field.blockSignals(True)
        current = self.cmb_fill_field.currentData()
        self.cmb_fill_field.clear()
        for name in self._all_field_names:
            self.cmb_fill_field.addItem(self._field_labels.get(name, name), name)
        if current:
            idx = self.cmb_fill_field.findData(current)
            if idx >= 0:
                self.cmb_fill_field.setCurrentIndex(idx)
        self.cmb_fill_field.blockSignals(False)
        self._rebuild_fill_presets()
        self._sync_fill_field_completer()

    def _connect_layer_signals(self):
        layer = self._layer
        if layer is None:
            return
        layer.selectionChanged.connect(self._on_layer_selection_changed)
        layer.editingStarted.connect(self._on_editing_started)
        layer.editingStopped.connect(self._on_editing_stopped)
        layer.attributeValueChanged.connect(self._on_attribute_changed)
        layer.featureAdded.connect(self._on_feature_added)
        layer.featureDeleted.connect(self._on_feature_deleted)
        for signal, slot in self._optional_layer_signals(layer):
            try:
                signal.connect(slot)
            except Exception:
                pass

    def _optional_layer_signals(self, layer):
        pairs = []
        for name, slot in (
            ("rendererChanged", self._on_layer_renderer_changed),
            ("updatedFields", self._on_layer_fields_updated),
            ("layerModified", self._on_layer_modified),
            ("afterCommitChanges", self._on_layer_edits_flushed),
            ("afterRollBack", self._on_layer_edits_flushed),
        ):
            signal = getattr(layer, name, None)
            if signal is not None:
                pairs.append((signal, slot))
        return pairs

    def _disconnect_layer_signals(self):
        layer = self._layer
        if layer is None:
            return
        for signal, slot in (
            (layer.selectionChanged, self._on_layer_selection_changed),
            (layer.editingStarted, self._on_editing_started),
            (layer.editingStopped, self._on_editing_stopped),
            (layer.attributeValueChanged, self._on_attribute_changed),
            (layer.featureAdded, self._on_feature_added),
            (layer.featureDeleted, self._on_feature_deleted),
        ) + tuple(self._optional_layer_signals(layer)):
            if signal is None:
                continue
            try:
                signal.disconnect(slot)
            except Exception:
                pass

    def _on_layer_renderer_changed(self):
        self._rebuild_quick_filter()
        self._on_quick_filter_changed(0)

    def _schedule_reload(self, delay=40):
        """Coalesce bursts (e.g. deleting 1000 features = 1000 signals) into one reload."""
        self._invalidate_layer_value_cache()
        self._reload_timer.start(max(0, int(delay)))

    def _on_feature_added(self, _fid):
        self._schedule_reload()
        self._schedule_quick_value_refresh()

    def _on_feature_deleted(self, _fid):
        self._schedule_reload()
        self._schedule_quick_value_refresh()

    def _on_layer_modified(self):
        self._invalidate_layer_value_cache()
        self.model.invalidate_modified()
        self._status_timer.start(150)
        if self._current_scope_mode() == "modified":
            self._schedule_reload(300)

    def _on_layer_edits_flushed(self, *_args):
        self.model.invalidate_modified()
        self._schedule_reload()

    def _on_layer_fields_updated(self):
        layer = self._layer
        if layer is None:
            return
        try:
            names = [f.name() for f in layer.fields()]
        except RuntimeError:
            return
        if names == self._all_field_names and self.model.fields_match_layer():
            return
        self._refresh_field_structure()

    def _refresh_field_structure(self):
        """Re-read layer fields after add/delete/rename; keep filters, sort and column order."""
        layer = self._layer
        if layer is None:
            return
        self._all_field_names = [f.name() for f in layer.fields()]
        self._visible_fields = [n for n in self._visible_fields if n in self._all_field_names]
        for n in self._all_field_names:
            if n not in self._visible_fields:
                self._visible_fields.append(n)
        if self._freeze_field and self._freeze_field not in self._all_field_names:
            self._freeze_field = ""
        self._apply_freeze_to_visible_order()
        self._invalidate_layer_value_cache()
        self.model.refresh_fields(self._visible_fields)
        self._apply_remarks_to_ui()
        self._rebuild_quick_filter()
        self._apply_text_filter_now()
        self._update_frozen_visibility()
        self._update_row_header_width()

    def _on_scope_changed(self, _index):
        self._update_canvas_extent_watch()
        self._apply_scope_now()
        self._update_row_header_width()
        if self.model.sort_field():
            self._refresh_column_stats(self.model.sort_field())
        self._update_status()
        self._schedule_column_widths()

    def _current_scope_mode(self):
        mode = self.cmb_scope.currentData()
        return mode if mode else "all"

    def _map_extent_in_layer_crs(self):
        layer = self._layer
        if layer is None:
            return None
        try:
            canvas = self.iface.mapCanvas()
            extent = canvas.extent()
            canvas_crs = canvas.mapSettings().destinationCrs()
            layer_crs = layer.crs()
            if canvas_crs != layer_crs:
                xform = QgsCoordinateTransform(
                    canvas_crs, layer_crs, QgsProject.instance()
                )
                extent = xform.transformBoundingBox(extent)
            return extent
        except Exception:
            return None

    def _apply_scope_now(self, reload_now=True):
        mode = self._current_scope_mode()
        rect = self._map_extent_in_layer_crs() if mode == "canvas" else None
        if mode == "canvas" and rect is None and self._layer is not None:
            self.status.showMessage("地图范围无法换算到图层坐标系，「地图可见」没有结果", 5000)
        return self.model.set_scope_mode(mode, rect, reload_now=reload_now)

    def _update_canvas_extent_watch(self):
        canvas = None
        try:
            canvas = self.iface.mapCanvas()
        except Exception:
            canvas = None
        if canvas is not None and self._watching_canvas:
            try:
                canvas.extentsChanged.disconnect(self._on_canvas_extents_changed)
            except Exception:
                pass
            self._watching_canvas = False
        if canvas is not None and self._current_scope_mode() == "canvas":
            try:
                canvas.extentsChanged.connect(self._on_canvas_extents_changed)
                self._watching_canvas = True
            except Exception:
                self._watching_canvas = False

    def _on_canvas_extents_changed(self):
        if self._current_scope_mode() != "canvas":
            return
        self._canvas_scope_timer.stop()
        self._canvas_scope_timer.start(FILTER_DELAY_MS)

    def _refresh_after_canvas_scope(self):
        if self._current_scope_mode() != "canvas":
            return
        rect = self._map_extent_in_layer_crs()
        last = self.model.canvas_rect()
        if rect is not None and last is not None and rect == last:
            return
        self._apply_scope_now()
        self._update_row_header_width()
        if self.model.sort_field():
            self._refresh_column_stats(self.model.sort_field())
        self._update_status()
        self._schedule_column_widths()

    def _on_filter_text_changed(self, _text):
        self._filter_timer.stop()
        self._filter_timer.start(FILTER_DELAY_MS)

    def _on_filter_field_changed(self, _index):
        # field change applies immediately with current text
        self._filter_timer.stop()
        self._apply_text_filter_now()

    def _apply_text_filter_now(self):
        field_name = self.cmb_filter_field.currentData()
        if hasattr(self, "cmb_quick_filter"):
            self.model.set_category_filter(
                self.cmb_quick_filter.expression(), reload_now=False
            )
        self.model.set_text_filter(self.ed_text.text(), field_name=field_name)
        self._update_row_header_width()
        # keep stats for current sort field
        if self.model.sort_field():
            self._refresh_column_stats(self.model.sort_field())
        else:
            self._clear_column_stats()
        self._update_status()
        self._schedule_column_widths()

    def reload_table(self):
        self._reload_timer.stop()
        self._invalidate_layer_value_cache()
        if self._layer is not None:
            view_state = self._capture_view_state()
            self.model.reload()
            self._restore_view_state(view_state)
        self._update_row_header_width()
        self._update_frozen_visibility()
        if self.model.sort_field():
            self._refresh_column_stats(self.model.sort_field())
        self._update_status()

    def _capture_view_state(self):
        state = {"fid": None, "field": None, "v": 0, "h": 0}
        try:
            cur = self.table.currentIndex()
            if cur.isValid():
                state["fid"] = self.model.fid_at(cur.row())
                names = self.model.field_names()
                if 0 <= cur.column() < len(names):
                    state["field"] = names[cur.column()]
            state["v"] = self.table.verticalScrollBar().value()
            state["h"] = self.table.horizontalScrollBar().value()
        except Exception:
            pass
        return state

    def _restore_view_state(self, state):
        if not state:
            return
        try:
            row = self.model.row_for_fid(state["fid"]) if state["fid"] is not None else -1
            names = self.model.field_names()
            col = names.index(state["field"]) if state["field"] in names else -1
            if row >= 0 and col >= 0:
                self.table.selectionModel().setCurrentIndex(
                    self.model.index(row, col), QItemSelectionModel.NoUpdate
                )
            vsb = self.table.verticalScrollBar()
            vsb.setValue(min(state["v"], vsb.maximum()))
            hsb = self.table.horizontalScrollBar()
            hsb.setValue(min(state["h"], hsb.maximum()))
        except Exception:
            pass
        self._sync_selection_from_layer()

    def _update_row_header_width(self):
        """
        Vertical header width ≈ 2× natural width for current row-count digits.
        Adapts to 1 vs 10000 rows; not a fixed pixel size.
        """
        nrows = max(self.model.rowCount(), 1)
        sample = str(nrows)  # widest label when 1-based
        for view in (self.table, self.frozen):
            vh = view.verticalHeader()
            fm = vh.fontMetrics()
            try:
                text_w = fm.horizontalAdvance(sample)
            except AttributeError:
                text_w = fm.width(sample)
            try:
                margin = vh.style().pixelMetric(vh.style().PM_HeaderMargin, None, vh)
            except Exception:
                margin = 4
            natural = text_w + margin * 2 + 8
            width = max(int(natural * 2), 36)
            vh.setMinimumWidth(width)
            vh.setFixedWidth(width)

    def _apply_freeze_to_visible_order(self):
        """Ensure freeze field is first among visible columns when enabled."""
        field = self._freeze_field
        if not field:
            return
        if field not in self._visible_fields:
            self._visible_fields.insert(0, field)
        else:
            self._visible_fields = [field] + [n for n in self._visible_fields if n != field]

    def _on_section_moved(self, _logical_index, _old_visual, _new_visual):
        """Update in-session column order after header drag (not persisted)."""
        header = self.table.horizontalHeader()
        names = self.model.field_names()
        if not names:
            return
        ordered = [None] * len(names)
        for logical in range(len(names)):
            visual = header.visualIndex(logical)
            if 0 <= visual < len(ordered):
                ordered[visual] = names[logical]
        ordered = [n for n in ordered if n is not None]
        if self._freeze_field and self._freeze_field in ordered:
            ordered = [self._freeze_field] + [n for n in ordered if n != self._freeze_field]
        self._visible_fields = ordered

    def _on_row_header_clicked(self, row):
        """Click row number: select that feature across frozen and main panes."""
        if self._layer is None or self._syncing_selection:
            return
        fid = self.model.fid_at(row)
        if fid is None:
            return
        self._syncing_selection = True
        try:
            self._layer.selectByIds([fid])
        finally:
            self._syncing_selection = False
        self._sync_selection_from_layer()
        self._update_status()

    def _on_row_header_double_clicked(self, row):
        """Double-click row number: select that feature and zoom to it."""
        if self._layer is None:
            return
        fid = self.model.fid_at(row)
        if fid is None:
            return
        self._syncing_selection = True
        try:
            self._layer.selectByIds([fid])
        finally:
            self._syncing_selection = False
        self._sync_selection_from_layer()
        if self._layer.isSpatial():
            self.iface.mapCanvas().zoomToSelected(self._layer)
            self.iface.mapCanvas().refresh()
        self._update_status()

    def _on_freeze_field_changed(self, _index):
        self._freeze_field = self.cmb_freeze.currentData() or ""
        self._apply_freeze_to_visible_order()
        if self._layer is not None:
            self.model.set_display_fields(self._visible_fields)
        self._update_frozen_visibility()

    def _update_frozen_visibility(self):
        cols = self.model.columnCount()
        names = self.model.field_names()
        freeze_on = bool(self._freeze_field) and cols > 1 and names and names[0] == self._freeze_field
        self.frozen.setVisible(freeze_on)
        if not freeze_on:
            for c in range(cols):
                self.table.setColumnHidden(c, False)
        else:
            for c in range(cols):
                self.frozen.setColumnHidden(c, c != 0)
                self.table.setColumnHidden(c, c == 0)
        self._sync_frozen_geometry()
        if not self._applying_col_widths:
            self._schedule_column_widths()
        if hasattr(self, "quick_fill"):
            self.quick_fill.schedule_sync()

    def _sync_frozen_geometry(self):
        """Keep frozen and main viewports the same height so rows stay aligned."""
        frozen = getattr(self, "frozen", None)
        table = getattr(self, "table", None)
        if frozen is None or table is None:
            return
        hbar = table.horizontalScrollBar()
        need_bar = hbar.maximum() > hbar.minimum()
        policy = Qt.ScrollBarAlwaysOn if need_bar else Qt.ScrollBarAlwaysOff
        if frozen.horizontalScrollBarPolicy() != policy:
            frozen.setHorizontalScrollBarPolicy(policy)
        heads = (table.horizontalHeader(), frozen.horizontalHeader())
        height = max([40] + [h.sizeHint().height() for h in heads])
        for h in heads:
            if h.minimumHeight() != height:
                h.setMinimumHeight(height)
        frozen.verticalScrollBar().setValue(table.verticalScrollBar().value())

    def _on_header_clicked(self, section):
        names = self.model.field_names()
        if section < 0 or section >= len(names):
            return
        name = names[section]
        self._set_fill_field(name)
        ascending = True
        if self.model.sort_field() == name:
            ascending = not self.model.sort_ascending()
        self.model.sort_by_field(name, ascending)
        self._update_row_header_width()
        self._refresh_column_stats(name)
        arrow = "升序" if ascending else "降序"
        label = self._field_labels.get(name, name)
        self.status.showMessage(f"按 {label} {arrow}（智能数字）排序", 2000)
        self._update_status()

    def _set_fill_field(self, field_name):
        """Sync 赋值 bar target field to the given field name."""
        if not field_name or not hasattr(self, "cmb_fill_field"):
            return
        idx = self.cmb_fill_field.findData(field_name)
        if idx >= 0 and self.cmb_fill_field.currentIndex() != idx:
            self.cmb_fill_field.setCurrentIndex(idx)

    def _sync_fill_field_from_index(self, model_index):
        if model_index is None or not model_index.isValid():
            return
        names = self.model.field_names()
        col = model_index.column()
        if 0 <= col < len(names):
            self._set_fill_field(names[col])

    def _sync_fill_field_from_views(self):
        """Use current cell, else first selected cell."""
        for view in (self.table, self.frozen):
            cur = view.currentIndex()
            if cur.isValid():
                self._sync_fill_field_from_index(cur)
                return
        indexes = self._selected_cell_indexes()
        if indexes:
            self._sync_fill_field_from_index(indexes[-1])

    @staticmethod
    def _format_sum(value):
        if value is None:
            return "—"
        if abs(value - round(value)) < 1e-9:
            return str(int(round(value)))
        text = f"{value:.6f}".rstrip("0").rstrip(".")
        return text

    @staticmethod
    def _sum_numeric_values(values):
        """
        Sum values that are pure numbers (incl. numeric text).
        Returns None if any non-empty value is not numeric.
        """
        total = 0.0
        count = 0
        for v in values:
            if v is None or v == NULL:
                continue
            if isinstance(v, str) and v.strip() == "":
                continue
            num = try_parse_number(v)
            if num is None:
                return None
            total += num
            count += 1
        if count == 0:
            return None
        return total

    @staticmethod
    def _duplicate_summary(values):
        """
        Case-insensitive duplicate check on non-empty values.
        Returns display string: '无重名' or '有重名(N组/M条)'.
        """
        keys = []
        for v in values:
            if v is None or v == NULL:
                continue
            text = value_text(v).strip()
            if not text:
                continue
            keys.append(text.casefold())
        if not keys:
            return "无数据"
        counts = Counter(keys)
        dup_groups = sum(1 for n in counts.values() if n > 1)
        if dup_groups == 0:
            return "无重名"
        dup_rows = sum(n for n in counts.values() if n > 1)
        return f"有重名({dup_groups}组/{dup_rows}条)"

    def _invalidate_layer_value_cache(self, *_args):
        self._layer_value_cache = {}

    def _field_values_entire_layer(self, field_name):
        layer = self._layer
        if layer is None:
            return []
        cached = self._layer_value_cache.get(field_name)
        if cached is not None:
            return cached
        field_idx = layer.fields().indexFromName(field_name)
        if field_idx < 0:
            return []
        values = []
        req = (
            QgsFeatureRequest()
            .setFlags(QgsFeatureRequest.NoGeometry)
            .setSubsetOfAttributes([field_idx])
        )
        for feat in layer.getFeatures(req):
            values.append(feat.attribute(field_idx))
        self._layer_value_cache = {field_name: values}
        return values

    def _refresh_column_stats(self, field_name):
        """
        After sorting a column:
        - pure numeric → filtered/all sums
        - otherwise → case-insensitive duplicate check (filtered/all)
        """
        self._clear_column_stats()
        self._clear_selection_stats()
        self._stats_mode = None
        if not field_name or self._layer is None:
            return

        filtered_vals = self.model.column_values(field_name)
        all_vals = self._field_values_entire_layer(field_name)

        filtered_sum = self._sum_numeric_values(filtered_vals)
        if filtered_sum is not None:
            all_sum = self._sum_numeric_values(all_vals)
            if all_sum is not None:
                self._stats_field_name = field_name
                self._sum_filtered = filtered_sum
                self._sum_all = all_sum
                self._stats_mode = "column"
                return

        # Not pure numeric → duplicate name check (ignore case)
        self._stats_field_name = field_name
        self._dup_filtered = self._duplicate_summary(filtered_vals)
        self._dup_all = self._duplicate_summary(all_vals)
        self._stats_mode = "column"

    def _clear_column_stats(self):
        self._stats_field_name = None
        self._sum_filtered = None
        self._sum_all = None
        self._dup_filtered = None
        self._dup_all = None

    def _clear_selection_stats(self):
        self._sel_count = None
        self._sel_sum = None
        self._sel_dup = None

    def _schedule_selection_stats(self):
        if not hasattr(self, "_selection_stats_timer"):
            return
        self._selection_stats_timer.stop()
        self._selection_stats_timer.start(FILTER_DELAY_MS)

    def _selected_cell_raw_values(self):
        values = []
        for idx in self._selected_cell_indexes():
            # Prefer EditRole; NULL comes back as None
            val = self.model.data(idx, Qt.EditRole)
            if val is None:
                # Distinguish empty display vs missing index: treat as NULL
                values.append(NULL)
            else:
                values.append(val)
        return values

    def _refresh_selection_stats(self):
        """Stats for currently selected cells (debounced). Column stats kept in memory."""
        indexes = self._selected_cell_indexes()
        if not indexes:
            self._clear_selection_stats()
            if self._stats_mode == "selection":
                self._stats_mode = "column" if self._stats_field_name else None
            self._update_stats_label()
            return

        values = self._selected_cell_raw_values()
        self._clear_selection_stats()
        numeric_sum = self._sum_numeric_values(values)
        if numeric_sum is not None:
            # count non-empty numeric contributors
            count = 0
            for v in values:
                if v is None or v == NULL:
                    continue
                if isinstance(v, str) and v.strip() == "":
                    continue
                if try_parse_number(v) is not None:
                    count += 1
            self._sel_count = count
            self._sel_sum = numeric_sum
            self._stats_mode = "selection"
        else:
            self._sel_dup = self._duplicate_summary(values)
            self._stats_mode = "selection"
        self._update_stats_label()

    def _header_logical_at(self, header, pos):
        visual = header.visualIndexAt(pos.x())
        if visual >= 0:
            return header.logicalIndex(visual)
        return header.logicalIndexAt(pos)

    def _show_header_column_menu(self, header, pos):
        logical = self._header_logical_at(header, pos)
        names = self.model.field_names()
        if logical < 0 or logical >= len(names):
            self.status.showMessage("未点中字段列，请对准列标题右键", 2500)
            return
        # Skip hidden columns (e.g. frozen col 0 hidden on main table)
        if header.isSectionHidden(logical):
            self.status.showMessage("该列已隐藏，请在可见列标题上右键", 2500)
            return

        field_name = names[logical]
        label = self._field_labels.get(field_name, field_name)
        menu = QMenu(self)
        act_copy = menu.addAction("复制本列")
        act_copy_header = menu.addAction("复制本列（含表头）")
        act_copy_back = self._add_colored_menu_action(
            menu, "复制本列（可回贴）", "#1565C0"
        )
        act_paste_back = self._add_colored_menu_action(
            menu, "粘贴回本列", "#C62828"
        )
        act_copy.triggered.connect(
            lambda _=False, n=field_name: self._copy_column_to_clipboard(n, False)
        )
        act_copy_header.triggered.connect(
            lambda _=False, n=field_name: self._copy_column_to_clipboard(n, True)
        )
        act_copy_back.triggered.connect(
            lambda _=False, n=field_name: self._copy_column_roundtrip(n)
        )
        act_paste_back.triggered.connect(
            lambda _=False, n=field_name: self._paste_roundtrip_column(n)
        )
        menu.addSeparator()
        act_unique = menu.addAction("唯一值统计…")
        act_unique.setToolTip("统计当前表格行里本列每个值出现几次")
        act_dup = menu.addAction("选中重复值")
        act_blank = menu.addAction("选中空值")
        act_unique.triggered.connect(
            lambda _=False, n=field_name: self._show_unique_values(n)
        )
        act_dup.triggered.connect(
            lambda _=False, n=field_name: self._select_column_duplicates(n)
        )
        act_blank.triggered.connect(
            lambda _=False, n=field_name: self._select_column_blanks(n)
        )
        menu.addSeparator()
        act_remark = menu.addAction("编辑备注…")
        act_remark.triggered.connect(
            lambda _=False, n=field_name: self._edit_remarks(n)
        )
        menu.exec_(header.mapToGlobal(pos))

    def _column_groups(self, field_name):
        fids = self.model.fids()
        values = self.model.column_values(field_name)
        return group_column(fids, values)

    def _select_fids_on_layer(self, fids, message):
        layer = self._layer
        if layer is None:
            return
        layer.selectByIds(list(fids))
        self.status.showMessage(message, 6000)

    def _select_column_duplicates(self, field_name):
        if self._layer is None or self.model.rowCount() == 0:
            self.status.showMessage("表格里没有行", 3000)
            return
        groups = self._column_groups(field_name)
        fids = []
        dup_values = 0
        for key, (_raw, group_fids) in groups.items():
            if key != BLANK_KEY and len(group_fids) > 1:
                dup_values += 1
                fids.extend(group_fids)
        label = self._field_labels.get(field_name, field_name)
        if not fids:
            self.status.showMessage("「%s」在当前表格行里没有重复值" % label, 5000)
            return
        self._select_fids_on_layer(
            fids,
            "「%s」有 %d 个值重复，已选中 %d 条要素（仅统计当前表格行，空值不算）"
            % (label, dup_values, len(fids)),
        )

    def _select_column_blanks(self, field_name):
        if self._layer is None or self.model.rowCount() == 0:
            self.status.showMessage("表格里没有行", 3000)
            return
        slot = self._column_groups(field_name).get(BLANK_KEY)
        label = self._field_labels.get(field_name, field_name)
        if not slot:
            self.status.showMessage("「%s」在当前表格行里没有空值" % label, 5000)
            return
        self._select_fids_on_layer(
            slot[1],
            "「%s」已选中 %d 条空值（NULL 或空白，仅统计当前表格行）" % (label, len(slot[1])),
        )

    def _show_unique_values(self, field_name):
        layer = self._layer
        if layer is None or self.model.rowCount() == 0:
            self.status.showMessage("表格里没有行", 3000)
            return
        field_idx = layer.fields().indexFromName(field_name)
        if field_idx < 0:
            return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            groups = self._column_groups(field_name)
        finally:
            QApplication.restoreOverrideCursor()
        label = self._field_labels.get(field_name, field_name)

        def label_for(raw):
            try:
                return self.model.value_map_label(field_idx, raw) or ""
            except Exception:
                return ""

        def on_select(fids, n_values):
            self._select_fids_on_layer(
                fids, "已选中 %d 个值对应的 %d 条要素" % (n_values, len(fids))
            )

        def on_filter(checked):
            self._quick_filter_by_values(field_name, checked)

        dlg = UniqueValuesDialog(self, label, groups, label_for, on_filter, on_select)
        dlg.setAttribute(Qt.WA_DeleteOnClose, True)
        dlg.show()

    def _quick_filter_by_values(self, field_name, checked):
        """Put checked (key, [raw, fids]) groups into the top-bar 筛选 as field-value mode."""
        mode_combo = getattr(self, "cmb_quick_mode", None)
        value_combo = getattr(self, "cmb_quick_filter", None)
        if mode_combo is None or value_combo is None:
            return
        idx = mode_combo.findData(field_name)
        if idx < 0:
            self.status.showMessage("该字段不在「筛选」的字段列表里", 4000)
            return
        wanted = set()
        for key, (raw, _fids) in checked:
            if key == BLANK_KEY:
                wanted.add(_blank_field_expr(field_name))
            else:
                wanted.add(field_eq_expression(field_name, _expr_attr(raw)))
        mode_combo.blockSignals(True)
        mode_combo.setCurrentIndex(idx)
        mode_combo.blockSignals(False)
        self._fill_quick_values(wanted)
        applied = set(value_combo.checked_payloads()) & wanted
        self._on_quick_filter_changed()
        if len(applied) < len(wanted):
            self.status.showMessage(
                "「筛选」下拉只列出前 %d 个值，有 %d 个勾选值没能加入"
                % (QUICK_VALUE_LIMIT, len(wanted) - len(applied)),
                8000,
            )
        else:
            self.status.showMessage("已按 %d 个值筛选" % len(applied), 4000)

    def _show_row_header_menu(self, header, pos):
        rows = self.model.rowCount()
        if rows == 0:
            return
        row = header.logicalIndexAt(pos)
        menu = QMenu(self)
        act_range = menu.addAction("选中第 a–b 行…")
        act_to_end = None
        if 0 <= row < rows:
            act_to_end = menu.addAction("从第 %d 行选到末行" % (row + 1))
        act_range.triggered.connect(
            lambda _=False, r=row: self._select_row_range_prompt(r)
        )
        if act_to_end is not None:
            act_to_end.triggered.connect(
                lambda _=False, r=row: self._select_rows(list(range(r, rows)))
            )
        menu.exec_(header.mapToGlobal(pos))

    def _select_row_range_prompt(self, row):
        rows = self.model.rowCount()
        start = row + 1 if 0 <= row < rows else 1
        text, ok = QInputDialog.getText(
            self,
            "按行号选择",
            "行号范围（当前共 %d 行，按表格显示顺序）：\n"
            "例如 10-50、1-20,35,80-  （80- 表示到末行）" % rows,
            QLineEdit.Normal,
            "%d-%d" % (start, rows),
        )
        if not ok:
            return
        try:
            picked = parse_row_ranges(text, rows)
        except ValueError as exc:
            QMessageBox.information(self, "按行号选择", str(exc))
            return
        self._select_rows(picked)

    def _select_rows(self, picked_rows):
        fids = [self.model.fid_at(r) for r in picked_rows]
        fids = [f for f in fids if f is not None]
        if not fids:
            return
        self._select_fids_on_layer(fids, "已选中 %d 行" % len(fids))

    def _add_colored_menu_action(self, menu, text, color):
        """Menu row with its own text color. Plain QAction follows the theme."""
        act = QWidgetAction(menu)
        button = QPushButton(text, menu)
        button.setFlat(True)
        button.setFont(menu.font())
        button.setStyleSheet(
            "QPushButton { color: %s; text-align: left; padding: 5px 16px 5px 28px;"
            " border: none; background: transparent; }"
            "QPushButton:hover { background: %s; }" % (color, theme.color("hover"))
        )
        button.clicked.connect(act.trigger)
        button.clicked.connect(menu.close)
        act.setDefaultWidget(button)
        menu.addAction(act)
        return act

    def _copy_column_to_clipboard(self, field_name, include_header=False):
        """Copy all filtered-row values of one field (not just on-screen rows)."""
        values = self.model.column_values(field_name)
        lines = []
        if include_header:
            lines.append(field_name)
        for val in values:
            if val is None or val == NULL:
                lines.append("")
            else:
                lines.append(value_text(val))
        clipboard = QApplication.clipboard()
        if clipboard is None:
            try:
                from qgis.core import QgsApplication

                clipboard = QgsApplication.clipboard()
            except Exception:
                clipboard = None
        if clipboard is None:
            QMessageBox.warning(self, "复制", "无法访问剪贴板。")
            return
        clipboard.setText("\n".join(lines))
        label = self._field_labels.get(field_name, field_name)
        self.status.showMessage(f"已复制列「{label}」共 {len(values)} 行到剪贴板", 4000)

    def _app_clipboard(self):
        clipboard = QApplication.clipboard()
        if clipboard is None:
            try:
                clipboard = QgsApplication.clipboard()
            except Exception:
                clipboard = None
        return clipboard

    def _clipboard_text(self):
        clipboard = self._app_clipboard()
        if clipboard is None:
            return ""
        return clipboard.text() or ""

    def _copy_column_roundtrip(self, field_name):
        """Copy filtered rows as #fid + value so paste can write back by feature id."""
        layer = self._layer
        if layer is None:
            return
        fids = self.model.fids()
        values = self.model.column_values(field_name)
        if not fids:
            QMessageBox.information(self, "复制", "当前筛选没有可复制的行。")
            return
        if len(fids) != len(values):
            QMessageBox.warning(self, "复制", "行数和取值对不上，没有复制。")
            return
        try:
            layer_id = layer.id() or ""
        except Exception:
            layer_id = ""
        buf = io.StringIO()
        writer = csv.writer(buf, delimiter="\t", lineterminator="\n", quoting=csv.QUOTE_MINIMAL)
        fid_header = (
            "%s@%s" % (ROUNDTRIP_FID_HEADER, layer_id) if layer_id else ROUNDTRIP_FID_HEADER
        )
        writer.writerow([fid_header, field_name])
        for fid, val in zip(fids, values):
            if val is None or val == NULL:
                text = ""
            else:
                text = value_text(val)
            writer.writerow([int(fid), text])
        clipboard = self._app_clipboard()
        if clipboard is None:
            QMessageBox.warning(self, "复制", "无法访问剪贴板。")
            return
        clipboard.setText(buf.getvalue())
        label = self._field_labels.get(field_name, field_name)
        self.status.showMessage(
            "已复制列「%s」共 %s 行（两列：编号和值，可改值后粘贴回本列）" % (label, len(fids)),
            5000,
        )

    def _missing_feature_ids(self, layer, fids):
        want = []
        seen = set()
        for fid in fids:
            fid = int(fid)
            if fid not in seen:
                seen.add(fid)
                want.append(fid)
        found = set()
        request = (
            QgsFeatureRequest()
            .setFilterFids(want)
            .setFlags(QgsFeatureRequest.NoGeometry)
            .setSubsetOfAttributes([])
        )
        for feat in layer.getFeatures(request):
            found.add(feat.id())
        return [fid for fid in want if fid not in found]

    def _paste_roundtrip_column(self, target_field=None):
        """Write clipboard values back by feature id. One bad row writes nothing."""
        layer = self._layer
        if layer is None:
            return
        if not layer.isEditable():
            QMessageBox.information(self, "粘贴回列", "请先切换到编辑模式。")
            return
        text = self._clipboard_text()
        if not clipboard_is_roundtrip(text):
            QMessageBox.information(
                self,
                "粘贴回列",
                "剪贴板不是可回贴格式。请用列标题「复制本列（可回贴）」复制，"
                "只改值、不要改编号列，再粘贴。普通复制没有编号，不能按位置贴回。",
            )
            return
        parsed, err = parse_roundtrip_text(text)
        if err:
            QMessageBox.warning(self, "粘贴回列", err)
            return
        src_field = parsed["field"]
        layer_id = parsed["layer_id"]
        if layer_id:
            try:
                current_id = layer.id() or ""
            except Exception:
                current_id = ""
            if current_id and layer_id != current_id:
                QMessageBox.warning(self, "粘贴回列", "这份数据来自另一个图层，不能贴到当前表。")
                return
        field_name = target_field or src_field
        field_idx = layer.fields().indexFromName(field_name)
        if field_idx < 0:
            QMessageBox.warning(self, "粘贴回列", "当前图层没有字段「%s」。" % field_name)
            return
        rows = parsed["rows"]
        missing = self._missing_feature_ids(layer, [fid for fid, _val in rows])
        if missing:
            sample = "、".join(str(fid) for fid in missing[:8])
            extra = "" if len(missing) <= 8 else " 等 %s 个" % len(missing)
            QMessageBox.warning(
                self,
                "粘贴回列",
                "有 %s 个编号不在当前图层（%s%s）。一条都没写。" % (len(missing), sample, extra),
            )
            return
        sample = "\n".join(
            "编号 %s → %s" % (fid, raw if raw != "" else "（空）") for fid, raw in rows[:3]
        )
        if target_field and target_field != src_field:
            question = (
                "剪贴板来自字段「%s」，将按编号写入当前列「%s」，共 %s 行。\n"
                "对的是编号，不是表格第几行。下面顺序可以不连着，不会错位。\n%s\n继续？"
                % (src_field, target_field, len(rows), sample)
            )
        else:
            question = (
                "将按编号写回字段「%s」，共 %s 行。\n"
                "对的是编号，不是表格第几行。下面顺序可以不连着，不会错位。\n%s\n继续？"
                % (field_name, len(rows), sample)
            )
        if QMessageBox.question(self, "粘贴回列", question) != QMessageBox.Yes:
            return
        field = layer.fields().at(field_idx)
        values = {}
        for fid, raw in rows:
            values[fid] = self._coerce_value_for_field(field, raw)
        updated = self._commit_attribute_values(
            layer, field_idx, field_name, values, "粘贴回列"
        )
        if updated:
            self.status.showMessage("已按编号写回 %s 行 → %s" % (updated, field_name), 4000)
        else:
            self.status.showMessage("编号已对齐，字段「%s」的值没有变化" % field_name, 4000)

    def _on_table_selection(self, *_args):
        if self._syncing_selection:
            return
        self._push_selection_to_layer(from_view=self.table)
        self._schedule_selection_stats()
        self._sync_fill_field_from_views()

    def _on_frozen_selection(self, *_args):
        if self._syncing_selection:
            return
        self._push_selection_to_layer(from_view=self.frozen)
        self._schedule_selection_stats()
        self._sync_fill_field_from_views()

    def _on_table_current_changed(self, current, _previous):
        if self._syncing_selection:
            return
        self._sync_fill_field_from_index(current)

    def _on_frozen_current_changed(self, current, _previous):
        if self._syncing_selection:
            return
        self._sync_fill_field_from_index(current)

    def _push_selection_to_layer(self, from_view):
        if self._layer is None:
            return
        indexes = from_view.selectionModel().selectedIndexes()
        other = self.frozen if from_view is self.table else self.table
        indexes = list(indexes) + list(other.selectionModel().selectedIndexes())
        fids = set()
        for idx in indexes:
            fid = self.model.fid_at(idx.row())
            if fid is not None:
                fids.add(fid)
        self._syncing_selection = True
        try:
            self._layer.selectByIds(list(fids))
        finally:
            self._syncing_selection = False
        self._update_status()

    def _on_layer_selection_changed(self, *_args):
        if self._syncing_selection:
            return
        self._sync_selection_from_layer()
        if self._current_scope_mode() == "selected":
            self._selected_scope_timer.start(120)
        self._update_status()

    def _refresh_selected_scope(self):
        if self._current_scope_mode() != "selected":
            return
        self._apply_scope_now()
        self._sync_selection_from_layer()
        self._update_row_header_width()
        self._update_status()
        self._schedule_column_widths()

    def _sync_selection_from_layer(self):
        if self._layer is None:
            return
        self._syncing_selection = True
        try:
            self.table.selectionModel().clearSelection()
            self.frozen.selectionModel().clearSelection()
            selected = set(self._layer.selectedFeatureIds())
            if not selected:
                return
            selection = QItemSelection()
            cols = max(0, self.model.columnCount() - 1)
            for fid in selected:
                row = self.model.row_for_fid(fid)
                if row < 0:
                    continue
                left = self.model.index(row, 0)
                right = self.model.index(row, cols)
                selection.select(left, right)
            self.table.selectionModel().select(selection, QItemSelectionModel.Select)
            if self.frozen.isVisible():
                sel0 = QItemSelection()
                for fid in selected:
                    row = self.model.row_for_fid(fid)
                    if row < 0:
                        continue
                    idx = self.model.index(row, 0)
                    sel0.select(idx, idx)
                self.frozen.selectionModel().select(sel0, QItemSelectionModel.Select)
        finally:
            self._syncing_selection = False

    def _on_editing_started(self):
        self.model.invalidate_column_cache()
        self.model.invalidate_modified()
        self.act_toggle_edit.setChecked(True)
        self._update_edit_actions()
        self._update_window_title()

    def _on_editing_stopped(self):
        self.model.invalidate_column_cache()
        self.model.invalidate_modified()
        self.act_toggle_edit.setChecked(False)
        self._update_edit_actions()
        self._update_window_title()
        self.reload_table()

    def _on_attribute_changed(self, fid, field, _value):
        self._invalidate_layer_value_cache()
        self.model.invalidate_fid(fid)
        row = self.model.row_for_fid(fid)
        if row >= 0:
            left = self.model.index(row, 0)
            right = self.model.index(row, self.model.columnCount() - 1)
            self.model.dataChanged.emit(left, right)
        self._schedule_quick_value_refresh(field)

    def _toggle_editing(self, checked):
        layer = self._layer
        if layer is None:
            self.act_toggle_edit.setChecked(False)
            return
        if checked:
            if not layer.isEditable() and not layer.startEditing():
                QMessageBox.warning(self, "编辑", "无法开始编辑该图层。")
                self.act_toggle_edit.setChecked(False)
        else:
            if layer.isEditable() and layer.isModified():
                reply = QMessageBox.question(
                    self,
                    "结束编辑",
                    "有未保存修改，是否保存？",
                    QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                )
                if reply == QMessageBox.Cancel:
                    self.act_toggle_edit.setChecked(True)
                    return
                if reply == QMessageBox.Save:
                    if not layer.commitChanges():
                        errs = layer.commitErrors()
                        msg = "\n".join(errs) if isinstance(errs, (list, tuple)) else (errs or "未知错误")
                        QMessageBox.warning(self, "保存失败", msg)
                        self.act_toggle_edit.setChecked(True)
                        return
                else:
                    self._disconnect_layer_signals()
                    try:
                        layer.rollBack()
                    finally:
                        self._connect_layer_signals()
            elif layer.isEditable():
                self._disconnect_layer_signals()
                try:
                    layer.rollBack()
                finally:
                    self._connect_layer_signals()
        self._update_edit_actions()
        self._update_window_title()
        self.reload_table()

    def _save_edits(self):
        layer = self._layer
        if layer is None or not layer.isEditable():
            return
        if not layer.commitChanges():
            errs = layer.commitErrors()
            msg = "\n".join(errs) if isinstance(errs, (list, tuple)) else (errs or "未知错误")
            QMessageBox.warning(self, "保存失败", msg)
            layer.startEditing()
        else:
            layer.startEditing()
            self.status.showMessage("已保存", 3000)
        self._update_edit_actions()
        self._update_window_title()

    def _revert_edits(self):
        layer = self._layer
        if layer is None or not layer.isEditable():
            return
        if QMessageBox.question(self, "回滚", "放弃未保存修改？") != QMessageBox.Yes:
            return
        self._disconnect_layer_signals()
        try:
            layer.rollBack()
            layer.startEditing()
        finally:
            self._connect_layer_signals()
        self.reload_table()
        self._update_edit_actions()
        self._update_window_title()

    def _delete_selected(self):
        layer = self._layer
        if layer is None or not layer.isEditable():
            QMessageBox.information(self, "删除", "请先切换到编辑模式。")
            return
        fids = layer.selectedFeatureIds()
        if not fids:
            QMessageBox.information(self, "删除", "没有选中的要素。")
            return
        if QMessageBox.question(self, "删除", f"删除选中的 {len(fids)} 个要素？") != QMessageBox.Yes:
            return
        layer.beginEditCommand("删除要素")
        try:
            ok = bool(layer.deleteFeatures(list(fids)))
        except Exception:
            ok = False
        if ok:
            layer.endEditCommand()
        else:
            layer.destroyEditCommand()
            QMessageBox.warning(self, "删除", "删除失败。")
        self._schedule_reload()

    def _layer_supports_editing(self, layer):
        if layer is None or not layer.isValid():
            return False
        try:
            if hasattr(layer, "supportsEditing"):
                return bool(layer.supportsEditing())
        except Exception:
            pass
        provider = layer.dataProvider()
        if provider is None:
            return False
        caps = provider.capabilities()
        return bool(
            caps
            & (
                QgsVectorDataProvider.ChangeAttributeValues
                | QgsVectorDataProvider.DeleteFeatures
            )
        )

    def _update_edit_actions(self):
        layer = self._layer
        can = self._layer_supports_editing(layer)
        editing = layer is not None and layer.isEditable()

        def _en(act, enabled):
            if act is not None:
                act.setEnabled(enabled)

        _en(self.act_toggle_edit, can)
        _en(self.act_save, editing)
        _en(self.act_revert, editing)
        _en(self.act_delete, editing)
        _en(self.act_copy, layer is not None)
        _en(self.act_cut, editing)
        _en(self.act_paste, editing)
        _en(self.act_fields, layer is not None)
        _en(self.act_remarks, True)
        _en(self.act_display_mode, True)
        _en(self.act_deselect, layer is not None)
        if hasattr(self, "fill_bar"):
            self.fill_bar.setVisible(editing)
        self._update_quick_fill_visibility()
        if hasattr(self, "table"):
            self.table.setEditTriggers(
                QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed
                if editing
                else QAbstractItemView.NoEditTriggers
            )
            if hasattr(self, "frozen"):
                self.frozen.setEditTriggers(self.table.editTriggers())

    def _select_all_filtered(self):
        layer = self._layer
        if layer is None:
            return
        fids = self.model.fids()
        if not fids:
            QMessageBox.information(self, "全选", "当前筛选没有要素。")
            return
        layer.selectByIds(fids)
        self._update_status()

    def _show_help(self):
        ver = plugin_version()
        dlg = QDialog(self)
        dlg.setWindowTitle("Help — Field Remarks Table %s" % ver)
        dlg.resize(560, 420)
        lay = QVBoxLayout(dlg)
        browser = QTextBrowser()
        browser.setOpenExternalLinks(False)
        browser.setHtml(HELP_HTML.replace("__VERSION__", ver))
        lay.addWidget(browser)
        btns = QDialogButtonBox(QDialogButtonBox.Close)
        btns.rejected.connect(dlg.reject)
        btns.clicked.connect(dlg.accept)
        lay.addWidget(btns)
        dlg.exec_()

    def _manage_fields(self):
        layer = self._layer
        if layer is None:
            return
        dlg = FieldsManagerDialog(layer, self, self._remarks)
        dlg.exec_()
        remarks_changed = False
        try:
            remarks_changed = bool(dlg.remarks_changed())
        except Exception:
            remarks_changed = False
        if dlg.changed():
            self._refresh_field_structure()
        elif remarks_changed:
            self._apply_remarks_to_ui()

    def _export_kmz(self):
        layer = self._layer
        if layer is None:
            QMessageBox.information(self, "导出 KMZ", "无图层。")
            return
        if not layer.isSpatial():
            QMessageBox.information(self, "导出 KMZ", "该图层没有几何，无法导出 KMZ。")
            return
        try:
            total_rows = int(layer.featureCount())
        except Exception:
            total_rows = -1
        dlg = ExportKmzDialog(
            self._all_field_names,
            self._field_labels,
            self,
            table_rows=self.model.rowCount(),
            total_rows=total_rows,
        )
        if dlg.exec_() != QDialog.Accepted:
            return
        fids = self.model.fids() if dlg.table_only() else None
        if fids is not None and not fids:
            QMessageBox.information(self, "导出 KMZ", "当前表格没有行。")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "导出 KMZ", os.path.expanduser("~"), "KMZ (*.kmz)"
        )
        if not path:
            return
        if not path.lower().endswith(".kmz"):
            path += ".kmz"
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            written, skipped = export_layer_to_kmz(
                layer,
                path,
                dlg.title_field(),
                dlg.description_fields(),
                dlg.crs_authid(),
                fids=fids,
                use_layer_style=dlg.use_layer_style(),
            )
        except Exception as e:
            QMessageBox.warning(self, "导出 KMZ 失败", str(e))
            return
        finally:
            QApplication.restoreOverrideCursor()
        self.status.showMessage(
            f"KMZ 已导出：写入 {written}，跳过无几何 {skipped} → {path}", 6000
        )
        QMessageBox.information(
            self,
            "导出 KMZ",
            f"完成。\n写入要素：{written}\n跳过（无几何）：{skipped}\n\n{path}",
        )

    def _relayout_fill_bar(self, is_affix, is_replace, fill_on):
        """Pack fill controls left. Hidden editors must not keep a stretch gap.

        Do not use isVisible() here: the bar starts hidden, and a child of a
        hidden parent reports not visible even after setVisible(True).
        """
        lay = self.fill_bar.layout()
        if lay is None:
            return

        def _stretch(widget, value):
            index = lay.indexOf(widget)
            if index >= 0:
                lay.setStretch(index, value)
                policy = widget.sizePolicy()
                policy.setRetainSizeWhenHidden(False)
                widget.setSizePolicy(policy)

        _stretch(self.ed_fill_prefix, 1 if is_affix else 0)
        _stretch(self.ed_fill_suffix, 1 if is_affix else 0)
        _stretch(self.ed_fill, 1 if fill_on else 0)
        _stretch(self.ed_fill_find, 1 if is_replace else 0)
        _stretch(self.ed_fill_replace, 1 if is_replace else 0)
        expanding = is_affix or is_replace or fill_on
        if hasattr(self, "_fill_stretch_index"):
            lay.setStretch(self._fill_stretch_index, 0 if expanding else 1)
        lay.activate()

    def _on_fill_mode_changed(self, _index=None):
        mode = self.cmb_fill_mode.currentData()
        is_replace = mode == "replace"
        is_affix = mode == "affix"
        is_around = mode == "around_seq"
        self.btn_fill_expr.setEnabled(mode == "expr")
        show_width = mode in ("seq", "prefix_seq", "around_seq")
        fill_on = not is_replace and not is_affix and not is_around
        if hasattr(self, "ed_fill_find"):
            self.ed_fill.setVisible(fill_on)
            self.lbl_fill_find.setVisible(is_replace)
            self.ed_fill_find.setVisible(is_replace)
            self.lbl_fill_replace.setVisible(is_replace)
            self.ed_fill_replace.setVisible(is_replace)
        if hasattr(self, "cmb_fill_width"):
            self.lbl_fill_width.setVisible(show_width)
            self.cmb_fill_width.setVisible(show_width)
            if hasattr(self, "_fill_width_group"):
                self._fill_width_group.setVisible(show_width)
        if hasattr(self, "cmb_fill_seq_side"):
            self.lbl_fill_seq_side.setVisible(is_around)
            self.cmb_fill_seq_side.setVisible(is_around)
            if hasattr(self, "_fill_side_group"):
                self._fill_side_group.setVisible(is_around)
        if hasattr(self, "ed_fill_prefix"):
            self.lbl_fill_prefix.setVisible(is_affix)
            self.ed_fill_prefix.setVisible(is_affix)
            self.lbl_fill_suffix.setVisible(is_affix)
            self.ed_fill_suffix.setVisible(is_affix)
        self._relayout_fill_bar(is_affix, is_replace, fill_on)
        tips = {
            "const": "常量，或输入字段名引用其内容（如 TYPE；空=NULL）",
            "blank": "只写入空白单元格。已有内容不动。空=NULL，也可填字段名",
            "seq": "起始序号，默认 1。位数选自动或指定位数时补零（仅文本字段）",
            "prefix_seq": "前缀，如 A 或 H1-。位数作用在数字上，如 A001",
            "around_seq": "在已有文字前或后加上序号，原文字保留。空白只写序号",
            "affix": "前面、后面至少填一边。只改已有文字",
            "expr": "QGIS 表达式，如 \"POP\" + 1 或 $id",
            "replace": "对当前目标字段做部分替换，一格内全部替换；区分大小写",
        }
        self.ed_fill.setPlaceholderText(tips.get(mode, ""))
        self.ed_fill.setToolTip(
            tips.get(mode, "")
            if mode != "const"
            else "输入常量，或输入其它字段名（打字弹出下拉，中间字母也能搜，列出全部命中项）把该字段内容写入目标字段。\n"
            "要写入恰好等于字段名的文字，用单引号包起来，如 'TYPE'。"
        )
        self._update_fill_preset_visible()
        self._sync_fill_field_completer()

    def _on_fill_field_changed(self, _index=None):
        self._rebuild_fill_presets()
        self._sync_fill_field_completer()

    def _sync_fill_field_completer(self):
        if not hasattr(self, "ed_fill") or not hasattr(self, "_fill_field_model"):
            return
        mode = None
        if hasattr(self, "cmb_fill_mode"):
            mode = self.cmb_fill_mode.currentData()
        names = []
        if mode in ("const", "blank"):
            target = None
            if hasattr(self, "cmb_fill_field"):
                target = self.cmb_fill_field.currentData()
            names = [n for n in (self._all_field_names or []) if n and n != target]
        self._fill_field_model.setStringList(names)
        self.ed_fill.setCompleter(self._fill_field_completer if names else None)

    def _match_source_field(self, text):
        """Return a layer field name if text is a field reference, else None."""
        raw = (text or "").strip()
        if not raw:
            return None
        names = self._all_field_names or []
        target = None
        if hasattr(self, "cmb_fill_field"):
            target = self.cmb_fill_field.currentData()
        exact = None
        insensitive = []
        for name in names:
            if name == target:
                continue
            if name == raw:
                exact = name
                break
            if name.lower() == raw.lower():
                insensitive.append(name)
        if exact:
            return exact
        if len(insensitive) == 1:
            return insensitive[0]
        return None

    def _parse_const_fill_input(self, content):
        """('null', None) | ('field', src_name) | ('const', value)."""
        if content == "":
            return ("null", None)
        stripped = content.strip()
        if (
            len(stripped) >= 2
            and stripped[0] == stripped[-1]
            and stripped[0] in "'\""
        ):
            return ("const", stripped[1:-1])
        src = self._match_source_field(stripped)
        if src:
            return ("field", src)
        return ("const", content)

    def _copy_field_values(self, layer, dest_field, fids, src_name):
        src_idx = layer.fields().indexFromName(src_name)
        if src_idx < 0:
            return None
        fetched = self.model._fetch_attributes(fids, [src_idx])
        values = {}
        for fid in fids:
            raw = fetched.get(fid, {}).get(src_idx, NULL)
            values[fid] = self._coerce_value_for_field(dest_field, raw)
        return values

    def _drop_unchanged_fill_values(self, field_idx, values):
        if not values:
            return values
        fetched = self.model._fetch_attributes(list(values.keys()), [field_idx])
        changed = {}
        for fid, val in values.items():
            current = fetched.get(fid, {}).get(field_idx, NULL)
            if not attr_values_equal(current, val):
                changed[fid] = val
        return changed

    def _rebuild_fill_presets(self):
        if not hasattr(self, "cmb_fill_preset"):
            return
        self.cmb_fill_preset.blockSignals(True)
        self.cmb_fill_preset.clear()
        self.cmb_fill_preset.addItem("含义…", "")
        field_name = None
        if hasattr(self, "cmb_fill_field"):
            field_name = self.cmb_fill_field.currentData()
        meanings = []
        if field_name and hasattr(self.model, "field_meanings"):
            meanings = self.model.field_meanings(field_name)
        for item in meanings:
            payload = meaning_payload(item)
            self.cmb_fill_preset.addItem(meaning_display(item) or str(item), payload)
        self.cmb_fill_preset.blockSignals(False)
        self._update_fill_preset_visible()

    def _update_fill_preset_visible(self):
        if not hasattr(self, "cmb_fill_preset"):
            return
        mode = None
        if hasattr(self, "cmb_fill_mode"):
            mode = self.cmb_fill_mode.currentData()
        has = self.cmb_fill_preset.count() > 1
        self.cmb_fill_preset.setVisible(mode in ("const", "blank", "expr") and has)

    def _on_fill_preset_chosen(self, index):
        if index <= 0 or not hasattr(self, "ed_fill"):
            return
        payload = self.cmb_fill_preset.itemData(index)
        if not isinstance(payload, dict):
            payload = meaning_payload(self.cmb_fill_preset.itemText(index))
        kind = payload.get("kind") or "const"
        text = payload.get("value") or ""
        if not text:
            text = self.cmb_fill_preset.itemText(index)
        if not text:
            return
        if kind != "expr":
            resolved, missing = self._resolve_const_write(text)
            if not missing:
                text = resolved
        self.ed_fill.setText(str(text))
        if hasattr(self, "cmb_fill_mode"):
            self.cmb_fill_mode.blockSignals(True)
            idx = self.cmb_fill_mode.findData("expr" if kind == "expr" else "const")
            if idx >= 0:
                self.cmb_fill_mode.setCurrentIndex(idx)
            self.cmb_fill_mode.blockSignals(False)
            self._on_fill_mode_changed()

    def _refresh_field_labels(self):
        layer = self._layer
        self._field_labels = {}
        if layer is None:
            return
        lname = layer.name()
        for f in layer.fields():
            name = f.name()
            alias = (f.alias() or "").strip()
            remark_label = ""
            if hasattr(self, "_remarks") and self._remarks_active():
                remark_label = self._remarks.display_label(lname, name, "")
            self._field_labels[name] = field_display_label(name, alias, remark_label)

    def _apply_remarks_to_ui(self):
        layer = self._layer
        remarks_map = {}
        if layer is not None and self._remarks_active():
            remarks_map = self._remarks.fields_map(layer.name())
        self.model.set_field_remarks(remarks_map)
        if hasattr(self.model, "set_pack_variables"):
            pack_vars = []
            if self._remarks_active() and hasattr(self, "_remarks") and self._remarks is not None:
                try:
                    pack_vars = self._remarks.current_variables()
                except Exception:
                    pack_vars = []
            self.model.set_pack_variables(pack_vars)
        self._refresh_field_labels()
        if hasattr(self, "cmb_filter_field"):
            self._rebuild_filter_field_combo()
            self._rebuild_freeze_combo()
            self._rebuild_fill_field_combo()
        self._sync_quick_mode_labels()
        if hasattr(self, "quick_fill"):
            names = self.model.field_names()
            current = [n for n, _c in self.quick_fill._combos]
            if current != names:
                self.quick_fill.rebuild()
            else:
                self.quick_fill.reload_items()
        self._update_quick_fill_visibility()
        self._sync_remarks_action()
        self._schedule_column_widths()

    def _update_quick_fill_visibility(self):
        editing = self._layer is not None and self._layer.isEditable()
        on = editing and self._remarks_active()
        if not hasattr(self, "quick_fill"):
            return
        self.quick_fill.setVisible(on)
        if on:
            if not self.quick_fill._combos and self.model.field_names():
                self.quick_fill.rebuild()
            self.quick_fill.schedule_sync(0)
        if hasattr(self, "btn_fill_filtered"):
            if on:
                self.btn_fill_filtered.setToolTip(
                    "更新当前表格筛选后的全部行；若快速插入行已选含义，则按所选列写入（全空则不再确认）"
                )
                self.btn_fill_selected.setToolTip(
                    "仅更新已选中要素；若快速插入行已选含义，则按所选列写入（全空则不再确认）"
                )
            else:
                self.btn_fill_filtered.setToolTip("更新当前表格筛选后的全部行（含未滚到的）")
                self.btn_fill_selected.setToolTip("仅更新地图/表中已选中的要素")

    def _on_remarks_enabled_changed(self, _enabled):
        self._apply_remarks_to_ui()
        self._update_edit_actions()

    def _on_remark_pack_changed(self):
        self._apply_remarks_to_ui()

    def changeEvent(self, event):
        super().changeEvent(event)
        if not getattr(self, "_shared_reload_ready", False):
            return
        if event.type() != QEvent.ActivationChange or not self.isActiveWindow():
            return
        session = getattr(self, "_remarks", None)
        if session is None or not session.reload_from_disk():
            return
        self._apply_remarks_to_ui()
        hub = getattr(self, "_remarks_hub", None)
        if hub is not None and hasattr(hub, "adopt_shared_config"):
            hub.adopt_shared_config()

    def _on_remarks_hub_finished(self, *_args):
        self._remarks_hub = None

    def _attach_remarks_hub(self, hub):
        self._detach_remarks_hub()
        self._remarks_hub = hub
        if hub is not None and getattr(hub, "session", None) is not None:
            self._remarks = hub.session
        if hub is None:
            return
        hub.packChanged.connect(self._on_remark_pack_changed)
        hub.enabledChanged.connect(self._on_remarks_enabled_changed)
        hub.remarksChanged.connect(self._apply_remarks_to_ui)
        hub.finished.connect(self._on_remarks_hub_finished)

    def _detach_remarks_hub(self):
        hub = getattr(self, "_remarks_hub", None)
        if hub is None:
            return
        for signal, slot in (
            (hub.packChanged, self._on_remark_pack_changed),
            (hub.enabledChanged, self._on_remarks_enabled_changed),
            (hub.remarksChanged, self._apply_remarks_to_ui),
            (hub.finished, self._on_remarks_hub_finished),
        ):
            try:
                signal.disconnect(slot)
            except Exception:
                pass

    def _reuse_open_remarks_hub(self):
        hub = getattr(RemarksHubDialog, "_instance", None)
        try:
            if hub is not None:
                hub.windowTitle()
        except Exception:
            hub = None
        if hub is None:
            return
        self._attach_remarks_hub(hub)
        self._apply_remarks_to_ui()

    def _open_remarks_hub(self, *_args):
        focus_field = None
        if _args and isinstance(_args[0], str):
            focus_field = _args[0]
        hub = RemarksHubDialog.open_for(
            self.iface,
            session=self._remarks,
            parent=self.iface.mainWindow(),
            focus_field=focus_field,
        )
        self._attach_remarks_hub(hub)
        self._apply_remarks_to_ui()

    def _open_quick_name(self, *_args):
        from .remarks_dialog import QuickNameDialog

        parent = None
        try:
            parent = self.iface.mainWindow()
        except Exception:
            parent = None
        QuickNameDialog.open_for(self.iface, parent=parent)

    def _open_layer_remarks(self, focus_field=None, layer=None):
        if isinstance(focus_field, bool):
            focus_field = None
        self._open_remarks_hub(focus_field)

    def _edit_remarks(self, focus_field=None):
        if isinstance(focus_field, bool):
            focus_field = None
        self._open_layer_remarks(focus_field=focus_field)

    def _sync_fill_from_quick(self, field_name, value):
        self._set_fill_field(field_name)
        payload = value if isinstance(value, dict) else meaning_payload(value)
        kind = payload.get("kind") or "const"
        text = payload.get("value") or ""
        if kind != "expr":
            resolved, missing = self._resolve_const_write(text)
            if not missing:
                text = resolved
        mode = "expr" if kind == "expr" else "const"
        if hasattr(self, "cmb_fill_mode"):
            self.cmb_fill_mode.blockSignals(True)
            idx = self.cmb_fill_mode.findData(mode)
            if idx >= 0:
                self.cmb_fill_mode.setCurrentIndex(idx)
            self.cmb_fill_mode.blockSignals(False)
            self._on_fill_mode_changed()
        if hasattr(self, "ed_fill") and text is not None:
            self.ed_fill.setText(str(text))
        self.status.showMessage(
            "已选插入值：选弹出项立即写入，或点取消后用赋值条按钮写入", 4000
        )

    def _fill_target_fids(self, selected_only=False, title="赋值", scope=None):
        layer = self._layer
        if layer is None:
            return None
        if scope is None:
            scope = "selected" if selected_only else "filtered"
        if scope == "selected":
            selected = set(layer.selectedFeatureIds())
            if not selected:
                QMessageBox.information(self, title, "没有选中的要素。")
                return None
            fids = [fid for fid in self.model.fids() if fid in selected]
            if not fids:
                QMessageBox.information(
                    self,
                    title,
                    "选中的 %s 个要素都不在当前表格里（被范围、过滤或筛选挡住了）。\n"
                    "为避免改到看不见的要素，这次没有写入。\n"
                    "可以先清除过滤/筛选，或把范围切到「仅选中」。" % len(selected),
                )
                return None
            return fids
        if scope == "all":
            fids = self._all_layer_fids(layer)
            if not fids:
                QMessageBox.information(self, title, "图层没有要素。")
                return None
            return fids
        fids = self.model.fids()
        if not fids:
            QMessageBox.information(self, title, "当前没有可更新的筛选行。")
            return None
        return fids

    def _all_layer_fids(self, layer):
        try:
            return list(layer.allFeatureIds())
        except Exception:
            pass
        req = QgsFeatureRequest().setFlags(QgsFeatureRequest.NoGeometry)
        try:
            req.setNoAttributes()
        except Exception:
            pass
        return [feat.id() for feat in layer.getFeatures(req)]

    @staticmethod
    def _attr_is_empty(raw):
        if raw is None or raw == NULL:
            return True
        if isinstance(raw, str) and str(raw).strip() == "":
            return True
        return False

    def _pending_targets_all_empty(self, layer, pending, fids):
        indices = []
        for name in pending:
            idx = layer.fields().indexFromName(name)
            if idx >= 0:
                indices.append(idx)
        if not indices or not fids:
            return True
        fetched = self.model._fetch_attributes(fids, indices)
        for fid in fids:
            row = fetched.get(fid, {})
            for idx in indices:
                if not self._attr_is_empty(row.get(idx, NULL)):
                    return False
        return True

    def _pack_variables(self):
        remarks = getattr(self, "_remarks", None)
        if remarks is None:
            return []
        try:
            return remarks.current_variables()
        except Exception:
            return []

    def _resolve_const_write(self, value):
        return resolve_var_template(value, self._pack_variables())

    def _resolve_pending_or_warn(self, pending, title="快速插入"):
        resolved = {}
        missing = []
        seen = set()
        for field_name, raw in (pending or {}).items():
            payload = raw if isinstance(raw, dict) else meaning_payload(raw)
            kind = payload.get("kind") or "const"
            value = payload.get("value") or ""
            if kind == "expr":
                resolved[field_name] = payload
                continue
            text, lost = self._resolve_const_write(value)
            if lost:
                for name in lost:
                    if name not in seen:
                        seen.add(name)
                        missing.append(name)
                continue
            item = dict(payload)
            item["value"] = text
            item["text"] = text
            resolved[field_name] = item
        if missing:
            QMessageBox.information(
                self,
                title,
                "变量「%s」不存在，无法写入。" % "、".join(missing),
            )
            return None
        return resolved

    def _apply_quick_pending(self, pending, selected_only=False, scope=None, confirm=True):
        layer = self._layer
        if scope is None:
            scope = "selected" if selected_only else "filtered"
        pending = self._resolve_pending_or_warn(pending, title="快速插入")
        if not pending:
            return
        fids = self._fill_target_fids(title="快速插入", scope=scope)
        if not fids:
            return
        scope_tip = {"selected": "选中", "filtered": "筛选", "all": "全部"}.get(scope, scope)
        if confirm and not self._pending_targets_all_empty(layer, pending, fids):
            lines = "\n".join(
                "  %s = %s" % (name, self._pending_shown(val))
                for name, val in pending.items()
            )
            if (
                QMessageBox.question(
                    self,
                    "快速插入",
                    f"将按快速插入行写入 {len(fids)} 条（{scope_tip}）：\n{lines}\n继续？",
                )
                != QMessageBox.Yes
            ):
                return
        total = 0
        skipped = 0
        multi = len(pending) > 1
        if multi:
            layer.beginEditCommand("快速插入")
        try:
            for field_name, raw in pending.items():
                field_idx = layer.fields().indexFromName(field_name)
                if field_idx < 0:
                    continue
                field = layer.fields().at(field_idx)
                payload = raw if isinstance(raw, dict) else meaning_payload(raw)
                kind = payload.get("kind") or "const"
                value = payload.get("value") or ""
                if kind == "expr":
                    values = self._eval_fill_expression(
                        layer, field, fids, value, skip_errors=True
                    )
                    if not values:
                        skipped += 1
                        continue
                else:
                    coerced = self._coerce_value_for_field(field, value)
                    values = {fid: coerced for fid in fids}
                total += self._commit_attribute_values(
                    layer, field_idx, field_name, values, "快速插入", in_command=multi
                ) or 0
        finally:
            if multi:
                if total:
                    layer.endEditCommand()
                else:
                    layer.destroyEditCommand()
        self.quick_fill.clear_pending(list(pending.keys()))
        if total:
            extra = "，%s 列因表达式失败已跳过" % skipped if skipped else ""
            self.status.showMessage(f"快速插入完成：更新 {total} 处{extra}", 4000)
        elif skipped:
            self.status.showMessage("快速插入：表达式未能写入任何行", 4000)

    @staticmethod
    def _pending_shown(val):
        if isinstance(val, dict):
            return val.get("text") or val.get("value") or ""
        return val

    def _ask_quick_fill_scope(self, field_name, value, combo):
        box = QMessageBox(self)
        box.setWindowTitle("快速插入")
        shown = combo.currentText() if combo is not None else str(value)
        box.setText(f"将「{shown}」写入字段「{field_name}」")
        btn_all = box.addButton("更新全部", QMessageBox.ActionRole)
        btn_filt = box.addButton("更新筛选项", QMessageBox.ActionRole)
        btn_sel = box.addButton("更新选中", QMessageBox.ActionRole)
        btn_cancel = box.addButton("取消", QMessageBox.RejectRole)
        box.setDefaultButton(btn_sel)
        box.exec_()
        clicked = box.clickedButton()
        if clicked is None or clicked == btn_cancel:
            return
        pending = {field_name: value}
        if clicked == btn_all:
            self._apply_quick_pending(pending, scope="all", confirm=False)
        elif clicked == btn_filt:
            self._apply_quick_pending(pending, scope="filtered", confirm=False)
        elif clicked == btn_sel:
            self._apply_quick_pending(pending, scope="selected", confirm=False)

    def _quick_fill_field(self, field_name, value, selected_only=True):
        layer = self._layer
        if layer is None:
            return
        if not layer.isEditable():
            QMessageBox.information(self, "快速插入", "请先切换到编辑模式。")
            return
        if not field_name:
            return
        field_idx = layer.fields().indexFromName(field_name)
        if field_idx < 0:
            return
        field = layer.fields().at(field_idx)
        if selected_only:
            selected = set(layer.selectedFeatureIds())
            fids = [fid for fid in self.model.fids() if fid in selected]
            if not fids:
                QMessageBox.information(self, "快速插入", "没有选中的要素。")
                return
        else:
            fids = self.model.fids()
            if not fids:
                QMessageBox.information(self, "快速插入", "当前没有可更新的筛选行。")
                return
        coerced = self._coerce_value_for_field(field, value)
        values = {fid: coerced for fid in fids}
        updated = self._commit_attribute_values(
            layer, field_idx, field_name, values, "快速插入"
        )
        if updated:
            self.status.showMessage(
                f"快速插入：{updated} 行 → {field_name} = {value}", 4000
            )

    def _open_fill_expression_builder(self):
        if self._layer is None:
            return
        dlg = QgsExpressionBuilderDialog(self._layer, self.ed_fill.text(), self)
        dlg.setWindowTitle("赋值表达式")
        if dlg.exec_():
            self.ed_fill.setText(dlg.expressionText())
            self.cmb_fill_mode.blockSignals(True)
            idx = self.cmb_fill_mode.findData("expr")
            if idx >= 0:
                self.cmb_fill_mode.setCurrentIndex(idx)
            self.cmb_fill_mode.blockSignals(False)
            self._on_fill_mode_changed()

    def _field_stores_text(self, field):
        type_name = (field.typeName() or "").lower()
        if any(token in type_name for token in ("string", "text", "char", "varchar")):
            return True
        try:
            from qgis.PyQt.QtCore import QVariant

            return field.type() == QVariant.String
        except Exception:
            return False

    def _coerce_value_for_field(self, field, raw):
        """Field-ready value, or a _CoerceIssue that _commit_attribute_values reports."""
        status, value, note = coerce_for_field(field, raw)
        if status == "ok":
            return value
        return _CoerceIssue(status, raw, value, note)

    def _confirm_coerce_issues(self, command_name, field_name, total, invalid, rounded, toolong):
        """Return True to write the convertible values, False to cancel."""
        if not invalid and not rounded and not toolong:
            return True

        def samples(items):
            out = []
            for fid, issue in items[:4]:
                raw = value_text(issue.raw) or "（空）"
                if issue.status == "rounded":
                    out.append("    编号 %s：%s → %s" % (fid, raw, issue.value))
                else:
                    out.append("    编号 %s：%s（%s）" % (fid, raw, issue.note))
            if len(items) > 4:
                out.append("    …")
            return "\n".join(out)

        lines = ["字段「%s」本次要写入 %s 条。" % (field_name, total + len(invalid))]
        if invalid:
            lines.append("\n%s 条和字段类型不符，写不进去，会跳过：\n%s" % (len(invalid), samples(invalid)))
        if rounded:
            lines.append("\n%s 条是小数，整数字段会四舍五入：\n%s" % (len(rounded), samples(rounded)))
        if toolong:
            lines.append(
                "\n%s 条文字超过字段长度，保存时数据源可能截断或拒绝：\n%s"
                % (len(toolong), samples(toolong))
            )
        if total <= 0:
            QMessageBox.warning(self, command_name, "\n".join(lines) + "\n\n没有可写入的值。")
            return False
        lines.append("\n继续写入其余 %s 条？" % total)
        return QMessageBox.question(self, command_name, "\n".join(lines)) == QMessageBox.Yes

    def _run_fill(self, selected_only=False):
        layer = self._layer
        if layer is None or not layer.isEditable():
            QMessageBox.information(self, "赋值", "请先切换到编辑模式。")
            return

        pending = {}
        if (
            self._remarks_active()
            and hasattr(self, "quick_fill")
            and self.quick_fill.isVisible()
        ):
            pending = self.quick_fill.pending_values()
        if pending:
            self._apply_quick_pending(pending, selected_only=selected_only)
            return

        field_name = self.cmb_fill_field.currentData()
        if not field_name:
            QMessageBox.information(self, "赋值", "请选择目标字段。")
            return
        field_idx = layer.fields().indexFromName(field_name)
        if field_idx < 0:
            return
        field = layer.fields().at(field_idx)
        mode = self.cmb_fill_mode.currentData()
        content = self.ed_fill.text()

        fids = self._fill_target_fids(selected_only=selected_only, title="赋值")
        if not fids:
            return

        if mode == "replace":
            self._run_replace(layer, field, field_idx, field_name, fids, selected_only)
            return
        if mode == "blank":
            self._run_fill_blank(layer, field, field_idx, field_name, fids, selected_only)
            return
        if mode == "around_seq":
            self._run_fill_around_seq(layer, field, field_idx, field_name, fids, selected_only)
            return
        if mode == "affix":
            self._run_fill_affix(layer, field, field_idx, field_name, fids, selected_only)
            return

        seq_start = 1
        seq_width = 0
        seq_order = None
        if mode in ("seq", "prefix_seq"):
            if mode == "seq" and content.strip():
                num = try_parse_number(content)
                if num is None:
                    QMessageBox.warning(self, "赋值", "序号模式请输入起始数字，或留空从 1 开始。")
                    return
                seq_start = int(round(num))
            seq_order = [fid for fid in self.model.fids() if fid in set(fids)]
            if selected_only and not seq_order:
                seq_order = list(fids)
            width_choice = "none"
            if hasattr(self, "cmb_fill_width"):
                width_choice = self.cmb_fill_width.currentData()
            seq_width = sequence_pad_width(width_choice, seq_start, len(seq_order))
            if seq_width > 0 and not self._field_stores_text(field):
                QMessageBox.warning(
                    self,
                    "赋值",
                    "补零只会留在文本字段里。当前字段是数字类型，前导零存不住。"
                    "请改成文本字段，或把位数选成「不补零」。",
                )
                return

        scope_tip = "选中" if selected_only else "筛选"
        const_kind, const_payload = (None, None)
        if mode == "const":
            const_kind, const_payload = self._parse_const_fill_input(content)
        if not self._pending_targets_all_empty(layer, {field_name: True}, fids):
            if const_kind == "field":
                confirm_msg = (
                    "将用字段「%s」的内容写入「%s」共 %s 条（%s）记录，继续？"
                    % (const_payload, field_name, len(fids), scope_tip)
                )
            else:
                confirm_msg = (
                    f"将向字段「{field_name}」写入 {len(fids)} 条（{scope_tip}）记录，继续？"
                )
            if (
                QMessageBox.question(
                    self,
                    "赋值确认",
                    confirm_msg,
                )
                != QMessageBox.Yes
            ):
                return

        values = {}
        src_field = None
        if mode == "const":
            kind, payload = self._parse_const_fill_input(content)
            if kind == "field":
                src_field = payload
                values = self._copy_field_values(layer, field, fids, src_field)
                if values is None:
                    QMessageBox.warning(self, "赋值", "找不到字段「%s」。" % src_field)
                    return
            else:
                if kind == "null":
                    raw = NULL
                else:
                    raw = payload
                    if isinstance(raw, str):
                        resolved, missing = self._resolve_const_write(raw)
                        if missing:
                            QMessageBox.information(
                                self,
                                "赋值",
                                "变量「%s」不存在，无法写入。" % "、".join(missing),
                            )
                            return
                        raw = resolved
                val = self._coerce_value_for_field(field, raw)
                for fid in fids:
                    values[fid] = val

        elif mode == "seq":
            for i, fid in enumerate(seq_order):
                number = seq_start + i
                raw = format_padded_int(number, seq_width) if seq_width > 0 else number
                values[fid] = self._coerce_value_for_field(field, raw)

        elif mode == "prefix_seq":
            prefix = content
            for i, fid in enumerate(seq_order):
                token = format_padded_int(i + 1, seq_width)
                values[fid] = self._coerce_value_for_field(field, "%s%s" % (prefix, token))

        elif mode == "expr":
            values = self._eval_fill_expression(layer, field, fids, content)
            if values is None:
                return
        else:
            return

        updated = self._commit_attribute_values(layer, field_idx, field_name, values, "赋值")
        if updated:
            if src_field:
                self.status.showMessage(
                    "赋值完成：已更新 %s 行 → %s ← %s" % (updated, field_name, src_field),
                    4000,
                )
            else:
                self.status.showMessage(f"赋值完成：已更新 {updated} 行 → {field_name}", 4000)

    def _fill_row_order(self, fids, selected_only):
        order = [fid for fid in self.model.fids() if fid in set(fids)]
        if selected_only and not order:
            order = list(fids)
        return order

    def _fill_width_choice(self):
        if hasattr(self, "cmb_fill_width"):
            return self.cmb_fill_width.currentData()
        return "none"

    def _run_fill_blank(self, layer, field, field_idx, field_name, fids, selected_only):
        content = self.ed_fill.text()
        kind, payload = self._parse_const_fill_input(content)
        fetched = self.model._fetch_attributes(fids, [field_idx])
        empty_fids = [
            fid
            for fid in fids
            if self._attr_is_empty(fetched.get(fid, {}).get(field_idx, NULL))
        ]
        if not empty_fids:
            QMessageBox.information(self, "赋值", "范围内没有空白单元格，已有内容不会改。")
            return
        scope_tip = "选中" if selected_only else "筛选"
        skipped = len(fids) - len(empty_fids)
        if skipped:
            if kind == "field":
                confirm_msg = (
                    "只把字段「%s」写入「%s」的空白单元格，共 %s 条（%s）。"
                    "已有内容 %s 条不动。继续？"
                    % (payload, field_name, len(empty_fids), scope_tip, skipped)
                )
            else:
                confirm_msg = (
                    "只写入「%s」的空白单元格，共 %s 条（%s）。已有内容 %s 条不动。继续？"
                    % (field_name, len(empty_fids), scope_tip, skipped)
                )
            if QMessageBox.question(self, "赋值确认", confirm_msg) != QMessageBox.Yes:
                return
        src_field = None
        values = {}
        if kind == "field":
            src_field = payload
            copied = self._copy_field_values(layer, field, empty_fids, src_field)
            if copied is None:
                QMessageBox.warning(self, "赋值", "找不到字段「%s」。" % src_field)
                return
            values = copied
        else:
            if kind == "null":
                raw = NULL
            else:
                raw = payload
                if isinstance(raw, str):
                    resolved, missing = self._resolve_const_write(raw)
                    if missing:
                        QMessageBox.information(
                            self,
                            "赋值",
                            "变量「%s」不存在，无法写入。" % "、".join(missing),
                        )
                        return
                    raw = resolved
            val = self._coerce_value_for_field(field, raw)
            for fid in empty_fids:
                values[fid] = val
        updated = self._commit_attribute_values(layer, field_idx, field_name, values, "赋值")
        if updated:
            self.status.showMessage(
                "已填空白 %s 行，跳过已有内容 %s 行 → %s" % (updated, skipped, field_name),
                4000,
            )
        elif not skipped:
            self.status.showMessage("赋值完成：已更新 0 行 → %s" % field_name, 4000)
        else:
            self.status.showMessage("空白单元格的值没有变化 → %s" % field_name, 4000)

    def _run_fill_around_seq(self, layer, field, field_idx, field_name, fids, selected_only):
        """Add a padded sequence before or after each cell's current text."""
        if not self._field_stores_text(field):
            QMessageBox.warning(
                self,
                "赋值",
                "前后序号是在已有文字上加序号，只写入文本字段。当前字段是数字类型，存不住。",
            )
            return
        place = "after"
        if hasattr(self, "cmb_fill_seq_side"):
            place = self.cmb_fill_seq_side.currentData() or "after"
        order = self._fill_row_order(fids, selected_only)
        width = sequence_pad_width(self._fill_width_choice(), 1, len(order))
        fetched = self.model._fetch_attributes(order, [field_idx])
        values = {}
        sample = None
        for i, fid in enumerate(order):
            token = format_padded_int(i + 1, width)
            current = fetched.get(fid, {}).get(field_idx, NULL)
            if self._attr_is_empty(current):
                text = ""
            else:
                text = str(current)
            raw = (token + text) if place == "before" else (text + token)
            values[fid] = self._coerce_value_for_field(field, raw)
            if sample is None and text:
                sample = "%s → %s" % (text, raw)
        if sample is None and order:
            token = format_padded_int(1, width)
            sample = "（空白）→ %s" % token
        scope_tip = "选中" if selected_only else "筛选"
        side = "前面" if place == "before" else "后面"
        if (
            QMessageBox.question(
                self,
                "赋值确认",
                "保留「%s」里的原文字，在%s加上序号，共 %s 条（%s）。如 %s。空白只写序号。继续？"
                % (field_name, side, len(order), scope_tip, sample or ""),
            )
            != QMessageBox.Yes
        ):
            return
        updated = self._commit_attribute_values(layer, field_idx, field_name, values, "赋值")
        if updated:
            self.status.showMessage(
                "前后序号完成：已在原文字%s加上序号，更新 %s 行 → %s" % (side, updated, field_name),
                4000,
            )

    def _run_fill_affix(self, layer, field, field_idx, field_name, fids, selected_only):
        prefix = self.ed_fill_prefix.text() if hasattr(self, "ed_fill_prefix") else ""
        suffix = self.ed_fill_suffix.text() if hasattr(self, "ed_fill_suffix") else ""
        if prefix == "" and suffix == "":
            QMessageBox.information(self, "赋值", "请填写要加在前面或后面的文字。")
            return
        if not self._field_stores_text(field):
            QMessageBox.warning(
                self,
                "赋值",
                "前后加字只写入文本字段。当前字段是数字类型，加字存不住。",
            )
            return
        fetched = self.model._fetch_attributes(fids, [field_idx])
        values = {}
        for fid in fids:
            raw = fetched.get(fid, {}).get(field_idx, NULL)
            if self._attr_is_empty(raw):
                continue
            values[fid] = self._coerce_value_for_field(field, "%s%s%s" % (prefix, raw, suffix))
        if not values:
            QMessageBox.information(self, "赋值", "范围内没有已有文字，空白单元格不会被改。")
            return
        scope_tip = "选中" if selected_only else "筛选"
        skipped = len(fids) - len(values)
        if (
            QMessageBox.question(
                self,
                "赋值确认",
                "给「%s」已有文字前面加「%s」、后面加「%s」，共 %s 条（%s）。空白 %s 条不动。继续？"
                % (field_name, prefix, suffix, len(values), scope_tip, skipped),
            )
            != QMessageBox.Yes
        ):
            return
        updated = self._commit_attribute_values(layer, field_idx, field_name, values, "赋值")
        if updated:
            self.status.showMessage(
                "前后加字完成：已更新 %s 行，空白未改 %s 行 → %s" % (updated, skipped, field_name),
                4000,
            )
        else:
            self.status.showMessage("已有文字没有变化 → %s" % field_name, 4000)

    def _eval_fill_expression(self, layer, field, fids, expr_text, skip_errors=False):
        expr_text = (expr_text or "").strip()
        if not expr_text:
            if skip_errors:
                return {}
            QMessageBox.warning(self, "赋值", "请输入表达式。")
            return None
        exp = QgsExpression(expr_text)
        if exp.hasParserError():
            QMessageBox.warning(
                self,
                "赋值" if not skip_errors else "快速插入",
                exp.parserErrorString(),
            )
            return {} if skip_errors else None
        ctx = QgsExpressionContext()
        ctx.appendScopes(QgsExpressionContextUtils.globalProjectLayerScopes(layer))
        exp.prepare(ctx)

        need_geom = True
        subset = None
        try:
            need_geom = bool(exp.needsGeometry())
        except Exception:
            need_geom = True
        try:
            ref = exp.referencedColumns() or set()
            if "*" not in ref:
                idxs = []
                for name in ref:
                    i = layer.fields().indexFromName(name)
                    if i >= 0:
                        idxs.append(i)
                subset = idxs
        except Exception:
            subset = None

        values = {}
        eval_error = None
        chunk = 2500
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            for i in range(0, len(fids), chunk):
                if eval_error:
                    break
                batch = fids[i : i + chunk]
                req = QgsFeatureRequest().setFilterFids(batch)
                if not need_geom:
                    req.setFlags(QgsFeatureRequest.NoGeometry)
                if subset is not None:
                    req.setSubsetOfAttributes(subset)
                for feat in layer.getFeatures(req):
                    ctx.setFeature(feat)
                    raw = exp.evaluate(ctx)
                    if exp.hasEvalError():
                        if skip_errors:
                            continue
                        eval_error = (feat.id(), exp.evalErrorString())
                        break
                    values[feat.id()] = self._coerce_value_for_field(field, raw)
        finally:
            QApplication.restoreOverrideCursor()
        if eval_error:
            QMessageBox.warning(
                self,
                "赋值",
                f"表达式错误（FID {eval_error[0]}）：{eval_error[1]}",
            )
            return None
        return values

    def _run_replace(self, layer, field, field_idx, field_name, fids, selected_only):
        find_text = self.ed_fill_find.text()
        replace_text = self.ed_fill_replace.text()
        if find_text == "":
            QMessageBox.warning(self, "替换", "请输入替换前的文字。")
            return

        fetched = self.model._fetch_attributes(fids, [field_idx])
        values = {}
        rows = 0
        occ = 0
        for fid in fids:
            raw = fetched.get(fid, {}).get(field_idx, NULL)
            if raw is None or raw == NULL:
                continue
            text = str(raw)
            n = text.count(find_text)
            if n <= 0:
                continue
            new_text = text.replace(find_text, replace_text)
            if new_text == text:
                continue
            values[fid] = self._coerce_value_for_field(field, new_text)
            rows += 1
            occ += n

        if not values:
            QMessageBox.information(
                self,
                "替换",
                f"当前范围内没有匹配「{find_text}」。",
            )
            return

        scope_tip = "选中" if selected_only else "筛选"
        if (
            QMessageBox.question(
                self,
                "替换确认",
                f"字段「{field_name}」（{scope_tip}）\n"
                f"将「{find_text}」替换为「{replace_text}」\n"
                f"命中 {rows} 行 / {occ} 处，继续？",
            )
            != QMessageBox.Yes
        ):
            return

        updated = self._commit_attribute_values(layer, field_idx, field_name, values, "替换", skip_unchanged=False)
        if updated:
            self.status.showMessage(
                f"替换完成：{updated} 行 / {occ} 处 → {field_name}",
                4000,
            )

    def _commit_attribute_values(
        self, layer, field_idx, field_name, values, command_name, skip_unchanged=True, in_command=False
    ):
        if not values:
            return 0
        invalid, rounded, toolong = [], [], []
        clean = {}
        for fid, val in values.items():
            if isinstance(val, _CoerceIssue):
                if val.status == "invalid":
                    invalid.append((fid, val))
                    continue
                (rounded if val.status == "rounded" else toolong).append((fid, val))
                clean[fid] = val.value
            else:
                clean[fid] = val
        values = clean
        if skip_unchanged and values:
            values = self._drop_unchanged_fill_values(field_idx, values)
        rounded = [item for item in rounded if item[0] in values]
        toolong = [item for item in toolong if item[0] in values]
        if not self._confirm_coerce_issues(
            command_name, field_name, len(values), invalid, rounded, toolong
        ):
            return 0
        if not values:
            return 0
        disconnected = False
        try:
            layer.attributeValueChanged.disconnect(self._on_attribute_changed)
            disconnected = True
        except Exception:
            disconnected = False

        QApplication.setOverrideCursor(Qt.WaitCursor)
        canvas = None
        frozen = False
        updated = 0
        try:
            try:
                canvas = self.iface.mapCanvas()
                if canvas is not None and not canvas.isFrozen():
                    canvas.freeze(True)
                    frozen = True
            except Exception:
                frozen = False
            own_command = not in_command
            if own_command:
                layer.beginEditCommand(command_name)
            attr_map = {int(fid): {int(field_idx): val} for fid, val in values.items()}
            used_batch = False
            ok = False
            try:
                ok = bool(layer.changeAttributeValues(attr_map))
                used_batch = True
            except Exception:
                used_batch = False
                ok = False
            if used_batch:
                if ok:
                    updated = len(values)
                    if own_command:
                        layer.endEditCommand()
                else:
                    if own_command:
                        layer.destroyEditCommand()
                    QMessageBox.warning(self, command_name, "写入失败。")
                    return 0
            else:
                for fid, val in values.items():
                    if layer.changeAttributeValue(fid, field_idx, val):
                        updated += 1
                if updated:
                    if own_command:
                        layer.endEditCommand()
                else:
                    if own_command:
                        layer.destroyEditCommand()
                    QMessageBox.warning(self, command_name, "写入失败。")
                    return 0
        finally:
            if frozen and canvas is not None:
                try:
                    canvas.freeze(False)
                except Exception:
                    pass
            QApplication.restoreOverrideCursor()
            if disconnected:
                try:
                    layer.attributeValueChanged.connect(self._on_attribute_changed)
                except Exception:
                    pass

        self._refresh_after_fill(field_name)
        return updated

    def refresh_after_external_edit(self, field_names=None):
        """Called from 快速命名 after it writes the same layer."""
        names = [n for n in (field_names or []) if n]
        if not names:
            self.model.refresh_cached_attributes()
            self._update_status()
            return
        if len(names) == 1:
            self._refresh_after_fill(names[0])
            return
        need_reload = self.model.sort_field() in names
        text = self.model.text_filter()
        if text:
            ff = self.model.filter_field()
            if ff is None or ff in names:
                need_reload = True
        if need_reload:
            self.reload_table()
            return
        self.model.refresh_cached_attributes()
        if self.model.sort_field():
            self._refresh_column_stats(self.model.sort_field())
        self._update_status()
        self._schedule_column_widths(0)

    def _refresh_after_fill(self, field_name):
        need_reload = self.model.sort_field() == field_name
        text = self.model.text_filter()
        if text:
            ff = self.model.filter_field()
            if ff is None or ff == field_name:
                need_reload = True
        if need_reload:
            self.reload_table()
        else:
            self.model.refresh_cached_attributes()
            if self.model.sort_field():
                self._refresh_column_stats(self.model.sort_field())
            self._update_status()
            self._schedule_column_widths(0)

    def _zoom_selected(self):
        if self._layer is None:
            return
        if not self._layer.selectedFeatureIds():
            QMessageBox.information(self, "缩放", "没有选中的要素。")
            return
        self.iface.mapCanvas().zoomToSelected(self._layer)
        self.iface.mapCanvas().refresh()

    def _invert_selection(self):
        """Invert selection within currently displayed table rows; keep outside selection."""
        layer = self._layer
        if layer is None:
            return
        visible = set(self.model.fids())
        if not visible:
            return
        selected = set(layer.selectedFeatureIds())
        outside = selected - visible
        flipped_on = visible - selected
        layer.selectByIds(list(outside | flipped_on))
        self._update_status()

    def _deselect_all(self):
        layer = self._layer
        if layer is None:
            return
        layer.removeSelection()
        self._update_status()

    def _export_csv(self):
        if self._layer is None:
            QMessageBox.information(self, "导出", "无图层。")
            return
        dlg = ExportCsvDialog(self)
        if dlg.exec_() != QDialog.Accepted:
            return
        scope = dlg.scope()
        qgis_fmt = dlg.use_qgis_format()
        coerce_num = dlg.coerce_numeric_text()
        path, _ = QFileDialog.getSaveFileName(
            self, "导出 CSV", os.path.expanduser("~"), "CSV (*.csv)"
        )
        if not path:
            return

        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            if qgis_fmt:
                self._write_csv_qgis_format(path, scope, coerce_num)
            else:
                self._write_csv_custom_order(path, scope, coerce_num)
        except OSError as e:
            QMessageBox.warning(self, "导出失败", str(e))
            return
        finally:
            QApplication.restoreOverrideCursor()

        tip_scope = "全部要素" if scope == ExportCsvDialog.SCOPE_ALL else "当前表格"
        tip_fmt = "QGIS格式" if qgis_fmt else "自定义列序"
        tip_num = "数字文本" if coerce_num else "原文"
        self.status.showMessage(
            f"已导出（{tip_scope} / {tip_fmt} / {tip_num}）：{path}", 5000
        )

    @staticmethod
    def _csv_cell(val, coerce_numeric=False):
        if val is None or val == NULL:
            return ""
        temporal = temporal_text(val)
        if temporal is not None:
            return temporal
        if coerce_numeric:
            num = try_parse_number(val)
            if num is not None:
                if abs(num - round(num)) < 1e-12:
                    return int(round(num))
                return num
        return val

    def _write_csv_custom_order(self, path, scope, coerce_numeric=False):
        """Export using plugin display column order (no geometry column)."""
        headers = self.model.field_names()
        if not headers:
            headers = list(self._all_field_names)
        name_to_idx = {
            self._layer.fields().at(i).name(): i
            for i in range(self._layer.fields().count())
        }
        field_indices = [name_to_idx[n] for n in headers if n in name_to_idx]

        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            if scope == ExportCsvDialog.SCOPE_VISIBLE:
                fids = self.model.fids()
                if not fids:
                    return
                values_by_fid = {}
                chunk = 2500
                for i in range(0, len(fids), chunk):
                    batch = fids[i : i + chunk]
                    req = (
                        QgsFeatureRequest()
                        .setFilterFids(batch)
                        .setFlags(QgsFeatureRequest.NoGeometry)
                        .setSubsetOfAttributes(field_indices)
                    )
                    for feat in self._layer.getFeatures(req):
                        values_by_fid[feat.id()] = [
                            self._csv_cell(feat.attribute(idx), coerce_numeric)
                            for idx in field_indices
                        ]
                for fid in fids:
                    writer.writerow(values_by_fid.get(fid, [""] * len(field_indices)))
            else:
                req = QgsFeatureRequest().setFlags(QgsFeatureRequest.NoGeometry)
                for feat in self._layer.getFeatures(req):
                    writer.writerow(
                        [
                            self._csv_cell(feat.attribute(idx), coerce_numeric)
                            for idx in field_indices
                        ]
                    )

    def _write_csv_qgis_format(self, path, scope, coerce_numeric=False):
        """
        Match QGIS attribute table copy/paste:
        wkt_geom + layer fields in native provider/layer order.
        """
        layer = self._layer
        fields = layer.fields()
        field_names = [fields.at(i).name() for i in range(fields.count())]
        headers = ["wkt_geom"] + field_names

        req = QgsFeatureRequest()
        if scope == ExportCsvDialog.SCOPE_VISIBLE:
            fids = self.model.fids()
            if not fids:
                with open(path, "w", newline="", encoding="utf-8-sig") as f:
                    csv.writer(f).writerow(headers)
                return
            req.setFilterFids(fids)

        fid_order = None
        if scope == ExportCsvDialog.SCOPE_VISIBLE:
            fid_order = {fid: i for i, fid in enumerate(self.model.fids())}

        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            collected = []
            for feat in layer.getFeatures(req):
                geom = feat.geometry()
                if geom is None or geom.isEmpty():
                    wkt = ""
                else:
                    wkt = geom.asWkt()
                row = [wkt] + [
                    self._csv_cell(feat.attribute(i), coerce_numeric)
                    for i in range(fields.count())
                ]
                if fid_order is not None:
                    collected.append((fid_order.get(feat.id(), 10**12), row))
                else:
                    writer.writerow(row)
            if fid_order is not None:
                collected.sort(key=lambda x: x[0])
                for _, row in collected:
                    writer.writerow(row)

    def _update_status(self):
        layer = self._layer
        if layer is None:
            self.status.showMessage("无图层")
            self.lbl_stats.clear()
            self.lbl_stats.setStyleSheet("")
            return
        total = layer.featureCount()
        shown = self.model.rowCount()
        selected = len(layer.selectedFeatureIds())
        if layer.isEditable() and layer.isModified():
            changed = len(self.model.modified_fids())
            edit = "编辑·未保存（已改 %s 条）" % changed if changed else "编辑·未保存"
        elif layer.isEditable():
            edit = "编辑中"
        else:
            edit = "只读"
        geom = ""
        try:
            geom = {0: "点", 1: "线", 2: "面"}.get(int(layer.geometryType()), "")
        except Exception:
            geom = ""
        if geom:
            geom = "  |  " + geom
        sort = ""
        if self.model.sort_field():
            arrow = "↑" if self.model.sort_ascending() else "↓"
            sort = f"  |  排序 {self.model.sort_field()}{arrow}"
        crs = ""
        try:
            c = layer.crs()
            if c is not None and c.isValid():
                auth = (c.authid() or "").strip()
                crs = f"  |  {auth}" if auth else f"  |  {c.description()}"
        except Exception:
            crs = ""
        empty = ""
        if shown == 0 and total:
            empty = "  |  " + self._empty_result_hint()
        self.status.showMessage(
            f"{layer.name()}{geom}  |  共 {total}  |  显示 {shown}  |  选中 {selected}  |  {edit}{sort}{crs}{empty}"
        )
        self._update_stats_label()

    def _empty_result_hint(self):
        """Why the table is empty although the layer has features."""
        reasons = []
        scope = self._current_scope_mode()
        if scope == "selected":
            reasons.append("范围是「仅选中」")
        elif scope == "canvas":
            reasons.append("范围是「地图可见」")
        elif scope == "modified":
            reasons.append("范围是「仅已修改」")
        if self.model.text_filter():
            reasons.append("过滤「%s」" % self.model.text_filter())
        if self.model.category_filter():
            reasons.append("筛选")
        if not reasons:
            return "没有匹配的行"
        return "没有匹配的行：%s，可清除或把范围切回「全部要素」" % "、".join(reasons)

    def _update_stats_label(self):
        """Bottom-right: selection-cell stats, or column sort stats."""
        if self._stats_mode == "selection":
            if self._sel_sum is not None and self._sel_count is not None:
                self.lbl_stats.setStyleSheet("")
                self.lbl_stats.setText(
                    f"选中合计 {self._sel_count}个"
                    f" / 总和 {self._format_sum(self._sel_sum)}"
                )
                return
            if self._sel_dup is not None:
                text = f"选中重名 {self._sel_dup}"
                if "有重名" in self._sel_dup:
                    self.lbl_stats.setStyleSheet("color: #c62828; font-weight: bold;")
                elif self._sel_dup.startswith("无重名"):
                    self.lbl_stats.setStyleSheet("color: #2e7d32; font-weight: bold;")
                else:
                    self.lbl_stats.setStyleSheet("")
                self.lbl_stats.setText(text)
                return

        if self._stats_mode == "column" and self._stats_field_name:
            label = self._field_labels.get(self._stats_field_name, self._stats_field_name)

            if self._sum_filtered is not None and self._sum_all is not None:
                self.lbl_stats.setStyleSheet("")
                self.lbl_stats.setText(
                    f"{label}合计 筛选 {self._format_sum(self._sum_filtered)}"
                    f" / 全部 {self._format_sum(self._sum_all)}"
                )
                return

            if self._dup_filtered is not None and self._dup_all is not None:
                text = f"{label}重名 筛选 {self._dup_filtered} / 全部 {self._dup_all}"
                has_dup = (
                    "有重名" in self._dup_filtered or "有重名" in self._dup_all
                )
                if has_dup:
                    self.lbl_stats.setStyleSheet("color: #c62828; font-weight: bold;")
                else:
                    no_dup = (
                        self._dup_filtered.startswith("无重名")
                        and self._dup_all.startswith("无重名")
                    )
                    if no_dup:
                        self.lbl_stats.setStyleSheet(
                            "color: #2e7d32; font-weight: bold;"
                        )
                    else:
                        self.lbl_stats.setStyleSheet("")
                self.lbl_stats.setText(text)
                return

        self.lbl_stats.clear()
        self.lbl_stats.setStyleSheet("")

    def _selected_cell_indexes(self):
        seen = set()
        out = []
        for view in (self.table, self.frozen):
            sm = view.selectionModel()
            if sm is None:
                continue
            for idx in sm.selectedIndexes():
                if not idx.isValid():
                    continue
                key = (idx.row(), idx.column())
                if key in seen:
                    continue
                seen.add(key)
                out.append(idx)
        return out

    def _with_layer_as_active(self, callback):
        """Run callback with this dialog's layer as iface active layer (QGIS clipboard)."""
        layer = self._layer
        if layer is None:
            return False
        prev = None
        try:
            prev = self.iface.activeLayer()
        except Exception:
            prev = None
        try:
            self.iface.setActiveLayer(layer)
            callback()
            return True
        except Exception as exc:
            QMessageBox.warning(self, "属性表", str(exc))
            return False
        finally:
            if prev is not None and prev != layer:
                try:
                    self.iface.setActiveLayer(prev)
                except Exception:
                    pass

    def keyPressEvent(self, event):
        if event.matches(QKeySequence.Copy):
            self._copy_by_shortcut()
            return
        super().keyPressEvent(event)

    def _copy_by_shortcut(self):
        if self._selected_cell_indexes():
            self._copy_selected_cells()
            return
        self._copy_features()

    def _cell_clipboard_text(self, val):
        if val is None or val == NULL:
            return ""
        text = value_text(val)
        if "\t" in text or "\n" in text or "\r" in text:
            text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\t", " ")
        return text

    def _copy_selected_cells(self):
        indexes = self._selected_cell_indexes()
        if not indexes:
            self.status.showMessage("请先选择单元格", 3000)
            return
        cells = {}
        rows = set()
        cols = set()
        for idx in indexes:
            row = idx.row()
            col = idx.column()
            rows.add(row)
            cols.add(col)
            val = self.model.data(idx, Qt.EditRole)
            cells[(row, col)] = self._cell_clipboard_text(val)
        row_list = sorted(rows)
        col_list = sorted(cols)
        lines = []
        for row in row_list:
            lines.append("\t".join(cells.get((row, col), "") for col in col_list))
        text = "\n".join(lines)
        clip = QApplication.clipboard()
        if clip is None:
            QMessageBox.warning(self, "复制", "无法访问剪贴板。")
            return
        clip.setText(text)
        self.status.showMessage("已复制 %s 个单元格到剪贴板" % len(indexes), 3000)

    def _copy_features(self):
        layer = self._layer
        if layer is None:
            return
        n = len(layer.selectedFeatureIds())
        if n == 0:
            self.status.showMessage("请先选中要素（选择单元格会同步选中对应行）", 3000)
            return
        act = self.iface.actionCopyFeatures()
        if act is None:
            QMessageBox.warning(self, "复制", "当前 QGIS 无复制要素动作。")
            return
        if self._with_layer_as_active(lambda: act.trigger()):
            self.status.showMessage(f"已复制 {n} 个要素到剪贴板", 3000)

    def _cut_features(self):
        layer = self._layer
        if layer is None:
            return
        if not layer.isEditable():
            QMessageBox.information(self, "剪切", "请先切换到编辑模式。")
            return
        n = len(layer.selectedFeatureIds())
        if n == 0:
            self.status.showMessage("请先选中要剪切的要素", 3000)
            return
        act = self.iface.actionCutFeatures()
        if act is None:
            QMessageBox.warning(self, "剪切", "当前 QGIS 无剪切要素动作。")
            return
        if self._with_layer_as_active(lambda: act.trigger()):
            self.reload_table()
            self.status.showMessage(f"已剪切 {n} 个要素", 3000)

    def _paste_features(self):
        layer = self._layer
        if layer is None:
            return
        if not layer.isEditable():
            QMessageBox.information(self, "粘贴", "请先切换到编辑模式。")
            return
        if clipboard_is_roundtrip(self._clipboard_text()):
            self.status.showMessage("剪贴板是「编号 + 值」两列 → 按编号粘贴回列", 4000)
            self._paste_roundtrip_column(None)
            return
        act = self.iface.actionPasteFeatures()
        if act is None:
            QMessageBox.warning(self, "粘贴", "当前 QGIS 无粘贴要素动作。")
            return
        if self._with_layer_as_active(lambda: act.trigger()):
            self._schedule_reload()
            self.status.showMessage("剪贴板不是可回贴格式 → 已按 QGIS 要素粘贴（新增要素）", 4000)

    def showEvent(self, event):
        super().showEvent(event)
        try:
            self.setMaximumSize(QWIDGETSIZE_MAX, QWIDGETSIZE_MAX)
        except Exception:
            pass
        self._schedule_column_widths(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if getattr(self, "_col_width_mode", "fit") == "fit":
            self._schedule_column_widths(80)

    def closeEvent(self, event):
        self._save_session_geometry()
        self._filter_timer.stop()
        for name in ("_reload_timer", "_selected_scope_timer", "_status_timer", "_quick_value_timer"):
            timer = getattr(self, name, None)
            if timer is not None:
                timer.stop()
        for signal, slot in (
            (QgsProject.instance().layersWillBeRemoved, self._on_layers_removed),
            (self.iface.currentLayerChanged, self._on_current_layer_changed),
        ):
            try:
                signal.disconnect(slot)
            except Exception:
                pass
        if hasattr(self, "_selection_stats_timer"):
            self._selection_stats_timer.stop()
        if hasattr(self, "_canvas_scope_timer"):
            self._canvas_scope_timer.stop()
        if hasattr(self, "_col_width_timer"):
            self._col_width_timer.stop()
        # force disconnect canvas watch
        if hasattr(self, "cmb_scope"):
            try:
                # temporarily pretend not canvas
                self._watching_canvas = True
                canvas = self.iface.mapCanvas()
                canvas.extentsChanged.disconnect(self._on_canvas_extents_changed)
            except Exception:
                pass
            self._watching_canvas = False
        self._disconnect_layer_signals()
        self._detach_remarks_hub()
        self._remarks_hub = None
        try:
            QgsProject.instance().readProject.disconnect(self._on_project_read)
        except Exception:
            pass
        try:
            QgsProject.instance().cleared.disconnect(self._on_project_cleared)
        except Exception:
            pass
        super().closeEvent(event)

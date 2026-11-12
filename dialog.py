# -*- coding: utf-8 -*-
"""Main attribute table dialog."""

import csv
import io
import os
from collections import Counter
from .i18n import localize_button_box, tr

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
from .fields_manager import FieldsManagerDialog
from .settings_store import SettingsStore
from .settings_dialog import SettingsDialog
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
from .fill_replace import apply_replace
from .fill_expressions import expression_from_text
from .expression_library_dialog import ExpressionDropdown, ExpressionLibraryDialog, manage_icon
from .qt_compat import QAction, event_pos, run_exec
from .wide_combo import WidePopupCombo, open_full_text_popup


def plugin_version():
    path = os.path.join(os.path.dirname(__file__), "metadata.txt")
    try:
        with open(path, "r", encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("version="):
                    return (line.split("=", 1)[1] or "").strip() or "—"
    except Exception:
        pass  # nosec B110
    return "—"


FILTER_DELAY_MS = 500

# Not a legal field name, so it cannot collide with a real column called category.
QUICK_MODE_CATEGORY = "\x1fquick-category"


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
        self.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.view().viewport().installEventFilter(self)
        edit.installEventFilter(self)
        self.add_check_item(tr("全部"), None, True)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.showPopup()
            event.accept()
            return
        QComboBox.mousePressEvent(self, event)

    def wheelEvent(self, event):
        event.ignore()

    def hidePopup(self):
        QComboBox.hidePopup(self)
        # Closing the list selects the clicked row and would replace the summary.
        self._sync_text()

    def showPopup(self):
        open_full_text_popup(self)
        self._sync_text()

    def eventFilter(self, obj, event):
        edit = self.lineEdit()
        if obj is edit and event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
            self.showPopup()
            return True
        if obj is self.view().viewport():
            etype = event.type()
            if etype == QEvent.Type.MouseButtonPress:
                return True
            if etype == QEvent.Type.MouseButtonRelease:
                index = self.view().indexAt(event_pos(event))
                if index.isValid():
                    self._toggle_row(index.row())
                return True
        return QComboBox.eventFilter(self, obj, event)

    def clear_items(self):
        self.model().clear()

    def add_check_item(self, text, payload, checked=False):
        item = QStandardItem(text)
        item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
        item.setData(payload, Qt.ItemDataRole.UserRole)
        item.setToolTip(text)
        item.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
        self.model().appendRow(item)

    def add_note(self, text):
        item = QStandardItem(text)
        item.setFlags(Qt.ItemFlag.ItemIsEnabled)
        item.setToolTip(text)
        self.model().appendRow(item)

    def checked_payloads(self):
        out = []
        model = self.model()
        for row in range(1, model.rowCount()):
            item = model.item(row)
            if item is None or not (item.flags() & Qt.ItemFlag.ItemIsUserCheckable):
                continue
            if item.checkState() == Qt.CheckState.Checked:
                payload = item.data(Qt.ItemDataRole.UserRole)
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
        if item is None or not (item.flags() & Qt.ItemFlag.ItemIsUserCheckable):
            return
        if row == 0:
            self._check_all_only()
        else:
            item.setCheckState(
                Qt.CheckState.Unchecked if item.checkState() == Qt.CheckState.Checked else Qt.CheckState.Checked
            )
            if self.checked_payloads():
                all_item = model.item(0)
                if all_item is not None:
                    all_item.setCheckState(Qt.CheckState.Unchecked)
            else:
                self._check_all_only()
        self._sync_text()
        self.selectionChanged.emit()

    def _check_all_only(self):
        model = self.model()
        for row in range(model.rowCount()):
            item = model.item(row)
            if item is None or not (item.flags() & Qt.ItemFlag.ItemIsUserCheckable):
                continue
            item.setCheckState(Qt.CheckState.Checked if row == 0 else Qt.CheckState.Unchecked)

    def ensure_some_check(self):
        if not self.checked_payloads():
            self._check_all_only()
        self._sync_text()

    def _sync_text(self):
        labels = []
        model = self.model()
        for row in range(1, model.rowCount()):
            item = model.item(row)
            if item is None or not (item.flags() & Qt.ItemFlag.ItemIsUserCheckable):
                continue
            if item.checkState() == Qt.CheckState.Checked:
                labels.append(item.text())
        if not labels:
            text = tr("全部")
            tip = tr("全部（不额外筛选）")
        elif len(labels) == 1:
            text = labels[0]
            tip = labels[0]
        else:
            joined = tr("、").join(labels)
            text = joined if len(joined) <= 18 else (tr("已选 %d 项") % len(labels))
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
        pass  # nosec B110
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
    if text.startswith(prefix) and text[len(prefix):].strip():
        return text[len(prefix):].strip(), True
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
        return None, tr("剪贴板是空的。")
    raw = str(text).lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
    if not raw.strip():
        return None, tr("剪贴板是空的。")
    try:
        rows = list(csv.reader(io.StringIO(raw), delimiter="\t"))
    except Exception as exc:
        return None, tr("无法读取剪贴板：%s") % exc
    while rows and (not rows[-1] or all(not (cell or "").strip() for cell in rows[-1])):
        rows.pop()
    if not rows:
        return None, tr("剪贴板是空的。")
    header = rows[0]
    layer_id, ok = _split_fid_header(header[0] if header else "")
    if not ok:
        return None, tr(
            "剪贴板不是可回贴格式。请用列标题「复制本列（可回贴）」，"
            "第一列必须是编号（表头以 #fid 开头），第二列才是要改的值。"
        )
    data_rows = []
    for row in rows[1:]:
        if not row or all(not (cell or "").strip() for cell in row):
            continue
        data_rows.append(row)
    if not data_rows:
        return None, tr("没有可写回的数据行。")

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
        return None, tr(
            "值列是空的，没有写入，表格里的原数据不会被清掉。"
            "请同时复制编号列和有内容的值列，不要只复制空列。"
        )
    if 1 in nonempty:
        if len(nonempty) > 1:
            return None, tr("除了编号和值之外还有别的内容，没有写入，避免贴错列。")
        value_idx = 1
    elif header_field:
        return None, tr(
            "字段「%s」这一列是空的，没有写入，避免把原数据清掉。"
            "请复制编号列和这一列。"
        ) % header_field
    elif len(nonempty) == 1:
        value_idx = nonempty[0]
    else:
        return None, tr("除了编号和值之外还有别的内容，没有写入，避免贴错列。")
    field_name = ""
    if value_idx < len(header) and (header[value_idx] or "").strip():
        field_name = header[value_idx].strip()
    if not field_name or (layer_id and field_name == layer_id):
        return None, tr("表头缺少字段名。第一列是编号，第二列的表头应是字段名。")

    parsed = []
    seen = set()
    errors = []
    for lineno, row in enumerate(rows[1:], start=2):
        if not row or all(not (cell or "").strip() for cell in row):
            continue
        fid = _parse_fid_token(_roundtrip_cell(row, 0))
        if fid is None:
            errors.append(tr("第 %s 行编号无效：%s") % (lineno, (_roundtrip_cell(row, 0) or "").strip()))
            continue
        if fid in seen:
            errors.append(tr("编号 %s 重复（第 %s 行）") % (fid, lineno))
            continue
        seen.add(fid)
        parsed.append((fid, _roundtrip_cell(row, value_idx)))
    if errors:
        shown = "\n".join(errors[:8])
        more = "" if len(errors) <= 8 else tr("\n…共 %s 处问题") % len(errors)
        return None, tr("没有写入。请改好后再贴：\n%s%s") % (shown, more)
    if not parsed:
        return None, tr("没有可写回的数据行。")
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
# Language sits immediately left of the toolbar-order button.
DEFAULT_TOOLBAR_ORDER = [
    "edit",
    "save",
    "reload",
    "revert",
    "sep1",
    "delete",
    "select_all",
    "invert",
    "deselect",
    "copy",
    "cut",
    "paste",
    "sep4",
    "remarks",
    "display_mode",
    "col_width",
    "sep2",
    "export_csv",
    "field_map",
    "line_dir",
    "sep5",
    "zoom",
    "fields",
    "help",
    "sep3",
    "theme",
    "sep6",
    "language",
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
        if et == QEvent.Type.ContextMenu:
            self._handler(self._header, event_pos(event))
            return True
        if et == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.RightButton:
            self._handler(self._header, event_pos(event))
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
        if event.type() == QEvent.Type.KeyPress and event.matches(QKeySequence.StandardKey.Copy):
            self._dialog._copy_by_shortcut()
            return True
        return super().eventFilter(obj, event)


class ExportCsvDialog(QDialog):
    """Choose export scope and column format."""

    SCOPE_ALL = "all"
    SCOPE_VISIBLE = "visible"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("导出 CSV"))
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(tr("导出范围：")))
        self.radio_all = QRadioButton(tr("图层全部要素（默认）"))
        self.radio_visible = QRadioButton(tr("仅当前表格显示的要素"))
        self.radio_all.setChecked(True)
        layout.addWidget(self.radio_all)
        layout.addWidget(self.radio_visible)

        self.chk_qgis_format = QCheckBox(
            tr("按 QGIS 属性表格式（首列 wkt_geom / 经纬度 + 图层原始字段顺序）")
        )
        self.chk_qgis_format.setChecked(True)
        self.chk_qgis_format.setToolTip(
            tr("勾选：与自带属性表复制粘贴一致（wkt_geom + 图层字段顺序）；\n"
               "不勾选：按本插件当前表格的列顺序导出（不含几何列）。")
        )
        layout.addWidget(self.chk_qgis_format)

        self.chk_numeric_text = QCheckBox(
            tr("文本型纯数字（含小数）按数字导出")
        )
        self.chk_numeric_text.setChecked(True)
        self.chk_numeric_text.setToolTip(
            tr("勾选：字段虽为文本，但内容是纯数字时按数值写入 CSV，便于 Excel 计算；\n"
               "不勾选：一律按文本写出。")
        )
        layout.addWidget(self.chk_numeric_text)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        localize_button_box(btns)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def scope(self):
        return self.SCOPE_ALL if self.radio_all.isChecked() else self.SCOPE_VISIBLE

    def use_qgis_format(self):
        return self.chk_qgis_format.isChecked()

    def coerce_numeric_text(self):
        return self.chk_numeric_text.isChecked()


def _html_escape(text):
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _html_slots(template, slots):
    """Drop raw HTML into each %s of an already translated sentence."""
    parts = str(template).split("%s")
    if len(parts) != len(slots) + 1:
        return ""
    out = []
    for index, part in enumerate(parts):
        out.append(_html_escape(part))
        if index < len(slots):
            out.append(slots[index])
    return "".join(out)


def _bold_digits(text):
    """Escape text and bold each number, including a decimal part."""
    source = str(text)
    out = []
    start = 0
    index = 0
    length = len(source)
    while index < length:
        if source[index].isdigit():
            end = index + 1
            while end < length and source[end].isdigit():
                end += 1
            if end < length and source[end] == "." and end + 1 < length and source[end + 1].isdigit():
                end += 1
                while end < length and source[end].isdigit():
                    end += 1
            out.append(_html_escape(source[start:index]))
            out.append("<b>%s</b>" % _html_escape(source[index:end]))
            start = end
            index = end
            continue
        index += 1
    out.append(_html_escape(source[start:]))
    return "".join(out)


def _count_html(value, alert):
    color = "#c62828" if alert else "#000000"
    return '<b style="color:%s">%s</b>' % (color, value)


class _FitLabel(QLabel):
    """One status-bar cell. Shows as much of the text as the cell width allows.

    Markup is used while the plain sentence fits. A narrow cell falls back to
    elided plain text so a clipped tag cannot swallow the rest of the line.
    """

    def __init__(self, align, parent=None):
        super().__init__(parent)
        self._full = ""
        self._html = ""
        self._tip = ""
        self.setAlignment(align)
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.setTextFormat(Qt.TextFormat.PlainText)

    def setText(self, text):
        self._full = "" if text is None else str(text)
        self._html = ""
        self._refit()

    def set_markup(self, plain, html):
        self._full = "" if plain is None else str(plain)
        self._html = "" if html is None else str(html)
        self._refit()

    def setToolTip(self, tip):
        self._tip = "" if tip is None else str(tip)
        self._refit()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._refit()

    def _refit(self):
        width = self.contentsRect().width()
        plain = self._full
        html = self._html
        use_html = False
        if html:
            if width <= 8 or not plain:
                use_html = True
            else:
                use_html = self.fontMetrics().horizontalAdvance(plain) + 6 <= width
        if use_html:
            fmt = Qt.TextFormat.RichText
            shown = html
            clipped = False
        else:
            fmt = Qt.TextFormat.PlainText
            shown = plain
            if width > 8 and plain:
                shown = self.fontMetrics().elidedText(plain, Qt.TextElideMode.ElideRight, width)
            clipped = shown != plain
        if self.textFormat() != fmt:
            self.setTextFormat(fmt)
        if QLabel.text(self) != shown:
            QLabel.setText(self, shown)
        tip = self._tip
        if clipped and plain and not tip:
            tip = plain
        if QLabel.toolTip(self) != tip:
            QLabel.setToolTip(self, tip)


class AttributeTableDialog(QDialog):
    """Enhanced attribute table window."""

    def __init__(self, iface_ref, parent=None):
        # Parent should be iface.mainWindow() so the dialog stays with QGIS
        # (above QGIS when switching layers; no independent taskbar minimize).
        super().__init__(parent)
        # A closed window must not stay alive listening to layer switches.
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
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
        self._shortcut_carriers = []
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

        self.setWindowTitle(tr("无图层"))
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowMinimizeButtonHint
            | Qt.WindowType.WindowMaximizeButtonHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        self.resize(1100, 620)
        self.setMinimumSize(420, 300)
        self.setMaximumSize(QWIDGETSIZE_MAX, QWIDGETSIZE_MAX)
        self._restore_session_geometry()

        self.model = FeatureTableModel(self)
        self.model.set_header_mode(self._settings.load_header_mode())
        self.model.editRejected.connect(lambda msg: self._show_status(msg, 6000))
        self._build_ui()
        theme.register(self)
        try:
            from .i18n import language_changed

            language_changed().connect(self._on_ui_language_changed)
        except Exception:
            pass  # nosec B110
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
            act.setToolTip(tr("界面风格：%s") % tr(theme.THEME_LABELS[theme.current_theme()]))
        self._sync_frozen_geometry()

    def _show_theme_menu(self):
        current = theme.current_theme()
        menu = QMenu(self)
        for key in theme.THEME_ORDER:
            act = menu.addAction(
                self._tool_icon(theme.THEME_ICONS[key]), tr(theme.THEME_LABELS[key])
            )
            act.setCheckable(True)
            act.setChecked(key == current)
            act.triggered.connect(lambda _=False, k=key: theme.set_theme(k))
        anchor = None
        tool_act = self._tool_actions.get("theme")
        if tool_act is not None:
            anchor = self.toolbar.widgetForAction(tool_act)
        if anchor is not None and anchor.isVisible():
            run_exec(menu, anchor.mapToGlobal(anchor.rect().bottomLeft()))
        else:
            from qgis.PyQt.QtGui import QCursor

            run_exec(menu, QCursor.pos())

    def _restore_session_geometry(self):
        if _SESSION_GEOMETRY is not None:
            try:
                self.restoreGeometry(_SESSION_GEOMETRY)
            except Exception:
                pass  # nosec B110

    def _save_session_geometry(self):
        global _SESSION_GEOMETRY
        try:
            _SESSION_GEOMETRY = self.saveGeometry()
        except Exception:
            pass  # nosec B110

    def _theme_icon(self, name):
        """QGIS theme icon; name like mActionToggleEditing.svg."""
        try:
            icon = QgsApplication.getThemeIcon(name)
            if icon is not None and not icon.isNull():
                return icon
        except Exception:
            pass  # nosec B110
        try:
            icon = QgsApplication.getThemeIcon("/" + name.lstrip("/"))
            if icon is not None and not icon.isNull():
                return icon
        except Exception:
            pass  # nosec B110
        return QIcon()

    def _tool_icon(self, icon_ref):
        """Theme svg name, or plugin:filename under attribute_table/icons/."""
        if icon_ref.startswith("plugin:"):
            from qgis.PyQt.QtCore import QSize

            name = icon_ref[len("plugin:"):]
            icons_dir = os.path.join(os.path.dirname(__file__), "icons")
            from .i18n import current_language
            from .i18n.catalog import LANG_ZH

            lang = current_language()
            # Column-width icons are pictures, shared by every language.
            if lang != LANG_ZH and not (
                name.startswith("colwidth_")
                or name.startswith("pin_")
                or name.startswith("case_")
                or name.startswith("exact_")
            ):
                lang_dir = os.path.join(icons_dir, lang)
                lang_path = os.path.join(lang_dir, name)
                if os.path.exists(lang_path):
                    icons_dir = lang_dir
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
        raw = {
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
            "theme": (
                "界面风格",
                self._show_theme_menu,
                theme.THEME_ICONS.get(theme.current_theme(), theme.THEME_ICONS["default"]),
                False,
            ),
            "help": ("帮助", self._show_help, "mActionHelpContents.svg", False),
            "customize": (
                "设置",
                self._open_settings,
                "mActionOptions.svg",
                False,
            ),
            "language": (
                "语言",
                self._show_language_menu,
                self._language_icon_ref(),
                False,
            ),
            "field_map": (
                "字段映射复制",
                self._open_field_map,
                "plugin:field_map_24.png",
                False,
            ),
            "line_dir": (
                "线方向检查",
                self._open_line_dir,
                "plugin:line_dir_24.png",
                False,
            ),
        }
        return {key: (tr(spec[0]), spec[1], spec[2], spec[3]) for key, spec in raw.items()}

    def _language_icon_ref(self):
        from .i18n import current_language
        from .i18n.catalog import LANG_ZH

        if current_language() == LANG_ZH:
            return "plugin:lang_zh_24.png"
        return "plugin:lang_24.png"

    def _show_language_menu(self):
        from .i18n import current_language, set_language
        from .i18n.catalog import available_languages

        menu = QMenu(self)
        current = current_language()
        # Labels are endonyms: each language always shows in its own spelling,
        # never translated into the current interface language.
        for key, label in available_languages():
            act = menu.addAction(label)
            act.setCheckable(True)
            act.setChecked(key == current)
            act.triggered.connect(lambda _=False, k=key: set_language(k))
        anchor = None
        tool_act = self._tool_actions.get("language")
        if tool_act is not None:
            anchor = self.toolbar.widgetForAction(tool_act)
        if anchor is not None and anchor.isVisible():
            run_exec(menu, anchor.mapToGlobal(anchor.rect().bottomLeft()))
        else:
            from qgis.PyQt.QtGui import QCursor

            run_exec(menu, QCursor.pos())

    def _open_field_map(self, *_args):
        from .tools.field_map_dialog import FieldMapDialog

        FieldMapDialog.open_for(self.iface, self)

    def _open_line_dir(self, *_args):
        from .tools.line_dir_dialog import LineDirDialog

        LineDirDialog.open_for(self.iface, self)

    def _on_ui_language_changed(self, *_args):
        self._rebuild_toolbar()
        if hasattr(self, "lbl_search"):
            self.lbl_search.setText(tr("过滤"))
        if hasattr(self, "lbl_quick_filter"):
            self.lbl_quick_filter.setText(tr("筛选"))
        if hasattr(self, "lbl_freeze"):
            self.lbl_freeze.setText(tr("冻结"))
        if hasattr(self, "ed_text"):
            self.ed_text.setPlaceholderText(tr("输入即过滤…"))
        scope_labels = {
            "all": tr("全部要素"),
            "selected": tr("仅选中"),
            "canvas": tr("地图可见要素"),
            "modified": tr("仅已修改"),
        }
        combo = getattr(self, "cmb_scope", None)
        if combo is not None:
            for i in range(combo.count()):
                key = combo.itemData(i)
                if key in scope_labels:
                    combo.setItemText(i, scope_labels[key])
        if hasattr(self, "cmb_scope"):
            self.cmb_scope.setToolTip(
                tr("范围：全部要素 / 仅选中 / 地图可见要素（画布范围内，平移缩放后约 500 毫秒刷新）"
                   " / 仅已修改（本次编辑里改过、新增、还没保存的要素）")
            )
        if hasattr(self, "cmb_quick_mode"):
            self.cmb_quick_mode.setToolTip(tr("分类筛选，或选择一个字段按其取值筛选"))
            self._rebuild_quick_filter()
        elif hasattr(self, "cmb_quick_filter"):
            self._fill_quick_values(set(self.cmb_quick_filter.checked_payloads()))
        if hasattr(self, "cmb_filter_field"):
            self._rebuild_filter_field_combo()
        if hasattr(self, "cmb_freeze"):
            self.cmb_freeze.setToolTip(tr("将指定字段固定到首列并冻结显示"))
            self._rebuild_freeze_combo()
        if hasattr(self, "cmb_fill_field"):
            self.cmb_fill_field.setToolTip(tr("要写入的目标字段"))
        self._sync_pin_button()
        self._retranslate_fill_bar()
        self._update_status()

    def _fill_mode_tip(self):
        return tr(
            "常量：直接填 1 或文字；也可输入字段名引用其内容\n"
            "前后序号：在已有文字前面或后面加上序号（只选一边），原文字保留，序号用位数补零\n"
            "前后加字：在已有文字前或后追加，空白不动\n"
            "表达式：QGIS 表达式\n"
            "替换：标准只改命中片段；基于查找值在前或后插入；所在字段整格替换。写入是常量或表达式，默认标准加常量。一个格子里选：停在标准、基于查找值或所在字段上再选具体写法"
        )

    def _retranslate_fill_bar(self):
        if not hasattr(self, "cmb_fill_mode"):
            return
        if hasattr(self, "lbl_fill"):
            self.lbl_fill.setText(tr("赋值："))
        if hasattr(self, "btn_pin"):
            self._sync_pin_button()
        modes = (
            ("常量", "const"),
            ("前后序号", "around_seq"),
            ("前后加字", "affix"),
            ("表达式", "expr"),
            ("替换", "replace"),
        )
        combo = self.cmb_fill_mode
        current = combo.currentData()
        combo.blockSignals(True)
        for i, (msgid, data) in enumerate(modes):
            if i < combo.count() and combo.itemData(i) == data:
                combo.setItemText(i, tr(msgid))
        if current in ("blank", "seq", "prefix_seq"):
            idx = combo.findData("const")
            if idx >= 0:
                combo.setCurrentIndex(idx)
        combo.blockSignals(False)
        combo.setToolTip(self._fill_mode_tip())
        if hasattr(self, "lbl_fill_width"):
            self.lbl_fill_width.setText(tr("位数"))
        if hasattr(self, "cmb_fill_width"):
            width = self.cmb_fill_width
            width.blockSignals(True)
            labels = {"none": tr("不补零"), "auto": tr("自动")}
            for i in range(width.count()):
                data = width.itemData(i)
                if data in labels:
                    width.setItemText(i, labels[data])
                elif isinstance(data, int):
                    width.setItemText(i, tr("%d位") % data)
            width.blockSignals(False)
            width.setToolTip(
                tr("不补零：1、2、3\n"
                   "自动：按本次最大序号的位数补零。从 1 写到 100 为 001，写到 1000 为 0001\n"
                   "指定位数：4 位为 0001。超出位数不截断（10000 仍是 10000）\n"
                   "前导零只留在文本字段")
            )
        if hasattr(self, "lbl_fill_seq_side"):
            self.lbl_fill_seq_side.setText(tr("加在"))
        if hasattr(self, "cmb_fill_seq_side"):
            side = self.cmb_fill_seq_side
            side.blockSignals(True)
            for i in range(side.count()):
                data = side.itemData(i)
                if data == "after":
                    side.setItemText(i, tr("后面"))
                elif data == "before":
                    side.setItemText(i, tr("前面"))
            side.blockSignals(False)
            side.setToolTip(tr("序号加在已有文字的前面或后面，只选一边。原文字保留。"))
        if hasattr(self, "lbl_fill_prefix"):
            self.lbl_fill_prefix.setText(tr("前面"))
        if hasattr(self, "ed_fill_prefix"):
            self.ed_fill_prefix.setPlaceholderText(tr("加在现有文字前，可空"))
            self.ed_fill_prefix.setToolTip(tr("加在已有文字前面。空白单元格不会被改成只有这段字。"))
        if hasattr(self, "lbl_fill_suffix"):
            self.lbl_fill_suffix.setText(tr("后面"))
        if hasattr(self, "ed_fill_suffix"):
            self.ed_fill_suffix.setPlaceholderText(tr("加在现有文字后，可空"))
            self.ed_fill_suffix.setToolTip(tr("加在已有文字后面。空白单元格不动。"))
        if hasattr(self, "btn_replace_choice"):
            self._rebuild_replace_menu()
        if hasattr(self, "chk_replace_case"):
            self._sync_replace_match_buttons()
        if hasattr(self, "lbl_fill_find"):
            self.lbl_fill_find.setText(tr("查找"))
        if hasattr(self, "ed_fill_find"):
            self.ed_fill_find.setPlaceholderText(tr("要查找的文字"))
            self.ed_fill_find.setToolTip(tr("默认部分匹配，并且区分大小写。空白格子不参与。"))
        if hasattr(self, "lbl_fill_replace"):
            self.lbl_fill_replace.setText(tr("写入"))
        self._sync_replace_write_placeholder()
        if hasattr(self, "cmb_fill_preset"):
            self.cmb_fill_preset.setToolTip(tr("常用值：点选填入常量"))
        if hasattr(self, "btn_fill_expr"):
            self.btn_fill_expr.setToolTip(tr("打开表达式构建器"))
        if hasattr(self, "btn_fill_expr_lib"):
            self.btn_fill_expr_lib.setToolTip(tr("管理常用表达式：添加、修改、备注、删除"))
        if hasattr(self, "btn_fill_filtered"):
            self.btn_fill_filtered.setText(tr("更新筛选行"))
            self.btn_fill_filtered.setToolTip(tr("更新当前表格筛选后的全部行（含未滚到的）"))
        if hasattr(self, "btn_fill_selected"):
            self.btn_fill_selected.setText(tr("更新选中"))
            self.btn_fill_selected.setToolTip(tr("仅更新地图/表中已选中的要素"))
        self._on_fill_mode_changed()

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
        if "invert" in order:
            insert_at = order.index("invert") + 1
            for extra in ("deselect", "col_width"):
                if extra not in seen and extra in known:
                    order.insert(insert_at, extra)
                    seen.add(extra)
                    insert_at += 1
        if "language" in known and "language" not in seen:
            if "customize" in order:
                order.insert(order.index("customize"), "language")
            else:
                order.append("language")
            seen.add("language")
        if "field_map" in order:
            insert_at = order.index("field_map") + 1
            if "line_dir" in known and "line_dir" not in seen:
                order.insert(insert_at, "line_dir")
                seen.add("line_dir")
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
        if "language" in order and "customize" in order:
            order = [t for t in order if t != "language"]
            order.insert(order.index("customize"), "language")
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
            "cut": QKeySequence.StandardKey.Cut,
            "paste": QKeySequence.StandardKey.Paste,
        }
        if tool_id in shortcuts:
            act.setShortcut(shortcuts[tool_id])
            act.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        return act

    def _rebuild_toolbar(self):
        self.toolbar.clear()
        self._tool_actions = {}
        order = self._resolved_toolbar_order()
        hidden = set(self._settings.load_toolbar_hidden())
        if hidden:
            order = [
                tid
                for tid in order
                if tid == "customize" or str(tid).startswith("sep") or tid not in hidden
            ]
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
        btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
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
            self.btn_col_width.setToolTip(tr("列宽：完整显示（再点切换为适配窗口）"))
        else:
            self.btn_col_width.setIcon(self._tool_icon("plugin:colwidth_fit_24.png"))
            self.btn_col_width.setToolTip(tr("列宽：适配窗口（再点切换为完整显示）"))

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
            act.setToolTip(tr("字段备注（已套用配置）"))
        else:
            act.setIcon(self._tool_icon("plugin:remarks_off_24.png"))
            act.setToolTip(tr("字段备注"))

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
            act.setToolTip(tr("显示：注（再点切换为原值）"))
            act.setText(tr("显示注"))
        else:
            act.setIcon(self._tool_icon("plugin:display_value_24.png"))
            act.setToolTip(tr("显示：值（再点切换为备注）"))
            act.setText(tr("显示值"))

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
                    pass  # nosec B110

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

    def _shortcut_rows(self):
        """(tool_id, label) rows for the shortcuts tab. The plugin's own
        main window comes first; the rest follow toolbar order."""
        specs = self._tool_specs()
        excluded = {"cut", "paste", "col_width"}
        rows = [("open_table", tr("打开属性表"))]
        for tid in DEFAULT_TOOLBAR_ORDER:
            if tid.startswith("sep") or tid in excluded:
                continue
            if tid in specs:
                rows.append((tid, specs[tid][0]))
        for tid, spec in specs.items():
            if tid not in excluded and tid not in {r[0] for r in rows}:
                rows.append((tid, spec[0]))
        return rows

    def _open_settings(self):
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
        dlg = SettingsDialog(
            items,
            current,
            DEFAULT_TOOLBAR_ORDER,
            self._settings.load_toolbar_hidden(),
            self._shortcut_rows(),
            self._settings,
            self,
        )
        if run_exec(dlg) != QDialog.DialogCode.Accepted:
            return
        self._settings.save_toolbar_order(dlg.result_toolbar_order())
        self._settings.save_toolbar_hidden(dlg.result_toolbar_hidden())
        shortcuts = dlg.result_shortcuts()
        self._settings.save_shortcuts(shortcuts)
        old_fill_default = self._settings.load_fill_mode_default()
        dlg.apply_params()
        self._apply_header_mode()
        new_fill_default = self._settings.load_fill_mode_default()
        if new_fill_default != old_fill_default and new_fill_default != "remember":
            self._set_fill_mode(new_fill_default)
        self._rebuild_toolbar()
        # New shortcuts take effect in both windows right away.
        self._apply_dialog_shortcuts(shortcuts, warn=True)
        try:
            from qgis.utils import plugins

            plug = (plugins or {}).get("attribute_table")
            if plug is not None and getattr(plug, "apply_shortcuts", None):
                plug.apply_shortcuts()
        except Exception:
            pass  # nosec B110
        self._refresh_quick_values_keep()
        self._update_status()

    def _apply_header_mode(self):
        mode = self._settings.load_header_mode()
        if mode == self.model.header_mode():
            return
        self.model.set_header_mode(mode)
        for view in (getattr(self, "table", None), getattr(self, "frozen", None)):
            if view is not None:
                try:
                    view.horizontalHeader().updateGeometry()
                    view.horizontalHeader().viewport().update()
                except Exception:
                    pass  # nosec B110
        self._schedule_column_widths(0)

    def _apply_dialog_shortcuts(self, shortcuts=None, warn=False):
        """Hang the saved shortcuts on this dialog so they fire while the
        table window has focus. QGIS-main-window carriers live in plugin.py."""
        from qgis.PyQt.QtGui import QKeySequence

        from .settings_dialog import shortcut_holder

        if shortcuts is None:
            shortcuts = self._settings.load_shortcuts()
        for act in getattr(self, "_shortcut_carriers", []):
            try:
                self.removeAction(act)
                act.deleteLater()
            except Exception:
                pass  # nosec B110
        self._shortcut_carriers = []
        specs = self._tool_specs()
        blocked = []
        for raw_id, raw_text in (shortcuts or {}).items():
            tool_id = str(raw_id or "").strip()
            text = str(raw_text or "").strip()
            if not tool_id or not text:
                continue
            # "open_table" is not a toolbar tool; its carrier just opens the window.
            if tool_id != "open_table" and tool_id not in specs:
                continue
            seq = QKeySequence.fromString(text)
            if seq.isEmpty():
                continue
            holder = shortcut_holder(text, tool_id)
            if holder:
                blocked.append("%s（%s）" % (text, holder))
                continue
            carrier = QAction(self)
            carrier.setProperty("atp_shortcut_id", tool_id)
            carrier.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
            carrier.setShortcut(seq)
            carrier.triggered.connect(lambda _c=False, t=tool_id: self.fire_tool(t))
            self.addAction(carrier)
            self._shortcut_carriers.append(carrier)
        if blocked and warn:
            QMessageBox.warning(
                self,
                tr("快捷键"),
                tr("这些快捷键已被 QGIS 的其它功能占用：%s") % "、".join(blocked),
            )

    def fire_tool(self, tool_id):
        """Run one toolbar tool by id (used by the shortcut carriers).

        Unknown ids such as "open_table" just show and raise the window."""
        self.show()
        self.raise_()
        self.activateWindow()
        specs = self._tool_specs()
        spec = specs.get(str(tool_id))
        if spec is None:
            return
        slot = spec[1]
        slot()

    def _make_combo_shrinkable(self, combo, min_chars=6, min_px=72):
        """Don't let longest item lock the whole dialog width."""
        combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        combo.setMinimumContentsLength(min_chars)
        combo.setMinimumWidth(min_px)
        combo.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

    def _theme_host(self, object_name):
        """Group widgets without a filled background. Sizes stay as they are."""
        host = QWidget()
        host.setObjectName(object_name)
        host.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        lay = QHBoxLayout(host)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        return host

    def _theme_label(self, text, color):
        lbl = QLabel(tr(text))
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
        root.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)

        self.toolbar = OverflowToolBar()
        self.toolbar.setMovable(False)
        self.toolbar.setFloatable(False)
        self.toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.toolbar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        try:
            from qgis.PyQt.QtCore import QSize

            self.toolbar.setIconSize(QSize(24, 24))
        except Exception:
            pass  # nosec B110
        self._rebuild_toolbar()
        # Saved shortcuts must work as soon as the window opens.
        self._apply_dialog_shortcuts()

        root.addWidget(self.toolbar)

        filt_host = QWidget()
        filt_host.setMinimumWidth(0)
        filt_host.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        filt = QHBoxLayout(filt_host)
        filt.setContentsMargins(0, 0, 0, 0)
        filt.setSpacing(4)

        pin_group = self._theme_host("pinGroup")
        pin_group.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        pin_lay = pin_group.layout()
        self.btn_pin = QToolButton()
        self.btn_pin.setObjectName("pinBtn")
        self.btn_pin.setText("")
        self.btn_pin.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.btn_pin.setIconSize(QSize(24, 24))
        self.btn_pin.setCheckable(True)
        self.btn_pin.setFixedSize(24, 24)
        self.btn_pin.toggled.connect(self._on_pin_toggled)
        self.chk_pin = self.btn_pin
        pin_lay.addWidget(self.btn_pin)
        self._sync_pin_button(False)

        self.cmb_scope = WidePopupCombo()
        self.cmb_scope.addItem(tr("全部要素"), "all")
        self.cmb_scope.addItem(tr("仅选中"), "selected")
        self.cmb_scope.addItem(tr("地图可见要素"), "canvas")
        self.cmb_scope.addItem(tr("仅已修改"), "modified")
        self.cmb_scope.setToolTip(
            tr("范围：全部要素 / 仅选中 / 地图可见要素（画布范围内，平移缩放后约 500 毫秒刷新）"
               " / 仅已修改（本次编辑里改过、新增、还没保存的要素）")
        )
        self._make_combo_shrinkable(self.cmb_scope, min_chars=6, min_px=108)
        self.cmb_scope.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self._theme_combo(self.cmb_scope, "#3d7ec4")
        self.cmb_scope.currentIndexChanged.connect(self._on_scope_changed)
        pin_lay.addWidget(self.cmb_scope)
        filt.addWidget(pin_group)

        filter_group = self._theme_host("filterGroup")
        filter_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        filter_lay = filter_group.layout()
        self.lbl_search = self._theme_label(tr("过滤"), "#2a5a32")
        filter_lay.addWidget(self.lbl_search)
        self.cmb_filter_field = WidePopupCombo()
        self._make_combo_shrinkable(self.cmb_filter_field, min_chars=5, min_px=72)
        self.cmb_filter_field.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self._theme_combo(self.cmb_filter_field, "#3e8f4e")
        self.cmb_filter_field.currentIndexChanged.connect(self._on_filter_field_changed)
        filter_lay.addWidget(self.cmb_filter_field, 1)

        self.ed_text = QLineEdit()
        self.ed_text.setPlaceholderText(tr("输入即过滤…"))
        self.ed_text.setClearButtonEnabled(True)
        self.ed_text.setMinimumWidth(140)
        self.ed_text.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._theme_line(self.ed_text, "#3e8f4e")
        self.ed_text.textChanged.connect(self._on_filter_text_changed)
        filter_lay.addWidget(self.ed_text, 3)

        screen_group = self._theme_host("screenGroup")
        screen_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        screen_lay = screen_group.layout()
        self.lbl_quick_filter = self._theme_label(tr("筛选"), "#8a3a3a")
        screen_lay.addWidget(self.lbl_quick_filter)
        self.cmb_quick_mode = WidePopupCombo()
        self._make_combo_shrinkable(self.cmb_quick_mode, min_chars=4, min_px=72)
        self.cmb_quick_mode.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._theme_combo(self.cmb_quick_mode, "#a34b5a")
        self.cmb_quick_mode.setToolTip(tr("分类筛选，或选择一个字段按其取值筛选"))
        self.cmb_quick_mode.currentIndexChanged.connect(self._on_quick_mode_changed)
        screen_lay.addWidget(self.cmb_quick_mode, 1)
        self.cmb_quick_filter = MultiCheckCombo()
        self._make_combo_shrinkable(self.cmb_quick_filter, min_chars=4, min_px=84)
        self.cmb_quick_filter.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._theme_combo(self.cmb_quick_filter, "#a34b5a")
        self.cmb_quick_filter.selectionChanged.connect(self._on_quick_filter_changed)
        screen_lay.addWidget(self.cmb_quick_filter, 2)

        freeze_group = self._theme_host("freezeGroup")
        freeze_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        freeze_lay = freeze_group.layout()
        self.lbl_freeze = self._theme_label(tr("冻结"), "#6a5420")
        freeze_lay.addWidget(self.lbl_freeze)
        self.cmb_freeze = WidePopupCombo()
        self._make_combo_shrinkable(self.cmb_freeze, min_chars=8, min_px=96)
        self.cmb_freeze.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._theme_combo(self.cmb_freeze, "#c4962a")
        self.cmb_freeze.setToolTip(tr("将指定字段固定到首列并冻结显示"))
        self.cmb_freeze.currentIndexChanged.connect(self._on_freeze_field_changed)
        freeze_lay.addWidget(self.cmb_freeze, 1)

        # 钉 + 范围 → 冻结 → 筛选 → 过滤
        filt.addWidget(freeze_group, 2)
        filt.addWidget(screen_group, 3)
        filt.addWidget(filter_group, 4)

        self.fill_bar = QWidget()
        self.fill_bar.setObjectName("fillBar")
        self.fill_bar.setMinimumWidth(0)
        self.fill_bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        fill = QHBoxLayout(self.fill_bar)
        fill.setContentsMargins(0, 2, 0, 0)
        fill.setSpacing(4)
        self.lbl_fill = self._theme_label(tr("赋值："), "#4a3d66")
        fill.addWidget(self.lbl_fill)
        self.cmb_fill_field = WidePopupCombo()
        self._make_combo_shrinkable(self.cmb_fill_field, min_chars=8, min_px=100)
        self.cmb_fill_field.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self._theme_combo(self.cmb_fill_field, "#7b5ea8")
        self.cmb_fill_field.setToolTip(tr("要写入的目标字段"))
        self.cmb_fill_field.currentIndexChanged.connect(self._on_fill_field_changed)
        fill.addWidget(self.cmb_fill_field)
        fill.addWidget(self._theme_label("=", "#4a3d66"))
        self.cmb_fill_mode = WidePopupCombo()
        self.cmb_fill_mode.addItem(tr("常量"), "const")
        self.cmb_fill_mode.addItem(tr("前后序号"), "around_seq")
        self.cmb_fill_mode.addItem(tr("前后加字"), "affix")
        self.cmb_fill_mode.addItem(tr("表达式"), "expr")
        self.cmb_fill_mode.addItem(tr("替换"), "replace")
        self.cmb_fill_mode.setToolTip(self._fill_mode_tip())
        self._make_combo_shrinkable(self.cmb_fill_mode, min_chars=5, min_px=96)
        self._theme_combo(self.cmb_fill_mode, "#7b5ea8")
        self.cmb_fill_mode.currentIndexChanged.connect(self._on_fill_mode_changed)
        try:
            self.cmb_fill_mode.activated[int].connect(self._remember_fill_mode)
        except Exception:
            self.cmb_fill_mode.activated.connect(self._remember_fill_mode)
        fill.addWidget(self.cmb_fill_mode)
        self._fill_width_group = self._theme_host("fillWidthGroup")
        self._fill_width_group.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        width_lay = self._fill_width_group.layout()
        self.lbl_fill_width = self._theme_label(tr("位数"), "#2a4568")
        self.cmb_fill_width = WidePopupCombo()
        self.cmb_fill_width.addItem(tr("不补零"), "none")
        self.cmb_fill_width.addItem(tr("自动"), "auto")
        for _width in (2, 3, 4, 5, 6, 8, 10):
            self.cmb_fill_width.addItem(tr("%d位") % _width, _width)
        self.cmb_fill_width.setToolTip(
            tr("不补零：1、2、3\n"
               "自动：按本次最大序号的位数补零。从 1 写到 100 为 001，写到 1000 为 0001\n"
               "指定位数：4 位为 0001。超出位数不截断（10000 仍是 10000）\n"
               "前导零只留在文本字段")
        )
        self._make_combo_shrinkable(self.cmb_fill_width, min_chars=4, min_px=72)
        self._theme_combo(self.cmb_fill_width, "#3d7ab5")
        width_lay.addWidget(self.lbl_fill_width)
        width_lay.addWidget(self.cmb_fill_width)
        fill.addWidget(self._fill_width_group)
        self._fill_side_group = self._theme_host("fillSideGroup")
        self._fill_side_group.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        side_lay = self._fill_side_group.layout()
        self.lbl_fill_seq_side = self._theme_label(tr("加在"), "#6a4530")
        self.cmb_fill_seq_side = WidePopupCombo()
        self.cmb_fill_seq_side.addItem(tr("后面"), "after")
        self.cmb_fill_seq_side.addItem(tr("前面"), "before")
        self.cmb_fill_seq_side.setToolTip(tr("序号加在已有文字的前面或后面，只选一边。原文字保留。"))
        self._make_combo_shrinkable(self.cmb_fill_seq_side, min_chars=2, min_px=64)
        self._theme_combo(self.cmb_fill_seq_side, "#c47a45")
        side_lay.addWidget(self.lbl_fill_seq_side)
        side_lay.addWidget(self.cmb_fill_seq_side)
        fill.addWidget(self._fill_side_group)
        self.lbl_fill_prefix = self._theme_label(tr("前面"), "#4a3d66")
        self.ed_fill_prefix = QLineEdit()
        self.ed_fill_prefix.setClearButtonEnabled(True)
        self.ed_fill_prefix.setPlaceholderText(tr("加在现有文字前，可空"))
        self.ed_fill_prefix.setMinimumWidth(48)
        self._theme_line(self.ed_fill_prefix, "#7b5ea8")
        self.ed_fill_prefix.setToolTip(tr("加在已有文字前面。空白单元格不会被改成只有这段字。"))
        fill.addWidget(self.lbl_fill_prefix)
        fill.addWidget(self.ed_fill_prefix, 1)
        self.lbl_fill_suffix = self._theme_label(tr("后面"), "#4a3d66")
        self.ed_fill_suffix = QLineEdit()
        self.ed_fill_suffix.setClearButtonEnabled(True)
        self.ed_fill_suffix.setPlaceholderText(tr("加在现有文字后，可空"))
        self.ed_fill_suffix.setMinimumWidth(48)
        self._theme_line(self.ed_fill_suffix, "#7b5ea8")
        self.ed_fill_suffix.setToolTip(tr("加在已有文字后面。空白单元格不动。"))
        fill.addWidget(self.lbl_fill_suffix)
        fill.addWidget(self.ed_fill_suffix, 1)
        self.cmb_fill_preset = WidePopupCombo()
        self._make_combo_shrinkable(self.cmb_fill_preset, min_chars=4, min_px=72)
        self._theme_combo(self.cmb_fill_preset, "#7b5ea8")
        self.cmb_fill_preset.setToolTip(tr("常用值：点选填入常量"))
        try:
            self.cmb_fill_preset.activated[int].connect(self._on_fill_preset_chosen)
        except Exception:
            self.cmb_fill_preset.activated.connect(self._on_fill_preset_chosen)
        fill.addWidget(self.cmb_fill_preset)
        self.btn_fill_expr = QPushButton("ε")
        self.btn_fill_expr.setFixedWidth(28)
        self.btn_fill_expr.setToolTip(tr("打开表达式构建器"))
        self.btn_fill_expr.clicked.connect(self._open_fill_expression_builder)
        fill.addWidget(self.btn_fill_expr)
        self.btn_fill_expr_lib = QPushButton()
        lib_icon = manage_icon()
        if lib_icon is not None:
            self.btn_fill_expr_lib.setIcon(lib_icon)
            self.btn_fill_expr_lib.setIconSize(QSize(16, 16))
        else:
            self.btn_fill_expr_lib.setText("\u2630")
        self.btn_fill_expr_lib.setFixedWidth(28)
        self.btn_fill_expr_lib.setToolTip(tr("管理常用表达式：添加、修改、备注、删除"))
        self.btn_fill_expr_lib.clicked.connect(self._open_expression_library)
        fill.addWidget(self.btn_fill_expr_lib)
        self.ed_fill = QLineEdit()
        self.ed_fill.setClearButtonEnabled(True)
        self.ed_fill.setMinimumWidth(60)
        self.ed_fill.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._theme_line(self.ed_fill, "#7b5ea8")
        self._fill_field_model = QStringListModel(self)
        self._fill_field_completer = QCompleter(self._fill_field_model, self)
        self._fill_field_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._fill_field_completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        try:
            self._fill_field_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        except Exception:
            pass  # nosec B110
        self._fill_field_completer.setMaxVisibleItems(12)
        self.ed_fill.setCompleter(self._fill_field_completer)
        self._fill_expr_drop = ExpressionDropdown(
            self.ed_fill, lambda: self.cmb_fill_mode.currentData() == "expr"
        )
        fill.addWidget(self.ed_fill, 1)
        self._replace_group = QWidget()
        self._replace_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        replace_lay = QHBoxLayout(self._replace_group)
        replace_lay.setContentsMargins(0, 0, 0, 0)
        replace_lay.setSpacing(2)
        self._replace_choice = ("standard", "const", "after")
        self.btn_replace_choice = QToolButton()
        self.btn_replace_choice.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.btn_replace_choice.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.btn_replace_choice.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        self.btn_replace_choice.setStyleSheet(
            "QToolButton { background-color: palette(base); color: #1a1a1a;"
            " border: 1px solid #7b5ea8; padding: 2px 16px 2px 8px; }"
        )
        self._rebuild_replace_menu()
        replace_lay.addWidget(self.btn_replace_choice)
        self.lbl_fill_find = self._theme_label(tr("查找"), "#4a3d66")
        replace_lay.addWidget(self.lbl_fill_find)
        self.ed_fill_find = QLineEdit()
        self.ed_fill_find.setClearButtonEnabled(True)
        self.ed_fill_find.setPlaceholderText(tr("要查找的文字"))
        self.ed_fill_find.setMinimumWidth(72)
        self.ed_fill_find.setToolTip(tr("默认部分匹配，并且区分大小写。空白格子不参与。"))
        self._theme_line(self.ed_fill_find, "#7b5ea8")
        replace_lay.addWidget(self.ed_fill_find, 1)
        self.lbl_fill_replace = self._theme_label(tr("写入"), "#4a3d66")
        replace_lay.addWidget(self.lbl_fill_replace)
        self.ed_fill_replace = QLineEdit()
        self.ed_fill_replace.setClearButtonEnabled(True)
        self.ed_fill_replace.setPlaceholderText(tr("常量，留空表示删掉命中的那段"))
        self.ed_fill_replace.setMinimumWidth(72)
        self._theme_line(self.ed_fill_replace, "#7b5ea8")
        self._replace_expr_drop = ExpressionDropdown(
            self.ed_fill_replace,
            lambda: (
                self.cmb_fill_mode.currentData() == "replace"
                and self._replace_write_source() == "expr"
            ),
        )
        replace_lay.addWidget(self.ed_fill_replace, 1)
        self.chk_replace_case = self._replace_match_button("replaceCaseBtn", True)
        replace_lay.addWidget(self.chk_replace_case)
        self.chk_replace_exact = self._replace_match_button("replaceExactBtn", False)
        replace_lay.addWidget(self.chk_replace_exact)
        self._sync_replace_match_buttons()
        fill.addWidget(self._replace_group, 1)
        self._fill_stretch_index = fill.count()
        fill.addStretch(1)
        self.btn_fill_filtered = QPushButton(tr("更新筛选行"))
        self.btn_fill_filtered.setToolTip(tr("更新当前表格筛选后的全部行（含未滚到的）"))
        self.btn_fill_filtered.clicked.connect(lambda: self._run_fill(selected_only=False))
        fill.addWidget(self.btn_fill_filtered)
        self.btn_fill_selected = QPushButton(tr("更新选中"))
        self.btn_fill_selected.setToolTip(tr("仅更新地图/表中已选中的要素"))
        self.btn_fill_selected.clicked.connect(lambda: self._run_fill(selected_only=True))
        fill.addWidget(self.btn_fill_selected)
        self.fill_bar.setVisible(False)
        root.addWidget(filt_host)
        root.addWidget(self.fill_bar)
        self._apply_startup_fill_mode()
        self._on_fill_mode_changed()

        self.quick_fill = QuickFillBar(self)
        self.quick_fill.setVisible(False)
        root.addWidget(self.quick_fill)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.frozen = QTableView()
        self.table = QTableView()
        for view in (self.frozen, self.table):
            view.setModel(self.model)
            view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
            view.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
            view.setAlternatingRowColors(True)
            view.setSortingEnabled(False)
            view.verticalHeader().setDefaultSectionSize(22)
            view.setWordWrap(False)
            view.setMinimumWidth(0)
            view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            try:
                view.setSizeAdjustPolicy(QAbstractScrollArea.SizeAdjustPolicy.AdjustIgnored)
            except Exception:
                pass  # nosec B110
            view.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            view.horizontalHeader().setMinimumHeight(40)
            try:
                view.horizontalHeader().setMaximumSectionSize(QWIDGETSIZE_MAX)
                view.horizontalHeader().setMinimumSectionSize(36)
                view.horizontalHeader().setStretchLastSection(False)
            except Exception:
                pass  # nosec B110
        self._vm_delegate = ValueMapDelegate(self.model)
        self.table.setItemDelegate(self._vm_delegate)
        self.frozen.setItemDelegate(self._vm_delegate)
        self.frozen.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.frozen.horizontalHeader().setStretchLastSection(False)
        self.frozen.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.frozen.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.table.horizontalHeader().setSectionsMovable(True)
        self.table.horizontalHeader().sectionClicked.connect(self._on_header_clicked)
        self.table.horizontalHeader().sectionMoved.connect(self._on_section_moved)
        self.frozen.horizontalHeader().sectionClicked.connect(self._on_header_clicked)
        self._header_filters = []
        for header in (self.table.horizontalHeader(), self.frozen.horizontalHeader()):
            header.setSectionsClickable(True)
            # Prevent Qt default context handling; we use event filter
            header.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
            filt = _HeaderRightClickFilter(self, header)
            header.installEventFilter(filt)
            self._header_filters.append(filt)
        for header in (self.table.verticalHeader(), self.frozen.verticalHeader()):
            header.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
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
        self.splitter.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.splitter.splitterMoved.connect(lambda *_a: self.quick_fill.schedule_sync(0))
        root.addWidget(self.splitter, 1)

        self.status = QStatusBar()
        self.status.setSizeGripEnabled(False)
        # One permanent row. QStatusBar.showMessage hides every normal widget,
        # which is why the center length stayed blank while the left summary
        # and the right stats were both visible.
        self._status_text = ""
        self._status_html = ""
        self._status_toast = False
        self._toast_timer = QTimer(self)
        self._toast_timer.setSingleShot(True)
        self._toast_timer.timeout.connect(self._restore_status_text)
        # Fixed shares: title 40%, length 20%, stats 40%. A short window
        # clips each cell instead of letting the left title push the others out.
        self.lbl_status = _FitLabel(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.lbl_line_length = _FitLabel(Qt.AlignmentFlag.AlignCenter)
        self._length_host = self.lbl_line_length
        self.lbl_stats = _FitLabel(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        bar_host = QWidget()
        bar_lay = QHBoxLayout(bar_host)
        bar_lay.setContentsMargins(4, 0, 4, 0)
        bar_lay.setSpacing(8)
        bar_lay.addWidget(self.lbl_status, 4)
        bar_lay.addWidget(self.lbl_line_length, 2)
        bar_lay.addWidget(self.lbl_stats, 4)
        self.status.addPermanentWidget(bar_host, 1)
        root.addWidget(self.status)

        self._update_frozen_visibility()
        self._update_edit_actions()

    def _connect_project(self):
        QgsProject.instance().layersWillBeRemoved.connect(self._on_layers_removed)
        try:
            QgsProject.instance().readProject.connect(self._on_project_read)
        except Exception:
            pass  # nosec B110
        try:
            QgsProject.instance().cleared.connect(self._on_project_cleared)
        except Exception:
            pass  # nosec B110
        try:
            self.iface.currentLayerChanged.connect(self._on_current_layer_changed)
        except Exception:
            pass  # nosec B110

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

    def _crs_label(self, layer):
        try:
            crs = layer.crs()
        except Exception:
            return ""
        if crs is None:
            return ""
        try:
            if not crs.isValid():
                return ""
        except Exception:
            return ""
        auth = ""
        try:
            auth = (crs.authid() or "").strip()
        except Exception:
            auth = ""
        if auth:
            return auth
        try:
            return (crs.description() or "").strip()
        except Exception:
            return ""

    def _edit_state_text(self):
        layer = self._layer
        if layer is None or not layer.isEditable():
            return tr("只读")
        dirty = False
        try:
            dirty = bool(layer.isModified())
        except Exception:
            dirty = False
        if not dirty:
            return tr("编辑中")
        changed = 0
        try:
            changed = len(self.model.modified_fids())
        except Exception:
            changed = 0
        if changed:
            return tr("编辑·未保存（已改 %s 条）") % changed
        return tr("编辑·未保存")

    def _update_window_title(self):
        if self._layer is None:
            self.setWindowTitle(tr("无图层"))
            return
        parts = [self._layer.name()]
        crs = self._crs_label(self._layer)
        if crs:
            parts.append(crs)
        parts.append(self._edit_state_text())
        self.setWindowTitle(" - ".join(parts))

    def _on_pin_toggled(self, checked):
        self._pin_layer = checked
        self._sync_pin_button(checked)

    def _sync_pin_button(self, checked=None):
        btn = getattr(self, "btn_pin", None)
        if btn is None:
            return
        if checked is None:
            checked = bool(btn.isChecked())
        btn.setIconSize(QSize(24, 24))
        btn.setStyleSheet(
            "QToolButton#pinBtn { border: none; padding: 0; margin: 0; background: transparent; }"
            "QToolButton#pinBtn:hover { background: rgba(0,0,0,18); border-radius: 4px; }"
        )
        if checked:
            btn.setIcon(self._tool_icon("plugin:pin_on_24.png"))
            btn.setToolTip(tr("已钉住当前图层（再点取消）"))
        else:
            btn.setIcon(self._tool_icon("plugin:pin_off_24.png"))
            btn.setToolTip(tr("钉住图层：不随图例切换当前表"))

    def _replace_match_button(self, object_name, checked):
        btn = QToolButton()
        btn.setObjectName(object_name)
        btn.setText("")
        btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        btn.setIconSize(QSize(24, 24))
        btn.setFixedSize(24, 24)
        btn.setCheckable(True)
        btn.setChecked(checked)
        btn.toggled.connect(lambda _on: self._sync_replace_match_buttons())
        return btn

    def _sync_replace_match_buttons(self, *_args):
        plain = (
            "QToolButton#%s { border: none; padding: 0; margin: 0; background: transparent; }"
            "QToolButton#%s:hover { background: rgba(0,0,0,18); border-radius: 4px; }"
            "QToolButton#%s:checked { background: transparent; }"
        )
        case = getattr(self, "chk_replace_case", None)
        if case is not None:
            case.setIcon(self._tool_icon(
                "plugin:case_on_24.png" if case.isChecked() else "plugin:case_off_24.png"
            ))
            case.setIconSize(QSize(24, 24))
            case.setStyleSheet(plain % ("replaceCaseBtn", "replaceCaseBtn", "replaceCaseBtn"))
            case.setToolTip(tr("区分大小写。点亮后 Ab 和 ab 不算同一个，默认点亮。"))
        exact = getattr(self, "chk_replace_exact", None)
        if exact is not None:
            exact.setIcon(self._tool_icon(
                "plugin:exact_on_24.png" if exact.isChecked() else "plugin:exact_off_24.png"
            ))
            exact.setIconSize(QSize(24, 24))
            exact.setStyleSheet(plain % ("replaceExactBtn", "replaceExactBtn", "replaceExactBtn"))
            exact.setToolTip(tr("完整匹配。点亮后必须整格相等才算命中，默认只要包含查找文字。"))

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
            not hasattr(layer, "type") or layer.type() != QgsMapLayer.LayerType.VectorLayer
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
        self.cmb_filter_field.addItem(tr("所有字段"), None)
        for name in self._all_field_names:
            self.cmb_filter_field.addItem(self._field_labels.get(name, name), name)
        idx = self.cmb_filter_field.findData(current) if current else 0
        self.cmb_filter_field.setCurrentIndex(idx if idx >= 0 else 0)
        self.cmb_filter_field.blockSignals(False)

    def _quick_value_limit(self):
        """How many distinct values the quick-filter box may list (settings)."""
        return self._settings.load_quick_value_limit()

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
            mode_combo.addItem(tr("分类筛选"), QUICK_MODE_CATEGORY)
        for name in self._all_field_names:
            mode_combo.addItem(self._field_labels.get(name, name), name)
        if mode_combo.count() == 0:
            mode_combo.addItem(tr("（无字段）"), "")
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
                expr = it.get("filter_expr") or ""
                label = it.get("label") or tr("(未命名)")
                items.append(("%s (%d)" % (label, self._count_features(expr)), expr))
        elif mode:
            items, truncated = self._field_value_choices(mode)
        wanted = set(checked_exprs or ())
        matched = False
        combo.add_check_item(tr("全部"), None, True)
        for label, expr in items:
            checked = expr in wanted
            if checked:
                matched = True
            combo.add_check_item(label, expr, checked)
        if truncated:
            combo.add_note(tr("仅列出前 %d 个值") % self._quick_value_limit())
        if matched:
            all_item = combo.model().item(0)
            if all_item is not None:
                all_item.setCheckState(Qt.CheckState.Unchecked)
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
        blank_count = 0
        truncated = False
        req = (
            QgsFeatureRequest()
            .setFlags(QgsFeatureRequest.Flag.NoGeometry)
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
                blank_count += 1
                continue  # nosec B112
            key = value_key(raw)
            if key not in seen:
                if len(seen) >= self._quick_value_limit():
                    truncated = True
                    continue  # nosec B112
                seen[key] = [raw, 0]
            seen[key][1] += 1
        rows = []
        if blank_count:
            rows.append((0, 0.0, "", tr("(空)"), blank_count, _blank_field_expr(field_name)))
        for raw, count in seen.values():
            num = try_parse_number(raw)
            plain = _plain_attr(raw)
            desc = ""
            try:
                desc = qgis_description_for_value(layer, field_name, raw) or ""
            except Exception:
                desc = ""
            label = desc if desc and desc != plain else plain
            expr = field_eq_expression(field_name, _expr_attr(raw))
            shown = label
            if label != plain:
                shown = "%s (%s)" % (label, plain)
            if num is not None:
                rows.append((1, float(num), "", shown, count, expr))
            else:
                rows.append((2, 0.0, plain.casefold(), shown, count, expr))
        rows.sort(key=lambda row: (row[0], row[1], row[2], row[3]))
        items = []
        for _kind, _num, _text, label, count, expr in rows:
            items.append(("%s (%d)" % (label, count), expr))
        return items, truncated

    def _count_features(self, expression):
        layer = self._layer
        expr = (expression or "").strip()
        if layer is None or not expr:
            return 0
        request = QgsFeatureRequest().setFlags(QgsFeatureRequest.Flag.NoGeometry)
        try:
            request.setFilterExpression(expr)
            return sum(1 for _feat in layer.getFeatures(request))
        except Exception:
            return 0  # nosec B110

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
        self.cmb_freeze.addItem(tr("不冻结"), "")
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
                pass  # nosec B110

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
                pass  # nosec B110

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
            self._show_status(tr("地图范围无法换算到图层坐标系，「地图可见」没有结果"), 5000)
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
                pass  # nosec B110
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
            pass  # nosec B110
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
                    self.model.index(row, col), QItemSelectionModel.SelectionFlag.NoUpdate
                )
            vsb = self.table.verticalScrollBar()
            vsb.setValue(min(state["v"], vsb.maximum()))
            hsb = self.table.horizontalScrollBar()
            hsb.setValue(min(state["h"], hsb.maximum()))
        except Exception:
            pass  # nosec B110
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
        policy = Qt.ScrollBarPolicy.ScrollBarAlwaysOn if need_bar else Qt.ScrollBarPolicy.ScrollBarAlwaysOff
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
            name = names[col]
            self._set_fill_field(name)
            self._sync_quick_filter_field(name)

    def _sync_quick_filter_field(self, field_name):
        """Non-categorized layers: the quick filter follows the current column.

        Categorized layers keep「分类筛选」and never follow. Switching fields
        resets the checked values to「全部」(handled by _on_quick_mode_changed).
        """
        if not field_name:
            return
        if not self._settings.load_filter_follow_field():
            return
        combo = getattr(self, "cmb_quick_mode", None)
        if combo is None:
            return
        try:
            if self._usable_categories():
                return
        except Exception:
            return
        idx = combo.findData(field_name)
        if idx < 0 or idx == combo.currentIndex():
            return
        combo.setCurrentIndex(idx)

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
        Returns (kind, text). kind is empty / none / dup.
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
            return "empty", tr("无数据")
        counts = Counter(keys)
        dup_groups = sum(1 for n in counts.values() if n > 1)
        if dup_groups == 0:
            return "none", tr("无重名")
        dup_rows = sum(n for n in counts.values() if n > 1)
        return "dup", tr("有重名(%d组/%d条)") % (dup_groups, dup_rows)

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
            .setFlags(QgsFeatureRequest.Flag.NoGeometry)
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
            val = self.model.data(idx, Qt.ItemDataRole.EditRole)
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
            self._show_status(tr("未点中字段列，请对准列标题右键"), 2500)
            return
        # Skip hidden columns (e.g. frozen col 0 hidden on main table)
        if header.isSectionHidden(logical):
            self._show_status(tr("该列已隐藏，请在可见列标题上右键"), 2500)
            return

        field_name = names[logical]
        menu = QMenu(self)
        act_copy = menu.addAction(tr("复制本列"))
        act_copy_header = menu.addAction(tr("复制本列（含表头）"))
        act_copy_back = self._add_colored_menu_action(
            menu, tr("复制本列（可回贴）"), "#1565C0"
        )
        act_paste_back = self._add_colored_menu_action(
            menu, tr("粘贴回本列"), "#C62828"
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
        act_unique = menu.addAction(tr("唯一值统计…"))
        act_unique.setToolTip(tr("统计当前表格行里本列每个值出现几次"))
        act_dup = menu.addAction(tr("选中重复值"))
        act_blank = menu.addAction(tr("选中空值"))
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
        act_remark = menu.addAction(tr("编辑备注…"))
        act_remark.triggered.connect(
            lambda _=False, n=field_name: self._edit_remarks(n)
        )
        run_exec(menu, header.mapToGlobal(pos))

    def _column_groups(self, field_name):
        fids = self.model.fids()
        values = self.model.column_values(field_name)
        return group_column(fids, values)

    def _select_fids_on_layer(self, fids, message):
        layer = self._layer
        if layer is None:
            return
        layer.selectByIds(list(fids))
        self._show_status(message, 6000)

    def _select_column_duplicates(self, field_name):
        if self._layer is None or self.model.rowCount() == 0:
            self._show_status(tr("表格里没有行"), 3000)
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
            self._show_status(tr("「%s」在当前表格行里没有重复值") % label, 5000)
            return
        self._select_fids_on_layer(
            fids,
            tr("「%s」有 %d 个值重复，已选中 %d 条要素（仅统计当前表格行，空值不算）")
            % (label, dup_values, len(fids)),
        )

    def _select_column_blanks(self, field_name):
        if self._layer is None or self.model.rowCount() == 0:
            self._show_status(tr("表格里没有行"), 3000)
            return
        slot = self._column_groups(field_name).get(BLANK_KEY)
        label = self._field_labels.get(field_name, field_name)
        if not slot:
            self._show_status(tr("「%s」在当前表格行里没有空值") % label, 5000)
            return
        self._select_fids_on_layer(
            slot[1],
            tr("「%s」已选中 %d 条空值（NULL 或空白，仅统计当前表格行）") % (label, len(slot[1])),
        )

    def _show_unique_values(self, field_name):
        layer = self._layer
        if layer is None or self.model.rowCount() == 0:
            self._show_status(tr("表格里没有行"), 3000)
            return
        field_idx = layer.fields().indexFromName(field_name)
        if field_idx < 0:
            return
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
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
                fids, tr("已选中 %d 个值对应的 %d 条要素") % (n_values, len(fids))
            )

        def on_filter(checked):
            self._quick_filter_by_values(field_name, checked)

        dlg = UniqueValuesDialog(self, label, groups, label_for, on_filter, on_select)
        dlg.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        dlg.show()

    def _quick_filter_by_values(self, field_name, checked):
        """Put checked (key, [raw, fids]) groups into the top-bar 筛选 as field-value mode."""
        mode_combo = getattr(self, "cmb_quick_mode", None)
        value_combo = getattr(self, "cmb_quick_filter", None)
        if mode_combo is None or value_combo is None:
            return
        idx = mode_combo.findData(field_name)
        if idx < 0:
            self._show_status(tr("该字段不在「筛选」的字段列表里"), 4000)
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
            self._show_status(
                tr("「筛选」下拉只列出前 %d 个值，有 %d 个勾选值没能加入")
                % (self._quick_value_limit(), len(wanted) - len(applied)),
                8000,
            )
        else:
            self._show_status(tr("已按 %d 个值筛选") % len(applied), 4000)

    def _show_row_header_menu(self, header, pos):
        rows = self.model.rowCount()
        if rows == 0:
            return
        row = header.logicalIndexAt(pos)
        menu = QMenu(self)
        act_range = menu.addAction(tr("选中第 a–b 行…"))
        act_to_end = None
        if 0 <= row < rows:
            act_to_end = menu.addAction(tr("从第 %d 行选到末行") % (row + 1))
        act_range.triggered.connect(
            lambda _=False, r=row: self._select_row_range_prompt(r)
        )
        if act_to_end is not None:
            act_to_end.triggered.connect(
                lambda _=False, r=row: self._select_rows(list(range(r, rows)))
            )
        run_exec(menu, header.mapToGlobal(pos))

    def _select_row_range_prompt(self, row):
        rows = self.model.rowCount()
        start = row + 1 if 0 <= row < rows else 1
        text, ok = QInputDialog.getText(
            self,
            tr("按行号选择"),
            tr("行号范围（当前共 %d 行，按表格显示顺序）：\n"
               "例如 10-50、1-20,35,80-  （80- 表示到末行）") % rows,
            QLineEdit.EchoMode.Normal,
            "%d-%d" % (start, rows),
        )
        if not ok:
            return
        try:
            picked = parse_row_ranges(text, rows)
        except ValueError as exc:
            QMessageBox.information(self, tr("按行号选择"), str(exc))
            return
        self._select_rows(picked)

    def _select_rows(self, picked_rows):
        fids = [self.model.fid_at(r) for r in picked_rows]
        fids = [f for f in fids if f is not None]
        if not fids:
            return
        self._select_fids_on_layer(fids, tr("已选中 %d 行") % len(fids))

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
            QMessageBox.warning(self, tr("复制"), tr("无法访问剪贴板。"))
            return
        clipboard.setText("\n".join(lines))
        label = self._field_labels.get(field_name, field_name)
        self._show_status(tr("已复制列「%s」共 %s 行到剪贴板") % (label, len(values)), 4000)

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
            QMessageBox.information(self, tr("复制"), tr("当前筛选没有可复制的行。"))
            return
        if len(fids) != len(values):
            QMessageBox.warning(self, tr("复制"), tr("行数和取值对不上，没有复制。"))
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
            QMessageBox.warning(self, tr("复制"), tr("无法访问剪贴板。"))
            return
        clipboard.setText(buf.getvalue())
        label = self._field_labels.get(field_name, field_name)
        self._show_status(
            tr("已复制列「%s」共 %s 行（两列：编号和值，可改值后粘贴回本列）") % (label, len(fids)),
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
            .setFlags(QgsFeatureRequest.Flag.NoGeometry)
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
            QMessageBox.information(self, tr("粘贴回列"), tr("请先切换到编辑模式。"))
            return
        text = self._clipboard_text()
        if not clipboard_is_roundtrip(text):
            QMessageBox.information(
                self,
                tr("粘贴回列"),
                tr("剪贴板不是可回贴格式。请用列标题「复制本列（可回贴）」复制，"
                   "只改值、不要改编号列，再粘贴。普通复制没有编号，不能按位置贴回。"),
            )
            return
        parsed, err = parse_roundtrip_text(text)
        if err:
            QMessageBox.warning(self, tr("粘贴回列"), err)
            return
        src_field = parsed["field"]
        layer_id = parsed["layer_id"]
        if layer_id:
            try:
                current_id = layer.id() or ""
            except Exception:
                current_id = ""
            if current_id and layer_id != current_id:
                QMessageBox.warning(self, tr("粘贴回列"), tr("这份数据来自另一个图层，不能贴到当前表。"))
                return
        field_name = target_field or src_field
        field_idx = layer.fields().indexFromName(field_name)
        if field_idx < 0:
            QMessageBox.warning(self, tr("粘贴回列"), tr("当前图层没有字段「%s」。") % field_name)
            return
        rows = parsed["rows"]
        missing = self._missing_feature_ids(layer, [fid for fid, _val in rows])
        if missing:
            sample = tr("、").join(str(fid) for fid in missing[:8])
            extra = "" if len(missing) <= 8 else tr(" 等 %s 个") % len(missing)
            QMessageBox.warning(
                self,
                tr("粘贴回列"),
                tr("有 %s 个编号不在当前图层（%s%s）。一条都没写。") % (len(missing), sample, extra),
            )
            return
        sample = "\n".join(
            tr("编号 %s → %s") % (fid, raw if raw != "" else tr("（空）")) for fid, raw in rows[:3]
        )
        if target_field and target_field != src_field:
            question = (
                tr("剪贴板来自字段「%s」，将按编号写入当前列「%s」，共 %s 行。\n"
                   "对的是编号，不是表格第几行。下面顺序可以不连着，不会错位。\n%s\n继续？")
                % (src_field, target_field, len(rows), sample)
            )
        else:
            question = (
                tr("将按编号写回字段「%s」，共 %s 行。\n"
                   "对的是编号，不是表格第几行。下面顺序可以不连着，不会错位。\n%s\n继续？")
                % (field_name, len(rows), sample)
            )
        if QMessageBox.question(self, tr("粘贴回列"), question) != QMessageBox.StandardButton.Yes:
            return
        field = layer.fields().at(field_idx)
        values = {}
        for fid, raw in rows:
            values[fid] = self._coerce_value_for_field(field, raw)
        updated = self._commit_attribute_values(
            layer, field_idx, field_name, values, "粘贴回列"
        )
        if updated:
            self._show_status(tr("已按编号写回 %s 行 → %s") % (updated, field_name), 4000)
        else:
            self._show_status(tr("编号已对齐，字段「%s」的值没有变化") % field_name, 4000)

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
            self.table.selectionModel().select(selection, QItemSelectionModel.SelectionFlag.Select)
            if self.frozen.isVisible():
                sel0 = QItemSelection()
                for fid in selected:
                    row = self.model.row_for_fid(fid)
                    if row < 0:
                        continue
                    idx = self.model.index(row, 0)
                    sel0.select(idx, idx)
                self.frozen.selectionModel().select(sel0, QItemSelectionModel.SelectionFlag.Select)
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
                QMessageBox.warning(self, tr("编辑"), tr("无法开始编辑该图层。"))
                self.act_toggle_edit.setChecked(False)
        else:
            if layer.isEditable() and layer.isModified():
                reply = QMessageBox.question(
                    self,
                    tr("结束编辑"),
                    tr("有未保存修改，是否保存？"),
                    QMessageBox.StandardButton.Save
                    | QMessageBox.StandardButton.Discard
                    | QMessageBox.StandardButton.Cancel,
                )
                if reply == QMessageBox.StandardButton.Cancel:
                    self.act_toggle_edit.setChecked(True)
                    return
                if reply == QMessageBox.StandardButton.Save:
                    if not layer.commitChanges():
                        errs = layer.commitErrors()
                        msg = "\n".join(errs) if isinstance(errs, (list, tuple)) else (errs or tr("未知错误"))
                        QMessageBox.warning(self, tr("保存失败"), msg)
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
            msg = "\n".join(errs) if isinstance(errs, (list, tuple)) else (errs or tr("未知错误"))
            QMessageBox.warning(self, tr("保存失败"), msg)
            layer.startEditing()
        else:
            layer.startEditing()
            self._show_status(tr("已保存"), 3000)
        self._update_edit_actions()
        self._update_window_title()

    def _revert_edits(self):
        layer = self._layer
        if layer is None or not layer.isEditable():
            return
        if QMessageBox.question(self, tr("回滚"), tr("放弃未保存修改？")) != QMessageBox.StandardButton.Yes:
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
            QMessageBox.information(self, tr("删除"), tr("请先切换到编辑模式。"))
            return
        fids = layer.selectedFeatureIds()
        if not fids:
            QMessageBox.information(self, tr("删除"), tr("没有选中的要素。"))
            return
        if QMessageBox.question(self, tr("删除"), tr("删除选中的 %s 个要素？") % len(fids)) != QMessageBox.StandardButton.Yes:
            return
        layer.beginEditCommand(tr("删除要素"))
        try:
            ok = bool(layer.deleteFeatures(list(fids)))
        except Exception:
            ok = False
        if ok:
            layer.endEditCommand()
        else:
            layer.destroyEditCommand()
            QMessageBox.warning(self, tr("删除"), tr("删除失败。"))
        self._schedule_reload()

    def _layer_supports_editing(self, layer):
        if layer is None or not layer.isValid():
            return False
        try:
            if hasattr(layer, "supportsEditing"):
                return bool(layer.supportsEditing())
        except Exception:
            pass  # nosec B110
        provider = layer.dataProvider()
        if provider is None:
            return False
        caps = provider.capabilities()
        return bool(
            caps
            & (
                QgsVectorDataProvider.Capability.ChangeAttributeValues
                | QgsVectorDataProvider.Capability.DeleteFeatures
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
                QAbstractItemView.EditTrigger.DoubleClicked | QAbstractItemView.EditTrigger.EditKeyPressed
                if editing
                else QAbstractItemView.EditTrigger.NoEditTriggers
            )
            if hasattr(self, "frozen"):
                self.frozen.setEditTriggers(self.table.editTriggers())

    def _select_all_filtered(self):
        layer = self._layer
        if layer is None:
            return
        fids = self.model.fids()
        if not fids:
            QMessageBox.information(self, tr("全选"), tr("当前筛选没有要素。"))
            return
        layer.selectByIds(fids)
        self._update_status()

    def _show_help(self):
        from qgis.PyQt.QtWidgets import QTabWidget

        from .i18n import current_language
        from .i18n.help_pages import pages_for

        ver = plugin_version()
        dlg = QDialog(self)
        dlg.setWindowTitle(tr("帮助 — 字段备注表 %s") % ver)
        dlg.resize(720, 560)
        lay = QVBoxLayout(dlg)
        tabs = QTabWidget()
        for title, html in pages_for(current_language()):
            browser = QTextBrowser()
            browser.setOpenExternalLinks(False)
            browser.setHtml(html)
            tabs.addTab(browser, title)
        lay.addWidget(tabs, 1)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        localize_button_box(btns)
        btns.rejected.connect(dlg.reject)
        btns.clicked.connect(dlg.accept)
        lay.addWidget(btns)
        run_exec(dlg)

    def _manage_fields(self):
        layer = self._layer
        if layer is None:
            return
        dlg = FieldsManagerDialog(layer, self, self._remarks)
        run_exec(dlg)
        remarks_changed = False
        try:
            remarks_changed = bool(dlg.remarks_changed())
        except Exception:
            remarks_changed = False
        if dlg.changed():
            self._refresh_field_structure()
        elif remarks_changed:
            self._apply_remarks_to_ui()

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
        if hasattr(self, "_replace_group"):
            _stretch(self._replace_group, 1 if is_replace else 0)
        expanding = is_affix or is_replace or fill_on
        if hasattr(self, "_fill_stretch_index"):
            lay.setStretch(self._fill_stretch_index, 0 if expanding else 1)
        lay.activate()

    def _on_fill_mode_changed(self, _index=None):
        mode = self.cmb_fill_mode.currentData()
        is_replace = mode == "replace"
        is_affix = mode == "affix"
        is_around = mode == "around_seq"
        self.btn_fill_expr.setVisible(not is_replace)
        self.btn_fill_expr.setEnabled(mode == "expr")
        if hasattr(self, "btn_fill_expr_lib"):
            self.btn_fill_expr_lib.setVisible(mode == "expr")
        show_width = mode == "around_seq"
        fill_on = not is_replace and not is_affix and not is_around
        if hasattr(self, "_replace_group"):
            self._replace_group.setVisible(is_replace)
        if hasattr(self, "ed_fill_find"):
            self.ed_fill.setVisible(fill_on)
        if is_replace:
            self._on_replace_options_changed()
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
            "around_seq": "在已有文字前或后加上序号，原文字保留。空白只写序号",
            "affix": "前面、后面至少填一边。只改已有文字",
            "expr": "QGIS 表达式，如 \"POP\" + 1 或 $id",
            "replace": "标准只改命中片段；基于查找值在前或后插入；所在字段整格替换。写入默认常量",
        }
        self.ed_fill.setPlaceholderText(tr(tips.get(mode, "")))
        if mode == "const":
            fill_tip = tr("输入常量，或输入其它字段名（打字弹出下拉，中间字母也能搜，列出全部命中项）把该字段内容写入目标字段。\n"
                          "要写入恰好等于字段名的文字，用单引号包起来，如 'TYPE'。")
        elif mode == "expr":
            fill_tip = tr("QGIS 表达式。打字停一下会匹配已保存的表达式，右边箭头列出全部。双击全选，按住拖动可选中文字。\n"
                          "选中后显示为「«备注» 表达式」，运行的是 » 后面的部分；在框里改了按改后的执行，保存的不变。")
        else:
            fill_tip = tr(tips.get(mode, ""))
        self.ed_fill.setToolTip(fill_tip)
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
        if mode == "const":
            target = None
            if hasattr(self, "cmb_fill_field"):
                target = self.cmb_fill_field.currentData()
            names = [n for n in (self._all_field_names or []) if n and n != target]
        self._fill_field_model.setStringList(names)
        other = self._fill_field_completer if names else None
        if hasattr(self, "_fill_expr_drop"):
            self._fill_expr_drop.sync(other)
        else:
            self.ed_fill.setCompleter(other)
        if hasattr(self, "_replace_expr_drop"):
            self._replace_expr_drop.sync(None)

    def _remember_fill_mode(self, _index=None):
        mode = self.cmb_fill_mode.currentData()
        if mode:
            self._settings.save_fill_mode_last(mode)

    def _apply_startup_fill_mode(self):
        self._set_fill_mode(self._settings.startup_fill_mode())

    def _set_fill_mode(self, mode):
        if not hasattr(self, "cmb_fill_mode"):
            return
        idx = self.cmb_fill_mode.findData(mode)
        if idx < 0 or idx == self.cmb_fill_mode.currentIndex():
            return
        self.cmb_fill_mode.blockSignals(True)
        self.cmb_fill_mode.setCurrentIndex(idx)
        self.cmb_fill_mode.blockSignals(False)
        self._on_fill_mode_changed()

    def _open_expression_library(self):
        current = self.ed_fill.text() if hasattr(self, "ed_fill") else ""
        dlg = ExpressionLibraryDialog(self._layer, current, self)
        if not run_exec(dlg):
            return
        for drop in (getattr(self, "_fill_expr_drop", None), getattr(self, "_replace_expr_drop", None)):
            if drop is not None:
                drop.reload()
        self._sync_fill_field_completer()

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
        self.cmb_fill_preset.addItem(tr("含义…"), "")
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
        self.cmb_fill_preset.setVisible(mode in ("const", "expr") and has)

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
                    tr("更新当前表格筛选后的全部行；若快速插入行已选含义，则按所选列写入（全空则不再确认）")
                )
                self.btn_fill_selected.setToolTip(
                    tr("仅更新已选中要素；若快速插入行已选含义，则按所选列写入（全空则不再确认）")
                )
            else:
                self.btn_fill_filtered.setToolTip(tr("更新当前表格筛选后的全部行（含未滚到的）"))
                self.btn_fill_selected.setToolTip(tr("仅更新地图/表中已选中的要素"))

    def _on_remarks_enabled_changed(self, _enabled):
        self._apply_remarks_to_ui()
        self._update_edit_actions()

    def _on_remark_pack_changed(self):
        self._apply_remarks_to_ui()

    def changeEvent(self, event):
        super().changeEvent(event)
        if not getattr(self, "_shared_reload_ready", False):
            return
        if event.type() != QEvent.Type.ActivationChange or not self.isActiveWindow():
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
                pass  # nosec B110

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
        self._show_status(
            tr("已选插入值：选弹出项立即写入，或点取消后用赋值条按钮写入"), 4000
        )

    def _fill_target_fids(self, selected_only=False, title="赋值", scope=None):
        title = tr(title)
        layer = self._layer
        if layer is None:
            return None
        if scope is None:
            scope = "selected" if selected_only else "filtered"
        if scope == "selected":
            selected = set(layer.selectedFeatureIds())
            if not selected:
                QMessageBox.information(self, title, tr("没有选中的要素。"))
                return None
            fids = [fid for fid in self.model.fids() if fid in selected]
            if not fids:
                QMessageBox.information(
                    self,
                    title,
                    tr("选中的 %s 个要素都不在当前表格里（被范围、过滤或筛选挡住了）。\n"
                       "为避免改到看不见的要素，这次没有写入。\n"
                       "可以先清除过滤/筛选，或把范围切到「仅选中」。") % len(selected),
                )
                return None
            return fids
        if scope == "all":
            fids = self._all_layer_fids(layer)
            if not fids:
                QMessageBox.information(self, title, tr("图层没有要素。"))
                return None
            return fids
        fids = self.model.fids()
        if not fids:
            QMessageBox.information(self, title, tr("当前没有可更新的筛选行。"))
            return None
        return fids

    def _all_layer_fids(self, layer):
        try:
            return list(layer.allFeatureIds())
        except Exception:
            pass  # nosec B110
        req = QgsFeatureRequest().setFlags(QgsFeatureRequest.Flag.NoGeometry)
        try:
            req.setNoAttributes()
        except Exception:
            pass  # nosec B110
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
        title = tr(title)
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
                tr("变量「%s」不存在，无法写入。") % tr("、").join(missing),
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
        scope_tip = {"selected": tr("选中"), "filtered": tr("筛选"), "all": tr("全部")}.get(scope, scope)
        if confirm and not self._pending_targets_all_empty(layer, pending, fids):
            lines = "\n".join(
                "  %s = %s" % (name, self._pending_shown(val))
                for name, val in pending.items()
            )
            if (
                QMessageBox.question(
                    self,
                    tr("快速插入"),
                    tr("将按快速插入行写入 %s 条（%s）：\n%s\n继续？") % (len(fids), scope_tip, lines),
                )
                != QMessageBox.StandardButton.Yes
            ):
                return
        total = 0
        skipped = 0
        multi = len(pending) > 1
        if multi:
            layer.beginEditCommand(tr("快速插入"))
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
            extra = tr("，%s 列因表达式失败已跳过") % skipped if skipped else ""
            self._show_status(tr("快速插入完成：更新 %s 处%s") % (total, extra), 4000)
        elif skipped:
            self._show_status(tr("快速插入：表达式未能写入任何行"), 4000)

    @staticmethod
    def _pending_shown(val):
        if isinstance(val, dict):
            return val.get("text") or val.get("value") or ""
        return val

    def _ask_quick_fill_scope(self, field_name, value, combo):
        box = QMessageBox(self)
        box.setWindowTitle(tr("快速插入"))
        shown = combo.currentText() if combo is not None else str(value)
        box.setText(tr("将「%s」写入字段「%s」") % (shown, field_name))
        btn_all = box.addButton(tr("更新全部"), QMessageBox.ButtonRole.ActionRole)
        btn_filt = box.addButton(tr("更新筛选项"), QMessageBox.ButtonRole.ActionRole)
        btn_sel = box.addButton(tr("更新选中"), QMessageBox.ButtonRole.ActionRole)
        btn_cancel = box.addButton(tr("取消"), QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(btn_sel)
        run_exec(box)
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
            QMessageBox.information(self, tr("快速插入"), tr("请先切换到编辑模式。"))
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
                QMessageBox.information(self, tr("快速插入"), tr("没有选中的要素。"))
                return
        else:
            fids = self.model.fids()
            if not fids:
                QMessageBox.information(self, tr("快速插入"), tr("当前没有可更新的筛选行。"))
                return
        coerced = self._coerce_value_for_field(field, value)
        values = {fid: coerced for fid in fids}
        updated = self._commit_attribute_values(
            layer, field_idx, field_name, values, "快速插入"
        )
        if updated:
            self._show_status(
                tr("快速插入：%s 行 → %s = %s") % (updated, field_name, value), 4000
            )

    def _open_fill_expression_builder(self):
        if self._layer is None:
            return
        replace_expr = (
            hasattr(self, "cmb_fill_mode")
            and self.cmb_fill_mode.currentData() == "replace"
            and self._replace_write_source() == "expr"
        )
        current = self.ed_fill_replace.text() if replace_expr else self.ed_fill.text()
        dlg = QgsExpressionBuilderDialog(self._layer, expression_from_text(current), self)
        dlg.setWindowTitle(tr("赋值表达式"))
        if not run_exec(dlg):
            return
        if replace_expr:
            self.ed_fill_replace.setText(dlg.expressionText())
            return
        self.ed_fill.setText(dlg.expressionText())
        self.cmb_fill_mode.blockSignals(True)
        idx = self.cmb_fill_mode.findData("expr")
        if idx >= 0:
            self.cmb_fill_mode.setCurrentIndex(idx)
        self.cmb_fill_mode.blockSignals(False)
        self._on_fill_mode_changed()
        self._remember_fill_mode()

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
                raw = value_text(issue.raw) or tr("（空）")
                if issue.status == "rounded":
                    out.append(tr("    编号 %s：%s → %s") % (fid, raw, issue.value))
                else:
                    out.append(tr("    编号 %s：%s（%s）") % (fid, raw, issue.note))
            if len(items) > 4:
                out.append("    …")
            return "\n".join(out)

        lines = [tr("字段「%s」本次要写入 %s 条。") % (field_name, total + len(invalid))]
        if invalid:
            lines.append(tr("\n%s 条和字段类型不符，写不进去，会跳过：\n%s") % (len(invalid), samples(invalid)))
        if rounded:
            lines.append(tr("\n%s 条是小数，整数字段会四舍五入：\n%s") % (len(rounded), samples(rounded)))
        if toolong:
            lines.append(
                tr("\n%s 条文字超过字段长度，保存时数据源可能截断或拒绝：\n%s")
                % (len(toolong), samples(toolong))
            )
        if total <= 0:
            QMessageBox.warning(self, command_name, "\n".join(lines) + tr("\n\n没有可写入的值。"))
            return False
        lines.append(tr("\n继续写入其余 %s 条？") % total)
        return QMessageBox.question(self, command_name, "\n".join(lines)) == QMessageBox.StandardButton.Yes

    def _run_fill(self, selected_only=False):
        layer = self._layer
        if layer is None or not layer.isEditable():
            QMessageBox.information(self, tr("赋值"), tr("请先切换到编辑模式。"))
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
            QMessageBox.information(self, tr("赋值"), tr("请选择目标字段。"))
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
        if mode == "around_seq":
            self._run_fill_around_seq(layer, field, field_idx, field_name, fids, selected_only)
            return
        if mode == "affix":
            self._run_fill_affix(layer, field, field_idx, field_name, fids, selected_only)
            return

        scope_tip = tr("选中") if selected_only else tr("筛选")
        const_kind, const_payload = (None, None)
        if mode == "const":
            const_kind, const_payload = self._parse_const_fill_input(content)
        if not self._pending_targets_all_empty(layer, {field_name: True}, fids):
            if const_kind == "field":
                confirm_msg = tr(
                    "将用字段「%s」的内容写入「%s」共 %s 条（%s）记录，继续？"
                ) % (const_payload, field_name, len(fids), scope_tip)
            else:
                confirm_msg = tr(
                    "将向字段「%s」写入 %s 条（%s）记录，继续？"
                ) % (field_name, len(fids), scope_tip)
            if (
                QMessageBox.question(
                    self,
                    tr("赋值确认"),
                    confirm_msg,
                )
                != QMessageBox.StandardButton.Yes
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
                    QMessageBox.warning(self, tr("赋值"), tr("找不到字段「%s」。") % src_field)
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
                                tr("赋值"),
                                tr("变量「%s」不存在，无法写入。") % tr("、").join(missing),
                            )
                            return
                        raw = resolved
                val = self._coerce_value_for_field(field, raw)
                for fid in fids:
                    values[fid] = val

        elif mode == "expr":
            values = self._eval_fill_expression(layer, field, fids, content)
            if values is None:
                return
        else:
            return

        updated = self._commit_attribute_values(layer, field_idx, field_name, values, "赋值")
        if updated:
            if src_field:
                self._show_status(
                    tr("赋值完成：已更新 %s 行 → %s ← %s") % (updated, field_name, src_field),
                    4000,
                )
            else:
                self._show_status(
                    tr("赋值完成：已更新 %s 行 → %s") % (updated, field_name),
                    4000,
                )

    def _fill_row_order(self, fids, selected_only):
        order = [fid for fid in self.model.fids() if fid in set(fids)]
        if selected_only and not order:
            order = list(fids)
        return order

    def _fill_width_choice(self):
        if hasattr(self, "cmb_fill_width"):
            return self.cmb_fill_width.currentData()
        return "none"

    def _run_fill_around_seq(self, layer, field, field_idx, field_name, fids, selected_only):
        """Add a padded sequence before or after each cell's current text."""
        if not self._field_stores_text(field):
            QMessageBox.warning(
                self,
                tr("赋值"),
                tr("前后序号是在已有文字上加序号，只写入文本字段。当前字段是数字类型，存不住。"),
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
            sample = tr("（空白）→ %s") % token
        scope_tip = tr("选中") if selected_only else tr("筛选")
        side = tr("前面") if place == "before" else tr("后面")
        if (
            QMessageBox.question(
                self,
                tr("赋值确认"),
                tr("保留「%s」里的原文字，在%s加上序号，共 %s 条（%s）。如 %s。空白只写序号。继续？")
                % (field_name, side, len(order), scope_tip, sample or ""),
            )
            != QMessageBox.StandardButton.Yes
        ):
            return
        updated = self._commit_attribute_values(layer, field_idx, field_name, values, "赋值")
        if updated:
            self._show_status(
                tr("前后序号完成：已在原文字%s加上序号，更新 %s 行 → %s") % (side, updated, field_name),
                4000,
            )

    def _run_fill_affix(self, layer, field, field_idx, field_name, fids, selected_only):
        prefix = self.ed_fill_prefix.text() if hasattr(self, "ed_fill_prefix") else ""
        suffix = self.ed_fill_suffix.text() if hasattr(self, "ed_fill_suffix") else ""
        if prefix == "" and suffix == "":
            QMessageBox.information(self, tr("赋值"), tr("请填写要加在前面或后面的文字。"))
            return
        if not self._field_stores_text(field):
            QMessageBox.warning(
                self,
                tr("赋值"),
                tr("前后加字只写入文本字段。当前字段是数字类型，加字存不住。"),
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
            QMessageBox.information(self, tr("赋值"), tr("范围内没有已有文字，空白单元格不会被改。"))
            return
        scope_tip = tr("选中") if selected_only else tr("筛选")
        skipped = len(fids) - len(values)
        if (
            QMessageBox.question(
                self,
                tr("赋值确认"),
                tr("给「%s」已有文字前面加「%s」、后面加「%s」，共 %s 条（%s）。空白 %s 条不动。继续？")
                % (field_name, prefix, suffix, len(values), scope_tip, skipped),
            )
            != QMessageBox.StandardButton.Yes
        ):
            return
        updated = self._commit_attribute_values(layer, field_idx, field_name, values, "赋值")
        if updated:
            self._show_status(
                tr("前后加字完成：已更新 %s 行，空白未改 %s 行 → %s") % (updated, skipped, field_name),
                4000,
            )
        else:
            self._show_status(tr("已有文字没有变化 → %s") % field_name, 4000)

    def _eval_fill_expression(self, layer, field, fids, expr_text, skip_errors=False):
        expr_text = expression_from_text(expr_text)
        if not expr_text:
            if skip_errors:
                return {}
            QMessageBox.warning(self, tr("赋值"), tr("请输入表达式。"))
            return None
        exp = QgsExpression(expr_text)
        if exp.hasParserError():
            QMessageBox.warning(
                self,
                tr("赋值") if not skip_errors else tr("快速插入"),
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
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            for i in range(0, len(fids), chunk):
                if eval_error:
                    break
                batch = fids[i:i + chunk]
                req = QgsFeatureRequest().setFilterFids(batch)
                if not need_geom:
                    req.setFlags(QgsFeatureRequest.Flag.NoGeometry)
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
                tr("赋值"),
                tr("表达式错误（FID %s）：%s") % (eval_error[0], eval_error[1]),
            )
            return None
        return values

    def _replace_choice_parts(self):
        choice = getattr(self, "_replace_choice", None) or ("standard", "const", "after")
        mode, source, side = choice
        if mode not in ("standard", "around", "field"):
            mode = "standard"
        if source not in ("const", "expr"):
            source = "const"
        if side not in ("before", "after"):
            side = "after"
        return mode, source, side

    def _replace_mode(self):
        return self._replace_choice_parts()[0]

    def _replace_write_source(self):
        return self._replace_choice_parts()[1]

    def _replace_side(self):
        return self._replace_choice_parts()[2]

    def _replace_choice_label(self):
        mode, source, side = self._replace_choice_parts()
        mode_name = {
            "standard": tr("标准"),
            "around": tr("基于查找值"),
            "field": tr("所在字段"),
        }.get(mode, mode)
        write_name = tr("表达式") if source == "expr" else tr("常量")
        if mode == "around":
            place = tr("前面") if side == "before" else tr("后面")
            return "%s · %s · %s" % (mode_name, place, write_name)
        return "%s · %s" % (mode_name, write_name)

    def _set_replace_choice(self, mode, source, side):
        self._replace_choice = (mode, source, side)
        if hasattr(self, "btn_replace_choice"):
            self.btn_replace_choice.setText(self._replace_choice_label())
        self._on_replace_options_changed()

    def _rebuild_replace_menu(self):
        button = getattr(self, "btn_replace_choice", None)
        if button is None:
            return
        const_tip = tr("写入固定文字。留空表示删掉命中的那段")
        expr_tip = tr("按每个要素计算 QGIS 表达式。算失败的行跳过")
        groups = (
            (
                tr("标准"),
                tr("只改命中的那段，一格里多处都改"),
                (
                    ("standard", "const", "after", tr("常量"), const_tip),
                    ("standard", "expr", "after", tr("表达式"), expr_tip),
                ),
            ),
            (
                tr("基于查找值"),
                tr("在命中前面或后面插入，原文留下"),
                (
                    ("around", "const", "after", "%s · %s" % (tr("后面"), tr("常量")), const_tip),
                    ("around", "expr", "after", "%s · %s" % (tr("后面"), tr("表达式")), expr_tip),
                    ("around", "const", "before", "%s · %s" % (tr("前面"), tr("常量")), const_tip),
                    ("around", "expr", "before", "%s · %s" % (tr("前面"), tr("表达式")), expr_tip),
                ),
            ),
            (
                tr("所在字段"),
                tr("只要命中，整格换成新内容"),
                (
                    ("field", "const", "after", tr("常量"), const_tip),
                    ("field", "expr", "after", tr("表达式"), expr_tip),
                ),
            ),
        )
        menu = QMenu(button)
        for title, tip, rows in groups:
            sub = menu.addMenu(title)
            sub.setToolTip(tip)
            for mode, source, side, label, row_tip in rows:
                act = sub.addAction(label)
                act.setToolTip(row_tip)
                act.triggered.connect(
                    lambda _checked=False, m=mode, s=source, p=side: self._set_replace_choice(m, s, p)
                )
        old = button.menu()
        button.setMenu(menu)
        if old is not None:
            old.deleteLater()
        button.setText(self._replace_choice_label())
        mode, _source, _side = self._replace_choice_parts()
        tips = {
            "standard": tr("只改命中的那段，一格里多处都改"),
            "around": tr("在命中前面或后面插入，原文留下"),
            "field": tr("只要命中，整格换成新内容"),
        }
        button.setToolTip(tips.get(mode, ""))

    def _sync_replace_write_placeholder(self):
        edit = getattr(self, "ed_fill_replace", None)
        if edit is None:
            return
        source = self._replace_write_source()
        if source == "expr":
            edit.setPlaceholderText(tr("QGIS 表达式，如 concat(\"A\", $id)"))
            edit.setToolTip(tr("按每个要素计算。算失败的行跳过，其它行照常写。"))
        else:
            edit.setPlaceholderText(tr("常量，留空表示删掉命中的那段"))
            edit.setToolTip(tr("固定文字。留空表示删掉命中的那段；基于查找值时留空等于不插入。"))
        drop = getattr(self, "_replace_expr_drop", None)
        if drop is not None:
            drop.sync(None)

    def _on_replace_options_changed(self, _index=None):
        if hasattr(self, "lbl_fill_replace"):
            self.lbl_fill_replace.setVisible(True)
        if hasattr(self, "ed_fill_replace"):
            self.ed_fill_replace.setVisible(True)
        if hasattr(self, "btn_replace_choice"):
            mode, _source, _side = self._replace_choice_parts()
            tips = {
                "standard": tr("只改命中的那段，一格里多处都改"),
                "around": tr("在命中前面或后面插入，原文留下"),
                "field": tr("只要命中，整格换成新内容"),
            }
            self.btn_replace_choice.setToolTip(tips.get(mode, ""))
        self._sync_replace_write_placeholder()
        if hasattr(self, "btn_fill_expr") and hasattr(self, "cmb_fill_mode"):
            fill_mode = self.cmb_fill_mode.currentData()
            self.btn_fill_expr.setVisible(fill_mode != "replace")
            self.btn_fill_expr.setEnabled(fill_mode == "expr")

    def _run_replace(self, layer, field, field_idx, field_name, fids, selected_only):
        find_text = self.ed_fill_find.text()
        if find_text == "":
            QMessageBox.warning(self, tr("替换"), tr("请输入要查找的文字。"))
            return
        mode, source, side = self._replace_choice_parts()
        exact = bool(self.chk_replace_exact.isChecked()) if hasattr(self, "chk_replace_exact") else False
        case_sensitive = bool(self.chk_replace_case.isChecked()) if hasattr(self, "chk_replace_case") else True
        const_text = self.ed_fill_replace.text() if hasattr(self, "ed_fill_replace") else ""
        expr_text = expression_from_text(const_text)
        if source == "expr" and not str(expr_text).strip():
            QMessageBox.warning(self, tr("替换"), tr("请填写 QGIS 表达式，或改用常量。"))
            return

        order = self._fill_row_order(fids, selected_only)
        fetched = self.model._fetch_attributes(order, [field_idx])
        matched = []
        for fid in order:
            raw = fetched.get(fid, {}).get(field_idx, NULL)
            if raw is None or raw == NULL:
                continue
            _text, hits = apply_replace(
                str(raw), find_text, "", mode, side, exact, case_sensitive
            )
            if hits:
                matched.append(fid)
        if not matched:
            QMessageBox.information(
                self,
                tr("替换"),
                tr("当前范围内没有匹配「%s」。") % find_text,
            )
            return

        expr_values = {}
        expr_failed = []
        if source == "expr":
            expr_values, expr_failed = self._replace_expression_values(layer, matched, expr_text)
            if expr_values is None:
                return

        values = {}
        rows = 0
        occ = 0
        samples = []
        for fid in matched:
            raw = fetched.get(fid, {}).get(field_idx, NULL)
            old = str(raw)
            if source == "expr":
                if fid not in expr_values:
                    continue
                new_content = expr_values[fid]
            else:
                new_content = const_text
            new_text, hits = apply_replace(
                old, find_text, new_content, mode, side, exact, case_sensitive
            )
            if hits <= 0 or new_text == old:
                continue
            values[fid] = self._coerce_value_for_field(field, new_text)
            rows += 1
            occ += hits
            if len(samples) < 3:
                samples.append("%s → %s" % (old, new_text))

        if not values:
            if expr_failed:
                QMessageBox.warning(
                    self,
                    tr("替换"),
                    tr("表达式没有算出可写入的值。例如：%s") % expr_failed[0][1],
                )
            else:
                QMessageBox.information(self, tr("替换"), tr("命中的格子换成新内容后没有变化。"))
            return

        scope_tip = tr("选中") if selected_only else tr("筛选")
        mode_labels = {
            "standard": tr("标准（只改命中片段）"),
            "around": tr("基于查找值（%s插入，原文留下）") % (tr("前面") if side == "before" else tr("后面")),
            "field": tr("所在字段（整格替换）"),
        }
        if source == "expr":
            write_desc = tr("表达式：%s") % expr_text
        else:
            write_desc = tr("常量：%s") % (const_text if const_text != "" else tr("（空，删掉命中的那段）"))
        lines = [
            tr("字段「%s」（%s）") % (field_name, scope_tip),
            tr("查找：%s") % find_text,
            tr("模式：%s") % mode_labels.get(mode, mode),
            tr("写入：%s") % write_desc,
            tr("命中 %s 行 / %s 处。") % (rows, occ),
        ]
        if exact:
            lines.append(tr("完整匹配。"))
        if not case_sensitive:
            lines.append(tr("不区分大小写。"))
        if samples:
            lines.append(tr("例如：%s") % "；".join(samples))
        if expr_failed:
            lines.append(tr("另有 %s 行表达式失败，将跳过。") % len(expr_failed))
        lines.append(tr("继续？"))
        if QMessageBox.question(self, tr("替换确认"), "\n".join(lines)) != QMessageBox.StandardButton.Yes:
            return

        updated = self._commit_attribute_values(
            layer, field_idx, field_name, values, "替换", skip_unchanged=False
        )
        if updated:
            self._show_status(
                tr("替换完成：%s 行 / %s 处 → %s") % (updated, occ, field_name),
                4000,
            )

    def _replace_expression_values(self, layer, fids, expr_text):
        """Return ({fid: text}, [(fid, error), ...]). None values means the expression cannot be parsed."""
        expr_text = expression_from_text(expr_text)
        exp = QgsExpression(expr_text)
        if exp.hasParserError():
            QMessageBox.warning(self, tr("替换"), exp.parserErrorString())
            return None, []
        ctx = QgsExpressionContext()
        ctx.appendScopes(QgsExpressionContextUtils.globalProjectLayerScopes(layer))
        try:
            exp.prepare(ctx)
        except Exception:
            pass  # nosec B110
        need_geom = True
        try:
            need_geom = bool(exp.needsGeometry())
        except Exception:
            need_geom = True
        values = {}
        failed = []
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            req = QgsFeatureRequest().setFilterFids(list(fids))
            if not need_geom:
                req.setFlags(QgsFeatureRequest.Flag.NoGeometry)
            by_id = {}
            for feat in layer.getFeatures(req):
                by_id[feat.id()] = feat
            for fid in fids:
                feat = by_id.get(fid)
                if feat is None:
                    failed.append((fid, tr("要素不在图层里")))
                    continue
                ctx.setFeature(feat)
                raw = exp.evaluate(ctx)
                if exp.hasEvalError():
                    failed.append((fid, exp.evalErrorString() or tr("表达式求值失败")))
                    continue
                if raw is None or raw == NULL:
                    values[fid] = ""
                else:
                    values[fid] = str(raw)
        finally:
            QApplication.restoreOverrideCursor()
        return values, failed

    def _commit_attribute_values(
        self, layer, field_idx, field_name, values, command_name, skip_unchanged=True, in_command=False
    ):
        command_name = tr(command_name)
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

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
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
                    QMessageBox.warning(self, command_name, tr("写入失败。"))
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
                    QMessageBox.warning(self, command_name, tr("写入失败。"))
                    return 0
        finally:
            if frozen and canvas is not None:
                try:
                    canvas.freeze(False)
                except Exception:
                    pass  # nosec B110
            QApplication.restoreOverrideCursor()
            if disconnected:
                try:
                    layer.attributeValueChanged.connect(self._on_attribute_changed)
                except Exception:
                    pass  # nosec B110

        self._refresh_after_fill(field_name)
        return updated

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
            QMessageBox.information(self, tr("缩放"), tr("没有选中的要素。"))
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
            QMessageBox.information(self, tr("导出"), tr("无图层。"))
            return
        dlg = ExportCsvDialog(self)
        if run_exec(dlg) != QDialog.DialogCode.Accepted:
            return
        scope = dlg.scope()
        qgis_fmt = dlg.use_qgis_format()
        coerce_num = dlg.coerce_numeric_text()
        path, _ = QFileDialog.getSaveFileName(
            self, tr("导出 CSV"), os.path.expanduser("~"), tr("CSV (*.csv)")
        )
        if not path:
            return

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            if qgis_fmt:
                self._write_csv_qgis_format(path, scope, coerce_num)
            else:
                self._write_csv_custom_order(path, scope, coerce_num)
        except OSError as e:
            QMessageBox.warning(self, tr("导出失败"), str(e))
            return
        finally:
            QApplication.restoreOverrideCursor()

        tip_scope = tr("全部要素") if scope == ExportCsvDialog.SCOPE_ALL else tr("当前表格")
        tip_fmt = tr("QGIS格式") if qgis_fmt else tr("自定义列序")
        tip_num = tr("数字文本") if coerce_num else tr("原文")
        self._show_status(
            tr("已导出（%s / %s / %s）：%s") % (tip_scope, tip_fmt, tip_num, path), 5000
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
                    batch = fids[i:i + chunk]
                    req = (
                        QgsFeatureRequest()
                        .setFilterFids(batch)
                        .setFlags(QgsFeatureRequest.Flag.NoGeometry)
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
                req = QgsFeatureRequest().setFlags(QgsFeatureRequest.Flag.NoGeometry)
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

    def _show_status(self, text, timeout=0, html=None):
        """Left side of the bottom bar.

        timeout 0 is the running summary. A positive timeout is a toast:
        it replaces the summary, then the summary comes back. The center
        length and the right-hand stats are separate labels, so a toast
        does not blank them.
        """
        label = getattr(self, "lbl_status", None)
        if label is None:
            return
        if timeout:
            self._status_toast = True
            label.setText(text)
            timer = getattr(self, "_toast_timer", None)
            if timer is not None:
                timer.start(int(timeout))
            return
        self._status_text = text
        self._status_html = html or ""
        if not getattr(self, "_status_toast", False):
            if self._status_html:
                label.set_markup(text, self._status_html)
            else:
                label.setText(text)

    def _restore_status_text(self):
        self._status_toast = False
        label = getattr(self, "lbl_status", None)
        if label is None:
            return
        text = getattr(self, "_status_text", "") or ""
        html = getattr(self, "_status_html", "") or ""
        if html:
            label.set_markup(text, html)
        else:
            label.setText(text)

    def _update_status(self):
        self._update_window_title()
        layer = self._layer
        if layer is None:
            self._show_status(tr("无图层"))
            self.lbl_stats.clear()
            self.lbl_stats.setStyleSheet("")
            self._update_length_label()
            return
        total = layer.featureCount()
        shown = self.model.rowCount()
        selected = len(layer.selectedFeatureIds())
        sort = ""
        if self.model.sort_field():
            arrow = "↑" if self.model.sort_ascending() else "↓"
            sort = "  |  " + tr("排序") + " " + self.model.sort_field() + arrow
        empty = ""
        if shown == 0 and total:
            empty = "  |  " + self._empty_result_hint()
        template = tr("共 %s  |  显示 %s  |  选择 %s")
        plain = template % (total, shown, selected) + sort + empty
        html = _html_slots(
            template,
            [
                _count_html(total, False),
                _count_html(shown, shown != total),
                _count_html(selected, selected != total),
            ],
        )
        if html and (sort or empty):
            html += _html_escape(sort + empty)
        self._show_status(plain, html=html or None)
        self._update_stats_label()
        self._update_length_label()

    def _empty_result_hint(self):
        """Why the table is empty although the layer has features."""
        reasons = []
        scope = self._current_scope_mode()
        if scope == "selected":
            reasons.append(tr("范围是「仅选中」"))
        elif scope == "canvas":
            reasons.append(tr("范围是「地图可见」"))
        elif scope == "modified":
            reasons.append(tr("范围是「仅已修改」"))
        if self.model.text_filter():
            reasons.append(tr("过滤「%s」") % self.model.text_filter())
        if self.model.category_filter():
            reasons.append(tr("筛选"))
        if not reasons:
            return tr("没有匹配的行")
        return tr("没有匹配的行：%s，可清除或把范围切回「全部要素」") % tr("、").join(reasons)

    def _update_stats_label(self):
        """Bottom-right: selection-cell stats, or column sort stats."""
        if self._stats_mode == "selection":
            if self._sel_sum is not None and self._sel_count is not None:
                self.lbl_stats.setStyleSheet("")
                self.lbl_stats.setText(
                    tr("选中合计 %s个 / 总和 %s")
                    % (self._sel_count, self._format_sum(self._sel_sum))
                )
                return
            if self._sel_dup is not None:
                kind, detail = self._sel_dup
                template = tr("选中重名 %s")
                text = template % detail
                html = _html_slots(template, [_bold_digits(detail)])
                if kind == "dup":
                    self.lbl_stats.setStyleSheet("color: #c62828;")
                elif kind == "none":
                    self.lbl_stats.setStyleSheet("color: #2e7d32;")
                else:
                    self.lbl_stats.setStyleSheet("")
                if html:
                    self.lbl_stats.set_markup(text, html)
                else:
                    self.lbl_stats.setText(text)
                return

        if self._stats_mode == "column" and self._stats_field_name:
            label = self._field_labels.get(self._stats_field_name, self._stats_field_name)

            if self._sum_filtered is not None and self._sum_all is not None:
                self.lbl_stats.setStyleSheet("")
                self.lbl_stats.setText(
                    tr("%s合计 筛选 %s / 全部 %s")
                    % (
                        label,
                        self._format_sum(self._sum_filtered),
                        self._format_sum(self._sum_all),
                    )
                )
                return

            if self._dup_filtered is not None and self._dup_all is not None:
                kind_f, text_f = self._dup_filtered
                kind_a, text_a = self._dup_all
                template = tr("%s重名 筛选 %s / 全部 %s")
                text = template % (label, text_f, text_a)
                html = _html_slots(
                    template,
                    [_html_escape(label), _bold_digits(text_f), _bold_digits(text_a)],
                )
                if kind_f == "dup" or kind_a == "dup":
                    self.lbl_stats.setStyleSheet("color: #c62828;")
                elif kind_f == "none" and kind_a == "none":
                    self.lbl_stats.setStyleSheet("color: #2e7d32;")
                else:
                    self.lbl_stats.setStyleSheet("")
                if html:
                    self.lbl_stats.set_markup(text, html)
                else:
                    self.lbl_stats.setText(text)
                return

        self.lbl_stats.clear()
        self.lbl_stats.setStyleSheet("")

    def _update_length_label(self):
        """Bottom center: total real length of the selected features (line layers only).

        The empty state explains itself: the center area carries a tooltip
        naming the exact reason (param off / not a line layer / no geometry),
        so a blank middle is never a guess.
        """
        label = getattr(self, "lbl_line_length", None)
        if label is None:
            return
        host = getattr(self, "_length_host", None)

        def _tip(text):
            label.setToolTip(text)
            if host is not None:
                host.setToolTip(text)

        if not self._settings.load_show_line_length():
            label.clear()
            _tip(tr("参数「显示所选要素的线长度」未开启。"))
            return
        layer = self._layer
        if layer is None or not layer.isSpatial():
            label.clear()
            _tip(tr("无图层。") if layer is None else tr("当前图层没有几何。"))
            return
        try:
            gtype = int(layer.geometryType())
        except Exception:
            gtype = -1
        if gtype != 1:  # 1 = LineGeometry; not read from any attribute field
            label.clear()
            _tip(tr("当前图层不是线图层。只有线图层显示所选线长。"))
            return
        fids = layer.selectedFeatureIds()
        if not fids:
            label.setText("—")
            _tip(tr("线图层，未选中要素时显示「—」。"))
            return
        total = self._measure_selected_length(layer, fids)
        formatted = self._format_length(total)
        template = tr("所选线长 %s")
        text = template % formatted
        html = _html_slots(template, [_bold_digits(formatted)])
        if html:
            label.set_markup(text, html)
        else:
            label.setText(text)
        _tip(tr("线图层：已选 %d 条，线长合计 %s。") % (len(fids), formatted))

    def _measure_selected_length(self, layer, fids):
        """Sum geometry length of the selected features.

        Geographic CRS: ellipsoidal length (QgsDistanceArea + project ellipsoid).
        Projected CRS: planar length in CRS units (usually meters).
        Never reads a length attribute; geometry only, no attributes fetched.
        """
        from qgis.core import QgsDistanceArea, QgsFeatureRequest, QgsProject

        total = 0.0
        crs = layer.crs()
        da = None
        try:
            if crs is not None and crs.isValid() and crs.isGeographic():
                da = QgsDistanceArea()
                da.setSourceCrs(crs, QgsProject.instance().transformContext())
                da.setEllipsoid(QgsProject.instance().ellipsoid())
        except Exception:
            da = None
        try:
            req = QgsFeatureRequest().setFilterFids(list(fids))
            # QGIS 3.40 renamed the flag to setNoAttributes(); older builds
            # only know setFlags(NoAttributes). Probe instead of relying on
            # the AttributeError fallback path.
            setter = getattr(req, "setNoAttributes", None)
            if callable(setter):
                setter()
            else:
                req.setFlags(QgsFeatureRequest.NoAttributes)
        except Exception:
            req = QgsFeatureRequest().setFilterFids(list(fids))
        for feat in layer.getFeatures(req):
            geom = feat.geometry()
            if geom is None or geom.isEmpty():
                continue
            try:
                if da is not None:
                    total += da.measureLength(geom)
                else:
                    total += geom.length()
            except Exception:
                continue  # nosec B112
        return total

    @staticmethod
    def _format_length(meters):
        try:
            meters = float(meters)
        except (TypeError, ValueError):
            return "—"
        if meters < 0:
            return "—"
        if meters >= 1000:
            text = ("%.2f" % (meters / 1000.0)).rstrip("0").rstrip(".")
            return "%s km" % text
        text = ("%.2f" % meters).rstrip("0").rstrip(".")
        return "%s m" % text

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
            QMessageBox.warning(self, tr("属性表"), str(exc))
            return False
        finally:
            if prev is not None and prev != layer:
                try:
                    self.iface.setActiveLayer(prev)
                except Exception:
                    pass  # nosec B110

    def keyPressEvent(self, event):
        if event.matches(QKeySequence.StandardKey.Copy):
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
            self._show_status(tr("请先选择单元格"), 3000)
            return
        cells = {}
        rows = set()
        cols = set()
        for idx in indexes:
            row = idx.row()
            col = idx.column()
            rows.add(row)
            cols.add(col)
            val = self.model.data(idx, Qt.ItemDataRole.EditRole)
            cells[(row, col)] = self._cell_clipboard_text(val)
        row_list = sorted(rows)
        col_list = sorted(cols)
        lines = []
        for row in row_list:
            lines.append("\t".join(cells.get((row, col), "") for col in col_list))
        text = "\n".join(lines)
        clip = QApplication.clipboard()
        if clip is None:
            QMessageBox.warning(self, tr("复制"), tr("无法访问剪贴板。"))
            return
        clip.setText(text)
        self._show_status(tr("已复制 %s 个单元格到剪贴板") % len(indexes), 3000)

    def _copy_features(self):
        layer = self._layer
        if layer is None:
            return
        n = len(layer.selectedFeatureIds())
        if n == 0:
            self._show_status(tr("请先选中要素（选择单元格会同步选中对应行）"), 3000)
            return
        act = self.iface.actionCopyFeatures()
        if act is None:
            QMessageBox.warning(self, tr("复制"), tr("当前 QGIS 无复制要素动作。"))
            return
        if self._with_layer_as_active(lambda: act.trigger()):
            self._show_status(tr("已复制 %s 个要素到剪贴板") % n, 3000)

    def _cut_features(self):
        layer = self._layer
        if layer is None:
            return
        if not layer.isEditable():
            QMessageBox.information(self, tr("剪切"), tr("请先切换到编辑模式。"))
            return
        n = len(layer.selectedFeatureIds())
        if n == 0:
            self._show_status(tr("请先选中要剪切的要素"), 3000)
            return
        act = self.iface.actionCutFeatures()
        if act is None:
            QMessageBox.warning(self, tr("剪切"), tr("当前 QGIS 无剪切要素动作。"))
            return
        if self._with_layer_as_active(lambda: act.trigger()):
            self.reload_table()
            self._show_status(tr("已剪切 %s 个要素") % n, 3000)

    def _paste_features(self):
        layer = self._layer
        if layer is None:
            return
        if not layer.isEditable():
            QMessageBox.information(self, tr("粘贴"), tr("请先切换到编辑模式。"))
            return
        if clipboard_is_roundtrip(self._clipboard_text()):
            self._show_status(tr("剪贴板是「编号 + 值」两列 → 按编号粘贴回列"), 4000)
            self._paste_roundtrip_column(None)
            return
        act = self.iface.actionPasteFeatures()
        if act is None:
            QMessageBox.warning(self, tr("粘贴"), tr("当前 QGIS 无粘贴要素动作。"))
            return
        if self._with_layer_as_active(lambda: act.trigger()):
            self._schedule_reload()
            self._show_status(tr("剪贴板不是可回贴格式 → 已按 QGIS 要素粘贴（新增要素）"), 4000)

    def showEvent(self, event):
        super().showEvent(event)
        try:
            self.setMaximumSize(QWIDGETSIZE_MAX, QWIDGETSIZE_MAX)
        except Exception:
            pass  # nosec B110
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
                pass  # nosec B110
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
                pass  # nosec B110
            self._watching_canvas = False
        self._disconnect_layer_signals()
        self._detach_remarks_hub()
        self._remarks_hub = None
        # Shortcut carriers live on this widget; remove them explicitly so a
        # closed table never leaves stale QActions behind.
        for act in getattr(self, "_shortcut_carriers", []):
            try:
                self.removeAction(act)
                act.deleteLater()
            except Exception:
                pass  # nosec B110
        self._shortcut_carriers = []
        try:
            QgsProject.instance().readProject.disconnect(self._on_project_read)
        except Exception:
            pass  # nosec B110
        try:
            QgsProject.instance().cleared.disconnect(self._on_project_cleared)
        except Exception:
            pass  # nosec B110
        super().closeEvent(event)

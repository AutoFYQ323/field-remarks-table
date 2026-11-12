# -*- coding: utf-8 -*-
"""Settings dialog: toolbar / shortcuts / parameters.

Shortcut handling follows the LayersPanelTools pattern:
- QKeySequenceEdit rows, Backspace / Delete clears the recording
- a shortcut is refused while another row, a saved shortcut, one of this
  plugin's fixed in-table keys, or a QGIS action already uses it
- the conflict names the holder so the user can decide what to free
"""

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QKeySequence
from qgis.PyQt.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QGridLayout,
    QHBoxLayout,
    QKeySequenceEdit,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .i18n import localize_button_box, tr
from .settings_store import SettingsStore
from .toolbar_order_dialog import ToolbarOrderPage
from .wide_combo import WidePopupCombo


def _sequence_text(sequence):
    try:
        text = sequence.toString()
    except Exception:
        return ""
    return str(text or "").strip()


class _ShortcutEdit(QKeySequenceEdit):
    """Backspace / Delete clears the recorded sequence."""

    def keyPressEvent(self, event):
        try:
            key = int(event.key())
            mods = int(event.modifiers())
        except Exception:
            super().keyPressEvent(event)
            return
        if mods == 0 and key in (int(Qt.Key.Key_Backspace), int(Qt.Key.Key_Delete)):
            self.clear()
            return
        super().keyPressEvent(event)


def _is_our_carrier(obj):
    try:
        return bool(str(obj.property("atp_shortcut_id") or ""))
    except Exception:
        return False


def _holder_label(obj):
    try:
        text = str(obj.text() or "").strip()
        if text:
            return text
    except Exception:
        pass  # nosec B110
    try:
        return str(obj.objectName() or "").strip() or "QGIS"
    except Exception:
        return "QGIS"


def _object_sequences(obj):
    out = []
    getter = getattr(obj, "shortcut", None)
    if callable(getter):
        try:
            out.append(getter())
        except Exception:
            pass  # nosec B110
    getter = getattr(obj, "key", None)
    if callable(getter):
        try:
            out.append(getter())
        except Exception:
            pass  # nosec B110
    return [s for s in out if s is not None]


def shortcut_holder(sequence_text, own_id=""):
    """Name of the QGIS feature already bound to this sequence, or "".

    Own carrier actions (property atp_shortcut_id) never count as holders;
    the settings page reports duplicates between its own rows itself.
    """
    seq = QKeySequence.fromString(str(sequence_text or ""))
    if seq.isEmpty():
        return ""
    window = None
    try:
        from qgis.utils import iface

        window = iface.mainWindow()
    except Exception:
        window = None
    objects = []
    try:
        from qgis.gui import QgsGui

        manager = QgsGui.shortcutsManager()
        found = manager.objectForSequence(seq)
        if found is not None and not _is_our_carrier(found):
            return _holder_label(found)
        lister = getattr(manager, "listAll", None)
        if callable(lister):
            try:
                objects.extend(list(lister()))
            except Exception:
                pass  # nosec B110
    except Exception:
        pass  # nosec B110
    if window is not None:
        try:
            from .qt_compat import QAction

            objects.extend(window.findChildren(QAction))
        except Exception:
            pass  # nosec B110
        shortcut_type = None
        try:
            from qgis.PyQt.QtGui import QShortcut as shortcut_type
        except Exception:
            try:
                from qgis.PyQt.QtWidgets import QShortcut as shortcut_type
            except Exception:
                shortcut_type = None
        if shortcut_type is not None:
            try:
                objects.extend(window.findChildren(shortcut_type))
            except Exception:
                pass  # nosec B110
    seen = set()
    for obj in objects:
        if obj is None:
            continue
        ident = id(obj)
        if ident in seen:
            continue
        seen.add(ident)
        if _is_our_carrier(obj):
            continue
        for other in _object_sequences(obj):
            try:
                if other == seq and not other.isEmpty():
                    return _holder_label(obj)
            except Exception:
                continue  # nosec B112
    return ""


class ShortcutsPage(QWidget):
    """One row per plugin tool: label + QKeySequenceEdit."""

    # Fixed in-table keys. These tool actions already carry a Qt standard
    # sequence, and Ctrl+C always copies the selected cells inside the table.
    RESERVED = (
        ("cut", QKeySequence(QKeySequence.StandardKey.Cut)),
        ("paste", QKeySequence(QKeySequence.StandardKey.Paste)),
        ("cells", QKeySequence(QKeySequence.StandardKey.Copy)),
    )

    def __init__(self, rows, settings, parent=None):
        """rows: list of (tool_id, label). Existing values come from settings."""
        super().__init__(parent)
        self._rows = list(rows or [])
        self._settings = settings
        self._saved = dict(settings.load_shortcuts())
        self._edits = {}
        self._labels = {}
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel(tr("按组合键录制；按 Backspace 或 Delete 清除。只在 QGIS 窗口内响应，不是系统全局。")))
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        body = QWidget()
        grid = QGridLayout(body)
        grid.setContentsMargins(0, 0, 0, 0)
        for index, (tool_id, label) in enumerate(self._rows):
            lbl = QLabel(label)
            edit = _ShortcutEdit()
            edit.setObjectName("AttributeTablePlusShortcutEdit")
            edit.setToolTip(tr("按组合键录制；按 Backspace 或 Delete 清除。"))
            edit.setKeySequence(
                QKeySequence.fromString(self._saved.get(tool_id, ""))
            )
            edit.keySequenceChanged.connect(
                lambda *_a, e=edit, t=tool_id: self._on_recorded(t, e)
            )
            self._edits[tool_id] = edit
            self._labels[tool_id] = label
            grid.addWidget(lbl, index, 0)
            grid.addWidget(edit, index, 1)
        grid.setColumnStretch(0, 1)
        scroll.setWidget(body)
        layout.addWidget(scroll, 1)
        # The clear button lives in the dialog's bottom row, next to OK/Cancel;
        # the dialog decides when it is visible (only on this page).
        self.btn_clear = QPushButton(tr("清除全部"))
        self.btn_clear.clicked.connect(self._clear_all)

    def _clear_all(self):
        for edit in self._edits.values():
            edit.blockSignals(True)
            edit.clear()
            edit.blockSignals(False)

    def _reserved_holder(self, sequence_text, own_id):
        for rid, seq in self.RESERVED:
            if rid == own_id:
                continue
            if _sequence_text(seq) == sequence_text:
                if rid == "cells":
                    return tr("复制选中单元格（表格内固定）")
                if rid == "cut":
                    return tr("剪切选中要素（固定）")
                if rid == "paste":
                    return tr("粘贴要素（固定）")
        return ""

    def _on_recorded(self, tool_id, edit):
        """Record, then refuse when the sequence is taken. The holder is named."""
        sequence = _sequence_text(edit.keySequence())
        if not sequence:
            return
        holder = self._row_holder(sequence, tool_id)
        if not holder:
            holder = self._reserved_holder(sequence, tool_id)
        if not holder:
            holder = shortcut_holder(sequence, tool_id)
        if holder:
            edit.blockSignals(True)
            edit.clear()
            edit.blockSignals(False)
            self._report(
                tr("快捷键 %s 已被占用，未设置。") % sequence,
                holder,
            )

    def _row_holder(self, sequence_text, own_id):
        for other_id, edit in self._edits.items():
            if other_id == own_id:
                continue
            if _sequence_text(edit.keySequence()) == sequence_text:
                return self._labels.get(other_id, other_id)
        for other_id, text in self._saved.items():
            if other_id == own_id:
                continue
            if str(text or "").strip() == sequence_text:
                if other_id in self._labels:
                    return self._labels[other_id]
        return ""

    def _report(self, text, holder=""):
        if holder:
            text = "%s（%s）" % (text, holder)
        QMessageBox.warning(self, tr("快捷键"), text)

    def result_shortcuts(self):
        out = {}
        for tool_id, edit in self._edits.items():
            sequence = _sequence_text(edit.keySequence())
            if sequence:
                out[tool_id] = sequence
        return out


def _fit_combo(combo):
    """Closed box and its list both wide enough for the longest item."""
    metrics = combo.fontMetrics()
    advance = getattr(metrics, "horizontalAdvance", None) or metrics.width
    width = 0
    for row in range(combo.count()):
        width = max(width, advance(combo.itemText(row)))
    combo.setMinimumWidth(width + 48)
    try:
        combo.setSizeAdjustPolicy(combo.SizeAdjustPolicy.AdjustToContents)
    except Exception:
        pass  # nosec B110


def _select_data(combo, value):
    index = combo.findData(value)
    if index >= 0:
        combo.setCurrentIndex(index)


class ParamsPage(QWidget):
    """Runtime parameters. Everything here is optional and has a default."""

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self._settings = settings
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.chk_line_length = QCheckBox(tr("显示所选要素的线长度"))
        self.chk_line_length.setToolTip(
            tr("线图层时，属性表窗口底部中间显示当前所选要素的线长合计。读几何自己算，不读字段。默认关。")
        )
        self.chk_line_length.setChecked(settings.load_show_line_length())
        layout.addWidget(self.chk_line_length)

        self.chk_filter_follow = QCheckBox(tr("筛选跟随所选字段"))
        self.chk_filter_follow.setToolTip(
            tr("非分类图层时，表格里点到哪一列，「筛选」就切到哪个字段（已勾选的值重置为「全部」）。"
               "分类图层保持「分类筛选」不跟随。默认开。")
        )
        self.chk_filter_follow.setChecked(settings.load_filter_follow_field())
        layout.addWidget(self.chk_filter_follow)

        row_limit = QHBoxLayout()
        lbl_limit = QLabel(tr("快速筛选值上限"))
        lbl_limit.setToolTip(tr("「筛选」的值下拉最多列出多少个不同的值。值很多时只列前面这些。"))
        self.spin_limit = QSpinBox()
        self.spin_limit.setRange(10, 5000)
        self.spin_limit.setSingleStep(10)
        self.spin_limit.setValue(settings.load_quick_value_limit())
        row_limit.addWidget(lbl_limit)
        row_limit.addWidget(self.spin_limit)
        row_limit.addStretch()
        layout.addLayout(row_limit)

        row_tol = QHBoxLayout()
        lbl_tol = QLabel(tr("线方向检查吸附容差（米）"))
        lbl_tol.setToolTip(
            tr("线方向检查：端点距离不超过这个值才算接上。0.6 是默认。")
        )
        self.spin_tol = QDoubleSpinBox()
        self.spin_tol.setRange(0.01, 1000.0)
        self.spin_tol.setDecimals(2)
        self.spin_tol.setSingleStep(0.1)
        self.spin_tol.setValue(settings.load_line_dir_tolerance())
        row_tol.addWidget(lbl_tol)
        row_tol.addWidget(self.spin_tol)
        row_tol.addStretch()
        layout.addLayout(row_tol)

        row_header = QHBoxLayout()
        lbl_header = QLabel(tr("列标题显示"))
        header_tip = tr(
            "属性表列标题怎么显示字段。\n"
            "仅字段名：只显示数据源里的字段名。\n"
            "别名优先：有别名（或字段备注的中文名）只显示别名，没有就显示字段名。\n"
            "别名和字段名：别名在上、字段名在下，两行都显示（默认）。"
        )
        lbl_header.setToolTip(header_tip)
        self.cmb_header = WidePopupCombo()
        self.cmb_header.addItem(tr("仅字段名"), "name")
        self.cmb_header.addItem(tr("别名优先"), "alias")
        self.cmb_header.addItem(tr("别名和字段名"), "both")
        self.cmb_header.setToolTip(header_tip)
        _fit_combo(self.cmb_header)
        _select_data(self.cmb_header, settings.load_header_mode())
        row_header.addWidget(lbl_header)
        row_header.addWidget(self.cmb_header)
        row_header.addStretch()
        layout.addLayout(row_header)

        row_fill = QHBoxLayout()
        lbl_fill = QLabel(tr("编辑模式赋值方式默认"))
        fill_tip = tr(
            "打开属性表时赋值栏先选哪种方式。\n"
            "记住上次：沿用上次手动选的方式，你一改它就跟着记。\n"
            "其余各项：每次都从这种方式开始。"
        )
        lbl_fill.setToolTip(fill_tip)
        self.cmb_fill_default = WidePopupCombo()
        self.cmb_fill_default.addItem(tr("记住上次"), "remember")
        for msgid, data in (
            ("常量", "const"),
            ("前后序号", "around_seq"),
            ("前后加字", "affix"),
            ("表达式", "expr"),
            ("替换", "replace"),
        ):
            self.cmb_fill_default.addItem(tr(msgid), data)
        self.cmb_fill_default.setToolTip(fill_tip)
        _fit_combo(self.cmb_fill_default)
        _select_data(self.cmb_fill_default, settings.load_fill_mode_default())
        row_fill.addWidget(lbl_fill)
        row_fill.addWidget(self.cmb_fill_default)
        row_fill.addStretch()
        layout.addLayout(row_fill)

        layout.addStretch()

    def apply(self):
        s = self._settings
        s.save_show_line_length(self.chk_line_length.isChecked())
        s.save_filter_follow_field(self.chk_filter_follow.isChecked())
        s.save_quick_value_limit(self.spin_limit.value())
        s.save_line_dir_tolerance(self.spin_tol.value())
        s.save_header_mode(self.cmb_header.currentData())
        s.save_fill_mode_default(self.cmb_fill_default.currentData())


class SettingsDialog(QDialog):
    """Toolbar / shortcuts / parameters in one place."""

    def __init__(self, toolbar_items, toolbar_order, toolbar_default, hidden,
                 shortcut_rows, settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("设置"))
        self.resize(560, 520)
        self._settings = settings if settings is not None else SettingsStore()

        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()

        self.toolbar_page = ToolbarOrderPage(toolbar_items, toolbar_order, self)
        self.toolbar_page.set_default_order(toolbar_default)
        self.toolbar_page.set_hidden(hidden)
        self.tabs.addTab(self.toolbar_page, tr("工具栏"))

        self.shortcuts_page = ShortcutsPage(shortcut_rows, self._settings, self)
        self.tabs.addTab(self.shortcuts_page, tr("快捷键"))

        self.params_page = ParamsPage(self._settings, self)
        self.tabs.addTab(self.params_page, tr("参数"))

        layout.addWidget(self.tabs, 1)

        # One shared bottom row: the page action (清除全部, shortcuts page
        # only) sits at the left, OK/Cancel stay at the far right.
        bottom = QHBoxLayout()
        self._page_action_host = QWidget()
        page_lay = QHBoxLayout(self._page_action_host)
        page_lay.setContentsMargins(0, 0, 0, 0)
        page_lay.addWidget(self.shortcuts_page.btn_clear)
        bottom.addWidget(self._page_action_host)
        bottom.addStretch(1)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        localize_button_box(buttons)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        bottom.addWidget(buttons)
        layout.addLayout(bottom)
        self.tabs.currentChanged.connect(lambda *_a: self._sync_page_action())
        self._sync_page_action()

    def _sync_page_action(self):
        """清除全部 only shows while the shortcuts page is in front."""
        try:
            index = self.tabs.indexOf(self.shortcuts_page)
            self._page_action_host.setVisible(self.tabs.currentIndex() == index)
        except Exception:
            pass  # nosec B110

    def result_toolbar_order(self):
        return self.toolbar_page.result_order()

    def result_toolbar_hidden(self):
        return self.toolbar_page.result_hidden()

    def result_shortcuts(self):
        return self.shortcuts_page.result_shortcuts()

    def apply_params(self):
        self.params_page.apply()

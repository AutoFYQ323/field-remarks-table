# -*- coding: utf-8 -*-
"""Saved fill expressions: the manager dialog and the fill-box dropdown."""

from qgis.PyQt.QtCore import QEvent, QObject, QStringListModel, Qt, QTimer
from qgis.PyQt.QtGui import QBrush, QColor
from qgis.PyQt.QtWidgets import (
    QAbstractItemView,
    QCompleter,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QStyle,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from .fill_expressions import display_list, display_text, expression_from_text, load_items, save_items
from .i18n import localize_button_box, tr
from .qt_compat import QAction, run_exec


def manage_icon():
    """A list, not the settings gear. Every language reads a list as "manage these"."""
    try:
        from qgis.core import QgsApplication

        for path in ("/mActionOpenTable.svg", "/mActionEditTable.svg", "/mActionShowBookmarks.svg"):
            icon = QgsApplication.getThemeIcon(path)
            if icon is not None and not icon.isNull():
                return icon
    except Exception:
        pass  # nosec B110
    return None


def _parse_error(expr):
    try:
        from qgis.core import QgsExpression

        exp = QgsExpression(expr)
        if exp.hasParserError():
            return exp.parserErrorString() or tr("语法错误")
    except Exception:
        return ""
    return ""


class ExpressionLibraryDialog(QDialog):
    """Add, edit, note, reorder, and delete saved fill expressions."""

    COL_NOTE = 0
    COL_EXPR = 1

    def __init__(self, layer=None, current_text="", parent=None):
        super().__init__(parent)
        self._layer = layer
        self.setWindowTitle(tr("常用表达式"))
        self.resize(640, 400)
        layout = QVBoxLayout(self)
        hint = QLabel(tr(
            "赋值框里显示为「«备注» 表达式」。运行的是 » 后面的表达式，"
            "在赋值框里改了也按改后的执行，这里保存的不变。双击单元格可直接修改。"
        ))
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels([tr("表达式备注"), tr("表达式")])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(self.COL_NOTE, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(self.COL_EXPR, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(self.COL_NOTE, 160)
        self.table.itemChanged.connect(self._on_item_changed)
        layout.addWidget(self.table, 1)

        row = QHBoxLayout()
        self.btn_add = QPushButton(tr("添加"))
        self.btn_add.setToolTip(tr("新增一行。赋值框里有表达式时，先填入它。"))
        self.btn_builder = QPushButton(tr("表达式构建器…"))
        self.btn_builder.setToolTip(tr("在 QGIS 表达式构建器里编辑所选行的表达式"))
        self.btn_delete = QPushButton(tr("删除"))
        self.btn_up = QPushButton(tr("上移"))
        self.btn_down = QPushButton(tr("下移"))
        for btn in (self.btn_add, self.btn_builder, self.btn_delete, self.btn_up, self.btn_down):
            btn.setAutoDefault(False)
            row.addWidget(btn)
        row.addStretch(1)
        layout.addLayout(row)
        self.btn_add.clicked.connect(self._add_row)
        self.btn_builder.clicked.connect(self._edit_in_builder)
        self.btn_delete.clicked.connect(self._delete_row)
        self.btn_up.clicked.connect(lambda: self._move_row(-1))
        self.btn_down.clicked.connect(lambda: self._move_row(1))
        self.table.itemSelectionChanged.connect(self._sync_buttons)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        localize_button_box(buttons)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._current = expression_from_text(current_text)
        self._loading = True
        for item in load_items():
            self._append(item["note"], item["expr"])
        self._loading = False
        self._sync_buttons()

    def _append(self, note, expr):
        index = self.table.rowCount()
        self.table.insertRow(index)
        self.table.setItem(index, self.COL_NOTE, QTableWidgetItem(note))
        self.table.setItem(index, self.COL_EXPR, QTableWidgetItem(expr))
        self._mark_row(index)
        return index

    def _cell(self, index, col):
        item = self.table.item(index, col)
        return item.text() if item is not None else ""

    def _mark_row(self, index):
        item = self.table.item(index, self.COL_EXPR)
        if item is None:
            return
        expr = item.text().strip()
        error = _parse_error(expr) if expr else ""
        note_item = self.table.item(index, self.COL_NOTE)
        shown = display_text(expr, note_item.text() if note_item is not None else "")
        if error:
            item.setForeground(QBrush(QColor("#c62828")))
            item.setToolTip(tr("表达式有语法错误：%s") % error)
        else:
            item.setData(Qt.ItemDataRole.ForegroundRole, None)
            item.setToolTip(tr("赋值框里显示为：%s") % shown if expr else "")

    def _on_item_changed(self, item):
        if self._loading or item is None:
            return
        self.table.blockSignals(True)
        try:
            self._mark_row(item.row())
        finally:
            self.table.blockSignals(False)

    def _selected_row(self):
        rows = self.table.selectionModel().selectedRows()
        if rows:
            return rows[0].row()
        index = self.table.currentRow()
        return index if index >= 0 else -1

    def _sync_buttons(self):
        index = self._selected_row()
        has = index >= 0
        self.btn_builder.setEnabled(has)
        self.btn_delete.setEnabled(has)
        self.btn_up.setEnabled(has and index > 0)
        self.btn_down.setEnabled(has and index < self.table.rowCount() - 1)

    def _known(self, expr):
        for index in range(self.table.rowCount()):
            if self._cell(index, self.COL_EXPR).strip() == expr:
                return True
        return False

    def _add_row(self):
        expr = self._current if self._current and not self._known(self._current) else ""
        self.table.blockSignals(True)
        index = self._append("", expr)
        self.table.blockSignals(False)
        self.table.selectRow(index)
        self.table.setCurrentCell(index, self.COL_NOTE if expr else self.COL_EXPR)
        self.table.editItem(self.table.item(index, self.COL_NOTE if expr else self.COL_EXPR))

    def _edit_in_builder(self):
        index = self._selected_row()
        if index < 0:
            return
        from qgis.gui import QgsExpressionBuilderDialog

        dlg = QgsExpressionBuilderDialog(self._layer, self._cell(index, self.COL_EXPR), self)
        dlg.setWindowTitle(tr("常用表达式"))
        if not run_exec(dlg):
            return
        self.table.item(index, self.COL_EXPR).setText(dlg.expressionText())

    def _delete_row(self):
        index = self._selected_row()
        if index < 0:
            return
        self.table.removeRow(index)
        self._sync_buttons()

    def _move_row(self, step):
        index = self._selected_row()
        target = index + step
        if index < 0 or target < 0 or target >= self.table.rowCount():
            return
        self.table.blockSignals(True)
        for col in (self.COL_NOTE, self.COL_EXPR):
            a = self.table.takeItem(index, col)
            b = self.table.takeItem(target, col)
            self.table.setItem(index, col, b)
            self.table.setItem(target, col, a)
        self.table.blockSignals(False)
        self.table.selectRow(target)
        self._sync_buttons()

    def items(self):
        out = []
        for index in range(self.table.rowCount()):
            expr = self._cell(index, self.COL_EXPR).strip()
            if expr:
                out.append({"expr": expr, "note": self._cell(index, self.COL_NOTE)})
        return out

    def _accept(self):
        bad = [item for item in self.items() if _parse_error(item["expr"])]
        if bad:
            sample = display_text(bad[0]["expr"], bad[0]["note"])
            answer = QMessageBox.question(
                self,
                tr("常用表达式"),
                tr("有 %s 条表达式有语法错误，例如：%s\n仍然保存？") % (len(bad), sample),
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        save_items(self.items())
        self.accept()


_MATCH_DELAY_MS = 200


def _alive(obj):
    """False once Qt has deleted the C++ object behind this Python wrapper."""
    if obj is None:
        return False
    try:
        obj.objectName()
    except RuntimeError:
        return False
    return True


class _ClickFilter(QObject):
    """Double-click selects the whole expression. Press and drag stay with the line edit."""

    def __init__(self, owner, edit):
        super().__init__(edit)
        self._owner = owner
        self._edit = edit

    def eventFilter(self, obj, event):
        if obj is self._edit and event.type() == QEvent.Type.MouseButtonDblClick:
            if self._owner.active():
                self._owner.hide_popup()
                self._edit.selectAll()
                return True
        return False


class ExpressionDropdown(object):
    """The fill box stays a normal line edit.

    Saved expressions are not installed with QLineEdit.setCompleter: that call
    deletes a completer whose parent is the line edit, and the installed
    completer opens on every key and on mouse press, which blocks drag-select.
    Typing waits 200 ms, then lists saved expressions that contain the text.
    The trailing arrow lists them all at once.
    """

    def __init__(self, edit, active):
        self._edit = edit
        self._active = active
        host = edit.parent() or edit
        self._model = QStringListModel(host)
        self._completer = None
        self._build(host)
        self._timer = QTimer(edit)
        self._timer.setSingleShot(True)
        self._timer.setInterval(_MATCH_DELAY_MS)
        self._timer.timeout.connect(self._complete_typed)
        edit.textEdited.connect(self._schedule)
        self._filter = _ClickFilter(self, edit)
        edit.installEventFilter(self._filter)
        icon = edit.style().standardIcon(QStyle.StandardPixmap.SP_ArrowDown)
        self._arrow = QAction(icon, "", edit)
        self._arrow.triggered.connect(self.popup)
        edit.addAction(self._arrow, QLineEdit.ActionPosition.TrailingPosition)
        self._arrow.setVisible(False)
        self.reload()

    def _build(self, host):
        comp = QCompleter(self._model, host)
        comp.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        comp.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        try:
            comp.setFilterMode(Qt.MatchFlag.MatchContains)
        except Exception:
            pass  # nosec B110
        comp.setMaxVisibleItems(12)
        try:
            comp.activated[str].connect(self._accept_text)
        except Exception:
            try:
                comp.activated.connect(self._accept_text)
            except Exception:
                pass  # nosec B110
        self._completer = comp

    def _ensure(self):
        if _alive(self._completer) and _alive(self._model):
            return self._completer
        host = self._edit.parent() or self._edit
        if not _alive(self._model):
            self._model = QStringListModel(host)
        self._build(host)
        self.reload()
        return self._completer

    def active(self):
        try:
            return bool(self._active())
        except Exception:
            return False

    def reload(self):
        if not _alive(self._model):
            self._ensure()
            return
        try:
            rows = display_list(load_items())
        except Exception:
            rows = []
        self._model.setStringList(rows)
        self._arrow.setToolTip(tr("常用表达式"))
        comp = self._completer
        if not _alive(comp):
            return
        try:
            metrics = self._edit.fontMetrics()
            advance = getattr(metrics, "horizontalAdvance", None) or metrics.width
            widest = 0
            for text in rows:
                widest = max(widest, advance(text))
            comp.popup().setMinimumWidth(min(640, widest + 48))
        except Exception:
            pass  # nosec B110

    def has_items(self):
        if not _alive(self._model):
            return False
        return self._model.rowCount() > 0

    def hide_popup(self):
        if not _alive(self._completer):
            return
        try:
            popup = self._completer.popup()
            if popup is not None:
                popup.hide()
        except RuntimeError:
            pass  # nosec B110

    def _accept_text(self, text):
        if not isinstance(text, str):
            comp = self._completer
            if not _alive(comp):
                return
            try:
                text = comp.currentCompletion()
            except RuntimeError:
                return
        if not text:
            return
        self._timer.stop()
        self._edit.setText(text)
        self._edit.setCursorPosition(len(text))

    def _schedule(self, _text=""):
        if not self.active():
            return
        self._timer.start(_MATCH_DELAY_MS)

    def _complete_typed(self):
        if not self.active():
            return
        try:
            if not self._edit.hasFocus():
                return
            text = self._edit.text()
        except RuntimeError:
            return
        if not str(text or "").strip():
            self.hide_popup()
            return
        self._show_matches(text)

    def _show_matches(self, prefix):
        comp = self._ensure()
        try:
            if comp.widget() is not self._edit:
                comp.setWidget(self._edit)
            comp.setCompletionPrefix(prefix or "")
            if comp.completionCount() <= 0:
                self.hide_popup()
                return
            comp.complete()
        except RuntimeError:
            pass  # nosec B110

    def sync(self, other_completer=None):
        """Expression mode keeps the box a plain edit. other_completer is the
        field-name list used by constant mode."""
        self._timer.stop()
        self.hide_popup()
        if self.active():
            self.reload()
        on = self.active() and self.has_items()
        self._arrow.setVisible(on)
        if self.active():
            comp = self._completer
            if _alive(comp):
                try:
                    if comp.widget() is not self._edit:
                        comp.setWidget(self._edit)
                except RuntimeError:
                    pass  # nosec B110
            # None, not the expression completer: QLineEdit would delete it
            # the next time the field-name completer is installed.
            self._edit.setCompleter(None)
            return
        if _alive(self._completer):
            try:
                self._completer.setWidget(None)
            except RuntimeError:
                pass  # nosec B110
        if not _alive(other_completer):
            other_completer = None
        self._edit.setCompleter(other_completer)

    def popup(self):
        if not self.active():
            return
        self._timer.stop()
        self.reload()
        if not self.has_items():
            return
        try:
            self._edit.setFocus()
        except RuntimeError:
            return
        self._show_matches("")

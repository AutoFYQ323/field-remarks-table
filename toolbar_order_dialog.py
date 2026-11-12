# -*- coding: utf-8 -*-
"""Toolbar order page: drag to reorder, checkbox to show/hide each button."""

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import (
    QLabel,
    QListWidget,
    QListWidgetItem,
    QAbstractItemView,
    QHBoxLayout,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from .i18n import tr


class ToolbarOrderPage(QWidget):
    def __init__(self, items, current_order, parent=None):
        """
        items: list of (id, label) for reorderable tools (no separators / customize)
        current_order: list of ids including 'sep' markers
        """
        super().__init__(parent)
        self._items = {i: lab for i, lab in items}
        self._hidden = set()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel(tr("拖拽调整顺序（分隔线也可拖动）。确定后本地保存：")))
        layout.addWidget(QLabel(tr("勾选表示在工具栏显示。取消勾选则隐藏，顺序仍保留。")))
        self.list = QListWidget()
        self.list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        layout.addWidget(self.list, 1)

        seen = set()
        for tid in current_order:
            if tid == "customize":
                continue
            if tid.startswith("sep"):
                self._add_sep(tid)
                seen.add(tid)
            elif tid in self._items:
                self._add_tool(tid, self._items[tid], tid not in self._hidden)
                seen.add(tid)
        for tid, lab in items:
            if tid not in seen:
                self._add_tool(tid, lab, tid not in self._hidden)

        row = QHBoxLayout()
        btn_sep = QPushButton(tr("插入分隔线"))
        btn_sep.clicked.connect(self._insert_sep)
        btn_reset = QPushButton(tr("恢复默认"))
        btn_reset.clicked.connect(self._reset_default)
        row.addWidget(btn_sep)
        row.addWidget(btn_reset)
        row.addStretch()
        layout.addLayout(row)

        self._default_order = list(current_order)

    def _add_sep(self, tid):
        item = QListWidgetItem(tr("—— 分隔线 ——"))
        item.setData(Qt.ItemDataRole.UserRole, tid)
        self.list.addItem(item)

    def _add_tool(self, tid, label, visible):
        item = QListWidgetItem(label)
        item.setData(Qt.ItemDataRole.UserRole, tid)
        item.setFlags(
            Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsSelectable
            | Qt.ItemFlag.ItemIsDragEnabled
            | Qt.ItemFlag.ItemIsUserCheckable
        )
        item.setCheckState(Qt.CheckState.Checked if visible else Qt.CheckState.Unchecked)
        self.list.addItem(item)

    def set_default_order(self, order):
        self._default_order = list(order)

    def set_hidden(self, hidden):
        self._hidden = set(hidden or [])
        for i in range(self.list.count()):
            item = self.list.item(i)
            tid = item.data(Qt.ItemDataRole.UserRole)
            if not tid or str(tid).startswith("sep"):
                continue
            item.setCheckState(Qt.CheckState.Unchecked if tid in self._hidden else Qt.CheckState.Checked)

    def _insert_sep(self):
        n = 1
        existing = {
            self.list.item(i).data(Qt.ItemDataRole.UserRole)
            for i in range(self.list.count())
        }
        while f"sep{n}" in existing:
            n += 1
        item = QListWidgetItem(tr("—— 分隔线 ——"))
        item.setData(Qt.ItemDataRole.UserRole, f"sep{n}")
        row = self.list.currentRow()
        if row < 0:
            self.list.addItem(item)
        else:
            self.list.insertItem(row + 1, item)

    def _reset_default(self):
        self._hidden = set()
        self.list.clear()
        for tid in self._default_order:
            if tid == "customize":
                continue
            if str(tid).startswith("sep"):
                self._add_sep(tid)
            else:
                self._add_tool(tid, self._items.get(tid, tid), True)

    def result_order(self):
        order = []
        for i in range(self.list.count()):
            tid = self.list.item(i).data(Qt.ItemDataRole.UserRole)
            if tid:
                order.append(tid)
        order.append("customize")
        return order

    def result_hidden(self):
        hidden = []
        for i in range(self.list.count()):
            item = self.list.item(i)
            tid = item.data(Qt.ItemDataRole.UserRole)
            if not tid or str(tid).startswith("sep") or tid == "customize":
                continue
            if item.checkState() != Qt.CheckState.Checked:
                hidden.append(tid)
        return hidden

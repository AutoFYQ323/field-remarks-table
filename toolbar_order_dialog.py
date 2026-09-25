# -*- coding: utf-8 -*-
"""Reorder toolbar actions and persist locally."""

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import (
    QCheckBox,
    QDialog,
    QVBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QDialogButtonBox,
    QAbstractItemView,
    QHBoxLayout,
    QPushButton,
)


class ToolbarOrderDialog(QDialog):
    def __init__(self, items, current_order, parent=None):
        """
        items: list of (id, label) for reorderable tools (no separators / customize)
        current_order: list of ids including 'sep' markers
        """
        super().__init__(parent)
        self.setWindowTitle("工具栏按钮顺序")
        self.resize(360, 420)
        self._items = {i: lab for i, lab in items}
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("拖拽调整顺序（分隔线也可拖动）。确定后本地保存："))
        self.chk_quick_name = QCheckBox("工具栏显示快速命名")
        self.chk_quick_name.setToolTip(
            "只决定属性表工具栏要不要多一个「快速命名」图标。"
            "快速命名是独立功能，与字段备注启用无关。"
        )
        self.chk_quick_name.setChecked(False)
        layout.addWidget(self.chk_quick_name)
        self.list = QListWidget()
        self.list.setDragDropMode(QAbstractItemView.InternalMove)
        layout.addWidget(self.list, 1)

        # populate from current_order, append any missing ids
        seen = set()
        for tid in current_order:
            if tid == "customize":
                continue
            if tid.startswith("sep"):
                item = QListWidgetItem("—— 分隔线 ——")
                item.setData(Qt.UserRole, tid)
                self.list.addItem(item)
                seen.add(tid)
            elif tid in self._items:
                item = QListWidgetItem(self._items[tid])
                item.setData(Qt.UserRole, tid)
                self.list.addItem(item)
                seen.add(tid)
        for tid, lab in items:
            if tid not in seen:
                item = QListWidgetItem(lab)
                item.setData(Qt.UserRole, tid)
                self.list.addItem(item)

        row = QHBoxLayout()
        btn_sep = QPushButton("插入分隔线")
        btn_sep.clicked.connect(self._insert_sep)
        btn_reset = QPushButton("恢复默认")
        btn_reset.clicked.connect(self._reset_default)
        row.addWidget(btn_sep)
        row.addWidget(btn_reset)
        row.addStretch()
        layout.addLayout(row)

        self._default_order = list(current_order)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def set_default_order(self, order):
        self._default_order = list(order)

    def set_show_quick_name(self, on):
        if hasattr(self, "chk_quick_name"):
            self.chk_quick_name.setChecked(bool(on))

    def show_quick_name(self):
        if hasattr(self, "chk_quick_name"):
            return bool(self.chk_quick_name.isChecked())
        return False

    def _insert_sep(self):
        n = 1
        existing = {
            self.list.item(i).data(Qt.UserRole)
            for i in range(self.list.count())
        }
        while f"sep{n}" in existing:
            n += 1
        item = QListWidgetItem("—— 分隔线 ——")
        item.setData(Qt.UserRole, f"sep{n}")
        row = self.list.currentRow()
        if row < 0:
            self.list.addItem(item)
        else:
            self.list.insertItem(row + 1, item)

    def _reset_default(self):
        self.set_show_quick_name(False)
        self.list.clear()
        for tid in self._default_order:
            if tid == "customize":
                continue
            if tid.startswith("sep"):
                item = QListWidgetItem("—— 分隔线 ——")
            else:
                item = QListWidgetItem(self._items.get(tid, tid))
            item.setData(Qt.UserRole, tid)
            self.list.addItem(item)

    def result_order(self):
        order = []
        for i in range(self.list.count()):
            tid = self.list.item(i).data(Qt.UserRole)
            if tid:
                order.append(tid)
        order.append("customize")
        return order

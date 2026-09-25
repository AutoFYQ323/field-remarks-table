# -*- coding: utf-8 -*-
"""KMZ export options dialog."""

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QFormLayout,
    QLabel,
    QComboBox,
    QListWidget,
    QListWidgetItem,
    QDialogButtonBox,
    QAbstractItemView,
    QPushButton,
    QHBoxLayout,
    QCheckBox,
)


class ExportKmzDialog(QDialog):
    def __init__(
        self, field_names, field_labels, parent=None, table_rows=None, total_rows=None
    ):
        super().__init__(parent)
        self.setWindowTitle("导出 KMZ")
        self.resize(420, 500)
        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel("默认导出图层全部要素（无几何要素将跳过）。默认坐标系 EPSG:4326。")
        )

        self.chk_table_only = QCheckBox()
        self._table_option = table_rows is not None
        if self._table_option:
            total_text = "" if total_rows is None or total_rows < 0 else "，图层共 %d 条" % total_rows
            self.chk_table_only.setText(
                "只导出当前表格里的 %d 行（受范围/过滤/筛选影响%s）" % (table_rows, total_text)
            )
        else:
            self.chk_table_only.setVisible(False)
        layout.addWidget(self.chk_table_only)

        self.chk_style = QCheckBox("使用图层颜色（单一/分类/分级符号）")
        self.chk_style.setToolTip("按当前图层符号给地标上色；规则符号等其他渲染方式不上色")
        self.chk_style.setChecked(True)
        layout.addWidget(self.chk_style)

        form = QFormLayout()
        self.cmb_title = QComboBox()
        self.cmb_title.addItem("（使用 FID）", "")
        for name in field_names:
            self.cmb_title.addItem(field_labels.get(name, name), name)
        form.addRow("标题字段：", self.cmb_title)

        self.cmb_crs = QComboBox()
        self.cmb_crs.setEditable(True)
        for auth in ("EPSG:4326", "EPSG:3857", "EPSG:4490", "EPSG:4547"):
            self.cmb_crs.addItem(auth)
        self.cmb_crs.setCurrentText("EPSG:4326")
        form.addRow("目标坐标系：", self.cmb_crs)
        layout.addLayout(form)

        layout.addWidget(QLabel("写入描述的字段（可多选）："))
        self.list = QListWidget()
        self.list.setSelectionMode(QAbstractItemView.MultiSelection)
        for name in field_names:
            item = QListWidgetItem(field_labels.get(name, name))
            item.setData(Qt.UserRole, name)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)
            self.list.addItem(item)
        layout.addWidget(self.list, 1)

        row = QHBoxLayout()
        btn_all = QPushButton("全选字段")
        btn_none = QPushButton("全不选")
        btn_all.clicked.connect(lambda: self._set_all(Qt.Checked))
        btn_none.clicked.connect(lambda: self._set_all(Qt.Unchecked))
        row.addWidget(btn_all)
        row.addWidget(btn_none)
        row.addStretch()
        layout.addLayout(row)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _set_all(self, state):
        for i in range(self.list.count()):
            self.list.item(i).setCheckState(state)

    def title_field(self):
        return self.cmb_title.currentData() or ""

    def table_only(self):
        return self._table_option and self.chk_table_only.isChecked()

    def use_layer_style(self):
        return self.chk_style.isChecked()

    def crs_authid(self):
        text = (self.cmb_crs.currentText() or "EPSG:4326").strip()
        return text or "EPSG:4326"

    def description_fields(self):
        names = []
        for i in range(self.list.count()):
            item = self.list.item(i)
            if item.checkState() == Qt.Checked:
                names.append(item.data(Qt.UserRole))
        return names

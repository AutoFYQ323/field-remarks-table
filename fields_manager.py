# -*- coding: utf-8 -*-
"""Field management: add (provider nativeTypes), rename, delete. No field calculator."""

from qgis.PyQt.QtCore import Qt, QVariant
from qgis.PyQt.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QMessageBox,
    QInputDialog,
    QLabel,
    QComboBox,
    QLineEdit,
    QFormLayout,
    QDialogButtonBox,
    QSpinBox,
)

from qgis.core import QgsField, QgsVectorDataProvider

from .remarks_store import field_is_empty


def _native_type_label(nt):
    name = getattr(nt, "mTypeName", None) or getattr(nt, "typeName", None) or ""
    desc = getattr(nt, "mTypeDesc", None) or getattr(nt, "typeDesc", None) or ""
    if desc and desc != name:
        return f"{desc} ({name})"
    return str(name or desc or "type")


def _native_qvariant(nt):
    t = getattr(nt, "mType", None)
    if t is None:
        t = getattr(nt, "type", None)
    return t if t is not None else QVariant.String


def _native_type_name(nt):
    return getattr(nt, "mTypeName", None) or getattr(nt, "typeName", None) or "string"


def _native_len_range(nt):
    mn = getattr(nt, "mMinLen", None)
    if mn is None:
        mn = getattr(nt, "minLen", 0) or 0
    mx = getattr(nt, "mMaxLen", None)
    if mx is None:
        mx = getattr(nt, "maxLen", 0) or 0
    return int(mn), int(mx)


def _native_prec_range(nt):
    mn = getattr(nt, "mMinPrec", None)
    if mn is None:
        mn = getattr(nt, "minPrec", 0) or 0
    mx = getattr(nt, "mMaxPrec", None)
    if mx is None:
        mx = getattr(nt, "maxPrec", 0) or 0
    return int(mn), int(mx)


class _NewFieldDialog(QDialog):
    """
    New-field dialog using provider.nativeTypes() — same type list idea as
    QGIS built-in add-field dialog (provider-specific).
    """

    def __init__(self, layer, parent=None):
        super().__init__(parent)
        self.layer = layer
        self.setWindowTitle("新建字段")
        form = QFormLayout(self)
        self.ed_name = QLineEdit()
        self.cmb_type = QComboBox()
        self.spn_len = QSpinBox()
        self.spn_prec = QSpinBox()
        self.spn_len.setRange(0, 10000)
        self.spn_prec.setRange(0, 20)

        provider = layer.dataProvider()
        natives = []
        if provider is not None:
            try:
                natives = list(provider.nativeTypes() or [])
            except Exception:
                natives = []
        if natives:
            for nt in natives:
                self.cmb_type.addItem(_native_type_label(nt), nt)
        else:
            # extreme fallback
            self.cmb_type.addItem("Integer", ("Integer", QVariant.Int, 0, 0))
            self.cmb_type.addItem("Real", ("Real", QVariant.Double, 0, 0))
            self.cmb_type.addItem("String", ("String", QVariant.String, 255, 0))

        self.cmb_type.currentIndexChanged.connect(self._on_type_changed)
        form.addRow("字段名：", self.ed_name)
        form.addRow("类型：", self.cmb_type)
        form.addRow("长度：", self.spn_len)
        form.addRow("精度：", self.spn_prec)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        form.addRow(btns)
        self._on_type_changed()

    def _current_native(self):
        return self.cmb_type.currentData()

    def _on_type_changed(self, _index=None):
        nt = self._current_native()
        if nt is None:
            return
        if isinstance(nt, tuple):
            _name, _qtype, length, prec = nt
            self.spn_len.setEnabled(True)
            self.spn_prec.setEnabled(True)
            self.spn_len.setValue(length)
            self.spn_prec.setValue(prec)
            return
        mn, mx = _native_len_range(nt)
        pmn, pmx = _native_prec_range(nt)
        if mx <= 0:
            mx = 255
        if mn < 0:
            mn = 0
        self.spn_len.setRange(mn, max(mx, mn))
        self.spn_len.setEnabled(mx > 0)
        default_len = 10 if mn == 0 and mx >= 10 else mn
        if mx >= 255 and mn == 0:
            default_len = 50
        self.spn_len.setValue(min(max(default_len, mn), mx if mx > 0 else default_len))

        if pmx <= 0:
            self.spn_prec.setEnabled(False)
            self.spn_prec.setValue(0)
        else:
            self.spn_prec.setEnabled(True)
            self.spn_prec.setRange(pmn, pmx)
            self.spn_prec.setValue(min(max(pmn, 0), pmx))

    def field(self):
        name = self.ed_name.text().strip()
        nt = self._current_native()
        length = self.spn_len.value()
        prec = self.spn_prec.value() if self.spn_prec.isEnabled() else 0
        if isinstance(nt, tuple):
            type_name, qtype, _l, _p = nt
            return QgsField(name, qtype, type_name, length, prec)
        qtype = _native_qvariant(nt)
        type_name = _native_type_name(nt)
        return QgsField(name, qtype, type_name, length, prec)


class FieldsManagerDialog(QDialog):
    """Manage layer fields: add / rename / delete."""

    def __init__(self, layer, parent=None, remarks_store=None):
        super().__init__(parent)
        self.layer = layer
        self._remarks = remarks_store
        self.setWindowTitle("字段管理")
        self.resize(420, 360)
        self._changed = False
        self._remarks_changed = False

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("当前图层字段（改名/删除需在编辑模式且数据源支持）："))
        self.list = QListWidget()
        layout.addWidget(self.list, 1)

        row = QHBoxLayout()
        self.btn_add = QPushButton("新建字段")
        self.btn_rename = QPushButton("重命名")
        self.btn_delete = QPushButton("删除字段")
        self.btn_remarks = QPushButton("字段备注")
        self.btn_add.clicked.connect(self._add_field)
        self.btn_rename.clicked.connect(self._rename_field)
        self.btn_delete.clicked.connect(self._delete_field)
        self.btn_remarks.clicked.connect(self._edit_remarks)
        row.addWidget(self.btn_add)
        row.addWidget(self.btn_rename)
        row.addWidget(self.btn_delete)
        row.addWidget(self.btn_remarks)
        layout.addLayout(row)

        close_btn = QDialogButtonBox(QDialogButtonBox.Close)
        close_btn.rejected.connect(self.reject)
        layout.addWidget(close_btn)

        self._reload()
        self._update_buttons()

    def changed(self):
        return self._changed

    def remarks_changed(self):
        return self._remarks_changed

    def _edit_remarks(self):
        parent = self.parent()
        if parent is not None and hasattr(parent, "_open_layer_remarks"):
            parent._open_layer_remarks(focus_field=self._selected_name())
            self._remarks_changed = True
            return
        if parent is not None and hasattr(parent, "_open_remarks_hub"):
            parent._open_remarks_hub()
            if getattr(parent, "_remarks_hub", None) is not None:
                parent._remarks_hub.focus_field(self._selected_name())
            self._remarks_changed = True

    def _reload(self):
        self.list.clear()
        lname = self.layer.name() if self.layer is not None else ""
        for f in self.layer.fields():
            alias = (f.alias() or "").strip()
            remark_label = ""
            if self._remarks is not None:
                remark_label = self._remarks.display_label(lname, f.name(), "")
            display = (remark_label or alias).strip()
            label = f"{f.name()} ({f.typeName()})"
            if display and display != f.name():
                label = f"{f.name()} ({display}) — {f.typeName()}"
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, f.name())
            self.list.addItem(item)

    def _selected_name(self):
        item = self.list.currentItem()
        return item.data(Qt.UserRole) if item else None

    def _provider_caps(self):
        p = self.layer.dataProvider()
        return p.capabilities() if p else 0

    def _update_buttons(self):
        editing = self.layer.isEditable()
        caps = self._provider_caps()
        can_add = bool(caps & QgsVectorDataProvider.AddAttributes)
        can_del = bool(caps & QgsVectorDataProvider.DeleteAttributes)
        can_rename = bool(caps & QgsVectorDataProvider.RenameAttributes)
        self.btn_add.setEnabled(editing and can_add)
        self.btn_delete.setEnabled(editing and can_del)
        self.btn_rename.setEnabled(editing and can_rename)
        if hasattr(self, "btn_remarks"):
            self.btn_remarks.setEnabled(self.layer is not None and self._remarks is not None)
        tips = []
        if not editing:
            tips.append("请先切换到编辑模式")
        if editing and not can_rename:
            tips.append("当前数据源不支持字段重命名")
        if editing and not can_add:
            tips.append("当前数据源不支持添加字段")
        if tips:
            self.setWindowTitle("字段管理 — " + "；".join(tips))
        else:
            self.setWindowTitle("字段管理")

    def _ensure_editing(self):
        if self.layer.isEditable():
            return True
        QMessageBox.information(self, "字段管理", "请先在属性表中切换到编辑模式。")
        return False

    def _add_field(self):
        if not self._ensure_editing():
            return
        dlg = _NewFieldDialog(self.layer, self)
        if dlg.exec_() != QDialog.Accepted:
            return
        field = dlg.field()
        if not field.name():
            QMessageBox.warning(self, "新建字段", "字段名不能为空。")
            return
        if self.layer.fields().indexFromName(field.name()) >= 0:
            QMessageBox.warning(self, "新建字段", "字段名已存在。")
            return
        if not self.layer.addAttribute(field):
            QMessageBox.warning(self, "新建字段", "添加失败（数据源可能不支持）。")
            return
        self.layer.updateFields()
        self._changed = True
        self._reload()

    def _rename_field(self):
        if not self._ensure_editing():
            return
        caps = self._provider_caps()
        if not (caps & QgsVectorDataProvider.RenameAttributes):
            QMessageBox.warning(
                self,
                "重命名",
                "当前数据源不支持直接重命名字段。\n"
                "（例如部分 Shapefile / 只读层。可换用 GeoPackage 等格式。）",
            )
            return
        old = self._selected_name()
        if not old:
            QMessageBox.information(self, "重命名", "请先选择一个字段。")
            return
        new, ok = QInputDialog.getText(
            self, "重命名字段", f"新名称（原名：{old}）：", text=old
        )
        if not ok:
            return
        new = new.strip()
        if not new or new == old:
            return
        if self.layer.fields().indexFromName(new) >= 0:
            QMessageBox.warning(self, "重命名", "目标字段名已存在。")
            return
        idx = self.layer.fields().indexFromName(old)
        if idx < 0:
            return
        if not self.layer.renameAttribute(idx, new):
            QMessageBox.warning(self, "重命名", "重命名失败。")
            return
        self.layer.updateFields()
        self._changed = True
        self._move_field_remark(old, new)
        self._reload()

    def _move_field_remark(self, old_name, new_name):
        if self._remarks is None or not old_name or not new_name or old_name == new_name:
            return
        lname = self.layer.name()
        old_entry = self._remarks.field_entry(lname, old_name)
        if field_is_empty(old_entry):
            return
        fields = self._remarks.fields_map(lname)
        fields[new_name] = old_entry
        fields.pop(old_name, None)
        self._remarks.set_layer_bundle(lname, fields)
        self._remarks_changed = True

    def _delete_field(self):
        if not self._ensure_editing():
            return
        name = self._selected_name()
        if not name:
            QMessageBox.information(self, "删除字段", "请先选择一个字段。")
            return
        if (
            QMessageBox.question(self, "删除字段", f"确定删除字段「{name}」？")
            != QMessageBox.Yes
        ):
            return
        idx = self.layer.fields().indexFromName(name)
        if idx < 0:
            return
        if not self.layer.deleteAttribute(idx):
            QMessageBox.warning(self, "删除字段", "删除失败（数据源可能不支持）。")
            return
        self.layer.updateFields()
        self._changed = True
        self._drop_field_remark(name)
        self._reload()

    def _drop_field_remark(self, name):
        """Ask before removing the deleted field's remark from the current pack."""
        if self._remarks is None or not name:
            return
        try:
            if self._remarks.is_placeholder():
                return
        except Exception:
            return
        lname = self.layer.name()
        if field_is_empty(self._remarks.field_entry(lname, name)):
            return
        if (
            QMessageBox.question(
                self,
                "删除字段",
                "字段「%s」在当前备注项目里还有中文名/说明/含义。\n"
                "一并删掉这条备注吗？（选「否」则保留，以后再建同名字段仍会套用）" % name,
            )
            != QMessageBox.Yes
        ):
            return
        fields = self._remarks.fields_map(lname)
        fields.pop(name, None)
        self._remarks.set_layer_bundle(lname, fields)
        self._remarks_changed = True

# -*- coding: utf-8 -*-
from ...i18n import tr
from qgis.core import (
    QgsProject,
    QgsVectorLayer,
)
from qgis.gui import QgsMapLayerComboBox
try:
    from qgis.core import QgsMapLayerProxyModel
except ImportError:
    from qgis.gui import QgsMapLayerProxyModel
from qgis.PyQt.QtCore import QEvent, QObject, QSize, Qt
from qgis.PyQt.QtGui import QColor, QIcon, QPalette, QPixmap
from qgis.PyQt.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QAbstractItemView,
    QPushButton,
    QCheckBox,
    QRadioButton,
    QSizePolicy,
    QTableWidget,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QButtonGroup,
    QWidget,
)

from .layer_picker import CHECKED, ITEM_USER_CHECKABLE, UNCHECKED, USER_ROLE, attr_key
from .ntal_legend import count_legend_keys, list_layer_categories, remap_filter_keys
from .ntal_scheme import (
    ACTION_TITLES,
    cable_accumulate,
    default_action_schemes,
    iter_action_scheme_rows,
    migrate_action_schemes,
)
from .ntal_scheme_preview import SchemePreviewPane


class NoWheelComboBox(QComboBox):
    def wheelEvent(self, event):
        event.ignore()


class WheelBlockerFilter(QObject):
    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Wheel:
            return True
        return False


def _layers_named(name):
    n = str(name or "").strip()
    if not n:
        return []
    return [
        lyr for lyr in QgsProject.instance().mapLayers().values()
        if isinstance(lyr, QgsVectorLayer) and lyr.name() == n
    ]


def find_layer_by_name(name, layer_id=None):
    """先按图层 ID 找（同名图层不会串），找不到再按名称。"""
    if layer_id:
        lyr = QgsProject.instance().mapLayer(layer_id)
        if isinstance(lyr, QgsVectorLayer):
            return lyr
    exact = _layers_named(name)
    return exact[0] if exact else None


def find_row_layer(row):
    row = row or {}
    return find_layer_by_name(row.get("layer"), row.get("layer_id"))


def resolve_group(group):
    group = group or {}
    layers = []
    filters = {}
    seen = set()
    for row in group.get("rows") or []:
        layer = find_row_layer(row)
        if layer is None or layer.id() in seen:
            continue
        seen.add(layer.id())
        layers.append(layer)
        flt = row.get("filter")
        if not flt:
            continue
        if flt.get("keys") is not None:
            filters[layer.id()] = {
                "keys": list(flt.get("keys") or []),
                "labels": list(flt.get("labels") or []),
            }
        elif flt.get("field") is not None:
            filters[layer.id()] = {
                "field": flt["field"],
                "values": list(flt.get("values") or []),
            }
    return layers, filters, (group.get("field") or "").strip()


GROUP_TITLES = {
    "occ": "光交",
    "splice": "接头",
    "fat": "分纤盒",
    "user": "用户点",
    "cable": "光缆",
    "drop": "皮线",
}
OPTIONAL_FIELDS = {"occ"}


def _stale_filter(layer, flt):
    if not flt or flt.get("keys") is None or not flt.get("keys"):
        return 0
    try:
        _keys, stale = remap_filter_keys(layer, flt)
    except Exception:
        return 0
    return stale


def match_report(layers_cfg):
    missing = []
    configured = 0
    for key, title in GROUP_TITLES.items():
        group = (layers_cfg or {}).get(key) or {}
        field = (group.get("field") or "").strip()
        for row in group.get("rows") or []:
            name = (row.get("layer") or "").strip()
            if not name:
                continue
            configured += 1
            layer = find_row_layer(row)
            if layer is None:
                missing.append(tr("找不到图层：{}").format(name))
                continue
            if not row.get("layer_id") and len(_layers_named(name)) > 1:
                missing.append(tr("有多个同名图层「{}」，请在图层配置里重新选一次再保存。").format(name))
            stale = _stale_filter(layer, row.get("filter"))
            if stale:
                missing.append(tr("图层 {} 的分类筛选有 {} 类对不上当前符号（已按分类名称兜底匹配），建议重新筛选。").format(name, stale))
            names = [item.name() for item in layer.fields()]
            if field and field not in names:
                missing.append(tr("找不到字段：{}（图层 {}）").format(field, name))
            if key == "drop":
                continue
            code_field = (group.get("code_field") or "").strip()
            if code_field and code_field not in names:
                missing.append(tr("找不到字段：{}（图层 {}）").format(code_field, name))
    if not configured:
        return tr("还没有配置任何图层。")
    if not missing:
        return tr("所配置的图层和字段都能找到。")
    return "\n".join(missing)


class _ClearButtonCenterFilter(QObject):
    def eventFilter(self, obj, event):
        et = event.type()
        try:
            show = QEvent.Type.Show
            resize = QEvent.Type.Resize
        except AttributeError:
            show = QEvent.Type.Show
            resize = QEvent.Type.Resize
        if et in (show, resize):
            host = obj if isinstance(obj, QLineEdit) else obj.parentWidget()
            if host is None:
                return False
            for btn in host.findChildren(QToolButton):
                if btn.parentWidget() is not host:
                    continue  # nosec B112
                y = max(0, (host.height() - btn.height()) // 2)
                if btn.y() != y:
                    btn.move(btn.x(), y)
        return False


class FieldClearLineEdit(QLineEdit):
    def __init__(self, parent=None):
        super(FieldClearLineEdit, self).__init__(parent)
        self.setClearButtonEnabled(True)
        self._center_filter = _ClearButtonCenterFilter(self)
        self.installEventFilter(self._center_filter)
        self.textChanged.connect(lambda _t: self._hook_clear_buttons())
        self._hook_clear_buttons()

    def _hook_clear_buttons(self):
        for btn in self.findChildren(QToolButton):
            btn.setAutoRaise(True)
            btn.setFixedSize(14, 14)
            btn.setStyleSheet("QToolButton { border: none; margin: 0; padding: 0; }")
            btn.installEventFilter(self._center_filter)
        self._reposition_clear()

    def resizeEvent(self, event):
        super(FieldClearLineEdit, self).resizeEvent(event)
        self._reposition_clear()

    def _reposition_clear(self):
        for btn in self.findChildren(QToolButton):
            if btn.parentWidget() is not self:
                continue
            y = max(0, (self.height() - btn.height()) // 2)
            if btn.y() != y:
                btn.move(btn.x(), y)


def _color_icon(color_name, size=12):
    pix = QPixmap(size, size)
    color = QColor(color_name) if color_name else QColor("#cccccc")
    if not color.isValid():
        color = QColor("#cccccc")
    pix.fill(color)
    return QIcon(pix)


class CategoryFilterDialog(QDialog):
    def __init__(self, layer, current_filter=None, parent=None, include_unchecked=False):
        super(CategoryFilterDialog, self).__init__(parent)
        self.layer = layer
        self._include_unchecked = bool(include_unchecked)
        self.setWindowTitle(tr("筛选分类 — {}").format(layer.name() if layer else ""))
        self.setMinimumWidth(380)
        self.setMinimumHeight(360)
        layout = QVBoxLayout(self)
        self.hint = QLabel(tr("只勾选要使用的分类。未勾选的要素不参与。分类来自图层符号化（分类/规则），括号内是要素数量。"))
        self.hint.setWordWrap(True)
        layout.addWidget(self.hint)
        btn_row = QHBoxLayout()
        all_btn = QPushButton(tr("全选"))
        none_btn = QPushButton(tr("全不选"))
        all_btn.clicked.connect(lambda: self._set_all(True))
        none_btn.clicked.connect(lambda: self._set_all(False))
        btn_row.addWidget(all_btn)
        btn_row.addWidget(none_btn)
        btn_row.addStretch(1)
        layout.addLayout(btn_row)
        self.value_list = QListWidget()
        layout.addWidget(self.value_list, 1)
        try:
            buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        except AttributeError:
            buttons = QDialogButtonBox(
                QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
            )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self._load_categories(current_filter)

    def _preset_keys(self, current_filter):
        current = current_filter or {}
        if current.get("keys") is not None:
            return set(str(k) for k in (current.get("keys") or []))
        if current.get("values") is not None:
            keys = set(attr_key(v) for v in (current.get("values") or []))
            for label in current.get("labels") or []:
                keys.add(attr_key(label))
            return keys
        return None

    def _load_categories(self, current_filter):
        self.value_list.clear()
        items, err = list_layer_categories(self.layer, include_unchecked=self._include_unchecked)
        if err:
            self.hint.setText(tr("%s。没有可筛选的分组时，将使用该图层全部要素。") % err)
            return
        keys = [info["key"] for info in items]
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            counts = count_legend_keys(self.layer, keys, include_unchecked=self._include_unchecked)
        except Exception:
            counts = {k: 0 for k in keys}
        finally:
            QApplication.restoreOverrideCursor()
        preset = self._preset_keys(current_filter)
        matched = False
        pending = []
        for info in items:
            key = info["key"]
            label = info.get("label") or key
            count = int(counts.get(key, 0))
            if preset is None:
                on = True
            else:
                on = key in preset or attr_key(label) in preset
                matched = matched or on
            pending.append((key, label, info.get("color"), count, on))
        if preset is not None and not matched:
            pending = [(key, label, color, count, True) for key, label, color, count, _on in pending]
        for key, label, color, count, on in pending:
            item = QListWidgetItem(_color_icon(color), "%s  (%s)" % (label, count))
            item.setData(USER_ROLE, key)
            item.setData(USER_ROLE + 1, label)
            item.setFlags(item.flags() | ITEM_USER_CHECKABLE)
            item.setCheckState(CHECKED if on else UNCHECKED)
            self.value_list.addItem(item)

    def _set_all(self, checked):
        state = CHECKED if checked else UNCHECKED
        for i in range(self.value_list.count()):
            self.value_list.item(i).setCheckState(state)

    def result_filter(self):
        total = self.value_list.count()
        if total <= 0:
            return None
        checked_keys = []
        checked_labels = []
        for i in range(total):
            item = self.value_list.item(i)
            if item.checkState() == CHECKED:
                checked_keys.append(item.data(USER_ROLE))
                checked_labels.append(item.data(USER_ROLE + 1) or "")
        if not checked_keys:
            return {"keys": [], "labels": []}
        if len(checked_keys) >= total:
            return None
        return {"keys": checked_keys, "labels": checked_labels}


class LayerGroupTable(QFrame):
    def __init__(self, title, geometry_type, field_label=tr("字段"), field_optional=False,
                 icon="●", color="#1565c0", extra_field_label=None, extra_field_key="code_field",
                 field_tip="", extra_field_tip="", hide_primary=False, group_tip="",
                 include_unchecked=False, parent=None):
        super(LayerGroupTable, self).__init__(parent)
        self.setProperty("class", "card")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.geometry_type = geometry_type
        self.field_optional = field_optional
        self.extra_field_key = extra_field_key
        self.field_combo = None
        self.extra_field_combo = None
        self.field_hint = ""
        if field_label and not hide_primary:
            self.field_hint = field_label + (tr("(可选)") if field_optional else "")
        self.extra_field_hint = extra_field_label or ""
        self._wheel_filters = []
        self._row_filters = []
        self._include_unchecked = bool(include_unchecked)
        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(3)
        head = QHBoxLayout()
        head.setSpacing(4)
        icon_lab = QLabel(icon)
        icon_lab.setStyleSheet(
            "font-size: 16px; font-weight: 700; color: %s; min-width: 18px;" % color
        )
        title_lab = QLabel(title)
        title_lab.setStyleSheet(
            "font-size: 14px; font-weight: 700; color: %s;" % color
        )
        title_lab.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        if group_tip:
            icon_lab.setToolTip(group_tip)
            title_lab.setToolTip(group_tip)
        head.addWidget(icon_lab)
        head.addWidget(title_lab)
        head.addStretch()
        add_btn = QPushButton(tr("增加"))
        add_btn.setObjectName("miniBtn")
        add_btn.clicked.connect(lambda: self.add_row(""))
        head.addWidget(add_btn)
        del_btn = QPushButton(tr("删除"))
        del_btn.setObjectName("miniBtn")
        del_btn.clicked.connect(self.remove_selected)
        head.addWidget(del_btn)
        root.addLayout(head)
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels([tr("图层"), tr("分类")])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setMinimumHeight(48)
        self.table.verticalHeader().setDefaultSectionSize(22)
        self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        root.addWidget(self.table, stretch=1)
        field_row = QHBoxLayout()
        field_row.setSpacing(4)
        if not hide_primary:
            self.field_combo = NoWheelComboBox()
            self._init_field_combo(self.field_combo, self.field_hint, field_tip)
            field_row.addWidget(self.field_combo, stretch=1)
        if extra_field_label:
            self.extra_field_combo = NoWheelComboBox()
            self._init_field_combo(self.extra_field_combo, self.extra_field_hint, extra_field_tip)
            field_row.addWidget(self.extra_field_combo, stretch=1)
        root.addLayout(field_row)

    def _init_field_combo(self, combo, hint, tooltip=""):
        combo.setEditable(True)
        combo.setLineEdit(FieldClearLineEdit())
        combo.setMinimumWidth(70)
        try:
            combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        except AttributeError:
            try:
                combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
            except Exception:
                pass  # nosec B110
        combo.setStyleSheet(
            "QComboBox { font-size: 11px; color: #1b1b1b; }"
            "QComboBox QLineEdit { font-size: 11px; color: #1b1b1b; padding: 0 4px; border: none; }"
            "QComboBox QLineEdit QToolButton { border: none; margin: 0; padding: 0; min-width: 14px; max-width: 14px;"
            " min-height: 14px; max-height: 14px; }"
            "QComboBox QAbstractItemView { color: #1b1b1b; background: #ffffff; font-size: 11px; }"
            "QComboBox QAbstractItemView::item { min-height: 18px; padding: 1px 4px; }"
            "QComboBox QAbstractItemView::item:disabled {"
            " color: #0d47a1; background: #c8e6c9; font-weight: 600; }"
        )
        try:
            edit = combo.lineEdit()
            if hasattr(edit, "_hook_clear_buttons"):
                edit._hook_clear_buttons()
            edit.setPlaceholderText(hint)
            pal = edit.palette()
            try:
                pal.setColor(QPalette.ColorRole.PlaceholderText, QColor("#1b5e20"))
            except Exception:
                pal.setColor(QPalette.ColorRole.PlaceholderText, QColor("#1b5e20"))
            edit.setPalette(pal)
        except Exception:
            try:
                combo.setPlaceholderText(hint)
            except Exception:
                pass  # nosec B110
        combo.currentTextChanged.connect(self._check_field_validity)
        if tooltip:
            combo.setToolTip(tooltip)

    def _disable_item_flags(self, item):
        flags = item.flags()
        try:
            flags = flags & ~Qt.ItemFlag.ItemIsEnabled & ~Qt.ItemFlag.ItemIsSelectable
        except TypeError:
            flags = flags & ~Qt.ItemFlag.ItemIsEnabled & ~Qt.ItemFlag.ItemIsSelectable
        item.setFlags(flags)
        item.setEnabled(False)

    def _add_hint_item(self, combo, hint):
        if not hint:
            combo.addItem("")
            return
        combo.addItem(hint)
        model = combo.model()
        item = model.item(0) if model is not None and hasattr(model, "item") else None
        if item is None:
            return
        self._disable_item_flags(item)
        font = item.font()
        font.setBold(True)
        try:
            font.setPointSize(9)
        except Exception:
            pass  # nosec B110
        item.setFont(font)
        item.setForeground(QColor("#0d47a1"))
        item.setBackground(QColor("#c8e6c9"))

    def _combo_value(self, combo, hint=""):
        if combo is None:
            return ""
        text = combo.currentText().strip()
        if not text or text == hint:
            return ""
        return text

    def sizeHint(self):
        return QSize(200, 128)

    def add_row(self, layer_name="", flt=None, layer_id=None):
        r = self.table.rowCount()
        self.table.insertRow(r)
        target = find_layer_by_name(layer_name, layer_id) if (layer_name or layer_id) else None
        if target or not layer_name:
            layer_combo = QgsMapLayerComboBox()
            layer_combo.setAllowEmptyLayer(True)
            if self.geometry_type == "point":
                layer_combo.setFilters(QgsMapLayerProxyModel.PointLayer)
            elif self.geometry_type == "line":
                layer_combo.setFilters(QgsMapLayerProxyModel.LineLayer)
            else:
                layer_combo.setFilters(QgsMapLayerProxyModel.VectorLayer)
            wf = WheelBlockerFilter(self)
            layer_combo.installEventFilter(wf)
            self._wheel_filters.append(wf)
            layer_combo.layerChanged.connect(self._on_layer_changed)
            if target:
                layer_combo.setLayer(target)
            layer_combo.setStyleSheet(
                "QComboBox { color:#1b1b1b; background:#ffffff; }"
                "QComboBox QAbstractItemView { color:#1b1b1b; background:#ffffff;"
                " selection-background-color:#c8e6c9; selection-color:#1b1b1b; }"
            )
            try:
                pal = layer_combo.palette()
                pal.setColor(QPalette.ColorRole.Text, QColor("#1b1b1b"))
                pal.setColor(QPalette.ColorRole.Base, QColor("#ffffff"))
                pal.setColor(QPalette.ColorRole.Window, QColor("#ffffff"))
                pal.setColor(QPalette.ColorRole.WindowText, QColor("#1b1b1b"))
                pal.setColor(QPalette.ColorRole.ButtonText, QColor("#1b1b1b"))
                pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#1b1b1b"))
                layer_combo.setPalette(pal)
            except Exception:
                try:
                    pal = layer_combo.palette()
                    pal.setColor(QPalette.ColorRole.Text, QColor("#1b1b1b"))
                    pal.setColor(QPalette.ColorRole.Base, QColor("#ffffff"))
                    pal.setColor(QPalette.ColorRole.WindowText, QColor("#1b1b1b"))
                    layer_combo.setPalette(pal)
                except Exception:
                    pass  # nosec B110
            self.table.setCellWidget(r, 0, layer_combo)
        else:
            missing_edit = QLineEdit(layer_name)
            missing_edit.setReadOnly(True)
            missing_edit.setStyleSheet("background-color: #ffcccc; color: #c00; border: 1px solid #c00;")
            missing_edit.setToolTip(tr("图层不存在: %s") % layer_name)
            self.table.setCellWidget(r, 0, missing_edit)
        self._row_filters.append(dict(flt) if flt else None)
        self._set_filter_button(r)
        self._refresh_field_combo()

    def _current_layer(self, row):
        w = self.table.cellWidget(row, 0)
        if isinstance(w, QgsMapLayerComboBox):
            return w.currentLayer()
        return None

    def _filter_caption(self, flt):
        if not flt:
            return tr("全部")
        if flt.get("keys") is not None:
            labels = flt.get("labels") or []
            if not labels:
                labels = flt.get("keys") or []
            if not labels:
                return tr("无")
            if len(labels) <= 2:
                return ",".join(attr_key(v) or tr("空") for v in labels)
            return tr("{}类").format(len(labels))
        if flt.get("values") is None:
            return tr("全部")
        values = flt.get("values") or []
        if not values:
            return tr("无")
        if len(values) <= 2:
            return ",".join(attr_key(v) or tr("空") for v in values)
        return tr("{}类").format(len(values))

    def _set_filter_button(self, row):
        btn = QPushButton(self._filter_caption(self._row_filters[row] if row < len(self._row_filters) else None))
        btn.setToolTip(tr("按分类筛选，未勾选的要素不参与"))
        btn.clicked.connect(lambda _=False, r=row: self._edit_filter(r))
        self.table.setCellWidget(row, 1, btn)

    def _edit_filter(self, row):
        layer = self._current_layer(row)
        if layer is None:
            return
        current = self._row_filters[row] if row < len(self._row_filters) else None
        dlg = CategoryFilterDialog(
            layer,
            current_filter=current,
            parent=self.window(),
            include_unchecked=self._include_unchecked,
        )
        accepted = dlg.exec() if hasattr(dlg, "exec") else dlg.exec_()
        if not accepted:
            return
        self._row_filters[row] = dlg.result_filter()
        self._set_filter_button(row)

    def _on_layer_changed(self):
        sender = self.sender()
        for r in range(self.table.rowCount()):
            if self.table.cellWidget(r, 0) is sender:
                self._row_filters[r] = None
                self._set_filter_button(r)
                break
        self._refresh_field_combo()

    def _refresh_one_combo(self, combo, old_text, fields_set, hint=""):
        old_text = (old_text or "").strip()
        if old_text == hint:
            old_text = ""
        combo.blockSignals(True)
        combo.clear()
        self._add_hint_item(combo, hint)
        for name in sorted(fields_set):
            if name and name != hint:
                combo.addItem(name)
        if old_text:
            idx = combo.findText(old_text)
            if idx >= 0:
                combo.setCurrentIndex(idx)
            else:
                combo.setEditText(old_text)
        else:
            combo.setCurrentIndex(-1)
            combo.setEditText("")
        combo.blockSignals(False)

    def _refresh_field_combo(self):
        old = self._combo_value(self.field_combo, self.field_hint)
        extra_old = ""
        if self.extra_field_combo is not None:
            extra_old = self._combo_value(self.extra_field_combo, self.extra_field_hint)
        fields_set = set()
        for r in range(self.table.rowCount()):
            layer = self._current_layer(r)
            if layer and isinstance(layer, QgsVectorLayer):
                for field in layer.fields():
                    fields_set.add(field.name())
        if self.field_combo is not None:
            self._refresh_one_combo(self.field_combo, old, fields_set, self.field_hint)
        if self.extra_field_combo is not None:
            self._refresh_one_combo(self.extra_field_combo, extra_old, fields_set, self.extra_field_hint)
        self._check_field_validity()

    def _mark_field(self, combo, field):
        if not field:
            combo.setStyleSheet("")
            return
        has_valid_layer = False
        all_have_field = True
        for r in range(self.table.rowCount()):
            lyr = self._current_layer(r)
            if lyr and isinstance(lyr, QgsVectorLayer):
                has_valid_layer = True
                if field not in [f.name() for f in lyr.fields()]:
                    all_have_field = False
        if has_valid_layer and not all_have_field:
            combo.setStyleSheet("background-color: #ffcccc; color: #c00; border: 1px solid #c00;")
        else:
            combo.setStyleSheet("")

    def _check_field_validity(self):
        if self.field_combo is not None:
            self._mark_field(self.field_combo, self._combo_value(self.field_combo, self.field_hint))
        if self.extra_field_combo is not None:
            self._mark_field(
                self.extra_field_combo,
                self._combo_value(self.extra_field_combo, self.extra_field_hint),
            )

    def remove_selected(self):
        rows = sorted({x.row() for x in self.table.selectedIndexes()}, reverse=True)
        for r in rows:
            self.table.removeRow(r)
            if r < len(self._row_filters):
                self._row_filters.pop(r)
        self._refresh_field_combo()

    def get_group(self):
        rows = []
        field = self._combo_value(self.field_combo, self.field_hint)
        for r in range(self.table.rowCount()):
            w = self.table.cellWidget(r, 0)
            layer_name = ""
            layer_id = ""
            if isinstance(w, QgsMapLayerComboBox):
                lyr = w.currentLayer()
                layer_name = lyr.name() if lyr else ""
                layer_id = lyr.id() if lyr else ""
            elif isinstance(w, QLineEdit):
                layer_name = w.text().strip()
            if not layer_name:
                continue
            item = {"layer": layer_name}
            if layer_id:
                item["layer_id"] = layer_id
            flt = self._row_filters[r] if r < len(self._row_filters) else None
            if flt:
                item["filter"] = flt
            rows.append(item)
        data = {"rows": rows, "field": field}
        if self.extra_field_combo is not None:
            data[self.extra_field_key] = self._combo_value(self.extra_field_combo, self.extra_field_hint)
        return data

    def set_group(self, group):
        self.table.setRowCount(0)
        self._row_filters = []
        group = group or {}
        for item in group.get("rows") or []:
            self.add_row(item.get("layer", ""), item.get("filter"), item.get("layer_id"))
        if not self.table.rowCount():
            self.add_row("")
        field = (group.get("field") or "").strip()
        self._refresh_field_combo()
        if field and self.field_combo is not None:
            idx = self.field_combo.findText(field)
            if idx >= 0:
                self.field_combo.setCurrentIndex(idx)
            else:
                self.field_combo.setEditText(field)
        if self.extra_field_combo is not None:
            extra = (group.get(self.extra_field_key) or "").strip()
            if extra:
                idx = self.extra_field_combo.findText(extra)
                if idx >= 0:
                    self.extra_field_combo.setCurrentIndex(idx)
                else:
                    self.extra_field_combo.setEditText(extra)
        self._check_field_validity()


class LayerConfigDialog(QDialog):
    def __init__(self, parent=None, data=None):
        super(LayerConfigDialog, self).__init__(parent)
        self.data = data or {}
        self.setWindowTitle(tr("图层配置"))
        self.setStyleSheet("""
            QDialog { background-color: #f1f8f4; color: #2e5c3e; font-size: 12px; }
            QFrame[class="card"] {
                background-color: #e8f5e9; border: 1px solid #a5d6a7; border-radius: 6px;
            }
            QPushButton {
                min-height: 18px; max-height: 22px; padding: 1px 8px; font-size: 11px;
                background-color: #c8e6c9; color: #1b5e20;
                border: 1px solid #81c784; border-radius: 4px;
            }
            QPushButton:hover { background-color: #a5d6a7; }
            QPushButton#miniBtn { min-width: 36px; max-width: 48px; padding: 0 4px; }
            QPushButton[class="primary"] {
                min-height: 24px; max-height: 26px; font-weight: 700;
                background: #43a047; color: #fff; border: 1px solid #2e7d32;
            }
            QComboBox {
                min-height: 22px; padding: 0 2px;
                color: #1b1b1b; background: #ffffff;
                border: 1px solid #a5d6a7; border-radius: 3px;
            }
            QLineEdit {
                min-height: 20px; padding: 1px 4px;
                color: #1b1b1b; background: #ffffff;
                border: 1px solid #a5d6a7; border-radius: 3px;
            }
            QComboBox QLineEdit {
                min-height: 18px; padding: 0 4px;
                margin: 0; border: none; background: #ffffff;
            }
            QComboBox QLineEdit QToolButton {
                border: none; margin: 0; padding: 0;
                min-width: 14px; max-width: 14px;
                min-height: 14px; max-height: 14px;
            }
            QComboBox QAbstractItemView {
                color: #1b1b1b; background: #ffffff;
                selection-background-color: #c8e6c9; selection-color: #1b1b1b;
                outline: 0;
            }
            QgsMapLayerComboBox { color: #1b1b1b; background: #ffffff; }
            QLabel { color: #33691e; }
            QTableWidget { background: #fff; gridline-color: #c8e6c9; font-size: 11px; }
            QHeaderView::section { background: #c8e6c9; padding: 2px; font-size: 11px; }
        """)
        self.setMinimumSize(860, 420)
        self.resize(900, 460)
        root = QVBoxLayout(self)
        grid = QGridLayout()
        grid.setSpacing(6)
        self.occ = LayerGroupTable(
            tr("光交"), "point", tr("字段(不用)"), False, "●", "#1565c0",
            field_tip=tr("只选光交图层。当前功能不读、不写这个字段。"),
        )
        self.splice = LayerGroupTable(
            tr("接头"), "point", tr("CODE读写字段"), False, "◆", "#6a1b9a",
            field_tip=tr("读写。接头命名：写入 CODE。分纤盒命名、光缆命名：读取 CODE。"),
        )
        self.fat = LayerGroupTable(
            tr("分纤盒"), "point", tr("户数读写字段"), False, "■", "#e65100",
            extra_field_label=tr("CODE读写字段"), extra_field_key="code_field",
            field_tip=tr("读写。分纤盒赋值：写入户数。光缆赋值、接头/分纤盒命名：读取户数。"),
            extra_field_tip=tr("读写。分纤盒命名：写入 CODE。光缆命名：读取 CODE。"),
        )
        self.user = LayerGroupTable(
            tr("用户点"), "point", tr("户数读取字段"), False, "○", "#2e7d32",
            field_tip=tr("读取。皮线赋值从这里读用户户数。分纤盒赋值用它核对总户数，不按用户点累加。"),
        )
        self.cable = LayerGroupTable(
            tr("光缆"), "line", tr("户数写入字段"), False, "━", "#c62828",
            extra_field_label=tr("CODE写入字段"), extra_field_key="code_field",
            field_tip=tr("写入。光缆赋值把分纤盒户数写到这里。主干/配线按两端点判定。"),
            extra_field_tip=tr("写入。光缆命名把生成的 CODE 写到这里。"),
            group_tip=tr("主干和配线用同一图层。光交–接头、接头–接头是主干；接头–分纤盒、分纤盒–分纤盒是配线。"),
        )
        self.drop = LayerGroupTable(
            tr("皮线"), "line", tr("户数读写字段"), False, "~", "#00897b",
            field_tip=tr("读写。皮线赋值：写入户数。分纤盒赋值：读取户数。"),
            group_tip=tr("皮线赋值把用户点户数写到这里。分纤盒赋值再把这里的户数加到所出的分纤盒。"),
        )
        grid.addWidget(self.occ, 0, 0)
        grid.addWidget(self.splice, 0, 1)
        grid.addWidget(self.fat, 0, 2)
        grid.addWidget(self.user, 1, 0)
        grid.addWidget(self.cable, 1, 1)
        grid.addWidget(self.drop, 1, 2)
        for i in range(2):
            grid.setRowStretch(i, 1)
        for i in range(3):
            grid.setColumnStretch(i, 1)
        root.addLayout(grid, stretch=1)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cbtn = QPushButton(tr("取消"))
        cbtn.clicked.connect(self.reject)
        obtn = QPushButton(tr("保存"))
        obtn.setProperty("class", "primary")
        obtn.clicked.connect(self.accept)
        btn_row.addWidget(cbtn)
        btn_row.addWidget(obtn)
        root.addLayout(btn_row)
        self.occ.set_group(self.data.get("occ"))
        self.splice.set_group(self.data.get("splice"))
        self.fat.set_group(self.data.get("fat"))
        self.user.set_group(self.data.get("user"))
        self.cable.set_group(self.data.get("cable"))
        self.drop.set_group(self.data.get("drop"))

    def get_data(self):
        return {
            "occ": self.occ.get_group(),
            "splice": self.splice.get_group(),
            "fat": self.fat.get_group(),
            "user": self.user.get_group(),
            "cable": self.cable.get_group(),
            "drop": self.drop.get_group(),
        }


class ParamDialog(QDialog):
    def __init__(
        self,
        parent=None,
        tolerance=0.6,
        clockwise=False,
        start_angle=100,
        prefix_box="PBO",
        prefix_cable="CDI",
        prefix_splice="BPE",
        accumulate=False,
        scheme_id=None,
        action_schemes=None,
    ):
        super(ParamDialog, self).__init__(parent)
        self.setWindowTitle(tr("参数配置"))
        self.setMinimumWidth(420)
        self._narrow_w = 440
        self._wide_w = 980
        self._scheme_tab_index = 1
        extra = """
            QLineEdit {
                min-height: 22px; padding: 2px 6px;
                color: #1b1b1b; background: #ffffff;
                border: 1px solid #a5d6a7; border-radius: 3px;
            }
            QTabWidget::pane { border: 1px solid #a5d6a7; }
            QTabBar::tab {
                min-height: 22px; padding: 4px 10px;
                background: #c8e6c9; color: #1b5e20;
                border: 1px solid #81c784;
            }
            QTabBar::tab:selected { background: #43a047; color: #ffffff; }
        """
        parent_ss = parent.styleSheet() if parent is not None and parent.styleSheet() else ""
        self.setStyleSheet(parent_ss + extra)
        root = QVBoxLayout(self)
        body = QHBoxLayout()
        left = QVBoxLayout()
        tabs = QTabWidget()
        self.tabs = tabs

        snap_page = QWidget()
        snap_root = QVBoxLayout(snap_page)
        hint = QLabel(tr("吸附按米计算。图层会先转到局部米制，工程默认 4326 或其它坐标系都可以。"))
        hint.setWordWrap(True)
        snap_root.addWidget(hint)
        form = QFormLayout()
        self.spin_tol = QDoubleSpinBox()
        self.spin_tol.setDecimals(2)
        self.spin_tol.setRange(0.1, 50.0)
        self.spin_tol.setSingleStep(0.1)
        self.spin_tol.setValue(float(tolerance) if tolerance else 0.6)
        self.spin_tol.setSuffix(tr(" 米"))
        form.addRow(tr("吸附容差"), self.spin_tol)
        dir_row = QHBoxLayout()
        self.dir_cw = QRadioButton(tr("顺时针"))
        self.dir_ccw = QRadioButton(tr("逆时针"))
        self.dir_group = QButtonGroup(self)
        self.dir_group.addButton(self.dir_cw)
        self.dir_group.addButton(self.dir_ccw)
        if clockwise:
            self.dir_cw.setChecked(True)
        else:
            self.dir_ccw.setChecked(True)
        dir_row.addWidget(self.dir_cw)
        dir_row.addWidget(self.dir_ccw)
        dir_row.addStretch(1)
        form.addRow(tr("方向排序"), dir_row)
        self.spin_angle = QDoubleSpinBox()
        self.spin_angle.setDecimals(1)
        self.spin_angle.setRange(0.0, 359.9)
        self.spin_angle.setSingleStep(1.0)
        self.spin_angle.setValue(float(start_angle) if start_angle is not None else 100.0)
        self.spin_angle.setSuffix(" °")
        form.addRow(tr("起始角度"), self.spin_angle)
        snap_root.addLayout(form)
        angle_hint = QLabel(
            tr('0°正北，90°正东，180°正南，270°正西。按出线第一段，不是线末端。方向和起始角只给光交 ODF：第一段主干一样长时才用来打破平局。接头分叉比该方向全部户数和到下一接头的主干长度，不用角度。分纤盒链路比户数和到首盒的线长，也不用角度。赋值和命名方案在「方案」页，六个功能各自一份。')
        )
        angle_hint.setWordWrap(True)
        snap_root.addWidget(angle_hint)
        snap_root.addStretch(1)
        tabs.addTab(snap_page, tr("吸附与排序"))
        tabs.addTab(self._build_scheme_page(action_schemes, scheme_id, accumulate), tr("方案"))

        var_page = QWidget()
        var_root = QVBoxLayout(var_page)
        var_form = QFormLayout()
        self.edit_prefix_splice = QLineEdit()
        self.edit_prefix_splice.setText(str(prefix_splice or "").strip() or "BPE")
        self.edit_prefix_splice.setPlaceholderText("BPE")
        var_form.addRow(tr("接头 CODE 前缀"), self.edit_prefix_splice)
        self.edit_prefix_box = QLineEdit()
        self.edit_prefix_box.setText(str(prefix_box or "").strip() or "PBO")
        self.edit_prefix_box.setPlaceholderText("PBO")
        var_form.addRow(tr("分纤盒 CODE 前缀"), self.edit_prefix_box)
        self.edit_prefix_cable = QLineEdit()
        self.edit_prefix_cable.setText(str(prefix_cable or "").strip() or "CDI")
        self.edit_prefix_cable.setPlaceholderText("CDI")
        var_form.addRow(tr("光缆 CODE 前缀"), self.edit_prefix_cable)
        var_root.addLayout(var_form)
        var_hint = QLabel(tr("接头前缀用于接头 CODE。分纤盒前缀用于分纤盒 CODE。光缆前缀用于主干/配线 CODE。"))
        var_hint.setWordWrap(True)
        var_root.addWidget(var_hint)
        var_root.addStretch(1)
        tabs.addTab(var_page, tr("变量配置"))

        io_page = QWidget()
        io_root = QVBoxLayout(io_page)
        io_hint = QLabel(
            tr('导出当前全部图层配置和参数（含分类筛选、字段、容差、各功能方案、前缀、城市/PM）。导入是全覆盖：立刻替换现有配置并保存，点取消也不会还原。')
        )
        io_hint.setWordWrap(True)
        io_root.addWidget(io_hint)
        io_row = QHBoxLayout()
        self.btn_export = QPushButton(tr("导出…"))
        self.btn_import = QPushButton(tr("导入…"))
        self.btn_import.setProperty("role", "main_layer")
        io_row.addWidget(self.btn_export, 1)
        io_row.addWidget(self.btn_import, 1)
        io_root.addLayout(io_row)
        io_root.addStretch(1)
        tabs.addTab(io_page, tr("导入导出"))
        self.btn_export.clicked.connect(self._export_config)
        self.btn_import.clicked.connect(self._import_config)

        left.addWidget(tabs)
        body.addLayout(left, 0)
        self.preview_pane = SchemePreviewPane(self)
        self.preview_pane.hide()
        body.addWidget(self.preview_pane, 1)
        root.addLayout(body)
        tabs.currentChanged.connect(self._on_param_tab)
        for action, combo in self.combo_action_scheme.items():
            combo.currentIndexChanged.connect(lambda _idx, key=action: self._on_scheme_combo(key))
        self.edit_prefix_splice.textChanged.connect(self.preview_pane.refresh_sim)
        self.edit_prefix_box.textChanged.connect(self.preview_pane.refresh_sim)
        self.edit_prefix_cable.textChanged.connect(self.preview_pane.refresh_sim)
        try:
            buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        except AttributeError:
            buttons = QDialogButtonBox(
                QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
            )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def tolerance(self):
        return float(self.spin_tol.value())

    def clockwise(self):
        return bool(self.dir_cw.isChecked())

    def start_angle(self):
        return float(self.spin_angle.value())

    def prefix_box(self):
        return (self.edit_prefix_box.text() or "").strip() or "PBO"

    def prefix_cable(self):
        return (self.edit_prefix_cable.text() or "").strip() or "CDI"

    def prefix_splice(self):
        return (self.edit_prefix_splice.text() or "").strip() or "BPE"

    def _on_param_tab(self, idx):
        is_scheme = idx == getattr(self, "_scheme_tab_index", 1)
        pane = getattr(self, "preview_pane", None)
        if pane is not None:
            pane.setVisible(is_scheme)
        if is_scheme:
            self.setMinimumWidth(self._wide_w)
            self.resize(max(self.width(), self._wide_w), max(self.height(), 560))
            if pane is not None:
                pane.refresh_sim()
        else:
            self.setMinimumWidth(self._narrow_w)
            self.resize(self._narrow_w, max(360, min(self.height(), 520)))

    def _on_scheme_combo(self, action):
        pane = getattr(self, "preview_pane", None)
        if pane is not None:
            pane.focus_action(action)

    def _build_scheme_page(self, action_schemes, scheme_id, accumulate):
        page = QWidget()
        root = QVBoxLayout(page)
        intro = QLabel(
            tr('组网骨架不变：光交 → 主干 → 接头 → 配线 → 分纤盒 → 入户。这里只改每个功能怎么写编号。六个功能各自独立，互不影响。以后加方案：在 ntal_scheme.py 的 ACTION_SCHEMES 对应功能下追加一行即可。')
        )
        intro.setWordWrap(True)
        intro.setStyleSheet("color: #555;")
        root.addWidget(intro)
        form = QFormLayout()
        self.combo_action_scheme = {}
        picked = migrate_action_schemes(action_schemes, scheme_id, accumulate)
        try:
            tip_role = Qt.ItemDataRole.ToolTipRole
        except AttributeError:
            tip_role = Qt.ToolTipRole
        for action, sid, title, tooltip in iter_action_scheme_rows():
            if action not in self.combo_action_scheme:
                combo = QComboBox()
                combo.setToolTip(tooltip)
                combo.currentIndexChanged.connect(
                    lambda _idx, box=combo: box.setToolTip(box.currentData(tip_role) or "")
                )
                self.combo_action_scheme[action] = combo
                form.addRow(tr(ACTION_TITLES.get(action, action)), combo)
            combo = self.combo_action_scheme[action]
            combo.addItem(title, sid)
            combo.setItemData(combo.count() - 1, tooltip, tip_role)
        for action, combo in self.combo_action_scheme.items():
            idx = combo.findData(picked.get(action, "current"))
            combo.setCurrentIndex(idx if idx >= 0 else 0)
            combo.setToolTip(combo.currentData(tip_role) or combo.toolTip())
        root.addLayout(form)
        root.addStretch(1)
        return page

    def action_schemes(self):
        out = default_action_schemes()
        for action, combo in getattr(self, "combo_action_scheme", {}).items():
            sid = combo.currentData()
            if sid:
                out[action] = sid
        return out

    def scheme_id(self):
        schemes = self.action_schemes()
        return schemes.get("line") or schemes.get("splice_code") or "current"

    def accumulate(self):
        return cable_accumulate(scheme_id=self.scheme_id())

    def _apply_action_schemes(self, params):
        params = params or {}
        picked = migrate_action_schemes(
            params.get("action_schemes"),
            params.get("scheme"),
            params.get("accumulate"),
        )
        for action, combo in getattr(self, "combo_action_scheme", {}).items():
            idx = combo.findData(picked.get(action, "current"))
            combo.setCurrentIndex(idx if idx >= 0 else 0)

    def apply_params(self, params):
        params = params or {}
        try:
            self.spin_tol.setValue(float(params.get("tolerance") or 0.6))
        except (TypeError, ValueError):
            pass  # nosec B110
        if bool(params.get("clockwise")):
            self.dir_cw.setChecked(True)
        else:
            self.dir_ccw.setChecked(True)
        try:
            self.spin_angle.setValue(float(params.get("start_angle") if params.get("start_angle") is not None else 100.0))
        except (TypeError, ValueError):
            pass  # nosec B110
        self._apply_action_schemes(params)
        self.edit_prefix_splice.setText(str(params.get("prefix_splice") or "").strip() or "BPE")
        self.edit_prefix_box.setText(str(params.get("prefix_box") or "").strip() or "PBO")
        self.edit_prefix_cable.setText(str(params.get("prefix_cable") or "").strip() or "CDI")
        pane = getattr(self, "preview_pane", None)
        if pane is not None:
            pane.refresh_sim()

    def _host(self):
        return self.parent()

    def _export_config(self):
        host = self._host()
        if host is not None and hasattr(host, "export_user_config"):
            host.export_user_config(self)

    def _import_config(self):
        host = self._host()
        if host is not None and hasattr(host, "import_user_config"):
            host.import_user_config(self)

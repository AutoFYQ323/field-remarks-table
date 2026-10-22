# -*- coding: utf-8 -*-
"""Self-check: remap renamed layers/fields when opening field remarks."""

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)
from .i18n import localize_button_box, tr

from qgis.core import QgsMapLayer, QgsProject

from .remarks_store import field_is_empty, layer_is_empty, normalize_layer


DELETE_LAYER = "__delete_layer__"
DELETE_FIELD = "__delete_field__"
RESET_DEFAULT = "reset_default"


def project_vector_layers():
    out = []
    try:
        layers = QgsProject.instance().mapLayers().values()
    except Exception:
        return out
    for layer in layers:
        try:
            ok = (
                layer is not None
                and hasattr(layer, "type")
                and layer.type() == QgsMapLayer.VectorLayer
            )
        except Exception:
            ok = False
        if not ok:
            continue  # nosec B112
        out.append(layer)
    out.sort(key=lambda item: item.name())
    return out


def pack_has_config(layers_map):
    if not isinstance(layers_map, dict):
        return False
    for entry in layers_map.values():
        if not layer_is_empty(entry):
            return True
    return False


def matching_layer_count(layers_map, qgis_names):
    count = 0
    for name, entry in (layers_map or {}).items():
        if layer_is_empty(entry):
            continue
        if name in qgis_names:
            count += 1
    return count


def configured_layer_names(layers_map):
    names = []
    for name, entry in (layers_map or {}).items():
        if not layer_is_empty(entry):
            names.append(name)
    return names


def collect_orphans(layers_map, qgis_layers):
    """Return (missing_layer_names, field_orphans {layer: [fields]})."""
    by_name = {}
    for layer in qgis_layers:
        by_name.setdefault(layer.name(), layer)
    missing_layers = []
    field_orphans = {}
    for lname, entry in (layers_map or {}).items():
        entry = normalize_layer(entry)
        if layer_is_empty(entry):
            continue
        layer = by_name.get(lname)
        if layer is None:
            missing_layers.append(lname)
            continue
        existing = set()
        try:
            existing = {f.name() for f in layer.fields()}
        except Exception:
            existing = set()
        missing_fields = []
        for fname, fentry in (entry.get("fields") or {}).items():
            if field_is_empty(fentry):
                continue  # nosec B112
            if fname not in existing:
                missing_fields.append(fname)
        if missing_fields:
            field_orphans[lname] = missing_fields
    return missing_layers, field_orphans


def apply_layer_remap(layers_map, mapping):
    """mapping: old_name -> new_name or DELETE_LAYER."""
    layers = {name: normalize_layer(entry) for name, entry in (layers_map or {}).items()}
    for old_name, target in mapping.items():
        if old_name not in layers:
            continue
        if target is None:
            continue
        entry = layers.pop(old_name)
        if target == DELETE_LAYER or target == "":
            continue
        if target in layers:
            dest = layers[target]
            if not (dest.get("label") or "").strip():
                dest["label"] = entry.get("label") or ""
            if not (dest.get("notes") or "").strip() and entry.get("notes"):
                dest["notes"] = entry.get("notes") or ""
            dest_fields = dest.setdefault("fields", {})
            for fname, fentry in (entry.get("fields") or {}).items():
                if fname not in dest_fields or field_is_empty(dest_fields.get(fname)):
                    dest_fields[fname] = fentry
            layers[target] = dest
        else:
            layers[target] = entry
    return layers


def apply_field_remap(layers_map, mapping):
    """mapping: (layer_name, old_field) -> new_field or DELETE_FIELD."""
    layers = {name: normalize_layer(entry) for name, entry in (layers_map or {}).items()}
    for (lname, old_field), target in mapping.items():
        if lname not in layers:
            continue
        fields = layers[lname].setdefault("fields", {})
        if old_field not in fields:
            continue
        if target is None:
            continue
        entry = fields.pop(old_field)
        if target == DELETE_FIELD or target == "":
            continue
        fields[target] = entry
    return layers


class _MismatchAskDialog(QDialog):
    def __init__(self, title, message, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.choice = None
        root = QVBoxLayout(self)
        lbl = QLabel(message)
        lbl.setWordWrap(True)
        root.addWidget(lbl)
        row = QHBoxLayout()
        btn_match = QPushButton(tr("开始匹配"))
        btn_copy = QPushButton(tr("复制为新项目"))
        btn_back = QPushButton(tr("返回重新选择"))
        btn_match.clicked.connect(lambda: self._pick("match"))
        btn_copy.clicked.connect(lambda: self._pick("copy"))
        btn_back.clicked.connect(self.reject)
        row.addWidget(btn_match)
        row.addWidget(btn_copy)
        row.addWidget(btn_back)
        root.addLayout(row)
        self.resize(440, 160)

    def _pick(self, choice):
        self.choice = choice
        self.accept()


class RemapDialog(QDialog):
    def __init__(self, layers_map, qgis_layers, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("匹配图层和字段"))
        self._layers_map = {
            name: normalize_layer(entry) for name, entry in (layers_map or {}).items()
        }
        self._qgis_layers = list(qgis_layers or [])
        self._layer_combos = {}
        self._field_combos = {}
        self.resize(520, 420)

        root = QVBoxLayout(self)
        tip = QLabel(
            tr("名字相同的已自动对应。下面只列出对不上的项。"
            "选「删除」才会丢掉这一份配置。")
        )
        tip.setWordWrap(True)
        root.addWidget(tip)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        self._form = QVBoxLayout(inner)
        scroll.setWidget(inner)
        root.addWidget(scroll, 1)

        self._build_form()

        self.copied = False
        self._session = None
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        localize_button_box(buttons)
        buttons.button(QDialogButtonBox.Cancel).setText(tr("返回重新选择"))
        btn_copy = buttons.addButton(tr("复制为新项目"), QDialogButtonBox.ActionRole)
        btn_copy.clicked.connect(self._copy_as_new)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def set_session(self, session):
        self._session = session

    def _copy_as_new(self):
        if self._session is None:
            return
        if copy_current_pack_drop_orphans(self._session, self):
            self.copied = True
            self.accept()

    def _qgis_names(self):
        return [layer.name() for layer in self._qgis_layers]

    def _layer_by_name(self, name):
        for layer in self._qgis_layers:
            if layer.name() == name:
                return layer
        return None

    def _build_form(self):
        while self._form.count():
            item = self._form.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._layer_combos = {}
        self._field_combos = {}

        missing_layers, field_orphans = collect_orphans(
            self._layers_map, self._qgis_layers
        )
        qgis_names = self._qgis_names()

        if missing_layers:
            self._form.addWidget(self._section(tr("对不上的图层")))
            for old_name in missing_layers:
                combo = QComboBox()
                combo.addItem(tr("请选择…"), None)
                combo.addItem(tr("删除该图层配置"), DELETE_LAYER)
                for name in qgis_names:
                    combo.addItem(name, name)
                combo.setCurrentIndex(0)
                combo.currentIndexChanged.connect(self._rebuild_fields)
                self._layer_combos[old_name] = combo
                self._form.addLayout(self._labeled_row(tr("图层「%s」→") % old_name, combo))

        self._field_box = QWidget()
        self._field_layout = QVBoxLayout(self._field_box)
        self._field_layout.setContentsMargins(0, 0, 0, 0)
        self._form.addWidget(self._field_box)
        self._fill_field_rows(field_orphans)
        self._form.addStretch(1)

    def _rebuild_fields(self, *_args):
        preview = apply_layer_remap(self._layers_map, self.layer_mapping())
        _missing, field_orphans = collect_orphans(preview, self._qgis_layers)
        self._fill_field_rows(field_orphans)

    def _fill_field_rows(self, field_orphans):
        while self._field_layout.count():
            item = self._field_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
            lay = item.layout()
            if lay is not None:
                while lay.count():
                    child = lay.takeAt(0)
                    w = child.widget()
                    if w is not None:
                        w.deleteLater()
        self._field_combos = {}
        if not field_orphans:
            return
        self._field_layout.addWidget(self._section(tr("对不上的字段")))
        for lname, fields in field_orphans.items():
            layer = self._layer_by_name(lname)
            field_names = []
            if layer is not None:
                try:
                    field_names = [f.name() for f in layer.fields()]
                except Exception:
                    field_names = []
            for old_field in fields:
                combo = QComboBox()
                combo.addItem(tr("请选择…"), None)
                combo.addItem(tr("删除该字段配置"), DELETE_FIELD)
                for fname in field_names:
                    combo.addItem(fname, fname)
                combo.setCurrentIndex(0)
                self._field_combos[(lname, old_field)] = combo
                self._field_layout.addLayout(
                    self._labeled_row("「%s」.%s →" % (lname, old_field), combo)
                )

    @staticmethod
    def _section(text):
        lbl = QLabel(text)
        lbl.setStyleSheet("font-weight: bold; margin-top: 8px;")
        return lbl

    @staticmethod
    def _labeled_row(text, widget):
        row = QHBoxLayout()
        lbl = QLabel(text)
        lbl.setMinimumWidth(180)
        row.addWidget(lbl)
        row.addWidget(widget, 1)
        return row

    def layer_mapping(self):
        out = {}
        for old_name, combo in self._layer_combos.items():
            out[old_name] = combo.currentData()
        return out

    def field_mapping(self):
        out = {}
        for key, combo in self._field_combos.items():
            out[key] = combo.currentData()
        return out

    def result_layers(self):
        layers = apply_layer_remap(self._layers_map, self.layer_mapping())
        return apply_field_remap(layers, self.field_mapping())

    def accept(self):
        pending = list(self._layer_combos.values()) + list(self._field_combos.values())
        for combo in pending:
            if combo.currentData() is None:
                QMessageBox.information(
                    self, tr("匹配"), tr("还有未选择的图层或字段。请选择对应项，或选删除。")
                )
                return
        super().accept()


def _orphan_field_names(field_orphans):
    return [
        "%s.%s" % (lname, fname)
        for lname, fields in (field_orphans or {}).items()
        for fname in fields
    ]


def _orphan_report(layers_map, qgis_layers):
    missing_layers, field_orphans = collect_orphans(layers_map, qgis_layers)
    lines = []
    if missing_layers:
        lines.append(tr("图层：") + "、".join(missing_layers))
    field_names = _orphan_field_names(field_orphans)
    if field_names:
        lines.append(tr("字段：") + "、".join(field_names))
    return "\n".join(lines) if lines else tr("（没有可丢弃的对不上项）")


def _drop_orphans(session):
    layers = dict(session._layers())
    qgis_layers = project_vector_layers()
    missing_layers, field_orphans = collect_orphans(layers, qgis_layers)
    layer_map = {name: DELETE_LAYER for name in missing_layers}
    layers = apply_layer_remap(layers, layer_map)
    field_map = {}
    for lname, fields in (field_orphans or {}).items():
        if lname in missing_layers:
            continue
        for fname in fields:
            field_map[(lname, fname)] = DELETE_FIELD
    layers = apply_field_remap(layers, field_map)
    session.replace_current_layers(layers)


def copy_current_pack_drop_orphans(session, parent=None):
    """Copy the current pack, then drop layers/fields that do not match this project."""
    if getattr(session, "is_placeholder", None) and session.is_placeholder():
        QMessageBox.information(
            parent,
            tr("复制为新项目"),
            tr("「%s」是占位项目，不能删除。") % session.current_name(),
        )
        return False
    report = _orphan_report(session._layers(), project_vector_layers())
    suggested = (session.current_name() or tr("未命名")) + " 2"
    name, ok = QInputDialog.getText(
        parent,
        tr("复制为新项目"),
        tr("以下图层或字段在当前工程对不上，复制后会从新项目中丢弃：")
        + "\n\n"
        + report
        + "\n\n"
        + tr("新项目名称："),
        text=suggested,
    )
    if not ok:
        return False
    name = (name or "").strip()
    if not name:
        return False
    session.duplicate_current(name)
    _drop_orphans(session)
    return True


def run_self_check(session, parent=None):
    """
    If any configured layer name is missing, ask to match, copy, or go back.
    Field-only mismatches go straight to remap, which can also copy the pack.
    Cancel remap resets to the placeholder pack.
    """
    if getattr(session, "is_placeholder", None) and session.is_placeholder():
        return False
    qgis_layers = project_vector_layers()
    layers_map = dict(session._layers())
    if not pack_has_config(layers_map):
        return False

    missing_layers, field_orphans = collect_orphans(layers_map, qgis_layers)
    if not missing_layers and not field_orphans:
        return False

    if missing_layers:
        n = len(missing_layers)
        msg = tr(
            "项目「%s」有 %s 个图层对不上：%s\n"
            "若选错了项目可返回重选。"
        ) % (
            session.current_name(),
            n,
            "、".join(missing_layers),
        )
        ask = _MismatchAskDialog(tr("图层对不上"), msg, parent)
        if ask.exec_() != QDialog.Accepted:
            return RESET_DEFAULT
        if ask.choice == "copy":
            if copy_current_pack_drop_orphans(session, parent):
                return True
            return RESET_DEFAULT
        if ask.choice != "match":
            return RESET_DEFAULT

    remap = RemapDialog(dict(session._layers()), qgis_layers, parent)
    remap.set_session(session)
    if remap.exec_() != QDialog.Accepted:
        return RESET_DEFAULT
    if getattr(remap, "copied", False):
        return True
    session.replace_current_layers(remap.result_layers())
    return True


def _join_names(items, limit=4):
    items = [str(x) for x in items if x]
    if not items:
        return ""
    sep = tr("、")
    if len(items) <= limit:
        return sep.join(items)
    return sep.join(items[:limit]) + tr(" 等%s项") % len(items)


def self_check_summary(session):
    """Short status for the hub footer: current pack vs this QGIS project."""
    if getattr(session, "is_placeholder", None) and session.is_placeholder():
        return tr("「默认（不可修改）」为占位项目，请新建或选择一套配置。")
    layers_map = {}
    try:
        layers_map = dict(session._layers())
    except Exception:
        layers_map = {}
    if not pack_has_config(layers_map):
        return tr("当前项目还没有图层配置。")
    qgis_layers = project_vector_layers()
    if not qgis_layers:
        return tr("当前工程没有矢量图层，无法核对配置。")
    missing_layers, field_orphans = collect_orphans(layers_map, qgis_layers)
    if not missing_layers and not field_orphans:
        return tr("配置的图层、字段全部有效。")
    parts = []
    if missing_layers:
        parts.append(tr("图层对不上：%s") % _join_names(missing_layers))
    field_names = [
        "%s.%s" % (lname, fname)
        for lname, fields in field_orphans.items()
        for fname in fields
    ]
    if field_names:
        parts.append(tr("字段对不上：%s") % _join_names(field_names))
    return tr("；").join(parts) or tr("配置的图层、字段全部有效。")

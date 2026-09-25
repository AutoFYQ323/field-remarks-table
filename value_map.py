# -*- coding: utf-8 -*-
"""Read QGIS Value Map widgets; overlay plugin meaning descriptions."""

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QComboBox, QLineEdit, QStyledItemDelegate
from qgis.core import NULL

from .remarks_store import normalize_meanings
from .value_utils import field_kind, value_text

try:
    from qgis.core import QgsValueMapFieldFormatter
except Exception:
    QgsValueMapFieldFormatter = None

_NULL_SENTINEL = "{2839923C-8B7D-419E-B84B-CA2FE9B80EC7}"
if QgsValueMapFieldFormatter is not None:
    try:
        _NULL_SENTINEL = QgsValueMapFieldFormatter.NULL_VALUE
    except Exception:
        pass

EMPTY_FLAG_ROLE = Qt.UserRole + 21


def value_key(value):
    if value is None or value == NULL:
        return ("null", "")
    text = str(value).strip()
    if text == _NULL_SENTINEL or text.upper() == "NULL":
        return ("null", "")
    if isinstance(value, bool):
        return ("b", "1" if value else "0")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        try:
            num = float(value)
            if num == int(num):
                return ("n", str(int(num)))
            return ("n", str(num))
        except (TypeError, ValueError):
            pass
    if text:
        try:
            num = float(text)
            if num == int(num):
                return ("n", str(int(num)))
        except (TypeError, ValueError):
            pass
    return ("s", text)


def is_null_map_value(value):
    return value_key(value)[0] == "null"


def editor_setup(layer, field_idx):
    if layer is None or field_idx is None or field_idx < 0:
        return None
    try:
        return layer.editorWidgetSetup(int(field_idx))
    except Exception:
        return None


def is_value_map_field(layer, field_idx):
    setup = editor_setup(layer, field_idx)
    if setup is None:
        return False
    try:
        return (setup.type() or "") == "ValueMap"
    except Exception:
        return False


def field_index(layer, field):
    if layer is None:
        return -1
    if isinstance(field, int):
        return field
    try:
        return layer.fields().indexFromName(str(field))
    except Exception:
        return -1


def read_value_map_pairs(layer, field):
    """[(qgis_description, stored_value), ...] in widget order. Empty if not Value Map."""
    idx = field_index(layer, field)
    if idx < 0 or not is_value_map_field(layer, idx):
        return []
    config = {}
    try:
        config = dict(layer.editorWidgetSetup(idx).config() or {})
    except Exception:
        return []
    stored_list = _pick_stored_values(layer, idx, config)
    pairs = []
    seen = set()
    for stored in stored_list:
        if is_null_map_value(stored):
            continue
        key = value_key(stored)
        if key in seen:
            continue
        seen.add(key)
        desc = _represent_desc(layer, idx, config, stored)
        if not desc:
            desc = _fallback_desc(config.get("map"), stored) or (
                "" if stored is None or stored == NULL else str(stored)
            )
        pairs.append((desc, stored))
    return pairs


def value_map_bundle(layer, field):
    """One pass: (meanings, defaults keyed by value_key)."""
    meanings = []
    defaults = {}
    for desc, stored in read_value_map_pairs(layer, field):
        if is_null_map_value(stored):
            continue
        stored_s = "" if stored is None or stored == NULL else str(stored)
        if not stored_s:
            continue
        cn = ("" if desc is None else str(desc)).strip() or stored_s
        meanings.append({"cn": cn, "value": stored_s, "kind": "const"})
        defaults[value_key(stored)] = cn
    return normalize_meanings(meanings), defaults


def layer_value_map_meanings(layer, field):
    """Meanings seeded from the QGIS value map: {cn, value, kind=const}."""
    return value_map_bundle(layer, field)[0]


def merge_value_map_meanings(existing, incoming):
    """Keep our descriptions for the same stored value; append new map items."""
    existing = normalize_meanings(existing)
    incoming = normalize_meanings(incoming)
    out = list(existing)
    seen = set()
    for item in existing:
        if item.get("kind") == "const":
            seen.add(value_key(item.get("value")))
    for item in incoming:
        if item.get("kind") != "const":
            continue
        key = value_key(item.get("value"))
        if key in seen or key[0] == "null":
            continue
        seen.add(key)
        out.append(item)
    return out


def meanings_signature(items):
    return [
        (item.get("kind"), item.get("cn"), item.get("value"))
        for item in normalize_meanings(items)
    ]


def qgis_description_for_value(layer, field, value):
    if is_null_map_value(value):
        return ""
    key = value_key(value)
    for desc, stored in read_value_map_pairs(layer, field):
        if value_key(stored) == key:
            return ("" if desc is None else str(desc)).strip()
    return ""


def value_map_defaults(layer, field):
    """value_key(stored) -> QGIS default description."""
    return value_map_bundle(layer, field)[1]


def is_auto_meaning(meaning, defaults):
    """True if this const meaning still matches the QGIS value-map description."""
    from .remarks_store import normalize_meaning

    item = normalize_meaning(meaning)
    if not item or item.get("kind") != "const" or not defaults:
        return False
    key = value_key(item.get("value"))
    if key not in defaults:
        return False
    return (item.get("cn") or "").strip() == defaults[key]


def _represent_desc(layer, field_idx, config, value):
    if QgsValueMapFieldFormatter is None or is_null_map_value(value):
        return ""
    try:
        text = QgsValueMapFieldFormatter().representValue(
            layer, field_idx, config, None, value
        )
        text = ("" if text is None else str(text)).strip()
    except Exception:
        return ""
    if not text or value_key(text) == value_key(value):
        return ""
    return text


def _count_resolved(layer, field_idx, config, candidates):
    n = 0
    for stored in candidates or []:
        if is_null_map_value(stored):
            continue
        if _represent_desc(layer, field_idx, config, stored):
            n += 1
    return n


def _pick_stored_values(layer, field_idx, config):
    raw = config.get("map") if isinstance(config, dict) else None
    if isinstance(raw, (list, tuple)):
        out = []
        for item in raw:
            pair = _pair_from_item(item)
            if pair is not None:
                out.append(pair[1])
        return out
    if isinstance(raw, dict):
        keys = list(raw.keys())
        vals = list(raw.values())
        if _count_resolved(layer, field_idx, config, vals) > _count_resolved(
            layer, field_idx, config, keys
        ):
            return vals
        return keys
    return []


def _fallback_desc(raw, stored):
    key = value_key(stored)
    if isinstance(raw, (list, tuple)):
        for item in raw:
            pair = _pair_from_item(item)
            if pair is None:
                continue
            desc, val = pair
            if value_key(val) == key:
                return ("" if desc is None else str(desc)).strip()
            if value_key(desc) == key:
                return ("" if val is None else str(val)).strip()
    if isinstance(raw, dict):
        for left, right in raw.items():
            if value_key(left) == key:
                return ("" if right is None else str(right)).strip()
            if value_key(right) == key:
                return ("" if left is None else str(left)).strip()
    return ""


def _pair_from_item(item):
    if isinstance(item, dict):
        if len(item) == 1:
            desc, stored = next(iter(item.items()))
            return ("" if desc is None else str(desc), stored)
        desc = item.get("description", item.get("label", item.get("key")))
        stored = item.get("value", item.get("code"))
        if desc is None and stored is None:
            return None
        return ("" if desc is None else str(desc), stored)
    if isinstance(item, (list, tuple)) and len(item) >= 2:
        return ("" if item[0] is None else str(item[0]), item[1])
    return None


class ValueMapDelegate(QStyledItemDelegate):
    """Combo for Value Map columns; other columns keep the default line edit."""

    def __init__(self, table_model, parent=None):
        super().__init__(parent)
        self._model = table_model

    def createEditor(self, parent, option, index):
        items = self._choices(index)
        if not items:
            if self._uses_text_editor(index):
                editor = QLineEdit(parent)
                editor.setFrame(False)
                return editor
            return super().createEditor(parent, option, index)
        combo = QComboBox(parent)
        combo.setEditable(False)
        combo.addItem("(空)")
        combo.setItemData(0, True, EMPTY_FLAG_ROLE)
        for _label, stored, display in items:
            combo.addItem(display or _label, stored)
            combo.setItemData(combo.count() - 1, "值：%s" % stored, Qt.ToolTipRole)
        return combo

    def _uses_text_editor(self, index):
        """Qt's default spin/date editors cut decimals to 2 and drop seconds."""
        layer = self._model.layer() if self._model is not None else None
        field_idx = self._field_idx(index)
        if layer is None or field_idx < 0:
            return False
        try:
            kind = field_kind(layer.fields().at(field_idx))
        except Exception:
            return False
        return kind in ("int", "real", "date", "datetime", "time")

    def setEditorData(self, editor, index):
        if isinstance(editor, QLineEdit) and self._uses_text_editor(index):
            editor.setText(value_text(index.data(Qt.EditRole)))
            editor.selectAll()
            return
        if not isinstance(editor, QComboBox):
            return super().setEditorData(editor, index)
        raw = index.data(Qt.EditRole)
        if raw is None or raw == NULL:
            editor.setCurrentIndex(0)
            return
        key = value_key(raw)
        for i in range(editor.count()):
            if editor.itemData(i, EMPTY_FLAG_ROLE):
                continue
            if value_key(editor.itemData(i)) == key:
                editor.setCurrentIndex(i)
                return
        editor.addItem(str(raw), raw)
        editor.setCurrentIndex(editor.count() - 1)

    def setModelData(self, editor, model, index):
        if isinstance(editor, QLineEdit) and self._uses_text_editor(index):
            model.setData(index, editor.text(), Qt.EditRole)
            return
        if not isinstance(editor, QComboBox):
            return super().setModelData(editor, model, index)
        row = editor.currentIndex()
        if row < 0 or editor.itemData(row, EMPTY_FLAG_ROLE):
            model.setData(index, NULL, Qt.EditRole)
            return
        stored = editor.itemData(row)
        layer = self._model.layer() if self._model is not None else None
        if layer is not None:
            try:
                from .classify_assign import coerce_value_for_field

                field_idx = self._field_idx(index)
                if field_idx >= 0:
                    stored = coerce_value_for_field(layer.fields().at(field_idx), stored)
            except Exception:
                pass
        model.setData(index, stored, Qt.EditRole)

    def _choices(self, index):
        if self._model is None or not index.isValid():
            return None
        getter = getattr(self._model, "value_map_choices", None)
        if not callable(getter):
            return None
        field_idx = self._field_idx(index)
        if field_idx < 0:
            return None
        try:
            name = self._model.fields_meta()[index.column()][1]
        except Exception:
            name = ""
        return getter(field_idx, name)

    def _field_idx(self, index):
        try:
            return int(self._model.fields_meta()[index.column()][0])
        except Exception:
            return -1

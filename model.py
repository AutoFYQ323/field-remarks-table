# -*- coding: utf-8 -*-
"""Lazy feature table model for large vector layers."""

from collections import OrderedDict
import re

from qgis.PyQt.QtCore import Qt, QAbstractTableModel, QModelIndex, pyqtSignal
from qgis.PyQt.QtGui import QColor, QBrush, QFont
from qgis.core import (
    QgsApplication,
    QgsFeatureRequest,
    QgsFields,
    QgsMapLayer,
    NULL,
)

from .value_utils import coerce_for_field, field_kind, temporal_text, value_text

_NUM_RE = re.compile(r"^[\s]*[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?[\s]*$")


def _field_origin(name):
    value = getattr(QgsFields, "Origin" + name, None)
    if value is None:
        try:
            from qgis.core import Qgis

            value = getattr(Qgis.FieldOrigin, name)
        except Exception:
            value = None
    return value


_ORIGIN_EXPRESSION = _field_origin("Expression")
_ORIGIN_JOIN = _field_origin("Join")

# Providers that run a text ILIKE filter in the data source instead of in QGIS.
_SQL_PROVIDERS = {"ogr", "postgres", "spatialite", "mssql", "oracle", "hana"}


def try_parse_number(value):
    """Parse numeric value from int/float or numeric text. Return float or None."""
    if value is None or value == NULL:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "")
    if not text or not _NUM_RE.match(text):
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _same_value(current, new_val):
    if current is None or current == NULL or new_val is None or new_val == NULL:
        return False
    try:
        return type(current) is type(new_val) and current == new_val
    except Exception:
        return False


class FeatureCache:
    """LRU cache of QgsFeature by fid."""

    def __init__(self, maxsize=800):
        self.maxsize = maxsize
        self._cache = OrderedDict()

    def clear(self):
        self._cache.clear()

    def get(self, fid):
        feat = self._cache.get(fid)
        if feat is not None:
            self._cache.move_to_end(fid)
        return feat

    def put(self, fid, feature):
        self._cache[fid] = feature
        self._cache.move_to_end(fid)
        while len(self._cache) > self.maxsize:
            self._cache.popitem(last=False)

    def pop(self, fid):
        self._cache.pop(fid, None)

    def prefetch(self, layer, fids, field_indices=None):
        missing = [fid for fid in fids if fid not in self._cache]
        if not missing:
            return
        req = QgsFeatureRequest().setFilterFids(missing)
        req.setFlags(QgsFeatureRequest.NoGeometry)
        if field_indices:
            req.setSubsetOfAttributes(list(field_indices))
        for feat in layer.getFeatures(req):
            self.put(feat.id(), feat)


class FeatureTableModel(QAbstractTableModel):
    """
    Row = feature, Column = field (by field names).
    Header shows remark label (else QGIS alias) + original name.
    Sorting treats numeric text as numbers.
    """

    FID_ROLE = Qt.UserRole + 1

    # message shown when a cell edit cannot be stored in the field
    editRejected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._layer = None
        self._fids = []
        self._fid_row = {}
        # (index, name, typeName, alias)
        self._fields = []
        self._field_names = []
        # field_name -> {label, hint, presets}
        self._field_remarks = {}
        self._pack_variables = []
        self._cache = FeatureCache()
        self._sort_field = None
        self._sort_asc = True
        self._text_filter = ""
        self._filter_field = None  # None = all fields
        self._category_filter_expr = ""
        # Scope: "all" | "selected" | "canvas"
        self._scope_mode = "all"
        self._canvas_rect = None  # QgsRectangle in layer CRS when scope=canvas
        # QGIS-like NULL: dim italic text + light background (not solid black "NULL")
        self._null_brush = QBrush(QColor(242, 242, 242))
        self._null_fg = QBrush(QColor(150, 150, 150))
        self._null_font = QFont()
        self._null_font.setItalic(True)
        self._vm_by_idx = None
        self._vm_label_by_idx = None
        self._show_note = True
        self._modified_brush = QBrush(QColor(255, 240, 190))
        # per display column: editable by config/origin, right aligned
        self._col_editable = None
        self._col_align = None
        # fid -> set(field_idx) or None (= whole row, added feature); None = rebuild
        self._modified = None

    def layer(self):
        return self._layer

    def set_layer(self, layer, rebuild=True):
        self.beginResetModel()
        self._layer = layer
        self._cache.clear()
        self._fids = []
        self._fid_row = {}
        self._fields = []
        self._field_names = []
        self._field_remarks = {}
        self._pack_variables = []
        self._category_filter_expr = ""
        self._canvas_rect = None
        self.invalidate_value_maps()
        self.invalidate_column_cache()
        self.invalidate_modified()
        if layer is not None and layer.isValid() and layer.type() == QgsMapLayer.VectorLayer:
            fields = layer.fields()
            for i in range(fields.count()):
                f = fields.at(i)
                alias = (f.alias() or "").strip()
                self._fields.append((i, f.name(), f.typeName(), alias))
                self._field_names.append(f.name())
            if rebuild:
                self._rebuild_fids_unlocked()
        self.endResetModel()

    def refresh_fields(self, names):
        """Re-read field indexes after the layer's fields changed; rows rebuilt by the next reload."""
        layer = self._layer
        if layer is None:
            return
        fields = layer.fields()
        full = {}
        for i in range(fields.count()):
            f = fields.at(i)
            full[f.name()] = (i, f.name(), f.typeName(), (f.alias() or "").strip())
        new_fields = [full[n] for n in names if n in full] or list(full.values())
        self.beginResetModel()
        self._fields = new_fields
        self._field_names = [n for _, n, _, _ in new_fields]
        if self._sort_field and self._sort_field not in full:
            self._sort_field = None
            self._sort_asc = True
        if self._filter_field and self._filter_field not in full:
            self._filter_field = None
        self._cache.clear()
        self.invalidate_value_maps()
        self.invalidate_column_cache()
        self.invalidate_modified()
        self.endResetModel()

    def fields_match_layer(self):
        """True when every column still points at the same field index/name."""
        layer = self._layer
        if layer is None:
            return True
        try:
            fields = layer.fields()
        except RuntimeError:
            return True
        for idx, name, _t, _a in self._fields:
            if idx >= fields.count() or fields.at(idx).name() != name:
                return False
        return True

    def invalidate_column_cache(self):
        self._col_editable = None
        self._col_align = None

    def _build_column_cache(self):
        layer = self._layer
        editable = []
        align = []
        if layer is None:
            self._col_editable, self._col_align = editable, align
            return
        fields = layer.fields()
        try:
            form = layer.editFormConfig()
        except Exception:
            form = None
        for field_idx, _name, _typename, _alias in self._fields:
            ok = True
            if form is not None:
                try:
                    ok = not bool(form.readOnly(field_idx))
                except Exception:
                    ok = True
            if ok:
                ok = self._origin_editable(layer, fields, field_idx)
            editable.append(ok)
            kind = "other"
            try:
                kind = field_kind(fields.at(field_idx))
            except Exception:
                pass
            align.append(kind in ("int", "real"))
        self._col_editable, self._col_align = editable, align

    @staticmethod
    def _origin_editable(layer, fields, field_idx):
        """Expression (virtual) fields never; joined fields only when the join is editable."""
        try:
            origin = fields.fieldOrigin(field_idx)
        except Exception:
            return True
        if origin == _ORIGIN_EXPRESSION:
            return False
        if origin == _ORIGIN_JOIN:
            try:
                res = layer.joinBuffer().joinForFieldIndex(field_idx, fields)
                info = res[0] if isinstance(res, tuple) else res
                return bool(info is not None and info.isEditable())
            except Exception:
                return False
        return True

    def invalidate_modified(self):
        self._modified = None

    def _modified_map(self):
        if self._modified is not None:
            return self._modified
        out = {}
        layer = self._layer
        buf = None
        try:
            if layer is not None and layer.isEditable():
                buf = layer.editBuffer()
        except Exception:
            buf = None
        if buf is not None:
            try:
                for fid, attrs in (buf.changedAttributeValues() or {}).items():
                    out[int(fid)] = set(int(i) for i in (attrs or {}).keys())
            except Exception:
                pass
            try:
                for fid in (buf.addedFeatures() or {}).keys():
                    out[int(fid)] = None
            except Exception:
                pass
            try:
                for fid in (buf.changedGeometries() or {}).keys():
                    out.setdefault(int(fid), set())
            except Exception:
                pass
        self._modified = out
        return out

    def modified_fids(self):
        return list(self._modified_map().keys())

    def _cell_modified(self, fid, field_idx):
        mod = self._modified_map()
        if fid not in mod:
            return False
        cols = mod[fid]
        return cols is None or field_idx in cols

    def field_names(self):
        return list(self._field_names)

    def fields_meta(self):
        return list(self._fields)

    def set_pack_variables(self, items):
        from .remarks_store import normalize_variables

        self._pack_variables = normalize_variables(items)
        self.invalidate_value_maps()

    def pack_variables(self):
        return list(getattr(self, "_pack_variables", None) or [])

    def set_field_remarks(self, remarks_by_field):
        """Overlay plugin remarks (label/hint/presets) without reloading rows."""
        self._field_remarks = dict(remarks_by_field or {})
        self.invalidate_value_maps()
        self._refresh_field_aliases()
        cols = self.columnCount()
        rows = self.rowCount()
        if cols > 0:
            self.headerDataChanged.emit(Qt.Horizontal, 0, cols - 1)
        if rows > 0 and cols > 0:
            self.dataChanged.emit(
                self.index(0, 0),
                self.index(rows - 1, cols - 1),
                [Qt.DisplayRole, Qt.ToolTipRole],
            )

    def _refresh_field_aliases(self):
        layer = self._layer
        if layer is None or not self._fields:
            return
        fields = layer.fields()
        updated = []
        for _i, name, _typename, _alias in self._fields:
            idx = fields.indexFromName(name)
            if idx < 0:
                continue
            f = fields.at(idx)
            updated.append((idx, f.name(), f.typeName(), (f.alias() or "").strip()))
        if updated:
            self._fields = updated
            self._field_names = [n for _, n, _, _ in updated]

    def field_remarks(self, field_name):
        return dict(self._field_remarks.get(field_name) or {})

    def field_meanings(self, field_name):
        from .remarks_store import normalize_meanings

        entry = self._field_remarks.get(field_name) or {}
        meanings = entry.get("meanings")
        if meanings is None:
            meanings = entry.get("presets") or []
        return normalize_meanings(meanings)

    def field_presets(self, field_name):
        from .remarks_store import meaning_write_value

        return [meaning_write_value(m) for m in self.field_meanings(field_name)]

    def header_label(self, field_name):
        for _i, name, _t, alias in self._fields:
            if name == field_name:
                return self._format_header(name, alias, self._remark_label(name))
        return field_name

    def _remark_label(self, field_name):
        entry = self._field_remarks.get(field_name) or {}
        return (entry.get("label") or "").strip()

    def _remark_hint(self, field_name):
        entry = self._field_remarks.get(field_name) or {}
        return (entry.get("hint") or "").strip()

    def _remark_notes(self, field_name):
        entry = self._field_remarks.get(field_name) or {}
        return entry.get("notes") or ""

    @staticmethod
    def _format_header(name, alias, remark_label=""):
        display = (remark_label or "").strip() or (alias or "").strip()
        if display and display != name:
            return f"{display}\n{name}"
        return name

    def set_display_fields(self, names):
        if self._layer is None:
            return
        fields = self._layer.fields()
        full = []
        for i in range(fields.count()):
            f = fields.at(i)
            full.append((i, f.name(), f.typeName(), (f.alias() or "").strip()))
        name_to_meta = {n: meta for meta in full for n in (meta[1],)}
        new_fields = [name_to_meta[n] for n in names if n in name_to_meta]
        if not new_fields:
            new_fields = full
        self.beginResetModel()
        self._fields = new_fields
        self._field_names = [n for _, n, _, _ in new_fields]
        self._cache.clear()
        self.invalidate_column_cache()
        self.endResetModel()

    def set_text_filter(self, text, field_name=None, reload_now=True):
        self._text_filter = (text or "").strip()
        self._filter_field = field_name or None
        if reload_now:
            self.reload()

    def set_filter_field(self, field_name, reload_now=True):
        self._filter_field = field_name or None
        if reload_now:
            self.reload()

    def set_category_filter(self, expr, reload_now=True):
        self._category_filter_expr = (expr or "").strip()
        if reload_now:
            self.reload()

    def category_filter(self):
        return self._category_filter_expr

    def set_scope_mode(self, mode, canvas_rect=None, reload_now=True):
        """
        mode: 'all' | 'selected' | 'canvas' | 'modified'
        canvas_rect: QgsRectangle in layer CRS (required for canvas mode).
        """
        self._scope_mode = mode or "all"
        self._canvas_rect = canvas_rect
        if reload_now:
            self.reload()

    def canvas_rect(self):
        return self._canvas_rect if self._scope_mode == "canvas" else None

    def set_selected_only(self, enabled):
        # backward-compatible helper
        self.set_scope_mode("selected" if enabled else "all", None)

    def scope_mode(self):
        return self._scope_mode

    def text_filter(self):
        return self._text_filter

    def filter_field(self):
        return self._filter_field

    def selected_only(self):
        return self._scope_mode == "selected"

    def sort_field(self):
        return self._sort_field

    def sort_ascending(self):
        return self._sort_asc

    def reload(self):
        self.beginResetModel()
        self._cache.clear()
        self._rebuild_fids_unlocked()
        self.endResetModel()

    def _rebuild_fids_unlocked(self):
        self._fids = []
        self._fid_row = {}
        layer = self._layer
        if layer is None:
            return

        req = QgsFeatureRequest()
        cat_expr = (self._category_filter_expr or "").strip()
        need_attrs = bool(self._text_filter) or bool(self._sort_field) or bool(cat_expr)
        # The extent filter is a bounding-box test done by the provider; rows never need geometry.
        req.setFlags(QgsFeatureRequest.NoGeometry)
        if not need_attrs:
            req.setNoAttributes()

        if self._scope_mode == "selected":
            selected = layer.selectedFeatureIds()
            if not selected:
                return
            req.setFilterFids(selected)
        elif self._scope_mode == "canvas":
            rect = self._canvas_rect
            if rect is None or rect.isEmpty():
                return
            req.setFilterRect(rect)
        elif self._scope_mode == "modified":
            changed = self.modified_fids()
            if not changed:
                return
            req.setFilterFids(changed)

        text = self._text_filter.lower()
        filter_idx = None
        if self._filter_field:
            filter_idx = layer.fields().indexFromName(self._filter_field)
            if filter_idx < 0:
                filter_idx = None

        exprs = [cat_expr] if cat_expr else []
        pre = self._provider_prefilter(layer, text, filter_idx)
        if pre:
            exprs.append(pre)
        if exprs:
            req.setFilterExpression(" AND ".join("(%s)" % e for e in exprs))

        pairs = []  # (fid, sort_value) or just collect fids
        sort_idx = -1
        if self._sort_field:
            sort_idx = layer.fields().indexFromName(self._sort_field)

        # Limit fetched attributes when the needed columns are known.
        # Category expressions may reference extra fields — don't subset then.
        if not cat_expr and need_attrs:
            subset = []
            if text and filter_idx is not None:
                subset.append(filter_idx)
            elif text:
                subset = None
            if subset is not None and sort_idx >= 0 and sort_idx not in subset:
                subset.append(sort_idx)
            if subset is not None:
                req.setSubsetOfAttributes(subset)

        for feat in layer.getFeatures(req):
            if text:
                if filter_idx is not None:
                    v = feat.attribute(filter_idx)
                    if not self._filter_hit(v, text, filter_idx):
                        continue
                else:
                    matched = False
                    attrs = feat.attributes()
                    for i, v in enumerate(attrs):
                        if self._filter_hit(v, text, i):
                            matched = True
                            break
                    if not matched:
                        continue

            if self._sort_field and sort_idx >= 0:
                pairs.append((feat.id(), feat.attribute(sort_idx)))
            else:
                self._fids.append(feat.id())

        if self._sort_field and sort_idx >= 0:
            self._fids = [fid for fid, _ in self._sort_pairs_smart(pairs, self._sort_asc)]
        self._fid_row = {fid: i for i, fid in enumerate(self._fids)}

    def _provider_prefilter(self, layer, text, filter_idx):
        """
        ILIKE on one text field so the data source narrows rows first.
        Only when it can never drop a row the Python match would keep:
        text field, no value-map/remark labels, no LIKE wildcards, no case folding
        beyond ASCII (SQLite ILIKE only folds ASCII).
        """
        if not text or filter_idx is None:
            return ""
        try:
            provider = layer.providerType()
        except Exception:
            provider = ""
        if provider not in _SQL_PROVIDERS:
            return ""
        if any(ch in text for ch in "%_\\"):
            return ""
        if any(ord(ch) > 127 and ch.lower() != ch.upper() for ch in text):
            return ""
        try:
            field = layer.fields().at(filter_idx)
        except Exception:
            return ""
        if field_kind(field) != "string":
            return ""
        if self._show_note:
            self._build_value_maps()
            if self._vm_label_by_idx.get(filter_idx):
                return ""
        name = field.name().replace('"', '""')
        return "\"%s\" ILIKE '%%%s%%'" % (name, text.replace("'", "''"))

    @staticmethod
    def _sort_pairs_smart(pairs, ascending):
        """Sort (fid, value) with numeric-text awareness; NULL always last."""

        def key(item):
            value = item[1]
            if value is None or value == NULL:
                return (2, 0.0, "")
            temporal = temporal_text(value)
            if temporal is not None:
                return (1, 0.0, temporal)
            num = try_parse_number(value)
            if num is not None:
                return (0, num, "")
            return (1, 0.0, str(value).lower())

        ordered = sorted(pairs, key=key, reverse=not ascending)
        # Keep NULL at end even when reverse
        nums_texts = [p for p in ordered if p[1] is not None and p[1] != NULL]
        nulls = [p for p in ordered if p[1] is None or p[1] == NULL]
        return nums_texts + nulls

    def sort_by_field(self, field_name, ascending=True):
        self._sort_field = field_name
        self._sort_asc = ascending
        self.reload()

    def clear_sort(self):
        self._sort_field = None
        self._sort_asc = True
        self.reload()

    def rowCount(self, parent=QModelIndex()):
        if parent.isValid():
            return 0
        return len(self._fids)

    def columnCount(self, parent=QModelIndex()):
        if parent.isValid():
            return 0
        return len(self._fields)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and 0 <= section < len(self._fields):
            idx, name, typename, alias = self._fields[section]
            remark_label = self._remark_label(name)
            if role == Qt.DisplayRole:
                label = self._format_header(name, alias, remark_label)
                if self._sort_field == name:
                    arrow = " ▲" if self._sort_asc else " ▼"
                    # put arrow on first line
                    parts = label.split("\n", 1)
                    parts[0] = parts[0] + arrow
                    return "\n".join(parts)
                return label
            if role == Qt.ToolTipRole:
                from .remarks_store import format_hover_text

                display = remark_label or ((alias or "").strip())
                return format_hover_text(
                    name,
                    display,
                    self.field_meanings(name),
                    self._remark_notes(name),
                    variables=getattr(self, "_pack_variables", None) or [],
                )
        if orientation == Qt.Vertical:
            if 0 <= section < len(self._fids):
                if role == Qt.DisplayRole:
                    return str(section + 1)  # 1-based row number
                if role == Qt.ToolTipRole:
                    return f"序号 {section + 1}\nFID {self._fids[section]}\n双击缩放到该要素"
        return None

    def flags(self, index):
        if not index.isValid():
            return Qt.NoItemFlags
        flags = Qt.ItemIsEnabled | Qt.ItemIsSelectable
        layer = self._layer
        if layer is not None and layer.isEditable():
            if self._col_editable is None:
                self._build_column_cache()
            col = index.column()
            if 0 <= col < len(self._col_editable) and self._col_editable[col]:
                flags |= Qt.ItemIsEditable
        return flags

    def column_editable(self, col):
        if self._col_editable is None:
            self._build_column_cache()
        return 0 <= col < len(self._col_editable) and self._col_editable[col]

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or self._layer is None:
            return None
        row, col = index.row(), index.column()
        if row < 0 or row >= len(self._fids) or col < 0 or col >= len(self._fields):
            return None

        fid = self._fids[row]
        field_idx = self._fields[col][0]

        if role == self.FID_ROLE:
            return fid

        feat = self._feature(fid)
        if feat is None:
            return None

        value = self._attr(feat, field_idx)

        is_null = value is None or value == NULL
        if role == Qt.DisplayRole:
            if self._show_note and not is_null:
                mapped = self.value_map_label(field_idx, value)
                if mapped:
                    return mapped
            return self._display_value(value)
        if role == Qt.EditRole:
            if is_null:
                return None
            return value
        if role == Qt.ToolTipRole:
            modified = self._cell_modified(fid, field_idx)
            tip = None
            if is_null:
                tip = "(空 / NULL)"
            else:
                raw = value_text(value)
                if self._show_note:
                    mapped = self.value_map_label(field_idx, value)
                    if mapped and mapped != raw:
                        tip = "%s\n%s" % (mapped, raw)
                if tip is None and len(raw) > 40:
                    tip = raw
            if modified:
                return (tip + "\n" if tip else "") + "（已修改，未保存）"
            return tip
        if role == Qt.BackgroundRole:
            if self._cell_modified(fid, field_idx):
                return self._modified_brush
            if is_null:
                return self._null_brush
        if role == Qt.ForegroundRole:
            if is_null:
                return self._null_fg
        if role == Qt.FontRole:
            if is_null:
                return self._null_font
        if role == Qt.TextAlignmentRole:
            if self._col_align is None:
                self._build_column_cache()
            if 0 <= col < len(self._col_align) and self._col_align[col]:
                return int(Qt.AlignRight | Qt.AlignVCenter)
        return None

    def setData(self, index, value, role=Qt.EditRole):
        if role != Qt.EditRole or not index.isValid() or self._layer is None:
            return False
        if not self._layer.isEditable():
            return False
        row, col = index.row(), index.column()
        fid = self._fids[row]
        field_idx = self._fields[col][0]
        field = self._layer.fields().at(field_idx)
        status, new_val, note = coerce_for_field(field, value)
        if status == "invalid":
            self.editRejected.emit(
                "「%s」写不进字段「%s」：%s" % (value_text(value), field.name(), note)
            )
            return False
        if status == "rounded":
            self.editRejected.emit(
                "字段「%s」是整数，%s 已四舍五入为 %s" % (field.name(), value_text(value), new_val)
            )
        elif status == "toolong":
            self.editRejected.emit(
                "字段「%s」%s，保存时数据源可能截断或拒绝" % (field.name(), note)
            )
        current = self._attr(self._cache.get(fid), field_idx)
        if _same_value(current, new_val):
            return True
        self._layer.beginEditCommand("编辑属性")
        ok = self._layer.changeAttributeValue(fid, field_idx, new_val)
        if ok:
            self._layer.endEditCommand()
        else:
            self._layer.destroyEditCommand()
        if ok:
            feat = self._cache.get(fid)
            if feat is not None:
                try:
                    feat.setAttribute(field_idx, new_val)
                except Exception:
                    self._cache.pop(fid)
            self.dataChanged.emit(
                index,
                index,
                [
                    Qt.DisplayRole,
                    Qt.EditRole,
                    Qt.BackgroundRole,
                    Qt.ForegroundRole,
                    Qt.FontRole,
                ],
            )
        return ok

    @staticmethod
    def _attr(feat, field_idx):
        if feat is None:
            return None
        try:
            if not feat.isValid():
                return None
        except Exception:
            return None
        try:
            attrs = feat.attributes()
        except Exception:
            attrs = None
        if attrs is not None and isinstance(field_idx, int):
            if field_idx < 0 or field_idx >= len(attrs):
                return None
            return attrs[field_idx]
        try:
            return feat.attribute(field_idx)
        except Exception:
            return None

    def _feature(self, fid):
        feat = self._cache.get(fid)
        if feat is not None:
            try:
                if feat.isValid():
                    return feat
            except Exception:
                pass
            self._cache.pop(fid)
        try:
            row = self._fid_row.get(fid)
            if row is None:
                return None
        except Exception:
            return None
        start = max(0, row - 40)
        end = min(len(self._fids), row + 60)
        field_indices = [meta[0] for meta in self._fields]
        self._cache.prefetch(self._layer, self._fids[start:end], field_indices)
        feat = self._cache.get(fid)
        try:
            if feat is not None and feat.isValid():
                return feat
        except Exception:
            return None
        return None

    @staticmethod
    def _display_value(value):
        if value is None or value == NULL:
            try:
                text = QgsApplication.nullRepresentation()
                if text is not None and str(text) != "":
                    return str(text)
            except Exception:
                pass
            return "NULL"
        text = value_text(value)
        if len(text) > 200:
            return text[:197] + "..."
        return text

    def fid_at(self, row):
        if 0 <= row < len(self._fids):
            return self._fids[row]
        return None

    def row_for_fid(self, fid):
        row = self._fid_row.get(fid)
        return row if row is not None else -1

    def fids(self):
        return list(self._fids)

    def invalidate_fid(self, fid):
        self._cache.pop(fid)

    def column_values(self, field_name):
        """
        Raw attribute values for all currently filtered rows, in table order.
        Efficient batch fetch — not limited to on-screen rows.
        """
        layer = self._layer
        if layer is None or not self._fids:
            return []
        field_idx = layer.fields().indexFromName(field_name)
        if field_idx < 0:
            return []
        values_by_fid = self._fetch_attributes(self._fids, [field_idx])
        return [values_by_fid.get(fid, {}).get(field_idx, NULL) for fid in self._fids]

    def _fetch_attributes(self, fids, field_indices, chunk=2500):
        """fid -> {field_idx: value} for the given fids (no geometry)."""
        layer = self._layer
        out = {}
        if layer is None or not fids or not field_indices:
            return out
        for i in range(0, len(fids), chunk):
            batch = fids[i : i + chunk]
            req = (
                QgsFeatureRequest()
                .setFilterFids(batch)
                .setFlags(QgsFeatureRequest.NoGeometry)
                .setSubsetOfAttributes(list(field_indices))
            )
            for feat in layer.getFeatures(req):
                out[feat.id()] = {
                    idx: self._attr(feat, idx) for idx in field_indices
                }
        return out

    def widest_plain_texts(self, max_chars=48, sample_limit=2500):
        """
        Longest single-line cell text per visible field, for column sizing.
        Skips NULL, newlines, and values longer than max_chars.
        Samples evenly when the filtered row count exceeds sample_limit.
        """
        names = list(self._field_names)
        best = {n: "" for n in names}
        if self._layer is None or not self._fids or not self._fields:
            return best
        fids = self._fids
        if len(fids) > sample_limit:
            step = max(1, len(fids) // sample_limit)
            fids = fids[::step][:sample_limit]
        indices = [meta[0] for meta in self._fields]
        fetched = self._fetch_attributes(fids, indices)
        best_len = {n: 0 for n in names}
        for attrs in fetched.values():
            for name, idx in zip(names, indices):
                val = attrs.get(idx, NULL)
                if val is None or val == NULL:
                    continue
                text = value_text(val)
                if "\n" in text or "\r" in text:
                    continue
                nchars = len(text)
                if nchars > max_chars or nchars <= best_len[name]:
                    continue
                best_len[name] = nchars
                best[name] = text
        return best

    def refresh_cached_attributes(self):
        """Drop cached features and repaint; keep current fid/filter/sort."""
        self._cache.clear()
        rows = self.rowCount()
        cols = self.columnCount()
        if rows <= 0 or cols <= 0:
            return
        self.dataChanged.emit(
            self.index(0, 0),
            self.index(rows - 1, cols - 1),
            [
                Qt.DisplayRole,
                Qt.EditRole,
                Qt.BackgroundRole,
                Qt.ForegroundRole,
                Qt.FontRole,
                Qt.ToolTipRole,
            ],
        )

    def invalidate_value_maps(self):
        self._vm_by_idx = None
        self._vm_label_by_idx = None

    def show_note(self):
        return bool(self._show_note)

    def set_show_note(self, enabled):
        enabled = bool(enabled)
        if self._show_note == enabled:
            return
        self._show_note = enabled
        rows = self.rowCount()
        cols = self.columnCount()
        if rows > 0 and cols > 0:
            self.dataChanged.emit(
                self.index(0, 0),
                self.index(rows - 1, cols - 1),
                [Qt.DisplayRole, Qt.ToolTipRole],
            )

    def _build_value_maps(self):
        if self._vm_by_idx is not None:
            return
        from .value_map import is_value_map_field, read_value_map_pairs, value_key
        from .remarks_store import normalize_meanings

        self._vm_by_idx = {}
        self._vm_label_by_idx = {}
        layer = self._layer
        if layer is None:
            return
        try:
            fields = layer.fields()
            count = fields.count()
        except Exception:
            return
        for i in range(count):
            pairs = []
            if is_value_map_field(layer, i):
                pairs = read_value_map_pairs(layer, i)
                self._vm_by_idx[i] = pairs
            labels = {}
            for desc, stored in pairs:
                key = value_key(stored)
                if key[0] == "null":
                    continue
                text = ("" if desc is None else str(desc)).strip()
                labels[key] = text or str(stored)
            name = fields.at(i).name()
            entry = self._field_remarks.get(name) or {}
            meanings = entry.get("meanings")
            if meanings is None:
                meanings = entry.get("presets") or []
            for item in normalize_meanings(meanings):
                if item.get("kind") != "const":
                    continue
                cn = (item.get("cn") or "").strip()
                if not cn:
                    continue
                from .remarks_store import resolve_var_template

                raw_value = item.get("value") or ""
                resolved, missing = resolve_var_template(
                    raw_value, getattr(self, "_pack_variables", None) or []
                )
                if missing:
                    continue
                labels[value_key(resolved)] = cn
            if labels:
                self._vm_label_by_idx[i] = labels

    def value_map_choices(self, field_idx, field_name=None):
        self._build_value_maps()
        pairs = self._vm_by_idx.get(field_idx)
        if not pairs:
            return None
        from .value_map import value_key

        labels = self._vm_label_by_idx.get(field_idx) or {}
        items = []
        for desc, stored in pairs:
            key = value_key(stored)
            if key[0] == "null":
                continue
            raw = "" if stored is None or stored == NULL else str(stored)
            if not raw:
                continue
            if self._show_note:
                label = labels.get(key) or ("" if desc is None else str(desc)).strip() or raw
            else:
                label = raw
            items.append((label, stored, label))
        return items or None

    def value_map_label(self, field_idx, value):
        if value is None or value == NULL:
            return ""
        self._build_value_maps()
        labels = self._vm_label_by_idx.get(field_idx)
        if not labels:
            return ""
        from .value_map import value_key

        return labels.get(value_key(value)) or ""

    def _filter_hit(self, value, text, field_idx):
        if value is None or value == NULL:
            return False
        hay = value_text(value).lower()
        if text in hay:
            return True
        if not self._show_note:
            return False
        mapped = self.value_map_label(field_idx, value)
        return bool(mapped) and text in mapped.lower()

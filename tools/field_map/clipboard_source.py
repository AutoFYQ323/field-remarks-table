# -*- coding: utf-8 -*-
"""Load features from the QGIS "Copy Features" clipboard text.

Ported from the Symbolic Style Replacement plugin. The system clipboard
carries text only (a WKT table, a WKB table, GeoJSON, or bare WKT lines).
Field values stay text; the user supplies the source CRS.
"""

from ...i18n import tr
from ...qt_compat import make_qgs_field, run_exec

_WKT_TYPES = (
    "GEOMETRYCOLLECTION",
    "MULTILINESTRING",
    "MULTIPOLYGON",
    "MULTIPOINT",
    "CIRCULARSTRING",
    "COMPOUNDCURVE",
    "CURVEPOLYGON",
    "MULTICURVE",
    "MULTISURFACE",
    "LINESTRING",
    "POLYGON",
    "POINT",
)


def split_tsv_rows(text):
    """Split QGIS clipboard TSV. Quoted fields may contain tabs, newlines, and doubled quotes."""
    text = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    # Strip the UTF-8 BOM. Written as an escape sequence on purpose: a literal
    # BOM char is invisible and easy to lose when the file is edited, which
    # once turned this check into startswith("") and ate the first character
    # of every clipboard text (breaking wkt_geom headers).
    if text.startswith("\ufeff"):  # escape sequence, not the raw BOM char
        text = text[1:]

    rows = []
    row = []
    cell = []
    quoted = False
    i = 0
    length = len(text)
    while i < length:
        char = text[i]
        if quoted:
            if char == '"':
                if i + 1 < length and text[i + 1] == '"':
                    cell.append('"')
                    i += 2
                    continue
                quoted = False
                i += 1
                continue
            cell.append(char)
            i += 1
            continue
        if char == '"' and not cell:
            quoted = True
            i += 1
            continue
        if char == "\t":
            row.append("".join(cell))
            cell = []
            i += 1
            continue
        if char == "\n":
            row.append("".join(cell))
            cell = []
            if row != [""]:
                rows.append(row)
            row = []
            i += 1
            continue
        cell.append(char)
        i += 1

    if cell or row:
        row.append("".join(cell))
        if row != [""]:
            rows.append(row)
    return rows


def looks_like_wkt(text):
    sample = (text or "").strip().upper()
    if not sample:
        return False
    for name in _WKT_TYPES:
        if not sample.startswith(name):
            continue
        rest = sample[len(name):]
        if rest.startswith((" ", "(", "Z", "M")):
            return True
    return False


def _clean_unique_names(names):
    used = set()
    result = []
    for index, name in enumerate(names):
        base = (name or "").strip() or tr("字段") + str(index + 1)
        candidate = base
        suffix = 2
        while candidate in used:
            candidate = "{}_{}".format(base, suffix)
            suffix += 1
        used.add(candidate)
        result.append(candidate)
    return result


def parse_table_clipboard(text):
    """
    Parse WKT/WKB clipboard text without QGIS.

    Returns (spec, error). spec rows hold raw geometry text and attribute strings.
    GeoJSON is detected here and parsed later with QGIS.
    """
    stripped = (text or "").strip()
    if not stripped:
        return None, tr("剪贴板是空的。请先在源工程里选中要素，再使用「复制要素」。")

    if stripped.startswith("{") or stripped.startswith("["):
        return {"kind": "geojson", "text": text}, ""

    rows = split_tsv_rows(text)
    if not rows:
        return None, tr("剪贴板是空的。请先在源工程里选中要素，再使用「复制要素」。")

    header = rows[0]
    geom_header = (header[0] or "").strip().lower()
    if geom_header in ("wkt_geom", "wkb_geom"):
        field_names = _clean_unique_names(header[1:])
        data_rows = []
        width = len(field_names)
        for raw in rows[1:]:
            if not any((cell or "").strip() for cell in raw):
                continue  # nosec B112
            geom_text = raw[0] if raw else ""
            attrs = list(raw[1:1 + width])
            if len(attrs) < width:
                attrs.extend([""] * (width - len(attrs)))
            data_rows.append({"geom": geom_text, "attrs": attrs})
        if not data_rows:
            return None, tr("剪贴板里没有要素。请先在源工程里选中要复制的要素。")
        return {
            "kind": "wkb" if geom_header == "wkb_geom" else "wkt",
            "field_names": field_names,
            "rows": data_rows,
        }, ""

    if "\t" in (text or ""):
        return None, (
            tr("剪贴板里只有属性、没有几何。")
            + tr("请把 QGIS「设置 → 选项 → 数据源 → 复制要素为」保持为默认的带 WKT 属性，然后重新复制。")
        )

    lines = [line for line in stripped.splitlines() if line.strip()]
    if lines and all(looks_like_wkt(line) for line in lines):
        return {
            "kind": "wkt",
            "field_names": [],
            "rows": [{"geom": line.strip(), "attrs": []} for line in lines],
        }, ""

    return None, (
        tr("剪贴板里不是 QGIS「复制要素」的内容。")
        + tr("请在源工程选中要素后使用「编辑 → 复制要素」，")
        + tr("并保持「复制要素为」为默认的带 WKT 属性。")
    )


def read_clipboard_text():
    from qgis.PyQt.QtWidgets import QApplication

    return QApplication.clipboard().text() or ""


def ask_clipboard_crs(parent):
    """Ask for the source CRS. Returns a CRS, or None if cancelled."""
    from qgis.PyQt.QtWidgets import QDialog, QDialogButtonBox, QLabel, QVBoxLayout
    from qgis.core import QgsCoordinateReferenceSystem, QgsProject
    from qgis.gui import QgsProjectionSelectionWidget

    dialog = QDialog(parent)
    dialog.setWindowTitle(tr("从剪贴板加载"))
    layout = QVBoxLayout(dialog)
    label = QLabel(
        tr("剪贴板不含坐标系。请指定源图层的坐标系。") + "\n"
        + tr("默认使用当前工程坐标系；与源图层不一致时改成源图层的坐标系，否则自动重投影会偏。")
    )
    label.setWordWrap(True)
    layout.addWidget(label)
    widget = QgsProjectionSelectionWidget()
    crs = QgsProject.instance().crs()
    if not crs.isValid():
        crs = QgsCoordinateReferenceSystem("EPSG:4326")
    widget.setCrs(crs)
    layout.addWidget(widget)
    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
    ok_button = buttons.button(QDialogButtonBox.StandardButton.Ok)
    cancel_button = buttons.button(QDialogButtonBox.StandardButton.Cancel)
    if ok_button is not None:
        ok_button.setText(tr("加载"))
    if cancel_button is not None:
        cancel_button.setText(tr("取消"))
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)
    if run_exec(dialog) != QDialog.DialogCode.Accepted:
        return None
    return widget.crs()


def _null_geometry_tokens():
    tokens = {"", "NULL"}
    try:
        from qgis.core import QgsApplication

        token = QgsApplication.nullRepresentation() or ""
        if token:
            tokens.add(token)
    except Exception:
        pass  # nosec B110
    return tokens


def _geometry_from_text(kind, text, blank_tokens):
    from qgis.core import QgsGeometry
    from qgis.PyQt.QtCore import QByteArray

    raw = (text or "").strip()
    if raw in blank_tokens:
        return None, "empty"
    if kind == "wkb":
        cleaned = "".join(raw.split())
        try:
            blob = bytes.fromhex(cleaned)
        except ValueError:
            return None, "invalid"
        geom = QgsGeometry()
        loaded = False
        try:
            loaded = bool(geom.fromWkb(blob))
        except Exception:
            loaded = False
        if not loaded or geom.isEmpty():
            try:
                geom = QgsGeometry()
                geom.fromWkb(QByteArray(blob))
            except Exception:
                geom = QgsGeometry()
        if geom is None or geom.isEmpty():
            return None, "invalid"
        return geom, ""

    geom = QgsGeometry.fromWkt(raw)
    if geom is None or geom.isEmpty():
        return None, "invalid"
    return geom, ""


def _attr_value(value):
    from qgis.PyQt.QtCore import NULL, QVariant

    if value is None or value is NULL:
        return NULL
    if isinstance(value, QVariant):
        if value.isNull():
            return NULL
        value = value.value()
        if value is None or value is NULL:
            return NULL
    text = str(value)
    if text == "":
        return NULL
    return text


def _parse_geojson(text):
    from qgis.core import QgsFields, QgsJsonUtils

    fields = QgsFields()
    try:
        fields = QgsJsonUtils.stringToFields(text) or QgsFields()
    except Exception:
        fields = QgsFields()

    features = None
    try:
        features = QgsJsonUtils.stringToFeatureList(text, fields, None)
    except TypeError:
        try:
            features = QgsJsonUtils.stringToFeatureList(text, fields)
        except Exception:
            features = None
    except Exception:
        features = None

    if not features:
        try:
            from qgis.core import QgsOgrUtils

            try:
                features = QgsOgrUtils.stringToFeatureList(text, fields, None)
            except TypeError:
                features = QgsOgrUtils.stringToFeatureList(text, fields)
        except Exception:
            features = None

    if not features:
        return None, tr("无法读取剪贴板中的 GeoJSON。请改用默认的「带 WKT 的属性」再复制一次。")

    names = [field.name() for field in fields] if fields is not None else []
    if not names:
        first_fields = features[0].fields()
        if first_fields is not None:
            names = [field.name() for field in first_fields]
    names = _clean_unique_names(names)
    rows = []
    for feature in features:
        attrs = feature.attributes()
        values = []
        for index in range(len(names)):
            values.append(attrs[index] if index < len(attrs) else None)
        rows.append({"geometry": feature.geometry(), "attrs": values})
    return {"kind": "geometry", "field_names": names, "rows": rows}, ""


def _row_geometry(spec, row, blank_tokens):
    kind = spec["kind"]
    if kind == "geometry":
        geom = row.get("geometry")
        if geom is None or geom.isEmpty():
            return None, "empty"
        from qgis.core import QgsGeometry

        return QgsGeometry(geom), ""
    return _geometry_from_text(kind, row.get("geom"), blank_tokens)


def _family_of(geom):
    from qgis.core import QgsWkbTypes

    family = QgsWkbTypes.geometryType(geom.wkbType())
    if family in (QgsWkbTypes.GeometryType.UnknownGeometry, QgsWkbTypes.GeometryType.NullGeometry):
        return None
    return family


def _target_wkb(geoms):
    from qgis.core import QgsWkbTypes

    kind = _family_of(geoms[0])
    base = {
        QgsWkbTypes.GeometryType.PointGeometry: QgsWkbTypes.Type.Point,
        QgsWkbTypes.GeometryType.LineGeometry: QgsWkbTypes.Type.LineString,
        QgsWkbTypes.GeometryType.PolygonGeometry: QgsWkbTypes.Type.Polygon,
    }.get(kind)
    if base is None:
        return None
    if any(QgsWkbTypes.isMultiType(geom.wkbType()) for geom in geoms):
        base = QgsWkbTypes.multiType(base)
    has_z = any(QgsWkbTypes.hasZ(geom.wkbType()) for geom in geoms)
    has_m = any(QgsWkbTypes.hasM(geom.wkbType()) for geom in geoms)
    if has_z or has_m:
        try:
            return QgsWkbTypes.zmType(base, has_z, has_m)
        except Exception:
            return base
    return base


def _fit_geometry(geom, target_wkb):
    from qgis.core import QgsGeometry, QgsWkbTypes

    fitted = QgsGeometry(geom)
    if fitted.isEmpty():
        return None
    if QgsWkbTypes.isMultiType(target_wkb) and not fitted.isMultipart():
        fitted.convertToMultiType()
    if QgsWkbTypes.hasZ(target_wkb) and not QgsWkbTypes.hasZ(fitted.wkbType()):
        try:
            cloned = fitted.constGet().clone()
            cloned.addZValue(0.0)
            fitted = QgsGeometry(cloned)
        except Exception:
            pass  # nosec B110
    if QgsWkbTypes.hasM(target_wkb) and not QgsWkbTypes.hasM(fitted.wkbType()):
        try:
            cloned = fitted.constGet().clone()
            cloned.addMValue(0.0)
            fitted = QgsGeometry(cloned)
        except Exception:
            pass  # nosec B110
    if fitted.isEmpty():
        return None
    return fitted


def _unique_layer_name(base):
    from qgis.core import QgsProject

    names = {layer.name() for layer in QgsProject.instance().mapLayers().values()}
    if base not in names:
        return base
    index = 2
    while "{} {}".format(base, index) in names:
        index += 1
    return "{} {}".format(base, index)


def _no_geometry_message(skipped_empty, skipped_invalid):
    if skipped_invalid and not skipped_empty:
        return tr("剪贴板里的几何无法识别。请用「编辑 → 复制要素」重新复制。")
    return (
        tr("剪贴板里没有有效几何。")
        + tr("请确认复制的是带几何的要素，且「复制要素为」不是「仅属性」。")
    )


def prepare_clipboard_features(text):
    """
    Parse clipboard text into geometries.

    Returns (prepared, error). prepared is consumed by build_clipboard_layer.
    """
    spec, error = parse_table_clipboard(text)
    if error:
        return None, error
    if spec["kind"] == "geojson":
        spec, error = _parse_geojson(spec["text"])
        if error:
            return None, error

    blank_tokens = _null_geometry_tokens()
    grouped = {}
    skipped_empty = 0
    skipped_invalid = 0
    for row in spec["rows"]:
        geom, status = _row_geometry(spec, row, blank_tokens)
        if geom is None:
            if status == "empty":
                skipped_empty += 1
            else:
                skipped_invalid += 1
            continue  # nosec B112
        family = _family_of(geom)
        if family is None:
            skipped_invalid += 1
            continue  # nosec B112
        grouped.setdefault(family, []).append((geom, row.get("attrs") or []))

    if not grouped:
        return None, _no_geometry_message(skipped_empty, skipped_invalid)

    family = max(grouped, key=lambda key: len(grouped[key]))
    chosen = grouped[family]
    skipped_other = sum(len(items) for key, items in grouped.items() if key != family)
    return {
        "field_names": spec.get("field_names") or [],
        "records": chosen,
        "skipped_empty": skipped_empty,
        "skipped_invalid": skipped_invalid,
        "skipped_other": skipped_other,
    }, ""


def _make_qgs_field(name, qtype, type_name, length, precision):
    """Create QgsField on both Qt 5 and Qt 6."""
    return make_qgs_field(name, qtype, type_name, length, precision)


def build_clipboard_layer(prepared, crs):
    """
    Create an in-memory layer. Does not add it to the project.

    Returns (layer or None, info or None, error).
    """
    from qgis.PyQt.QtCore import QVariant
    from qgis.core import QgsFeature, QgsGeometry, QgsVectorLayer, QgsWkbTypes

    records = prepared["records"]
    target_wkb = _target_wkb([geom for geom, _attrs in records])
    if target_wkb is None:
        return None, None, tr("剪贴板里的几何类型无法建成图层。")

    type_name = QgsWkbTypes.displayString(target_wkb)
    authid = ""
    if crs is not None and crs.isValid():
        authid = crs.authid() or ""
    uri = "{}?crs={}".format(type_name, authid) if authid else type_name
    layer_name = _unique_layer_name(tr("剪贴板要素"))
    layer = QgsVectorLayer(uri, layer_name, "memory")
    if (not layer.isValid()) and ("Z" in type_name or "M" in type_name):
        flat = QgsWkbTypes.flatType(target_wkb) if hasattr(QgsWkbTypes, "flatType") else None
        if flat is not None:
            type_name = QgsWkbTypes.displayString(flat)
            target_wkb = flat
            uri = "{}?crs={}".format(type_name, authid) if authid else type_name
            layer = QgsVectorLayer(uri, layer_name, "memory")
    if not layer.isValid():
        return None, None, tr("无法创建临时图层。")
    if crs is not None and crs.isValid():
        layer.setCrs(crs)

    provider = layer.dataProvider()
    qfields = [
        _make_qgs_field(name, QVariant.String, "String", 0, 0)
        for name in prepared["field_names"]
    ]
    if qfields:
        provider.addAttributes(qfields)
        layer.updateFields()

    skipped_invalid = prepared["skipped_invalid"]
    features = []
    for geom, attrs in records:
        fitted = _fit_geometry(geom, target_wkb)
        if fitted is None or fitted.isEmpty():
            skipped_invalid += 1
            continue  # nosec B112
        feature = QgsFeature(layer.fields())
        feature.setGeometry(QgsGeometry(fitted))
        values = []
        for index in range(len(prepared["field_names"])):
            raw = attrs[index] if index < len(attrs) else None
            values.append(_attr_value(raw))
        if values:
            feature.setAttributes(values)
        features.append(feature)

    if not features:
        return None, None, _no_geometry_message(prepared["skipped_empty"], skipped_invalid)

    ok, added = provider.addFeatures(features)
    if not ok:
        return None, None, tr("写入临时图层失败。")
    layer.updateExtents()
    layer.triggerRepaint()

    crs_text = ""
    if crs is not None and crs.isValid():
        crs_text = crs.authid() or crs.description() or tr("已指定")
    info = {
        "added": len(added) if added else len(features),
        "skipped_empty": prepared["skipped_empty"],
        "skipped_invalid": skipped_invalid,
        "skipped_other": prepared["skipped_other"],
        "crs_text": crs_text,
    }
    return layer, info, ""

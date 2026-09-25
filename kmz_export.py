# -*- coding: utf-8 -*-
"""Export vector layer features to KMZ (KML in zip), EPSG:4326 by default."""

import os
import zipfile
from html import escape

from qgis.core import (
    NULL,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsFeatureRequest,
    QgsGeometry,
    QgsProject,
    QgsWkbTypes,
)

from .value_map import value_key
from .value_utils import value_text


def _xml_text(value):
    if value is None or value == NULL:
        return ""
    return escape(value_text(value))


def _point_xml(pt):
    return f"<Point><coordinates>{pt.x()},{pt.y()},0</coordinates></Point>"


def _multi(chunks):
    chunks = [c for c in chunks if c]
    if not chunks:
        return None
    if len(chunks) == 1:
        return chunks[0]
    return "<MultiGeometry>" + "".join(chunks) + "</MultiGeometry>"


def _geometry_to_kml(geom):
    """Return KML geometry XML fragment (already in dest CRS), or None."""
    if geom is None or geom.isEmpty():
        return None

    wkb = geom.type()

    if wkb == QgsWkbTypes.PointGeometry:
        if geom.isMultipart():
            return _multi(_point_xml(p) for p in geom.asMultiPoint())
        return _point_xml(geom.asPoint())

    if wkb == QgsWkbTypes.LineGeometry:

        def line_xml(line):
            if not line:
                return ""
            coords = " ".join(f"{pt.x()},{pt.y()},0" for pt in line)
            return f"<LineString><coordinates>{coords}</coordinates></LineString>"

        if geom.isMultipart():
            return _multi(line_xml(line) for line in geom.asMultiPolyline())
        return _multi([line_xml(geom.asPolyline())])

    if wkb == QgsWkbTypes.PolygonGeometry:

        def poly_xml(polygon):
            if not polygon:
                return ""
            outer = polygon[0]
            outer_c = " ".join(f"{pt.x()},{pt.y()},0" for pt in outer)
            holes = []
            for ring in polygon[1:]:
                hc = " ".join(f"{pt.x()},{pt.y()},0" for pt in ring)
                holes.append(
                    "<innerBoundaryIs><LinearRing>"
                    f"<coordinates>{hc}</coordinates>"
                    "</LinearRing></innerBoundaryIs>"
                )
            return (
                "<Polygon>"
                "<outerBoundaryIs><LinearRing>"
                f"<coordinates>{outer_c}</coordinates>"
                "</LinearRing></outerBoundaryIs>"
                + "".join(holes)
                + "</Polygon>"
            )

        if geom.isMultipart():
            return _multi(poly_xml(poly) for poly in geom.asMultiPolygon())
        return _multi([poly_xml(geom.asPolygon())])

    c = geom.centroid().asPoint()
    return _point_xml(c)


def _kml_color(qcolor, alpha=None):
    """QColor -> KML aabbggrr."""
    a = qcolor.alpha() if alpha is None else alpha
    return "%02x%02x%02x%02x" % (a, qcolor.blue(), qcolor.green(), qcolor.red())


def _symbol_style_xml(symbol, geom_type):
    """KML <Style> body for a QGIS symbol, or None."""
    if symbol is None:
        return None
    try:
        color = symbol.color()
    except Exception:
        return None
    if not color.isValid():
        return None
    if geom_type == QgsWkbTypes.PointGeometry:
        return (
            f"<IconStyle><color>{_kml_color(color, 255)}</color><scale>1.0</scale>"
            "<Icon><href>https://maps.google.com/mapfiles/kml/shapes/placemark_circle.png</href></Icon>"
            "</IconStyle>"
        )
    if geom_type == QgsWkbTypes.LineGeometry:
        width = 2.0
        try:
            width = max(1.0, min(10.0, float(symbol.width()) * 3.78))
        except Exception:
            pass
        return f"<LineStyle><color>{_kml_color(color)}</color><width>{width:.1f}</width></LineStyle>"
    if geom_type == QgsWkbTypes.PolygonGeometry:
        stroke = None
        try:
            sl = symbol.symbolLayer(0)
            if sl is not None and hasattr(sl, "strokeColor"):
                stroke = sl.strokeColor()
        except Exception:
            stroke = None
        if stroke is None or not stroke.isValid():
            stroke = color.darker(140)
        return (
            f"<LineStyle><color>{_kml_color(stroke)}</color><width>1.5</width></LineStyle>"
            f"<PolyStyle><color>{_kml_color(color)}</color></PolyStyle>"
        )
    return None


class _StyleResolver:
    """Map a feature to a KML style id using a single/categorized/graduated renderer."""

    def __init__(self, layer):
        self.kind = None
        self.field_idx = -1
        self.geom_type = layer.geometryType()
        self._styles = {}
        self._style_order = []
        self._single = None
        self._by_key = {}
        self._default = None
        self._ranges = []
        renderer = layer.renderer()
        if renderer is None:
            return
        rtype = renderer.type()
        try:
            if rtype == "singleSymbol":
                self._single = self._style_id(renderer.symbol())
                self.kind = "single" if self._single else None
            elif rtype == "categorizedSymbol":
                idx = layer.fields().lookupField(renderer.classAttribute())
                if idx < 0:
                    return
                self.field_idx = idx
                for cat in renderer.categories():
                    if not cat.renderState():
                        continue
                    sid = self._style_id(cat.symbol())
                    val = cat.value()
                    if isinstance(val, (list, tuple)):
                        for v in val:
                            self._by_key.setdefault(value_key(v), sid)
                    elif val is None or val == NULL or (isinstance(val, str) and val == ""):
                        self._default = sid
                    else:
                        self._by_key.setdefault(value_key(val), sid)
                self.kind = "categorized"
            elif rtype == "graduatedSymbol":
                idx = layer.fields().lookupField(renderer.classAttribute())
                if idx < 0:
                    return
                self.field_idx = idx
                for rng in renderer.ranges():
                    if not rng.renderState():
                        continue
                    self._ranges.append(
                        (rng.lowerValue(), rng.upperValue(), self._style_id(rng.symbol()))
                    )
                self.kind = "graduated"
        except Exception:
            self.kind = None

    def _style_id(self, symbol):
        body = _symbol_style_xml(symbol, self.geom_type)
        if not body:
            return None
        sid = self._styles.get(body)
        if sid is None:
            sid = "s%d" % len(self._styles)
            self._styles[body] = sid
            self._style_order.append((sid, body))
        return sid

    def style_for(self, feat):
        if self.kind == "single":
            return self._single
        if self.kind is None or self.field_idx < 0:
            return None
        val = feat.attribute(self.field_idx)
        if self.kind == "categorized":
            if val is None or val == NULL:
                return self._default
            return self._by_key.get(value_key(val), self._default)
        if self.kind == "graduated":
            try:
                num = float(val)
            except (TypeError, ValueError):
                return None
            for lo, hi, sid in self._ranges:
                if lo <= num <= hi:
                    return sid
        return None

    def styles_xml(self):
        return "".join(f'<Style id="{sid}">{body}</Style>\n' for sid, body in self._style_order)


def export_layer_to_kmz(
    layer,
    output_path,
    title_field,
    description_fields,
    dest_crs_authid="EPSG:4326",
    fids=None,
    use_layer_style=False,
):
    """
    Export features of layer to KMZ: all features, or only ``fids`` when given.
    Skip features with null/empty geometry.
    Returns (written_count, skipped_no_geom).
    """
    dest_crs = QgsCoordinateReferenceSystem(dest_crs_authid)
    if not dest_crs.isValid():
        dest_crs = QgsCoordinateReferenceSystem("EPSG:4326")

    xform = None
    if layer.crs().isValid() and layer.crs() != dest_crs:
        xform = QgsCoordinateTransform(layer.crs(), dest_crs, QgsProject.instance())
        if not xform.isValid():
            raise RuntimeError("无法从 %s 转换到 %s" % (layer.crs().authid(), dest_crs.authid()))

    fields = layer.fields()
    title_idx = fields.indexFromName(title_field) if title_field else -1
    desc_indices = []
    for name in description_fields or []:
        i = fields.indexFromName(name)
        if i >= 0:
            desc_indices.append((name, i))

    styles = _StyleResolver(layer) if use_layer_style else None

    subset = []
    if title_idx >= 0:
        subset.append(title_idx)
    for _name, idx in desc_indices:
        if idx not in subset:
            subset.append(idx)
    if styles is not None and styles.field_idx >= 0 and styles.field_idx not in subset:
        subset.append(styles.field_idx)
    req = QgsFeatureRequest().setSubsetOfAttributes(subset)
    if fids is not None:
        req.setFilterFids(list(fids))

    placemarks = []
    written = 0
    skipped = 0

    for feat in layer.getFeatures(req):
        geom = feat.geometry()
        if geom is None or geom.isEmpty():
            skipped += 1
            continue

        geom2 = QgsGeometry(geom)
        if xform is not None:
            try:
                if geom2.transform(xform) != 0:
                    skipped += 1
                    continue
            except Exception:
                skipped += 1
                continue

        kml_geom = _geometry_to_kml(geom2)
        if not kml_geom:
            skipped += 1
            continue

        if title_idx >= 0:
            name = _xml_text(feat.attribute(title_idx)) or f"fid_{feat.id()}"
        else:
            name = f"fid_{feat.id()}"

        desc_rows = []
        for fname, idx in desc_indices:
            text = _xml_text(feat.attribute(idx)).replace("]]>", "]]&gt;")
            desc_rows.append(f"<tr><th>{escape(fname)}</th><td>{text}</td></tr>")
        if desc_rows:
            description = (
                "<![CDATA[<table border='1' cellpadding='3'>"
                + "".join(desc_rows)
                + "</table>]]>"
            )
        else:
            description = ""

        style_id = styles.style_for(feat) if styles is not None else None
        pm = (
            "<Placemark>"
            f"<name>{name}</name>"
            + (f"<description>{description}</description>" if description else "")
            + (f"<styleUrl>#{style_id}</styleUrl>" if style_id else "")
            + kml_geom
            + "</Placemark>"
        )
        placemarks.append(pm)
        written += 1

    layer_name = _xml_text(layer.name()) or "layer"
    kml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<kml xmlns="http://www.opengis.net/kml/2.2">\n'
        "<Document>\n"
        f"<name>{layer_name}</name>\n"
        + (styles.styles_xml() if styles is not None else "")
        + "\n".join(placemarks)
        + "\n</Document>\n</kml>\n"
    )

    out_dir = os.path.dirname(output_path)
    if out_dir and not os.path.isdir(out_dir):
        os.makedirs(out_dir)

    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("doc.kml", kml.encode("utf-8"))

    return written, skipped

# -*- coding: utf-8 -*-
from ...i18n import tr
"""Shared vector layer helpers."""

from qgis.core import QgsMapLayerType, QgsProject, QgsWkbTypes

FILTER_ALL = "all"
FILTER_POINT = "point"
FILTER_LINE = "line"
FILTER_POLYGON = "polygon"

FILTER_LABELS = {
    FILTER_ALL: "全部",
    FILTER_POINT: "仅点",
    FILTER_LINE: "仅线",
    FILTER_POLYGON: "仅面",
}


def layer_geometry_kind(layer):
    gtype = QgsWkbTypes.geometryType(layer.wkbType())
    if gtype == QgsWkbTypes.GeometryType.PointGeometry:
        return FILTER_POINT
    if gtype == QgsWkbTypes.GeometryType.LineGeometry:
        return FILTER_LINE
    if gtype == QgsWkbTypes.GeometryType.PolygonGeometry:
        return FILTER_POLYGON
    return FILTER_ALL


def layer_matches_filter(layer, filter_mode):
    if filter_mode == FILTER_ALL:
        return True
    return layer_geometry_kind(layer) == filter_mode


def layer_display_label(layer):
    kind = tr(FILTER_LABELS.get(layer_geometry_kind(layer), "未知"))
    return "{} [{} / {}]".format(
        layer.name(),
        QgsWkbTypes.displayString(layer.wkbType()),
        kind,
    )


def field_type_label(field):
    type_name = field.typeName() or "?"
    length_part = ""
    upper = (field.typeName() or "").upper()
    if field.length() > 0 and upper in ("STRING", "TEXT", "VARCHAR"):
        length_part = "({})".format(field.length())
    return "{}{}".format(type_name, length_part)


def list_vector_layers(filter_mode=FILTER_ALL, extra_layers=None):
    layers = []
    seen = set()

    for layer in QgsProject.instance().mapLayers().values():
        if layer.type() != QgsMapLayerType.VectorLayer:
            continue
        if layer.id() in seen:
            continue
        if layer_matches_filter(layer, filter_mode):
            layers.append(layer)
            seen.add(layer.id())

    if extra_layers:
        for layer in extra_layers:
            if layer is None or layer.id() in seen:
                continue
            if layer.type() != QgsMapLayerType.VectorLayer:
                continue
            if layer_matches_filter(layer, filter_mode):
                layers.append(layer)
                seen.add(layer.id())

    return sorted(layers, key=lambda lyr: lyr.name().lower())

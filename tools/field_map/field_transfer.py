# -*- coding: utf-8 -*-
from ...i18n import tr
"""Core feature transfer logic with field mapping and type coercion."""

import re

from qgis.PyQt.QtCore import QVariant, NULL
from qgis.core import (
    QgsFeature,
    QgsFeatureRequest,
    QgsGeometry,
    QgsCoordinateTransform,
    QgsProject,
    QgsWkbTypes,
    QgsMessageLog,
    Qgis,
)

LOG_TAG = "字段备注表"
_FIELD_SEP_RE = re.compile(r"[\s_\-]+")


def _log(message, level=Qgis.Info):
    QgsMessageLog.logMessage(message, LOG_TAG, level)


def normalize_field_name(name):
    return _FIELD_SEP_RE.sub("", (name or "").strip().casefold())


def _name_strong_enough(text):
    if not text:
        return False
    cjk = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
    if cjk:
        return len(text) >= 2
    return len(text) >= 3


def _unique_assign(left_names, right_names, pred):
    """Assign left→right only when each side has exactly one remaining candidate."""
    left_cands = {}
    for left in left_names:
        left_cands[left] = [right for right in right_names if pred(left, right)]
    assigned = {}
    for left, cands in left_cands.items():
        if len(cands) != 1:
            continue
        right = cands[0]
        owners = [name for name, cs in left_cands.items() if right in cs]
        if len(owners) == 1:
            assigned[left] = right
    return assigned


def auto_match_target_to_source(target_names, source_names, fuzzy=True):
    """Return dict target_name -> source_name. Auto-match is one-to-one."""
    used_targets = set()
    used_sources = set()
    result = {}

    def remaining_targets():
        return [name for name in target_names if name and name not in used_targets]

    def remaining_sources():
        return [name for name in source_names if name and name not in used_sources]

    def take(mapping):
        for target, source in mapping.items():
            if target in used_targets or source in used_sources:
                continue
            used_targets.add(target)
            used_sources.add(source)
            result[target] = source

    exact = {}
    for target in remaining_targets():
        for source in remaining_sources():
            if target == source and source not in exact.values():
                exact[target] = source
                break
    take(exact)

    take(_unique_assign(
        remaining_targets(),
        remaining_sources(),
        lambda target, source: target.casefold() == source.casefold(),
    ))

    if not fuzzy:
        return result

    take(_unique_assign(
        remaining_targets(),
        remaining_sources(),
        lambda target, source: bool(normalize_field_name(target))
        and normalize_field_name(target) == normalize_field_name(source),
    ))

    def pred_contains(target, source):
        left = normalize_field_name(target)
        right = normalize_field_name(source)
        if not left or not right or left == right:
            return False
        shorter, longer = (left, right) if len(left) <= len(right) else (right, left)
        if not _name_strong_enough(shorter):
            return False
        return shorter in longer

    take(_unique_assign(remaining_targets(), remaining_sources(), pred_contains))
    return result


def value_has_content(value):
    if value is None or value is NULL:
        return False
    if isinstance(value, QVariant):
        if value.isNull():
            return False
        value = value.value()
        if value is None or value is NULL:
            return False
    if isinstance(value, str) and not value.strip():
        return False
    return True


def field_fill_stats(layer):
    """Return {field_name: (filled_count, total_count)} for a vector layer."""
    if layer is None:
        return {}
    names = [field.name() for field in layer.fields()]
    if not names:
        return {}
    filled = [0] * len(names)
    total = 0
    request = QgsFeatureRequest().setFlags(QgsFeatureRequest.NoGeometry)
    request.setSubsetOfAttributes(list(range(len(names))))
    for feature in layer.getFeatures(request):
        total += 1
        for index in range(len(names)):
            if value_has_content(feature.attribute(index)):
                filled[index] += 1
    return {names[index]: (filled[index], total) for index in range(len(names))}


def geometry_type_label(layer):
    return QgsWkbTypes.displayString(layer.wkbType())


def geometry_types_compatible(source_layer, target_layer):
    """Allow same geometry type, or generic geometry vs specific."""
    src = QgsWkbTypes.geometryType(source_layer.wkbType())
    tgt = QgsWkbTypes.geometryType(target_layer.wkbType())
    if src == tgt:
        return True
    return src == QgsWkbTypes.GeometryType.UnknownGeometry or tgt == QgsWkbTypes.GeometryType.UnknownGeometry


def coerce_value(value, target_field):
    """Convert a QVariant value to something assignable to target_field."""
    if value is NULL or value is None:
        return NULL

    target_type = target_field.type()

    try:
        if target_type in (
            QVariant.Int,
            QVariant.UInt,
            QVariant.LongLong,
            QVariant.ULongLong,
        ):
            if isinstance(value, bool):
                return int(value)
            if isinstance(value, (int, float)):
                return int(value)
            text = str(value).strip()
            if text == "":
                return NULL
            if "." in text:
                return int(float(text))
            return int(text)

        if target_type == QVariant.Double:
            if isinstance(value, bool):
                return float(int(value))
            if isinstance(value, (int, float)):
                return float(value)
            text = str(value).strip()
            if text == "":
                return NULL
            return float(text)

        if target_type == QVariant.String:
            if value is NULL or value is None:
                return NULL
            return str(value)

        if target_type == QVariant.Bool:
            if isinstance(value, bool):
                return value
            if isinstance(value, (int, float)):
                return bool(value)
            text = str(value).strip().lower()
            if text in ("1", "true", "yes", "y", tr("是")):
                return True
            if text in ("0", "false", "no", "n", tr("否"), ""):
                return False
            return bool(value)

        return value
    except (TypeError, ValueError, OverflowError):
        return NULL


def transform_geometry(geometry, source_crs, target_crs):
    if geometry is None or geometry.isEmpty():
        return geometry
    if source_crs == target_crs:
        return QgsGeometry(geometry)
    transform = QgsCoordinateTransform(
        source_crs, target_crs, QgsProject.instance()
    )
    geom = QgsGeometry(geometry)
    geom.transform(transform)
    return geom


def build_field_mapping(target_fields, mapping_by_target_name):
    """
    mapping_by_target_name: dict target_field_name -> source_field_name or ''/None
    Returns list of (target_index, source_field_name) for active mappings.
    """
    result = []
    for idx, field in enumerate(target_fields):
        source_name = mapping_by_target_name.get(field.name())
        if source_name:
            result.append((idx, source_name))
    return result


def transfer_features(
    source_layer,
    target_layer,
    mapping_by_target_name,
    only_selected=False,
    reproject=True,
):
    """
    Copy features from source_layer to target_layer using field mapping.

    Returns dict with keys: success, copied, skipped, errors (list of str)
    """
    result = {
        "success": False,
        "copied": 0,
        "skipped": 0,
        "errors": [],
    }

    if source_layer is None or target_layer is None:
        result["errors"].append(tr("源图层或目标图层未选择。"))
        return result

    if source_layer.id() == target_layer.id():
        result["errors"].append(tr("源图层与目标图层不能是同一个。"))
        return result

    if not geometry_types_compatible(source_layer, target_layer):
        result["errors"].append(
            tr("几何类型不兼容：源={}，目标={}。").format(
                geometry_type_label(source_layer),
                geometry_type_label(target_layer),
            )
        )
        return result

    source_fields = source_layer.fields()
    target_fields = target_layer.fields()
    active_mappings = build_field_mapping(target_fields, mapping_by_target_name)

    if only_selected:
        features = list(source_layer.getSelectedFeatures())
        if not features:
            result["errors"].append(tr("源图层没有选中的要素。"))
            return result
    else:
        features = list(source_layer.getFeatures())

    if not features:
        result["errors"].append(tr("源图层没有可复制的要素。"))
        return result

    if not target_layer.isEditable():
        if not target_layer.startEditing():
            result["errors"].append(tr("无法开启目标图层编辑模式，请检查图层是否只读。"))
            return result

    source_crs = source_layer.crs()
    target_crs = target_layer.crs()
    need_reproject = reproject and source_crs != target_crs

    new_features = []
    for src_feat in features:
        geom = src_feat.geometry()
        if geom is None or geom.isEmpty():
            result["skipped"] += 1
            continue

        if need_reproject:
            geom = transform_geometry(geom, source_crs, target_crs)

        dst_feat = QgsFeature(target_fields)
        dst_feat.setGeometry(geom)

        attrs = [NULL] * len(target_fields)
        for tgt_idx, src_name in active_mappings:
            src_idx = source_fields.indexFromName(src_name)
            if src_idx < 0:
                continue
            raw = src_feat.attribute(src_idx)
            attrs[tgt_idx] = coerce_value(raw, target_fields.at(tgt_idx))

        dst_feat.setAttributes(attrs)
        new_features.append(dst_feat)

    if not new_features:
        result["errors"].append(tr("没有有效几何的要素可复制（可能全部被跳过）。"))
        return result

    ok, added = target_layer.dataProvider().addFeatures(new_features)
    if not ok:
        target_layer.rollBack()
        result["errors"].append(tr("写入目标图层失败，已回滚。"))
        return result

    target_layer.updateExtents()
    target_layer.triggerRepaint()

    result["success"] = True
    result["copied"] = len(added) if added else len(new_features)
    result["skipped"] = len(features) - result["copied"]

    _log(
        tr("复制完成：{} 条写入「{}」，跳过 {} 条。").format(
            result["copied"], target_layer.name(), result["skipped"]
        )
    )
    return result
